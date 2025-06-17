"""
Knowledge API Server - Phase 0.3: Basic Operations
FastAPI server with document ingestion and query functionality
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, UploadFile, File
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import gpt_4o_mini_complete, gpt_4o_complete, openai_complete, openai_embed
from lightrag.kg.shared_storage import initialize_pipeline_status
from lightrag.base import DocStatus
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List, Any, Callable
import requests
from urllib.parse import urlparse
import json
import re
import os
import logging
import sys
import hashlib
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

def configure_lightrag_logging():
    """Configure LightRAG logger to output to console"""
    try:
        from lightrag.utils import logger as lightrag_logger
        
        # Remove existing handlers to avoid duplicates
        lightrag_logger.handlers = []
        
        # Create console handler
        console_handler = logging.StreamHandler()
        
        # Get log level from environment or default to INFO
        lightrag_log_level = os.getenv("LIGHTRAG_LOG_LEVEL", "INFO").upper()
        log_level = getattr(logging, lightrag_log_level, logging.INFO)
        console_handler.setLevel(log_level)
        
        # Use same format as our application
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        
        # Add handler to LightRAG logger
        lightrag_logger.addHandler(console_handler)
        lightrag_logger.setLevel(log_level)
        
        # Also configure related loggers
        for logger_name in ["lightrag.kg.shared_storage", "lightrag.operate", "lightrag.lightrag"]:
            sub_logger = logging.getLogger(logger_name)
            sub_logger.handlers = []
            sub_logger.addHandler(console_handler)
            sub_logger.setLevel(log_level)
            sub_logger.propagate = False
        
        logger.info(f"LightRAG logging configured with level: {lightrag_log_level}")
    except ImportError as e:
        logger.warning(f"Could not import LightRAG logger: {e}")

# Configuration
PORT = int(os.getenv("KNOWLEDGE_SERVICE_PORT", "8004"))
KNOWLEDGE_DIR = Path(os.getenv("KNOWLEDGE_DIR", "./knowledge_base"))

# LightRAG configuration from environment
LIGHTRAG_CONFIG = {
    "working_dir": str(KNOWLEDGE_DIR),
    "llm_model_name": os.getenv("LIGHTRAG_LLM_MODEL", "gpt-4o-mini"),
    "llm_model_max_token_size": int(os.getenv("LIGHTRAG_MAX_TOKENS", "32768")),
    "llm_model_max_async": int(os.getenv("LIGHTRAG_MAX_ASYNC", "4")),
    "chunk_token_size": int(os.getenv("LIGHTRAG_CHUNK_SIZE", "1200")),
    "chunk_overlap_token_size": int(os.getenv("LIGHTRAG_CHUNK_OVERLAP_SIZE", "100")),
    "embedding_batch_num": int(os.getenv("LIGHTRAG_EMBEDDING_BATCH_NUM", "32")),
    "embedding_func_max_async": int(os.getenv("LIGHTRAG_EMBEDDING_FUNC_MAX_ASYNC", "16")),
    "summary_to_max_tokens": int(os.getenv("LIGHTRAG_MAX_TOKEN_SUMMARY", "1000")),
    "force_llm_summary_on_merge": int(os.getenv("LIGHTRAG_FORCE_LLM_SUMMARY_ON_MERGE", "1")),
}

# Backwards compatibility
BASE_CONFIG = LIGHTRAG_CONFIG

# Model function mapping
MODEL_FUNCTIONS = {
    "gpt-4o-mini": gpt_4o_mini_complete,
    "gpt-4o": gpt_4o_complete,
    # For o1/o3 models or any other OpenAI model, use the generic openai_complete
    "default": openai_complete,
}

def get_llm_model_func(model_name: str) -> Callable:
    """Get the appropriate LLM function for the given model name"""
    # Check if we have a specific function for this model
    if model_name in MODEL_FUNCTIONS:
        logger.info(f"Using specific function for model: {model_name}")
        return MODEL_FUNCTIONS[model_name]
    
    # For any other model (including o1/o3), use the generic openai_complete
    logger.info(f"Using generic OpenAI function for model: {model_name}")
    
    # Create a partial function that includes the model name
    from functools import partial
    return partial(openai_complete, hashing_kv={"global_config": {"llm_model_name": model_name}})

def get_embedding_func(model_name: str) -> Callable:
    """Get the embedding function with the specified model"""
    from functools import partial
    from lightrag.utils import wrap_embedding_func_with_attrs
    
    # Configure custom base URL if provided
    base_url = os.getenv("OPENAI_API_BASE")
    
    logger.info(f"Using embedding model: {model_name}")
    
    # Define embedding dimensions for known models
    embedding_dims = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }
    
    # Get embedding dimension for the model
    embedding_dim = embedding_dims.get(model_name, 1536)  # Default to 1536
    
    # Create the embedding function
    if base_url:
        embed_func = partial(openai_embed, model=model_name, base_url=base_url)
    else:
        embed_func = partial(openai_embed, model=model_name)
    
    # Wrap with required attributes
    return wrap_embedding_func_with_attrs(
        embedding_dim=embedding_dim,
        max_token_size=8192  # OpenAI's typical max tokens for embedding models
    )(embed_func)

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
        
        # Get the model function based on configuration
        model_name = LIGHTRAG_CONFIG["llm_model_name"]
        llm_func = get_llm_model_func(model_name)
        
        # Get the embedding function based on configuration
        embedding_model = os.getenv("LIGHTRAG_EMBEDDING_MODEL", "text-embedding-3-small")
        embedding_func = get_embedding_func(embedding_model)
        
        lightrag_instances[namespace_id] = LightRAG(
            **BASE_CONFIG,
            namespace_prefix=namespace_id,
            embedding_func=embedding_func,
            llm_model_func=llm_func
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
    
    # Configure LightRAG logging
    configure_lightrag_logging()

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

def is_document_stuck(doc: Any, status: str) -> bool:
    """Determine if a document is stuck based on its status and time"""
    from datetime import datetime, timezone, timedelta
    
    if not hasattr(doc, 'updated_at') or not doc.updated_at:
        return False
    
    try:
        # Parse the updated_at timestamp
        if isinstance(doc.updated_at, str):
            # Handle ISO format timestamps
            if doc.updated_at.endswith('Z'):
                doc_time = datetime.fromisoformat(doc.updated_at.replace('Z', '+00:00'))
            else:
                doc_time = datetime.fromisoformat(doc.updated_at)
        else:
            return False
            
        # Ensure timezone awareness
        if doc_time.tzinfo is None:
            doc_time = doc_time.replace(tzinfo=timezone.utc)
            
        current_time = datetime.now(timezone.utc)
        time_diff = current_time - doc_time
        
        # Define stuck thresholds
        if status == "processing":
            # Documents processing for more than 5 minutes are considered stuck
            return time_diff > timedelta(minutes=5)
        elif status == "pending":
            # Documents pending for more than 10 minutes are considered stuck
            return time_diff > timedelta(minutes=10)
            
    except Exception as e:
        logger.warning(f"Error checking if document is stuck: {e}")
        
    return False

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
            
            # Count stuck documents
            stuck_processing = sum(1 for doc in processing_docs.values() if is_document_stuck(doc, "processing"))
            stuck_pending = sum(1 for doc in pending_docs.values() if is_document_stuck(doc, "pending"))
            stuck_count = stuck_processing + stuck_pending
            
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
                "pending_count": status_counts["pending"] + status_counts["processing"],
                "stuck_count": stuck_count,
                "stuck_processing": stuck_processing,
                "stuck_pending": stuck_pending
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
            "pending_count": 0,
            "stuck_count": 0,
            "stuck_processing": 0,
            "stuck_pending": 0
        }

# Background processing functions
async def process_document_in_background(
    namespace_id: str, 
    content: str, 
    doc_id: str,
    metadata: Dict[str, Any]
):
    """Process a document in the background"""
    try:
        async with get_lightrag_instance(namespace_id) as rag:
            await rag.ainsert(content)
            logger.info(f"Background: Processed document {doc_id} in namespace '{namespace_id}': {len(content)} chars")
    except Exception as e:
        logger.error(f"Background: Failed to process document {doc_id} in namespace '{namespace_id}': {str(e)}")
        # Document will remain in PENDING/FAILED state for retry

async def process_file_in_background(
    namespace_id: str,
    text_content: str,
    doc_id: str,
    filename: str,
    metadata: Dict[str, Any]
):
    """Process an uploaded file in the background"""
    try:
        async with get_lightrag_instance(namespace_id) as rag:
            await rag.ainsert(text_content)
            logger.info(f"Background: Processed file {filename} (ID: {doc_id}) in namespace '{namespace_id}'")
    except Exception as e:
        logger.error(f"Background: Failed to process file {filename} (ID: {doc_id}) in namespace '{namespace_id}': {str(e)}")

async def process_url_content_in_background(
    namespace_id: str,
    text_content: str,
    url: str,
    metadata: Dict[str, Any]
):
    """Process URL content in the background"""
    try:
        doc_id = f"doc-{hashlib.md5(text_content.encode()).hexdigest()}"
        async with get_lightrag_instance(namespace_id) as rag:
            await rag.ainsert(text_content)
            logger.info(f"Background: Processed URL content from {url} in namespace '{namespace_id}'")
    except Exception as e:
        logger.error(f"Background: Failed to process URL content from {url} in namespace '{namespace_id}': {str(e)}")

# Document operations
@app.post("/api/{namespace_id}/documents")
async def add_document(namespace_id: str, doc: Document, background_tasks: BackgroundTasks):
    """Add document to namespace (non-blocking)"""
    # Validate namespace exists
    if namespace_id not in namespace_registry.namespaces:
        raise HTTPException(status_code=404, detail=f"Namespace '{namespace_id}' not found")
    
    # Generate document ID upfront
    doc_id = f"doc-{hashlib.md5(doc.content.encode()).hexdigest()}"
    
    # Queue for background processing
    background_tasks.add_task(
        process_document_in_background,
        namespace_id,
        doc.content,
        doc_id,
        doc.metadata
    )
    
    logger.info(f"Queued document {doc_id} for processing in namespace '{namespace_id}': {len(doc.content)} chars")
    
    # Return immediately
    return {
        "message": "Document queued for processing",
        "status": "pending",
        "namespace": namespace_id,
        "document_id": doc_id,
        "content_length": len(doc.content),
        "metadata": doc.metadata
    }

# Phase 2.6: UI is now read-only. All data ingestion happens via CLI.
"""
@app.post("/api/{namespace_id}/documents/upload")
async def upload_document(namespace_id: str, file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    '''Upload single file to namespace (non-blocking)'''
    # Validate namespace exists
    if namespace_id not in namespace_registry.namespaces:
        raise HTTPException(status_code=404, detail=f"Namespace '{namespace_id}' not found")
    
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
    
    # Generate document ID from content hash
    doc_id = f"doc-{hashlib.md5(text_content.encode()).hexdigest()}"
    
    # Queue for background processing
    background_tasks.add_task(
        process_file_in_background,
        namespace_id,
        text_content,
        doc_id,
        file.filename,
        metadata
    )
    
    logger.info(f"Queued file {file.filename} (ID: {doc_id}) for processing in namespace '{namespace_id}'")
    
    # Return immediately
    return {
        "message": "File queued for processing",
        "status": "pending",
        "namespace": namespace_id,
        "document_id": doc_id,
        "filename": file.filename,
        "content_length": len(text_content),
        "metadata": metadata
    }
"""

"""
@app.post("/api/{namespace_id}/documents/batch-upload")
async def upload_documents_batch(namespace_id: str, files: List[UploadFile] = File(...), background_tasks: BackgroundTasks = None):
    '''Upload multiple files to namespace (non-blocking)'''
    # Validate namespace exists
    if namespace_id not in namespace_registry.namespaces:
        raise HTTPException(status_code=404, detail=f"Namespace '{namespace_id}' not found")
    
    results = []
    failed_files = []
    
    for file in files:
        # Validate file type
        if not is_supported_file(file.filename):
            failed_files.append({
                "filename": file.filename,
                "error": f"Unsupported file type",
                "status": "failed"
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
            
            # Generate document ID from content hash
            doc_id = f"doc-{hashlib.md5(text_content.encode()).hexdigest()}"
            
            # Queue for background processing
            background_tasks.add_task(
                process_file_in_background,
                namespace_id,
                text_content,
                doc_id,
                file.filename,
                metadata
            )
            
            results.append({
                "document_id": doc_id,
                "filename": file.filename,
                "content_length": len(text_content),
                "metadata": metadata,
                "status": "pending"
            })
            logger.info(f"Queued file {file.filename} (ID: {doc_id}) for batch processing in namespace '{namespace_id}'")
            
        except UnicodeDecodeError:
            failed_files.append({
                "filename": file.filename,
                "error": "File must be UTF-8 encoded text",
                "status": "failed"
            })
        except Exception as e:
            logger.error(f"Error processing file {file.filename}: {e}")
            failed_files.append({
                "filename": file.filename,
                "error": str(e),
                "status": "failed"
            })
    
    # Determine status
    total_files = len(files)
    queued_files = len(results)
    
    if queued_files == total_files:
        status = "success"
        message = f"All {total_files} files queued for processing"
    elif queued_files > 0:
        status = "partial_success"
        message = f"Queued {queued_files} out of {total_files} files"
    else:
        status = "failure"
        message = "No files were queued successfully"
    
    return {
        "status": status,
        "message": message,
        "namespace": namespace_id,
        "successful_uploads": results,
        "failed_uploads": failed_files,
        "uploaded": queued_files,
        "failed": len(failed_files)
    }
"""

"""
@app.post("/api/{namespace_id}/documents/url")
async def fetch_and_ingest_url(namespace_id: str, req: URLRequest, background_tasks: BackgroundTasks):
    '''Fetch content from URL and ingest it (non-blocking)'''
    # Validate namespace exists
    if namespace_id not in namespace_registry.namespaces:
        raise HTTPException(status_code=404, detail=f"Namespace '{namespace_id}' not found")
    
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
    
    # Fetch content from URL (synchronous to fail fast on bad URLs)
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
    
    # Generate document ID from content
    doc_id = f"doc-{hashlib.md5(text_content.encode()).hexdigest()}"
    
    # Queue for background processing
    background_tasks.add_task(
        process_url_content_in_background,
        namespace_id,
        text_content,
        req.url,
        metadata
    )
    
    logger.info(f"Queued URL content from {req.url} for processing in namespace '{namespace_id}'")
    
    # Return immediately
    return {
        "message": "URL content queued for processing",
        "status": "pending",
        "namespace": namespace_id,
        "document_id": doc_id,
        "url": req.url,
        "content_length": len(text_content),
        "metadata": metadata
    }
"""

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

@app.get("/api/namespaces/{namespace_id}/processing")
async def get_processing_status(namespace_id: str):
    """Get all documents currently being processed or failed"""
    if namespace_id not in namespace_registry.namespaces:
        raise HTTPException(status_code=404, detail=f"Namespace '{namespace_id}' not found")
    
    try:
        async with get_lightrag_instance(namespace_id) as rag:
            # Get documents by status
            pending_docs = await rag.get_docs_by_status(DocStatus.PENDING)
            processing_docs = await rag.get_docs_by_status(DocStatus.PROCESSING)
            failed_docs = await rag.get_docs_by_status(DocStatus.FAILED)
            
            # Format documents for response
            def format_doc(doc_id: str, doc: Any, status: str) -> Dict:
                return {
                    "id": doc_id,
                    "status": status,
                    "chunks_count": getattr(doc, 'chunks_count', 0),
                    "content_length": getattr(doc, 'content_length', 0),
                    "created_at": getattr(doc, 'created_at', None),
                    "updated_at": getattr(doc, 'updated_at', None),
                    "file_path": getattr(doc, 'file_path', 'unknown'),
                    "error": getattr(doc, 'error', None),
                    "content_summary": getattr(doc, 'content_summary', '')[:200]  # First 200 chars
                }
            
            # Collect all documents
            all_docs = []
            
            for doc_id, doc in pending_docs.items():
                all_docs.append(format_doc(doc_id, doc, "pending"))
            
            for doc_id, doc in processing_docs.items():
                all_docs.append(format_doc(doc_id, doc, "processing"))
                
            for doc_id, doc in failed_docs.items():
                all_docs.append(format_doc(doc_id, doc, "failed"))
            
            # Sort by updated_at (most recent first)
            all_docs.sort(key=lambda x: x['updated_at'] or x['created_at'] or '', reverse=True)
            
            return {
                "namespace_id": namespace_id,
                "total": len(all_docs),
                "pending": len(pending_docs),
                "processing": len(processing_docs),
                "failed": len(failed_docs),
                "documents": all_docs
            }
            
    except Exception as e:
        logger.error(f"Error getting processing status for namespace {namespace_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get processing status: {str(e)}")

@app.get("/api/namespaces/{namespace_id}/documents/{doc_id}")
async def get_document_status(namespace_id: str, doc_id: str):
    """Get detailed status for a specific document"""
    if namespace_id not in namespace_registry.namespaces:
        raise HTTPException(status_code=404, detail=f"Namespace '{namespace_id}' not found")
    
    try:
        async with get_lightrag_instance(namespace_id) as rag:
            # Check all statuses to find the document
            for status in [DocStatus.PENDING, DocStatus.PROCESSING, DocStatus.PROCESSED, DocStatus.FAILED]:
                docs = await rag.get_docs_by_status(status)
                if doc_id in docs:
                    doc = docs[doc_id]
                    return {
                        "id": doc_id,
                        "namespace_id": namespace_id,
                        "status": status.value,
                        "chunks_count": getattr(doc, 'chunks_count', 0),
                        "content_length": getattr(doc, 'content_length', 0),
                        "created_at": getattr(doc, 'created_at', None),
                        "updated_at": getattr(doc, 'updated_at', None),
                        "file_path": getattr(doc, 'file_path', 'unknown'),
                        "error": getattr(doc, 'error', None),
                        "content": getattr(doc, 'content', '')[:1000],  # First 1000 chars
                        "content_summary": getattr(doc, 'content_summary', '')
                    }
            
            raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document {doc_id} in namespace {namespace_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get document status: {str(e)}")

@app.get("/api/namespaces/{namespace_id}/stuck")
async def get_stuck_documents(namespace_id: str):
    """Get all stuck documents (processing > 5 min or pending > 10 min)"""
    if namespace_id not in namespace_registry.namespaces:
        raise HTTPException(status_code=404, detail=f"Namespace '{namespace_id}' not found")
    
    try:
        async with get_lightrag_instance(namespace_id) as rag:
            from datetime import datetime, timezone
            
            # Get documents by status
            pending_docs = await rag.get_docs_by_status(DocStatus.PENDING)
            processing_docs = await rag.get_docs_by_status(DocStatus.PROCESSING)
            
            current_time = datetime.now(timezone.utc)
            stuck_docs = []
            
            # Check processing documents
            for doc_id, doc in processing_docs.items():
                if is_document_stuck(doc, "processing"):
                    updated_at = getattr(doc, 'updated_at', None)
                    if updated_at:
                        try:
                            if updated_at.endswith('Z'):
                                doc_time = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                            else:
                                doc_time = datetime.fromisoformat(updated_at)
                            if doc_time.tzinfo is None:
                                doc_time = doc_time.replace(tzinfo=timezone.utc)
                            time_stuck = current_time - doc_time
                            minutes_stuck = int(time_stuck.total_seconds() / 60)
                        except:
                            minutes_stuck = 0
                    else:
                        minutes_stuck = 0
                        
                    stuck_docs.append({
                        "id": doc_id,
                        "status": "processing",
                        "file_path": getattr(doc, 'file_path', 'unknown'),
                        "updated_at": updated_at,
                        "minutes_stuck": minutes_stuck,
                        "content_summary": getattr(doc, 'content_summary', '')[:200]
                    })
            
            # Check pending documents
            for doc_id, doc in pending_docs.items():
                if is_document_stuck(doc, "pending"):
                    updated_at = getattr(doc, 'updated_at', None)
                    if updated_at:
                        try:
                            if updated_at.endswith('Z'):
                                doc_time = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                            else:
                                doc_time = datetime.fromisoformat(updated_at)
                            if doc_time.tzinfo is None:
                                doc_time = doc_time.replace(tzinfo=timezone.utc)
                            time_stuck = current_time - doc_time
                            minutes_stuck = int(time_stuck.total_seconds() / 60)
                        except:
                            minutes_stuck = 0
                    else:
                        minutes_stuck = 0
                        
                    stuck_docs.append({
                        "id": doc_id,
                        "status": "pending",
                        "file_path": getattr(doc, 'file_path', 'unknown'),
                        "updated_at": updated_at,
                        "minutes_stuck": minutes_stuck,
                        "content_summary": getattr(doc, 'content_summary', '')[:200]
                    })
            
            # Sort by minutes stuck (most stuck first)
            stuck_docs.sort(key=lambda x: x['minutes_stuck'], reverse=True)
            
            return {
                "namespace_id": namespace_id,
                "total_stuck": len(stuck_docs),
                "stuck_processing": len([d for d in stuck_docs if d['status'] == 'processing']),
                "stuck_pending": len([d for d in stuck_docs if d['status'] == 'pending']),
                "documents": stuck_docs
            }
            
    except Exception as e:
        logger.error(f"Error getting stuck documents for namespace {namespace_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stuck documents: {str(e)}")

@app.post("/api/namespaces/{namespace_id}/retry-stuck")
async def retry_stuck_documents(namespace_id: str):
    """Retry all stuck documents by triggering the processing pipeline"""
    if namespace_id not in namespace_registry.namespaces:
        raise HTTPException(status_code=404, detail=f"Namespace '{namespace_id}' not found")
    
    try:
        async with get_lightrag_instance(namespace_id) as rag:
            # Simply trigger the pipeline - it will automatically pick up
            # any PROCESSING, FAILED, and PENDING documents
            logger.info(f"Triggering retry for stuck documents in namespace: {namespace_id}")
            await rag.apipeline_process_enqueue_documents()
        
        return {
            "status": "success",
            "message": "Reprocessing triggered for stuck documents",
            "namespace_id": namespace_id
        }
    except Exception as e:
        logger.error(f"Error triggering retry for namespace {namespace_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger retry: {str(e)}")

@app.get("/api/namespaces/{namespace_id}/recent")
async def get_recent_activity(
    namespace_id: str,
    hours: int = Query(default=24, ge=1, le=168, description="Hours to look back (1-168)")
):
    """Get recently processed documents (both successful and failed)"""
    if namespace_id not in namespace_registry.namespaces:
        raise HTTPException(status_code=404, detail=f"Namespace '{namespace_id}' not found")
    
    try:
        async with get_lightrag_instance(namespace_id) as rag:
            # Get processed and failed documents
            processed_docs = await rag.get_docs_by_status(DocStatus.PROCESSED)
            failed_docs = await rag.get_docs_by_status(DocStatus.FAILED)
            
            # Calculate cutoff time
            from datetime import datetime, timedelta, timezone
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            cutoff_str = cutoff_time.isoformat()
            
            # Collect recent documents
            recent_docs = []
            
            for doc_id, doc in processed_docs.items():
                updated_at = getattr(doc, 'updated_at', None)
                if updated_at and updated_at > cutoff_str:
                    recent_docs.append({
                        "id": doc_id,
                        "status": "processed",
                        "chunks_count": getattr(doc, 'chunks_count', 0),
                        "content_length": getattr(doc, 'content_length', 0),
                        "updated_at": updated_at,
                        "file_path": getattr(doc, 'file_path', 'unknown'),
                        "content_summary": getattr(doc, 'content_summary', '')[:200]
                    })
            
            for doc_id, doc in failed_docs.items():
                updated_at = getattr(doc, 'updated_at', None)
                if updated_at and updated_at > cutoff_str:
                    recent_docs.append({
                        "id": doc_id,
                        "status": "failed",
                        "chunks_count": 0,
                        "content_length": getattr(doc, 'content_length', 0),
                        "updated_at": updated_at,
                        "file_path": getattr(doc, 'file_path', 'unknown'),
                        "error": getattr(doc, 'error', None),
                        "content_summary": getattr(doc, 'content_summary', '')[:200]
                    })
            
            # Sort by updated_at (most recent first)
            recent_docs.sort(key=lambda x: x['updated_at'], reverse=True)
            
            return {
                "namespace_id": namespace_id,
                "hours": hours,
                "cutoff_time": cutoff_str,
                "total": len(recent_docs),
                "processed": len([d for d in recent_docs if d['status'] == 'processed']),
                "failed": len([d for d in recent_docs if d['status'] == 'failed']),
                "documents": recent_docs
            }
            
    except Exception as e:
        logger.error(f"Error getting recent activity for namespace {namespace_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get recent activity: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "gateway.main:app",
        host="0.0.0.0",
        port=PORT,
        reload=True,
        log_level="info"
    )