"""
Knowledge service proxy endpoints for the editor.
Forwards requests to the knowledge service running on port 8004.
"""

import httpx
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Query, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])

# Knowledge service URL
KNOWLEDGE_SERVICE_URL = settings.knowledge_service_url if hasattr(settings, 'knowledge_service_url') else "http://localhost:8004"

class NamespaceConfig(BaseModel):
    """Namespace configuration"""
    name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="Namespace description")

class QueryRequest(BaseModel):
    """Query request model"""
    query: str
    mode: str = Field(default="hybrid", description="Query mode: naive, local, global, hybrid")

class URLRequest(BaseModel):
    """URL ingestion request"""
    url: str = Field(..., description="URL to fetch content from")
    metadata: Dict[str, str] = Field(default_factory=dict, description="Additional metadata")

# Create async HTTP client
async_client = httpx.AsyncClient(timeout=30.0)

@router.get("/health")
async def health_check():
    """Check if knowledge service is available"""
    try:
        response = await async_client.get(f"{KNOWLEDGE_SERVICE_URL}/health")
        response.raise_for_status()
        data = response.json()
        return {
            "status": "healthy",
            "knowledge_service": data,
            "proxy": "editor-backend"
        }
    except httpx.RequestError as e:
        logger.error(f"Failed to reach knowledge service: {e}")
        raise HTTPException(
            status_code=503,
            detail="Knowledge service is unavailable"
        )

@router.get("/graphs")
async def list_knowledge_graphs():
    """List all knowledge graphs (namespaces) with statistics"""
    try:
        response = await async_client.get(f"{KNOWLEDGE_SERVICE_URL}/api/namespaces")
        response.raise_for_status()
        data = response.json()
        
        # Transform to match editor's expected format
        graphs = []
        for ns in data.get("namespaces", []):
            graph = {
                "id": ns["id"],
                "name": ns["name"],
                "description": ns["description"],
                "created_at": ns.get("created_at"),
                "document_count": 0,
                "last_updated": ns.get("created_at"),
                "status": "active"
            }
            
            # Fetch statistics for this namespace
            try:
                stats_response = await async_client.get(
                    f"{KNOWLEDGE_SERVICE_URL}/api/namespaces/{ns['id']}/statistics"
                )
                if stats_response.status_code == 200:
                    stats = stats_response.json()
                    graph["document_count"] = stats.get("document_count", 0)
                    graph["last_updated"] = stats.get("last_updated") or ns.get("created_at")
                    
                    # Set status based on document counts
                    if stats.get("pending_count", 0) > 0:
                        graph["status"] = "processing"
                    elif stats.get("failed_count", 0) > 0 and stats.get("document_count", 0) == 0:
                        graph["status"] = "error"
                    elif stats.get("document_count", 0) > 0:
                        graph["status"] = "active"
                    else:
                        graph["status"] = "empty"
                        
            except Exception as e:
                logger.warning(f"Failed to fetch stats for namespace {ns['id']}: {e}")
            
            graphs.append(graph)
        
        return {"graphs": graphs, "count": len(graphs)}
        
    except httpx.RequestError as e:
        logger.error(f"Failed to fetch namespaces: {e}")
        raise HTTPException(
            status_code=503,
            detail="Failed to fetch knowledge graphs"
        )

@router.post("/graphs")
async def create_knowledge_graph(
    graph_id: str = Query(..., regex="^[a-z0-9_]+$", description="Graph identifier"),
    config: NamespaceConfig = ...
):
    """Create a new knowledge graph"""
    try:
        response = await async_client.post(
            f"{KNOWLEDGE_SERVICE_URL}/api/namespaces",
            params={"namespace_id": graph_id},
            json=config.dict()
        )
        response.raise_for_status()
        data = response.json()
        
        return {
            "id": data["namespace_id"],
            "name": config.name,
            "description": config.description,
            "message": data["message"]
        }
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 409:
            raise HTTPException(status_code=409, detail="Knowledge graph already exists")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=str(e)
        )
    except httpx.RequestError as e:
        logger.error(f"Failed to create namespace: {e}")
        raise HTTPException(
            status_code=503,
            detail="Failed to create knowledge graph"
        )

@router.delete("/graphs/{graph_id}")
async def delete_knowledge_graph(graph_id: str):
    """Delete a knowledge graph"""
    try:
        response = await async_client.delete(
            f"{KNOWLEDGE_SERVICE_URL}/api/namespaces/{graph_id}"
        )
        response.raise_for_status()
        
        return {"message": f"Knowledge graph '{graph_id}' deleted successfully"}
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Knowledge graph not found")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=str(e)
        )
    except httpx.RequestError as e:
        logger.error(f"Failed to delete namespace: {e}")
        raise HTTPException(
            status_code=503,
            detail="Failed to delete knowledge graph"
        )

@router.get("/graphs/{graph_id}/statistics")
async def get_knowledge_graph_statistics(graph_id: str):
    """Get detailed statistics for a specific knowledge graph"""
    try:
        response = await async_client.get(
            f"{KNOWLEDGE_SERVICE_URL}/api/namespaces/{graph_id}/statistics"
        )
        response.raise_for_status()
        
        return response.json()
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Knowledge graph not found")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=str(e)
        )
    except httpx.RequestError as e:
        logger.error(f"Failed to fetch statistics: {e}")
        raise HTTPException(
            status_code=503,
            detail="Failed to fetch knowledge graph statistics"
        )

@router.post("/graphs/{graph_id}/upload")
async def upload_documents(
    graph_id: str,
    files: List[UploadFile] = File(...)
):
    """Upload documents to a knowledge graph"""
    try:
        # Prepare files for multipart upload
        file_data = []
        for file in files:
            content = await file.read()
            file_data.append(
                ("files", (file.filename, content, file.content_type or "application/octet-stream"))
            )
        
        # Forward to knowledge service
        response = await async_client.post(
            f"{KNOWLEDGE_SERVICE_URL}/api/{graph_id}/documents/batch-upload",
            files=file_data
        )
        response.raise_for_status()
        data = response.json()
        
        # Transform response
        return {
            "status": data["status"],
            "message": data["message"],
            "graph_id": graph_id,
            "uploaded": len(data.get("successful_uploads", [])),
            "failed": len(data.get("failed_uploads", [])),
            "details": {
                "successful": data.get("successful_uploads", []),
                "failed": data.get("failed_uploads", [])
            }
        }
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Knowledge graph not found")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=str(e)
        )
    except httpx.RequestError as e:
        logger.error(f"Failed to upload documents: {e}")
        raise HTTPException(
            status_code=503,
            detail="Failed to upload documents"
        )
    finally:
        # Reset file pointers for cleanup
        for file in files:
            await file.seek(0)

@router.post("/graphs/{graph_id}/url")
async def ingest_url(
    graph_id: str,
    request: URLRequest
):
    """Ingest content from a URL"""
    try:
        response = await async_client.post(
            f"{KNOWLEDGE_SERVICE_URL}/api/{graph_id}/documents/url",
            json=request.dict()
        )
        response.raise_for_status()
        data = response.json()
        
        return {
            "status": "success",
            "message": data["message"],
            "graph_id": graph_id,
            "url": request.url,
            "content_length": data.get("content_length", 0)
        }
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Knowledge graph not found")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=str(e)
        )
    except httpx.RequestError as e:
        logger.error(f"Failed to ingest URL: {e}")
        raise HTTPException(
            status_code=503,
            detail="Failed to ingest URL content"
        )

@router.post("/graphs/{graph_id}/query")
async def query_knowledge_graph(
    graph_id: str,
    request: QueryRequest
):
    """Query a knowledge graph"""
    try:
        response = await async_client.post(
            f"{KNOWLEDGE_SERVICE_URL}/api/{graph_id}/query",
            json=request.dict()
        )
        response.raise_for_status()
        data = response.json()
        
        return {
            "graph_id": graph_id,
            "query": request.query,
            "mode": request.mode,
            "result": data.get("result", ""),
            "sources": []  # TODO: Extract sources when available
        }
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Knowledge graph not found")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=str(e)
        )
    except httpx.RequestError as e:
        logger.error(f"Failed to query knowledge: {e}")
        raise HTTPException(
            status_code=503,
            detail="Failed to query knowledge graph"
        )

@router.on_event("shutdown")
async def shutdown_event():
    """Clean up HTTP client on shutdown"""
    await async_client.aclose()