"""Internal API endpoints for service-to-service communication."""

from fastapi import APIRouter
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/internal", tags=["internal"])

# OAuth completion is now handled through centralized database
# Agents service determines OAuth state from MerchantToken creation timestamp
# No cross-service notification needed
