"""Simple model configuration for HireCJ.

No abstractions, no strategies, just a dictionary.
"""

import os
from typing import Optional
from app.config import settings

# Default model configuration
MODEL_CONFIG = {
    "conversation_cj": {
        "model": os.getenv("CJ_MODEL", "gpt-4"),
        "temperature": float(
            os.getenv("CJ_TEMPERATURE", str(settings.default_temperature))
        ),
    },
    "conversation_merchant": {
        "model": os.getenv("MERCHANT_MODEL", "gpt-3.5-turbo"),
        "temperature": float(os.getenv("MERCHANT_TEMPERATURE", "0.8")),
    },
    "test_evaluation": {
        "model": os.getenv("EVALUATOR_MODEL", "gpt-4"),
        "temperature": float(os.getenv("EVALUATOR_TEMPERATURE", "0.1")),
        "max_tokens": settings.max_tokens_evaluation,
    },
    "universe_generation": {
        "model": os.getenv("UNIVERSE_GENERATOR_MODEL", "gpt-4"),
        "temperature": float(
            os.getenv(
                "UNIVERSE_GENERATOR_TEMPERATURE", str(settings.universe_temperature)
            )
        ),
    },
}


def get_model(purpose: str) -> str:
    """Get model name for a purpose."""
    if purpose not in MODEL_CONFIG:
        raise ValueError(f"Unknown model purpose: {purpose}")
    return MODEL_CONFIG[purpose]["model"]


def get_temperature(purpose: str) -> float:
    """Get temperature for a purpose."""
    if purpose not in MODEL_CONFIG:
        raise ValueError(f"Unknown model purpose: {purpose}")
    return MODEL_CONFIG[purpose]["temperature"]


def get_api_key(model: str) -> Optional[str]:
    """Get API key based on model name."""
    if model.startswith(("gpt-", "o1-", "o3-", "o4-")):
        return os.getenv("OPENAI_API_KEY") or settings.openai_api_key
    elif model.startswith("claude"):
        return os.getenv("ANTHROPIC_API_KEY") or settings.anthropic_api_key
    else:
        # Default to OpenAI
        return os.getenv("OPENAI_API_KEY") or settings.openai_api_key


def get_provider(model: str) -> str:
    """Determine provider from model name."""
    if model.startswith(("gpt-", "o1-", "o3-", "o4-")):
        return "openai"
    elif model.startswith("claude"):
        return "anthropic"
    else:
        return "openai"  # Default


class ModelPurpose:
    """Model usage categories for configuration."""

    CONVERSATION_CJ = "conversation_cj"
    CONVERSATION_MERCHANT = "conversation_merchant"
    TEST_EVALUATION = "test_evaluation"
    UNIVERSE_GENERATION = "universe_generation"
