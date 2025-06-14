"""
Unified logging configuration for all HireCJ services.
Provides consistent log formatting and file rotation.
"""

import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Optional


def setup_logging(
    service_name: str,
    log_level: str = "INFO",
    log_dir: str = "logs",
    max_bytes: int = 10_485_760,  # 10MB
    backup_count: int = 5,
    enable_console: bool = True,
    enable_file: bool = True,
):
    """
    Set up comprehensive logging configuration.

    Args:
        service_name: Application name for log files and formatters.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_dir: Directory for log files.
        max_bytes: Maximum size of each log file before rotation.
        backup_count: Number of backup files to keep.
        enable_console: Whether to log to console.
        enable_file: Whether to log to file.
    """
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    file_formatter = logging.Formatter(
        f"[{service_name}] [%(asctime)s] [%(name)s] [%(levelname)s] [%(funcName)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_formatter = logging.Formatter(
        f"[{service_name}] [%(asctime)s] [%(levelname)s] %(name)s - %(message)s", datefmt="%H:%M:%S"
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    root_logger.handlers.clear()

    if enable_file:
        log_file = log_path / f"{service_name}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    if enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # Configure third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("LiteLLM").setLevel(logging.WARNING)

    # Make uvicorn use our handlers
    for _name in ("uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(_name)
        uv_logger.handlers.clear()
        for h in root_logger.handlers:
            uv_logger.addHandler(h)
        uv_logger.setLevel(root_logger.level)
        uv_logger.propagate = False

    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging initialized - Service: {service_name}, Level: {log_level}, File: {enable_file}, Console: {enable_console}"
    )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)
