#!/usr/bin/env python3
"""Check OAuth URL configuration across services."""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_env_files():
    """Check all environment files for URL configuration."""
    print("🔍 Checking environment files...")
    
    # Check root .env
    root_env = Path(__file__).parent.parent / ".env"
    if root_env.exists():
        print(f"\n📄 {root_env}:")
        with open(root_env) as f:
            for line in f:
                if any(key in line for key in ["HOMEPAGE_URL", "FRONTEND_URL", "AUTH_SERVICE_URL"]):
                    print(f"  {line.strip()}")
    
    # Check .env.tunnel
    tunnel_env = Path(__file__).parent.parent / ".env.tunnel"
    if tunnel_env.exists():
        print(f"\n📡 {tunnel_env} (auto-generated):")
        with open(tunnel_env) as f:
            for line in f:
                if any(key in line for key in ["HOMEPAGE_URL", "FRONTEND_URL", "AUTH_SERVICE_URL", "OAUTH_REDIRECT"]):
                    print(f"  {line.strip()}")
    else:
        print("\n⚠️  No .env.tunnel found - run tunnel detection first")

def check_auth_config():
    """Check auth service configuration."""
    print("\n\n🔐 Auth Service Configuration:")
    
    # Import auth config
    try:
        from auth.app.config import settings
        print(f"  frontend_url: {settings.frontend_url}")
        print(f"  homepage_url: {settings.homepage_url}")
        print(f"  oauth_redirect_base_url: {settings.oauth_redirect_base_url}")
        print(f"  auth_service_url: {settings.auth_service_url}")
        
        # Show where OAuth will redirect
        print(f"\n🔄 OAuth will redirect to: {settings.frontend_url}/chat")
        
        # Check if using tunnel URLs
        if "hirecj.ai" in settings.frontend_url:
            print("✅ Using tunnel URLs - OAuth should work correctly")
        else:
            print("⚠️  Using localhost URLs - OAuth may not work from Shopify")
            
    except Exception as e:
        print(f"❌ Error loading auth config: {e}")

if __name__ == "__main__":
    check_env_files()
    check_auth_config()
    
    print("\n\n💡 To fix OAuth redirect issues:")
    print("  1. Make sure tunnel detection has run (check for .env.tunnel)")
    print("  2. Restart auth service to pick up new environment")
    print("  3. Check auth service logs for URL configuration")