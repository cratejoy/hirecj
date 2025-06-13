"""Main FastAPI application for HireCJ Auth Service."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import health, shopify_oauth

# Configure logging
import os

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Configure handlers
log_handlers = [logging.StreamHandler()]
log_handlers.append(logging.FileHandler("logs/auth-service.log"))

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=log_handlers
)

logger = logging.getLogger(__name__)

# Suppress httpcore debug logs but keep httpx INFO logs
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting HireCJ Auth Service")
    logger.info(f"Environment: {'Development' if settings.debug else 'Production'}")
    logger.info(f"API available at http://{settings.app_host}:{settings.app_port}")
    
    # Log configured URLs for debugging
    logger.info("🔧 Configured URLs:")
    logger.info(f"  Frontend URL: {settings.frontend_url}")
    logger.info(f"  Homepage URL: {settings.homepage_url}")
    logger.info(f"  OAuth Redirect Base: {settings.oauth_redirect_base_url}")
    logger.info(f"  Auth Service URL: {settings.auth_service_url}")
    
    # Log Shopify OAuth redirect URI that will be used
    logger.info("🛍️ Shopify OAuth Configuration:")
    logger.info(f"  Redirect URI: {settings.oauth_redirect_base_url}/api/v1/shopify/callback")
    logger.info(f"  Client ID: {settings.shopify_client_id}")
    logger.info(f"  Scopes: {settings.shopify_scopes}")
    
    # Log OAuth callback URLs
    if settings.debug:
        settings.log_oauth_urls()
    
    # Check if ngrok is enabled but no tunnel detected
    if settings.ngrok_enabled and settings.public_url.startswith("http://localhost"):
        logger.warning("⚠️  Ngrok enabled but no tunnel detected. Custom app callbacks will use localhost.")
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
# Full OAuth implementation with HMAC verification and token exchange
app.include_router(shopify_oauth.router, prefix=f"{settings.api_prefix}/shopify")

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
            "shopify_custom": f"{settings.api_prefix}/shopify"
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