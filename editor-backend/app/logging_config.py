"""Logging configuration for editor backend."""

import logging
import sys
from pathlib import Path

# Import shared logging config
sys.path.append(str(Path(__file__).parent.parent.parent / "shared"))
from logging_config import setup_logging as shared_setup_logging, get_logger


def setup_logging():
    """Setup logging for editor backend service."""
    shared_setup_logging(
        service_name="editor-backend",
        level="INFO"
    )