"""Entry point for running the editor backend service."""

if __name__ == "__main__":
    from app.main import app
    import uvicorn
    from app.config import settings
    
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )