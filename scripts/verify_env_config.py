#!/usr/bin/env python3
"""Verify that the unified environment configuration is working correctly."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def verify_service_config(service_name: str):
    """Verify configuration for a specific service."""
    print(f"\n🔍 Verifying {service_name} configuration...")
    
    try:
        if service_name == "auth":
            from auth.app.config import settings
        elif service_name == "agents":
            from agents.app.config import settings
        elif service_name == "database":
            from database.app.config import settings
        else:
            print(f"❌ Unknown service: {service_name}")
            return
        
        # Check key settings
        print(f"  ✅ Service Port: {settings.app_port}")
        
        if hasattr(settings, 'auth_service_url'):
            print(f"  ✅ Auth Service URL: {settings.auth_service_url}")
        if hasattr(settings, 'agents_service_url'):
            print(f"  ✅ Agents Service URL: {settings.agents_service_url}")
        if hasattr(settings, 'homepage_url'):
            print(f"  ✅ Homepage URL: {settings.homepage_url}")
        
        # Check database URL
        if hasattr(settings, 'database_url'):
            # Don't print the full URL with password
            db_url = settings.database_url
            if '@' in db_url:
                db_parts = db_url.split('@')
                db_url = db_parts[0].split('//')[0] + '//***:***@' + db_parts[1]
            print(f"  ✅ Database URL: {db_url}")
        
        # Check API keys (just verify they exist, don't print)
        if service_name == "auth":
            if settings.jwt_secret != "dev-secret-change-in-production":
                print(f"  ✅ JWT Secret: Configured")
            else:
                print(f"  ⚠️  JWT Secret: Using default (update .env.secrets)")
                
            if settings.shopify_client_id:
                print(f"  ✅ Shopify OAuth: Configured")
            else:
                print(f"  ⚠️  Shopify OAuth: Not configured")
                
        elif service_name == "agents":
            if settings.openai_api_key:
                print(f"  ✅ OpenAI API Key: Configured")
            else:
                print(f"  ❌ OpenAI API Key: Missing")
                
            if settings.anthropic_api_key:
                print(f"  ✅ Anthropic API Key: Configured")
            else:
                print(f"  ❌ Anthropic API Key: Missing")
        
        print(f"  ✅ Log Level: {settings.log_level}")
        
    except Exception as e:
        print(f"❌ Error loading {service_name} config: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Verify all service configurations."""
    print("🚀 Verifying Unified Environment Configuration")
    print("=" * 50)
    
    # Check root .env exists
    root_env = Path(__file__).parent.parent / ".env"
    if root_env.exists():
        print(f"✅ Root .env exists at {root_env}")
    else:
        print(f"❌ Root .env missing! Copy .env.example to .env")
        return 1
    
    # Verify each service
    for service in ["auth", "agents", "database"]:
        verify_service_config(service)
    
    # Check homepage (can't import Vite config from Python)
    print(f"\n🔍 Verifying homepage configuration...")
    homepage_env = Path(__file__).parent.parent / "homepage" / ".env"
    if homepage_env.exists():
        print(f"  ✅ Homepage .env exists")
        print(f"  ℹ️  Homepage uses vite.config.ts to load from root .env")
    else:
        print(f"  ⚠️  Homepage .env missing (Vite may require it)")
    
    print("\n✨ Configuration verification complete!")
    print("\nNote: Make sure to create .env.secrets files for each service with sensitive data.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())