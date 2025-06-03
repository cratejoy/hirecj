"""API Routes"""

from .catalog import router as catalog_router

# Import fact_checking module to export it
from . import fact_checking

__all__ = ["catalog_router", "fact_checking"]
