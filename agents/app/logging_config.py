"""
Centralized logging configuration for HireCJ backend.
Provides consistent log formatting and file rotation.
"""

import logging
import logging.handlers
from datetime import datetime
from pathlib import Path

from app.config import settings


def setup_logging(
    log_level: str = None,
    log_dir: str = None,
    app_name: str = "hirecj-backend",
    max_bytes: int = None,
    backup_count: int = None,
    enable_console: bool = True,
    enable_file: bool = True,
):
    """
    Set up comprehensive logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        app_name: Application name for log files
        max_bytes: Maximum size of each log file before rotation
        backup_count: Number of backup files to keep
        enable_console: Whether to log to console
        enable_file: Whether to log to file
    """
    # Use settings defaults if not provided
    if log_level is None:
        log_level = settings.log_level
    if log_dir is None:
        log_dir = settings.logs_dir
    if max_bytes is None:
        max_bytes = settings.log_max_bytes
    if backup_count is None:
        backup_count = settings.log_backup_count

    # Create logs directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # Create formatters
    file_formatter = logging.Formatter(
        "[%(asctime)s] [%(name)s] [%(levelname)s] [%(funcName)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s - %(message)s", datefmt="%H:%M:%S"
    )

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # File handler with rotation
    if enable_file:
        log_file = log_path / f"{app_name}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

        # Separate error log
        error_log_file = log_path / f"{app_name}.error.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        root_logger.addHandler(error_handler)

    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # Configure specific loggers
    configure_module_loggers()

    # --- Make uvicorn loggers use the same handlers we just configured ----
    for _name in ("uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(_name)
        # discard default uvicorn handlers
        uv_logger.handlers.clear()
        # attach our root handlers (console + rotating file)
        for h in root_logger.handlers:
            uv_logger.addHandler(h)
        # keep same log-level and stop further propagation
        uv_logger.setLevel(root_logger.level)
        uv_logger.propagate = False
    # ----------------------------------------------------------------------

    # Log startup
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging initialized - Level: {log_level}, File: {enable_file}, Console: {enable_console}"
    )
    if enable_file:
        logger.info(f"Log files: {log_path / f'{app_name}.log'}")


def configure_module_loggers():
    """Configure specific module loggers with appropriate levels."""
    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("LiteLLM").setLevel(logging.WARNING)

    # Set specific levels for our modules
    logging.getLogger("app.main").setLevel(logging.INFO)
    logging.getLogger("app.platforms.web_platform").setLevel(logging.INFO)
    logging.getLogger("app.services").setLevel(logging.INFO)
    logging.getLogger("app.agents").setLevel(logging.INFO)

    # Debug level for WebSocket and conversation handling
    logging.getLogger("websocket").setLevel(logging.DEBUG)
    logging.getLogger("conversation").setLevel(logging.DEBUG)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


class RequestLogger:
    """Context manager for logging API requests with timing."""

    def __init__(self, logger: logging.Logger, request_type: str, **kwargs):
        self.logger = logger
        self.request_type = request_type
        self.kwargs = kwargs
        self.start_time = None

    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.info(f"[REQUEST_START] {self.request_type} - {self.kwargs}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()

        if exc_type:
            self.logger.error(
                f"[REQUEST_ERROR] {self.request_type} - Duration: {duration:.3f}s - Error: {exc_val}",
                exc_info=True,
            )
        else:
            self.logger.info(
                f"[REQUEST_END] {self.request_type} - Duration: {duration:.3f}s"
            )
