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
import uuid
from datetime import datetime

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

# Create async HTTP clients with different timeouts
async_client = httpx.AsyncClient(timeout=30.0)  # Default client for queries
upload_client = httpx.AsyncClient(timeout=120.0)  # Extended timeout for uploads

# Simple in-memory batch tracker
batch_tracker: Dict[str, Dict[str, Any]] = {}

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
        # Log upload attempt
        logger.info(f"Starting upload to graph '{graph_id}' with {len(files)} files")
        
        # Prepare files for multipart upload and track sizes
        file_data = []
        total_size = 0
        file_info = []
        
        for file in files:
            content = await file.read()
            file_size = len(content)
            total_size += file_size
            file_info.append((file.filename, file_size))
            file_data.append(
                ("files", (file.filename, content, file.content_type or "application/octet-stream"))
            )
        
        logger.info(f"Total upload size: {total_size} bytes ({total_size / 1024 / 1024:.1f} MB)")
        
        # Forward to knowledge service with extended timeout
        response = await upload_client.post(
            f"{KNOWLEDGE_SERVICE_URL}/api/{graph_id}/documents/batch-upload",
            files=file_data
        )
        response.raise_for_status()
        data = response.json()
        
        # Generate batch ID
        batch_id = str(uuid.uuid4())
        
        # Extract document IDs from successful uploads
        document_ids = [doc.get("document_id") for doc in data.get("successful_uploads", []) if doc.get("document_id")]
        
        # Store batch info for tracking
        batch_tracker[batch_id] = {
            "graph_id": graph_id,
            "created_at": datetime.now().isoformat(),
            "total_files": len(files),
            "successful": len(data.get("successful_uploads", [])),
            "failed": len(data.get("failed_uploads", [])),
            "document_ids": document_ids
        }
        
        # Log successful upload
        logger.info(f"Upload successful for graph '{graph_id}', batch: {batch_id}")
        logger.info(f"  Successful uploads: {len(data.get('successful_uploads', []))}")
        logger.info(f"  Failed uploads: {len(data.get('failed_uploads', []))}")
        
        # Transform response
        return {
            "status": data["status"],
            "message": data["message"],
            "graph_id": graph_id,
            "batch_id": batch_id,
            "uploaded": len(data.get("successful_uploads", [])),
            "failed": len(data.get("failed_uploads", [])),
            "document_ids": document_ids,
            "details": {
                "successful": data.get("successful_uploads", []),
                "failed": data.get("failed_uploads", [])
            }
        }
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Knowledge graph not found")
        
        # Log the error details
        logger.error(f"HTTP error during upload: {e.response.status_code}")
        logger.error(f"  Response body: {e.response.text[:500]}...")  # First 500 chars
        logger.error(f"  Graph ID: {graph_id}")
        logger.error(f"  Number of files: {len(files)}")
        
        raise HTTPException(
            status_code=e.response.status_code,
            detail=str(e)
        )
    except httpx.RequestError as e:
        # Log detailed error information
        logger.error(f"Failed to upload documents - RequestError: {type(e).__name__}")
        logger.error(f"  Error details: {str(e)}")
        logger.error(f"  Graph ID: {graph_id}")
        logger.error(f"  Number of files: {len(files)}")
        
        # Log file details if available
        if 'file_info' in locals():
            for i, (filename, size) in enumerate(file_info):
                logger.error(f"  File {i+1}: {filename} ({size} bytes)")
            logger.error(f"  Total size: {total_size} bytes ({total_size / 1024 / 1024:.1f} MB)")
        
        # Provide more specific error message
        error_detail = "Failed to upload documents to knowledge service"
        if "timeout" in str(e).lower():
            error_detail = f"Upload timed out after 120 seconds. Try uploading fewer or smaller files."
        elif "connection" in str(e).lower():
            error_detail = "Could not connect to knowledge service. Please try again."
        
        raise HTTPException(
            status_code=503,
            detail=error_detail
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

@router.get("/graphs/{graph_id}/processing")
async def get_processing_status(graph_id: str):
    """Get documents currently being processed"""
    try:
        response = await async_client.get(
            f"{KNOWLEDGE_SERVICE_URL}/api/namespaces/{graph_id}/processing"
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
        logger.error(f"Failed to get processing status: {e}")
        raise HTTPException(
            status_code=503,
            detail="Failed to get processing status"
        )

@router.get("/graphs/{graph_id}/documents/{doc_id}")
async def get_document_status(graph_id: str, doc_id: str):
    """Get detailed status for a specific document"""
    try:
        response = await async_client.get(
            f"{KNOWLEDGE_SERVICE_URL}/api/namespaces/{graph_id}/documents/{doc_id}"
        )
        response.raise_for_status()
        
        return response.json()
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            if "document" in str(e).lower():
                raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found")
            else:
                raise HTTPException(status_code=404, detail="Knowledge graph not found")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=str(e)
        )
    except httpx.RequestError as e:
        logger.error(f"Failed to get document status: {e}")
        raise HTTPException(
            status_code=503,
            detail="Failed to get document status"
        )

@router.get("/graphs/{graph_id}/stuck")
async def get_stuck_documents(graph_id: str):
    """Get stuck documents (processing > 5 min or pending > 10 min)"""
    try:
        response = await async_client.get(
            f"{KNOWLEDGE_SERVICE_URL}/api/namespaces/{graph_id}/stuck"
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
        logger.error(f"Failed to get stuck documents: {e}")
        raise HTTPException(
            status_code=503,
            detail="Failed to get stuck documents"
        )

@router.post("/graphs/{graph_id}/retry-stuck")
async def retry_stuck_documents(graph_id: str):
    """Retry all stuck documents"""
    try:
        response = await async_client.post(
            f"{KNOWLEDGE_SERVICE_URL}/api/namespaces/{graph_id}/retry-stuck"
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
        logger.error(f"Failed to retry stuck documents: {e}")
        raise HTTPException(
            status_code=503,
            detail="Failed to retry stuck documents"
        )

@router.get("/graphs/{graph_id}/recent")
async def get_recent_activity(
    graph_id: str,
    hours: int = Query(default=24, ge=1, le=168, description="Hours to look back (1-168)")
):
    """Get recently processed documents"""
    try:
        response = await async_client.get(
            f"{KNOWLEDGE_SERVICE_URL}/api/namespaces/{graph_id}/recent",
            params={"hours": hours}
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
        logger.error(f"Failed to get recent activity: {e}")
        raise HTTPException(
            status_code=503,
            detail="Failed to get recent activity"
        )

@router.get("/batches/{batch_id}")
async def get_batch_status(batch_id: str):
    """Get status of a batch upload operation"""
    batch_info = batch_tracker.get(batch_id)
    if not batch_info:
        raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found")
    
    # Get current status of all documents in the batch
    graph_id = batch_info["graph_id"]
    document_statuses = []
    
    for doc_id in batch_info["document_ids"]:
        try:
            response = await async_client.get(
                f"{KNOWLEDGE_SERVICE_URL}/api/namespaces/{graph_id}/documents/{doc_id}"
            )
            if response.status_code == 200:
                doc_data = response.json()
                document_statuses.append({
                    "id": doc_id,
                    "status": doc_data.get("status"),
                    "chunks_count": doc_data.get("chunks_count", 0),
                    "error": doc_data.get("error")
                })
            else:
                document_statuses.append({
                    "id": doc_id,
                    "status": "unknown",
                    "error": "Failed to get document status"
                })
        except Exception as e:
            logger.error(f"Error getting status for document {doc_id}: {e}")
            document_statuses.append({
                "id": doc_id,
                "status": "unknown",
                "error": str(e)
            })
    
    # Calculate batch summary
    status_summary = {
        "pending": len([d for d in document_statuses if d["status"] == "pending"]),
        "processing": len([d for d in document_statuses if d["status"] == "processing"]),
        "processed": len([d for d in document_statuses if d["status"] == "processed"]),
        "failed": len([d for d in document_statuses if d["status"] == "failed"]),
        "unknown": len([d for d in document_statuses if d["status"] == "unknown"])
    }
    
    # Determine overall batch status
    if status_summary["failed"] > 0 and status_summary["processed"] == 0:
        batch_status = "failed"
    elif status_summary["pending"] > 0 or status_summary["processing"] > 0:
        batch_status = "processing"
    elif status_summary["processed"] == len(document_statuses):
        batch_status = "completed"
    else:
        batch_status = "partial_success"
    
    return {
        "batch_id": batch_id,
        "status": batch_status,
        "graph_id": graph_id,
        "created_at": batch_info["created_at"],
        "total_files": batch_info["total_files"],
        "status_summary": status_summary,
        "documents": document_statuses
    }

@router.on_event("shutdown")
async def shutdown_event():
    """Clean up HTTP clients on shutdown"""
    await async_client.aclose()
    await upload_client.aclose()