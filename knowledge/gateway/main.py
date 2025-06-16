"""
Knowledge API Server - Phase 0.3: Basic Operations
FastAPI server with document ingestion and query functionality
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, UploadFile, File
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import gpt_4o_mini_complete, openai_embed
from lightrag.kg.shared_storage import initialize_pipeline_status
from lightrag.base import DocStatus
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List, Any
import aiofiles
import requests
from urllib.parse import urlparse
import json
import re
import os
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from gateway.preprocessing import ContentPreprocessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
PORT = int(os.getenv("KNOWLEDGE_SERVICE_PORT", "8004"))
KNOWLEDGE_DIR = Path(os.getenv("KNOWLEDGE_DIR", "./knowledge_base"))
BASE_CONFIG = {
    "working_dir": str(KNOWLEDGE_DIR),
    "llm_model_name": os.getenv("LLM_MODEL", "gpt-4o-mini"),
}

# Supported file extensions for Phase 1.1
SUPPORTED_FILE_EXTENSIONS = {".txt", ".md", ".json"}

def is_supported_file(filename: str) -> bool:
    """Check if file extension is supported"""
    return any(filename.lower().endswith(ext) for ext in SUPPORTED_FILE_EXTENSIONS)

# Initialize preprocessor
preprocessor = ContentPreprocessor()

# Models
class NamespaceConfig(BaseModel):
    name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="Namespace description")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class Document(BaseModel):
    content: str
    metadata: Dict[str, str] = Field(default_factory=dict)

class QueryRequest(BaseModel):
    query: str
    mode: str = Field(default="hybrid", description="Query mode: naive, local, global, hybrid")

class URLRequest(BaseModel):
    url: str = Field(..., description="URL to fetch content from")
    metadata: Dict[str, str] = Field(default_factory=dict, description="Additional metadata")

# Dynamic Namespace Registry
class NamespaceRegistry:
    def __init__(self, storage_path: Path = KNOWLEDGE_DIR / "namespace_registry.json"):
        self.storage_path = storage_path
        self.namespaces: Dict[str, NamespaceConfig] = {}
        self._load_from_disk()
    
    def _load_from_disk(self):
        """Load namespace registry from persistent storage"""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if self.storage_path.exists():
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                self.namespaces = {
                    k: NamespaceConfig(**v) for k, v in data.items()
                }
            logger.info(f"Loaded {len(self.namespaces)} namespaces from disk")
    
    def _save_to_disk(self):
        """Persist namespace registry to disk"""
        with open(self.storage_path, 'w') as f:
            data = {k: v.dict() for k, v in self.namespaces.items()}
            json.dump(data, f, indent=2)
        logger.info("Namespace registry saved to disk")
    
    def create_namespace(self, namespace_id: str, config: NamespaceConfig) -> bool:
        """Create a new namespace"""
        # Validate namespace ID format
        if not re.match(r'^[a-z0-9_]+$', namespace_id):
            raise ValueError("Namespace ID must contain only lowercase letters, numbers, and underscores")
        
        if namespace_id in self.namespaces:
            return False
        
        self.namespaces[namespace_id] = config
        self._save_to_disk()
        logger.info(f"Created namespace: {namespace_id}")
        return True
    
    def delete_namespace(self, namespace_id: str) -> bool:
        """Delete a namespace"""
        if namespace_id not in self.namespaces:
            return False
        
        del self.namespaces[namespace_id]
        self._save_to_disk()
        
        # TODO: Clean up namespace data from LightRAG storage
        logger.info(f"Deleted namespace: {namespace_id}")
        return True
    
    def get_namespace(self, namespace_id: str) -> Optional[NamespaceConfig]:
        """Get namespace configuration"""
        return self.namespaces.get(namespace_id)
    
    def list_namespaces(self) -> Dict[str, NamespaceConfig]:
        """List all namespaces"""
        return self.namespaces.copy()

# Initialize registry
namespace_registry = NamespaceRegistry()

# LightRAG instance cache
lightrag_instances: Dict[str, LightRAG] = {}
_pipeline_initialized = False

@asynccontextmanager
async def get_lightrag_instance(namespace_id: str):
    """Get or create a LightRAG instance for the namespace"""
    if namespace_id not in namespace_registry.namespaces:
        raise HTTPException(status_code=404, detail=f"Namespace '{namespace_id}' not found")
    
    global _pipeline_initialized
    
    # Cache instances to avoid recreation
    if namespace_id not in lightrag_instances:
        logger.info(f"Creating LightRAG instance for namespace: {namespace_id}")
        lightrag_instances[namespace_id] = LightRAG(
            **BASE_CONFIG,
            namespace_prefix=namespace_id,
            embedding_func=openai_embed,
            llm_model_func=gpt_4o_mini_complete
        )
        # Initialize storages for the new instance
        await lightrag_instances[namespace_id].initialize_storages()
        logger.info(f"Initialized storages for namespace: {namespace_id}")
        
        # Initialize pipeline status once globally after first instance
        if not _pipeline_initialized:
            await initialize_pipeline_status()
            _pipeline_initialized = True
            logger.info("Initialized global pipeline status")
    
    yield lightrag_instances[namespace_id]

# Create FastAPI app
app = FastAPI(
    title="Knowledge API",
    description="LightRAG-based knowledge management system for HireCJ",
    version="0.3.0"
)

@app.on_event("startup")
async def startup_event():
    """Log startup information"""
    logger.info(f"Knowledge API starting on port {PORT}")
    logger.info("Phase 0.3: Basic Operations")
    logger.info(f"Working directory: {KNOWLEDGE_DIR}")
    logger.info(f"Loaded {len(namespace_registry.namespaces)} namespaces")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    logger.info("Shutting down Knowledge API...")
    
    # Finalize all LightRAG instances
    for namespace_id, rag in lightrag_instances.items():
        try:
            await rag.finalize_storages()
            logger.info(f"Finalized storages for namespace: {namespace_id}")
        except Exception as e:
            logger.error(f"Error finalizing namespace {namespace_id}: {e}")
    
    logger.info("Knowledge API shutdown complete")

@app.get("/health")
async def health():
    """API health check endpoint"""
    return {
        "status": "healthy",
        "port": PORT,
        "message": "Knowledge API is running",
        "version": "0.3.0",
        "phase": "0.3",
        "namespaces_count": len(namespace_registry.namespaces),
        "working_dir": str(KNOWLEDGE_DIR)
    }

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "Knowledge API",
        "description": "LightRAG-based knowledge management system",
        "health_check": "/health",
        "docs": "/docs",
        "namespaces": "/api/namespaces"
    }

# Namespace CRUD endpoints
@app.post("/api/namespaces")
async def create_namespace(
    namespace_id: str = Query(..., regex="^[a-z0-9_]+$", description="Namespace identifier"),
    config: NamespaceConfig = ...
):
    """Create a new namespace"""
    try:
        created = namespace_registry.create_namespace(namespace_id, config)
        if not created:
            raise HTTPException(status_code=409, detail="Namespace already exists")
        
        return {
            "namespace_id": namespace_id,
            "config": config.dict(),
            "message": f"Namespace '{namespace_id}' created successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/namespaces")
async def list_namespaces():
    """List all namespaces"""
    namespaces = namespace_registry.list_namespaces()
    return {
        "namespaces": [
            {"id": k, **v.dict()} 
            for k, v in namespaces.items()
        ],
        "count": len(namespaces)
    }

@app.get("/api/namespaces/{namespace_id}")
async def get_namespace(namespace_id: str):
    """Get a specific namespace"""
    namespace_config = namespace_registry.get_namespace(namespace_id)
    if not namespace_config:
        raise HTTPException(status_code=404, detail=f"Namespace '{namespace_id}' not found")
    
    return {
        "id": namespace_id,
        **namespace_config.dict()
    }

@app.delete("/api/namespaces/{namespace_id}")
async def delete_namespace(namespace_id: str):
    """Delete a namespace"""
    deleted = namespace_registry.delete_namespace(namespace_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Namespace '{namespace_id}' not found")
    
    # Remove cached LightRAG instance
    if namespace_id in lightrag_instances:
        del lightrag_instances[namespace_id]
        logger.info(f"Removed cached LightRAG instance for namespace: {namespace_id}")
    
    return {
        "message": f"Namespace '{namespace_id}' deleted successfully"
    }

@app.get("/api/namespaces/{namespace_id}/statistics")
async def get_namespace_statistics(namespace_id: str):
    """Get statistics for a namespace using LightRAG's official API"""
    if namespace_id not in namespace_registry.namespaces:
        raise HTTPException(status_code=404, detail=f"Namespace '{namespace_id}' not found")
    
    try:
        async with get_lightrag_instance(namespace_id) as rag:
            # Get all documents by different statuses
            processed_docs = await rag.get_docs_by_status(DocStatus.PROCESSED)
            pending_docs = await rag.get_docs_by_status(DocStatus.PENDING)
            processing_docs = await rag.get_docs_by_status(DocStatus.PROCESSING)
            failed_docs = await rag.get_docs_by_status(DocStatus.FAILED)
            
            # Count documents by status
            status_counts = {
                "processed": len(processed_docs),
                "pending": len(pending_docs),
                "processing": len(processing_docs),
                "failed": len(failed_docs)
            }
            
            # Calculate statistics
            document_count = status_counts["processed"]
            total_chunks = sum(doc.chunks_count or 0 for doc in processed_docs.values())
            
            # Find most recent update
            last_updated = None
            if processed_docs:
                # Extract just the updated_at timestamps
                update_times = [doc.updated_at for doc in processed_docs.values() if doc.updated_at]
                if update_times:
                    last_updated = max(update_times)
            
            return {
                "namespace_id": namespace_id,
                "document_count": document_count,
                "last_updated": last_updated,
                "total_chunks": total_chunks,
                "status_breakdown": status_counts,
                "failed_count": status_counts["failed"],
                "pending_count": status_counts["pending"] + status_counts["processing"]
            }
    except Exception as e:
        logger.error(f"Error getting statistics for namespace {namespace_id}: {e}")
        # Return empty statistics if namespace has no data yet
        return {
            "namespace_id": namespace_id,
            "document_count": 0,
            "last_updated": None,
            "total_chunks": 0,
            "status_breakdown": {},
            "failed_count": 0,
            "pending_count": 0
        }

# Document operations
@app.post("/api/{namespace_id}/documents")
async def add_document(namespace_id: str, doc: Document):
    """Add document to namespace"""
    async with get_lightrag_instance(namespace_id) as rag:
        await rag.ainsert(doc.content)
        logger.info(f"Added document to namespace '{namespace_id}': {len(doc.content)} chars")
    
    return {
        "message": "Document added successfully",
        "namespace": namespace_id,
        "content_length": len(doc.content),
        "metadata": doc.metadata
    }

@app.post("/api/{namespace_id}/documents/upload")
async def upload_document(namespace_id: str, file: UploadFile = File(...)):
    """Upload single file to namespace"""
    # Validate file type
    if not is_supported_file(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Supported types: {', '.join(SUPPORTED_FILE_EXTENSIONS)}"
        )
    
    # Read file content
    try:
        content = await file.read()
        text_content = content.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="File must be UTF-8 encoded text"
        )
    except Exception as e:
        logger.error(f"Error reading file {file.filename}: {e}")
        raise HTTPException(status_code=500, detail="Error reading file")
    
    # Process content based on file type
    extra_metadata = {}
    if file.filename.lower().endswith('.json'):
        # Preprocess JSON file
        text_content, extra_metadata = preprocessor.preprocess_json_file(text_content)
    else:
        # Regular text preprocessing
        text_content = preprocessor.preprocess_text(text_content)
    
    # Extract metadata
    metadata = {
        "source": file.filename,
        "file_size": len(content),
        "upload_time": datetime.now().isoformat(),
        "file_type": file.content_type or "text/plain",
        **extra_metadata
    }
    
    # Ingest into LightRAG
    async with get_lightrag_instance(namespace_id) as rag:
        await rag.ainsert(text_content)
        logger.info(f"Uploaded file to namespace '{namespace_id}': {file.filename} ({len(content)} bytes)")
    
    return {
        "message": "File uploaded successfully",
        "namespace": namespace_id,
        "filename": file.filename,
        "content_length": len(text_content),
        "metadata": metadata
    }

@app.post("/api/{namespace_id}/documents/batch-upload")
async def upload_documents_batch(namespace_id: str, files: List[UploadFile] = File(...)):
    """Upload multiple files to namespace"""
    results = []
    failed_files = []
    
    for file in files:
        # Validate file type
        if not is_supported_file(file.filename):
            failed_files.append({
                "filename": file.filename,
                "error": f"Unsupported file type"
            })
            continue
        
        # Read and process file
        try:
            content = await file.read()
            text_content = content.decode('utf-8')
            
            # Process content based on file type
            extra_metadata = {}
            if file.filename.lower().endswith('.json'):
                # Preprocess JSON file
                text_content, extra_metadata = preprocessor.preprocess_json_file(text_content)
            else:
                # Regular text preprocessing
                text_content = preprocessor.preprocess_text(text_content)
            
            # Extract metadata
            metadata = {
                "source": file.filename,
                "file_size": len(content),
                "upload_time": datetime.now().isoformat(),
                "file_type": file.content_type or "text/plain",
                **extra_metadata
            }
            
            # Ingest into LightRAG
            async with get_lightrag_instance(namespace_id) as rag:
                await rag.ainsert(text_content)
            
            results.append({
                "filename": file.filename,
                "content_length": len(text_content),
                "metadata": metadata
            })
            logger.info(f"Uploaded file to namespace '{namespace_id}': {file.filename}")
            
        except UnicodeDecodeError:
            failed_files.append({
                "filename": file.filename,
                "error": "File must be UTF-8 encoded text"
            })
        except Exception as e:
            logger.error(f"Error processing file {file.filename}: {e}")
            failed_files.append({
                "filename": file.filename,
                "error": str(e)
            })
    
    # Determine status
    total_files = len(files)
    successful_files = len(results)
    
    if successful_files == total_files:
        status = "success"
        message = f"All {total_files} files uploaded successfully"
    elif successful_files > 0:
        status = "partial_success"
        message = f"Uploaded {successful_files} out of {total_files} files"
    else:
        status = "failure"
        message = "No files were uploaded successfully"
    
    return {
        "status": status,
        "message": message,
        "namespace": namespace_id,
        "successful_uploads": results,
        "failed_uploads": failed_files
    }

@app.post("/api/{namespace_id}/documents/url")
async def fetch_and_ingest_url(namespace_id: str, req: URLRequest):
    """Fetch content from URL and ingest it"""
    # Validate URL
    try:
        parsed = urlparse(req.url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Invalid URL format")
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid URL format"
        )
    
    # Fetch content from URL
    try:
        # Set reasonable timeout and headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; HireCJ Knowledge Bot/1.0)'
        }
        response = requests.get(req.url, timeout=30, headers=headers)
        response.raise_for_status()
        
        # Get content type
        content_type = response.headers.get('Content-Type', '')
        
        # Process content
        text_content, extracted_metadata = preprocessor.preprocess_url_content(
            response.text,
            req.url,
            content_type
        )
        
        # Combine metadata
        metadata = {
            **extracted_metadata,
            **req.metadata,
            "status_code": response.status_code,
            "content_length": len(response.content)
        }
        
    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="Timeout while fetching URL"
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching URL {req.url}: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Error fetching URL: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error processing URL content: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error processing URL content"
        )
    
    # Ingest into LightRAG
    async with get_lightrag_instance(namespace_id) as rag:
        await rag.ainsert(text_content)
        logger.info(f"Ingested URL content to namespace '{namespace_id}': {req.url}")
    
    return {
        "message": "URL content ingested successfully",
        "namespace": namespace_id,
        "url": req.url,
        "content_length": len(text_content),
        "metadata": metadata
    }

@app.post("/api/{namespace_id}/query")
async def query_knowledge(namespace_id: str, req: QueryRequest):
    """Query specific namespace"""
    async with get_lightrag_instance(namespace_id) as rag:
        logger.info(f"Querying namespace '{namespace_id}' with mode '{req.mode}': {req.query}")
        result = await rag.aquery(req.query, param=QueryParam(mode=req.mode))
    
    return {
        "namespace": namespace_id,
        "query": req.query,
        "result": result,
        "mode": req.mode
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "gateway.main:app",
        host="0.0.0.0",
        port=PORT,
        reload=True,
        log_level="info"
    )