"""Health check endpoints."""

import time
from typing import Dict, Any

from fastapi import APIRouter

from app.config import settings

router = APIRouter(tags=["health"])

# Track service start time
SERVICE_START_TIME = time.time()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.
    
    Returns service health status and basic metrics.
    """
    uptime_seconds = time.time() - SERVICE_START_TIME
    
    return {
        "status": "healthy",
        "service": "hirecj-auth",
        "version": "1.0.0",
        "uptime_seconds": round(uptime_seconds, 2),
        "environment": "development" if settings.debug else "production",
        "timestamp": time.time()
    }


@router.get("/ping")
async def ping() -> Dict[str, str]:
    """Simple ping endpoint."""
    return {"pong": "ok"}