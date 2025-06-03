"""Model configuration package for HireCJ."""

from .simple_config import (
    ModelPurpose,
    MODEL_CONFIG,
    get_model,
    get_temperature,
    get_api_key,
    get_provider,
)

__all__ = [
    "ModelPurpose",
    "MODEL_CONFIG",
    "get_model",
    "get_temperature",
    "get_api_key",
    "get_provider",
]
