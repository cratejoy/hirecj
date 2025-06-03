"""
Main entry point for the HireCJ Auth service.

This module provides a standardized way to run the service with:
    python -m app
"""
import os
import sys

# Ensure the parent directory is in the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    """Run the auth service."""
    import uvicorn
    from app.config import settings
    
    # Use settings for configuration
    host = settings.app_host
    port = settings.app_port
    
    # Determine if we should reload based on environment
    reload = os.environ.get("APP_ENV", "development") == "development"
    log_level = os.environ.get("LOG_LEVEL", "info").lower()
    
    print(f"Starting HireCJ Auth service on {host}:{port}")
    print(f"Environment: {os.environ.get('APP_ENV', 'development')}")
    print(f"Log level: {log_level}")
    print(f"Hot reload: {'enabled' if reload else 'disabled'}")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
    )


if __name__ == "__main__":
    main()