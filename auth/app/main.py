"""Main FastAPI application for HireCJ Auth Service."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import health, oauth, shopify_custom

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
    logger.info("Starting HireCJ Auth Service")
    logger.info(f"Environment: {'Development' if settings.debug else 'Production'}")
    logger.info(f"API available at http://{settings.app_host}:{settings.app_port}")
    
    # Log OAuth URLs if in debug mode
    if settings.debug:
        settings.log_oauth_urls()
    
    # Check if ngrok is enabled but no tunnel detected
    if settings.ngrok_enabled and settings.oauth_redirect_base_url.startswith("http://localhost"):
        logger.warning("⚠️  Ngrok enabled but no tunnel detected. OAuth callbacks will use localhost.")
        logger.warning("💡 Run 'make dev-tunnel' to start with tunnel support.")
    
    yield
    # Shutdown
    logger.info("Shutting down HireCJ Auth Service")


# Initialize FastAPI app
app = FastAPI(
    title="HireCJ Auth Service",
    description="Authentication and OAuth management for HireCJ platform",
    version="1.0.0",
    lifespan=lifespan,
    debug=settings.debug,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
# Commenting out standard OAuth flow - replaced with custom app flow
# app.include_router(oauth.router, prefix=f"{settings.api_prefix}/oauth")
app.include_router(shopify_custom.router, prefix=f"{settings.api_prefix}/shopify")

# TODO: Add auth router when implemented
# app.include_router(auth.router, prefix=f"{settings.api_prefix}/auth")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "HireCJ Auth Service",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "docs": "/docs" if settings.debug else None,
            "shopify_custom": f"{settings.api_prefix}/shopify",
            # "oauth": f"{settings.api_prefix}/oauth"  # Replaced with custom app flow
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug
    )