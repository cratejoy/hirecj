#!/usr/bin/env python3
"""Show current model configurations for debugging and documentation."""

import os
import sys
import json

from app.model_config import MODEL_CONFIG, get_api_key, get_provider

# Add parent directory to path for local imports
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)


def show_configs():
    """Display current model configurations."""
    print("🤖 HireCJ Model Configuration")
    print("=" * 50)

    for purpose, config in MODEL_CONFIG.items():
        # Convert purpose to readable name
        readable_purpose = {
            "conversation_cj": "CJ Agent",
            "conversation_merchant": "Merchant Agent",
            "test_evaluation": "Test Evaluator",
            "universe_generation": "Universe Generator",
        }.get(purpose, purpose)

        model = config["model"]
        provider = get_provider(model)
        api_key = get_api_key(model)

        print(f"\n📋 {readable_purpose}")
        print("-" * 30)
        print(f"Provider:     {provider}")
        print(f"Model:        {model}")
        print(f"Temperature:  {config['temperature']}")

        if api_key:
            print("Status:       ✅ API Key Available")
        else:
            print("Status:       ❌ API Key Missing")

    print("\n" + "=" * 50)
    print("💡 Tips:")
    print("- All models must be configured via environment variables")
    print("- Use CJ_MODEL, MERCHANT_MODEL, EVALUATOR_MODEL")
    print("- Check .env.example for required configuration options")
    print("- No default models are provided - explicit configuration required")


def show_json():
    """Display configurations in JSON format."""
    # Convert MODEL_CONFIG to include provider and api_key info
    configs = {}
    for purpose, config in MODEL_CONFIG.items():
        model = config["model"]
        configs[purpose] = {
            "model": model,
            "temperature": config["temperature"],
            "provider": get_provider(model),
            "has_api_key": bool(get_api_key(model)),
        }
    print(json.dumps(configs, indent=2))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        show_json()
    else:
        show_configs()
