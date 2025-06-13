"""
Unified logging configuration for all HireCJ services.

This ensures consistent log formatting across all services.
"""
import logging
import sys
from typing import Optional


def setup_logging(service_name: str, level: str = "INFO") -> None:
    """
    Configure logging for a service with consistent formatting.
    
    Args:
        service_name: Name of the service (e.g., "agents", "auth")
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    # Create formatter with service name
    formatter = logging.Formatter(
        f'[{service_name}] %(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)