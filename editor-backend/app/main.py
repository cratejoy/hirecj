"""Main FastAPI application for HireCJ Editor Backend."""

import os
import logging
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.logging_config import setup_logging
from app.api.routes import prompts, personas, workflows, knowledge
from app.api.websocket import playground

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="HireCJ Editor Backend",
    description="Backend API for the HireCJ Agent Editor",
    version="1.0.0",
)

# Build allowed origins from configuration
allowed_origins = settings.allowed_origins

# Log CORS configuration for debugging
logger.info("🔧 CORS Configuration:")
logger.info(f"  Frontend URL: {settings.frontend_url}")
logger.info(f"  Public URL: {settings.public_url}")
logger.info(f"  Editor URL: {settings.editor_url}")
logger.info(f"  Allowed origins: {allowed_origins}")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("🚀 Starting HireCJ Editor Backend...")
    logger.info(f"  Service: {settings.service_name}")
    logger.info(f"  Port: {settings.api_port}")
    logger.info(f"  Environment: {settings.environment}")
    
    # Verify critical directories exist
    critical_paths = [
        ("Prompts", settings.prompts_dir),
        ("Personas", settings.personas_dir),
        ("Workflows", settings.workflows_dir),
        ("Scenarios", settings.scenarios_dir),
    ]
    
    for name, path in critical_paths:
        abs_path = Path(path).resolve()
        if abs_path.exists():
            logger.info(f"✅ {name} directory: {abs_path}")
        else:
            logger.warning(f"⚠️  {name} directory not found: {abs_path}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("👋 Shutting down HireCJ Editor Backend...")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "HireCJ Editor Backend",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "prompts": "/api/v1/prompts",
            "personas": "/api/v1/personas", 
            "workflows": "/api/v1/workflows",
            "knowledge": "/api/v1/knowledge",
            "health": "/health",
            "api_docs": "/docs",
        },
        "timestamp": datetime.now().isoformat()
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.service_name,
        "timestamp": datetime.now().isoformat(),
        "environment": settings.environment,
        "version": "1.0.0"
    }


# Test CORS endpoint
@app.get("/api/v1/test-cors")
async def test_cors():
    """Test endpoint to verify CORS is working"""
    return {
        "status": "ok",
        "message": "CORS is working correctly",
        "service": "editor-backend",
        "timestamp": datetime.now().isoformat()
    }


# Include API routers
app.include_router(prompts.router)
app.include_router(personas.router)
app.include_router(workflows.router)
app.include_router(knowledge.router)

# Include WebSocket router
app.include_router(playground.router)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle all uncaught exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal server error occurred",
            "type": type(exc).__name__,
            "message": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )