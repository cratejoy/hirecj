#!/usr/bin/env python3
"""
Distribute environment variables from single .env to services.

This script reads the master .env file and creates service-specific
.env files with only the variables each service needs.

Phase 4.0: True Environment Centralization
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Set

# Add parent directory to path to import shared modules
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.env_loader import env_loader

# Service variable mappings
SERVICE_VARS = {
    "auth": {
        "direct": [
            # Core configuration
            "ENVIRONMENT", "DEBUG", "LOG_LEVEL",
            
            # Service identity
            "AUTH_SERVICE_PORT",
            
            # Database
            "AUTH_DATABASE_URL",
            "REDIS_URL",
            
            # Security
            "SECRET_KEY", "JWT_SECRET_KEY", "JWT_SECRET", "JWT_ALGORITHM", 
            "JWT_EXPIRATION_MINUTES", "JWT_EXPIRATION_HOURS",
            "CREDENTIALS_ENCRYPTION_KEY", "ENCRYPTION_KEY",
            
            # OAuth credentials
            "SHOPIFY_CLIENT_ID", "SHOPIFY_CLIENT_SECRET", "SHOPIFY_SCOPES",
            "SLACK_CLIENT_ID", "SLACK_CLIENT_SECRET", "SLACK_APP_ID", "SLACK_SIGNING_SECRET",
            "ZENDESK_CLIENT_ID", "ZENDESK_CLIENT_SECRET", "ZENDESK_SUBDOMAIN",
            "INTERCOM_CLIENT_ID", "INTERCOM_CLIENT_SECRET",
            
            # URLs for OAuth callbacks
            "FRONTEND_URL", "BACKEND_URL", "HOMEPAGE_URL", "OAUTH_REDIRECT_BASE_URL",
            "FRONTEND_SUCCESS_PATH", "FRONTEND_ERROR_PATH",
            
            # App Host
            "APP_HOST",
            
            # Service URLs for API calls
            "AGENTS_SERVICE_URL", "DATABASE_SERVICE_URL",
            
            # Features
            "ENABLE_OAUTH", "ENABLE_AUTH",
            
            # CORS
            "ALLOWED_ORIGINS",
        ]
    },
    "agents": {
        "direct": [
            # Core configuration
            "ENVIRONMENT", "DEBUG", "LOG_LEVEL",
            
            # Service identity
            "AGENTS_SERVICE_PORT",
            
            # Redis
            "REDIS_URL", "REDIS_SESSION_TTL",
            
            # LLM API keys
            "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
            "GEMINI_API_KEY", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_DEPLOYMENT", "AZURE_OPENAI_API_VERSION",
            
            # Databases
            "SUPABASE_CONNECTION_STRING",
            "IDENTITY_SUPABASE_URL", "IDENTITY_SUPABASE_ANON_KEY",
            
            # Freshdesk
            "FRESHDESK_API_KEY", "FRESHDESK_DOMAIN",
            
            # Shopify API
            "SHOPIFY_API_TOKEN", "SHOPIFY_SHOP_DOMAIN",
            
            # Service URLs
            "AUTH_SERVICE_URL", "DATABASE_SERVICE_URL",
            
            # Model configuration
            "CJ_MODEL", "CJ_TEMPERATURE", "DEFAULT_CJ_VERSION",
            "MERCHANT_MODEL", "MERCHANT_TEMPERATURE",
            "EVALUATOR_MODEL", "EVALUATOR_TEMPERATURE",
            "UNIVERSE_GENERATOR_MODEL", "UNIVERSE_GENERATOR_TEMPERATURE",
            "FACT_EXTRACTION_MODEL",
            "MODEL_NAME", "DEFAULT_TEMPERATURE",
            
            # Features
            "ENABLE_FACT_CHECKING", "ENABLE_PERFORMANCE_METRICS",
            "ENABLE_PROMPT_CACHING", "ENABLE_LITELLM_CACHE",
            "ENABLE_CACHE_WARMING", "ENABLE_VERBOSE_LOGGING",
            "ENABLE_CHAT",
            
            # Cache settings
            "WARM_CACHE_ON_STARTUP", "CACHE_TTL", "CACHE_TTL_SHORT",
            "CACHE_WARM_CONCURRENCY",
            
            # API settings
            "API_PREFIX", "DEFAULT_PAGINATION_LIMIT", "MAX_WORKERS",
            "SYNC_BATCH_SIZE", "MAX_RETRIES", "REQUEST_TIMEOUT",
            
            # Conversation settings
            "DEFAULT_PERSONA_VERSION", "DEFAULT_TIMEOUT",
            "CONVERSATIONS_DIR", "MAX_CONVERSATION_TURNS",
            
            # Workers
            "WORKER_CONCURRENCY", "SYNC_INTERVAL_MINUTES", "CLEANUP_INTERVAL_HOURS",
            
            # Telemetry
            "CREWAI_TELEMETRY",
            
            # CORS
            "ALLOWED_ORIGINS",
        ]
    },
    "database": {
        "direct": [
            # Core configuration
            "ENVIRONMENT", "DEBUG", "LOG_LEVEL",
            
            # Service identity
            "DATABASE_SERVICE_PORT",
            
            # Database
            "DATABASE_URL",
            
            # API settings
            "API_PREFIX", "DEFAULT_PAGINATION_LIMIT",
        ]
    },
    "homepage": {
        "direct": [
            # Vite expects these specific variables
            "VITE_API_URL", "VITE_WS_URL", "VITE_AUTH_URL",
            
            # Port for development server
            "HOMEPAGE_PORT",
        ],
        "mappings": {
            # Map from our standard names to what Vite expects
            "VITE_API_URL": lambda vars: vars.get("AGENTS_SERVICE_URL", "http://localhost:8000"),
            "VITE_WS_URL": lambda vars: vars.get("AGENTS_SERVICE_URL", "http://localhost:8000").replace("http://", "ws://").replace("https://", "wss://"),
            "VITE_AUTH_URL": lambda vars: vars.get("AUTH_SERVICE_URL", "http://localhost:8103"),
        }
    }
}

def load_master_env() -> Dict[str, str]:
    """Load variables from master .env file."""
    # Use our single env loader
    env_loader.load()
    return env_loader.get_service_vars("all")

def write_service_env(service: str, variables: Dict[str, str]) -> None:
    """Write service-specific .env file."""
    service_env_path = Path(service) / ".env"
    
    # Ensure directory exists
    service_env_path.parent.mkdir(exist_ok=True)
    
    with open(service_env_path, 'w') as f:
        f.write("# ================================================\n")
        f.write(f"# Auto-generated from root .env - DO NOT EDIT\n")
        f.write(f"# Edit the root .env file instead\n")
        f.write(f"# Generated by: scripts/distribute_env.py\n")
        f.write("# ================================================\n\n")
        
        # Group variables by category for readability
        categories = {
            "Core": ["ENVIRONMENT", "DEBUG", "LOG_LEVEL"],
            "Service": [v for v in variables if "SERVICE" in v or "PORT" in v],
            "Database": [v for v in variables if "DATABASE" in v or "REDIS" in v or "SUPABASE" in v],
            "Security": [v for v in variables if any(x in v for x in ["SECRET", "KEY", "JWT", "ENCRYPTION"])],
            "OAuth": [v for v in variables if any(x in v for x in ["CLIENT_ID", "CLIENT_SECRET", "OAUTH"])],
            "Models": [v for v in variables if any(x in v for x in ["MODEL", "TEMPERATURE"])],
            "Features": [v for v in variables if v.startswith("ENABLE_")],
            "Other": []
        }
        
        # Collect remaining variables
        categorized = set()
        for cat_vars in categories.values():
            categorized.update(cat_vars)
        categories["Other"] = [v for v in variables if v not in categorized]
        
        # Write each category
        for category, cat_vars in categories.items():
            if not cat_vars:
                continue
                
            f.write(f"# {category}\n")
            for var in sorted(cat_vars):
                if var in variables:
                    f.write(f"{var}={variables[var]}\n")
            f.write("\n")
    
    print(f"✅ Created {service_env_path} with {len(variables)} variables")

def distribute_env() -> None:
    """Distribute environment variables to all services."""
    print("🔄 Distributing environment variables from .env to services...")
    
    # Load master env
    try:
        master_vars = load_master_env()
        print(f"📖 Loaded {len(master_vars)} variables from .env")
    except SystemExit:
        print("❌ Failed to load .env file")
        print("Make sure you have created .env from .env.master.example")
        sys.exit(1)
    
    # Track which variables are used
    used_vars: Set[str] = set()
    
    # Distribute to each service
    for service, config in SERVICE_VARS.items():
        service_vars = {}
        
        # Direct variables
        for var in config.get("direct", []):
            if var in master_vars:
                service_vars[var] = master_vars[var]
                used_vars.add(var)
        
        # Mapped variables
        for target, source in config.get("mappings", {}).items():
            if callable(source):
                value = source(master_vars)
                if value:
                    service_vars[target] = value
            elif source in master_vars:
                service_vars[target] = master_vars[source]
                used_vars.add(source)
        
        # Write service env
        write_service_env(service, service_vars)
    
    # Report unused variables
    unused_vars = set(master_vars.keys()) - used_vars
    if unused_vars:
        print(f"\n⚠️  Found {len(unused_vars)} unused variables:")
        for var in sorted(unused_vars):
            print(f"   - {var}")
        print("\nConsider adding these to SERVICE_VARS if they're needed by services.")
    
    print("\n✅ Environment distribution complete!")

if __name__ == "__main__":
    distribute_env()