"""Connection management API routes."""

import logging
from typing import List

from fastapi import APIRouter, HTTPException, status

from app.models import (
    Connection,
    ConnectionCreate,
    ConnectionStatus
)
from app.services.connection_manager import connection_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/connections", tags=["connections"])


@router.post("/", response_model=Connection, status_code=status.HTTP_201_CREATED)
async def create_connection(connection_data: ConnectionCreate):
    """Create a new connection."""
    try:
        connection = await connection_manager.create_connection(connection_data)
        return connection
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/", response_model=List[Connection])
async def list_connections():
    """List all connections."""
    return await connection_manager.list_connections()


@router.get("/{connection_id}", response_model=Connection)
async def get_connection(connection_id: str):
    """Get a specific connection."""
    connection = await connection_manager.get_connection(connection_id)
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection {connection_id} not found"
        )
    return connection


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(connection_id: str):
    """Delete a connection."""
    deleted = await connection_manager.delete_connection(connection_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection {connection_id} not found"
        )


@router.patch("/{connection_id}/refresh", response_model=Connection)
async def refresh_connection(connection_id: str):
    """Refresh a connection's credentials."""
    try:
        connection = await connection_manager.refresh_connection(connection_id)
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection {connection_id} not found"
            )
        return connection
    except Exception as e:
        logger.error(f"Error refreshing connection {connection_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh connection"
        )


@router.get("/{connection_id}/status", response_model=dict)
async def get_connection_status(connection_id: str):
    """Get the current status of a connection."""
    connection = await connection_manager.get_connection(connection_id)
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection {connection_id} not found"
        )
    
    # Check live status
    status = await connection_manager.check_connection_status(connection_id)
    
    return {
        "connection_id": connection_id,
        "provider": connection.provider,
        "status": status,
        "last_checked": connection.last_checked,
        "error_message": connection.error_message
    }