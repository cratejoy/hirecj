"""Main FastAPI application for HireCJ Service Connections."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import health, connections

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting HireCJ Service Connections API")
    yield
    # Shutdown
    logger.info("Shutting down HireCJ Service Connections API")


# Initialize FastAPI app
app = FastAPI(
    title="HireCJ Service Connections API",
    description="REST API for managing external service connections",
    version="1.0.0",
    lifespan=lifespan,
    debug=settings.debug
)

# Build allowed origins from configuration
allowed_origins = [
    settings.frontend_url,
    settings.auth_url,
    # Always allow localhost for development
    "http://localhost:3456",
    "http://localhost:8100", 
    "http://localhost:8103",
    "http://localhost:8002",
]

# Add public URLs if configured
if settings.public_url:
    allowed_origins.append(settings.public_url)

# Add reserved domains if detected
if "hirecj.ai" in settings.frontend_url:
    allowed_origins.extend([
        "https://amir.hirecj.ai",
        "https://amir-auth.hirecj.ai",
    ])

# Remove duplicates and empty strings
allowed_origins = list(set(filter(None, allowed_origins)))

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(connections.router, prefix=settings.api_prefix)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug
    )