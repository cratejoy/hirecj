#!/usr/bin/env python3
"""Verify evaluator model configuration."""

import os
import sys

# Add parent directory to path
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)

# Import after path modification
from app.model_config import (  # noqa: E402
    ModelPurpose,
    get_model,
    get_temperature,
    get_provider,
)

# Get the configuration
model = get_model(ModelPurpose.TEST_EVALUATION)
provider = get_provider(model)
temperature = get_temperature(ModelPurpose.TEST_EVALUATION)

print("Evaluator Model Configuration:")
print(f"- Model: {model}")
print(f"- Provider: {provider}")
print(f"- Temperature: {temperature}")
print(f"- Model from env: {os.getenv('EVALUATOR_MODEL')}")
