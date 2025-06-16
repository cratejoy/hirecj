"""
Knowledge API Server - Phase 0.3: Basic Operations
FastAPI server with document ingestion and query functionality
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import gpt_4o_mini_complete, openai_embed
from lightrag.kg.shared_storage import initialize_pipeline_status
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List
import json
import re
import os
import logging

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