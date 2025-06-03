"""Health check endpoints."""

from datetime import datetime
from typing import Dict

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", response_model=Dict[str, str])
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "hirecj-database"
    }


@router.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint."""
    return {
        "service": "HireCJ Service Connections API",
        "version": "1.0.0",
        "docs": "/docs"
    }