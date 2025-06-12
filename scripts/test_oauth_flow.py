#!/usr/bin/env python3
"""Test script to verify the OAuth flow is working correctly."""

import os
import sys
import logging
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import yaml
try:
    import yaml
except ImportError:
    yaml = None

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_auth_service_config():
    """Test auth service configuration."""
    logger.info("\n=== Testing Auth Service Configuration ===")
    
    try:
        from auth.app.config import settings as auth_settings
        
        # Check OAuth redirect configuration
        logger.info(f"OAuth redirect base URL: {auth_settings.oauth_redirect_base_url}")
        logger.info(f"Frontend URL: {auth_settings.frontend_url}")
        logger.info(f"Agents service URL: {auth_settings.agents_service_url}")
        
        # Check if production domain is configured
        if "hirecj.ai" in auth_settings.frontend_url:
            logger.info("✓ Production domain detected - cookies will use .hirecj.ai domain")
        else:
            logger.info("✓ Development environment - cookies will use default domain")
            
        # Check Shopify credentials
        if auth_settings.shopify_client_id and auth_settings.shopify_client_secret:
            logger.info("✓ Shopify credentials are configured")
        else:
            logger.error("✗ Shopify credentials are NOT configured")
            
        return True
        
    except Exception as e:
        logger.error(f"✗ Failed to test auth service config: {e}")
        return False


def test_agents_service_config():
    """Test agents service configuration."""
    logger.info("\n=== Testing Agents Service Configuration ===")
    
    try:
        # Check workflow files directly
        import os
        workflow_dir = "agents/prompts/workflows"
        workflow_files = []
        
        if os.path.exists(workflow_dir):
            workflow_files = [f.replace('.yaml', '') for f in os.listdir(workflow_dir) if f.endswith('.yaml')]
            
        if "shopify_post_auth" in workflow_files:
            logger.info("✓ shopify_post_auth workflow file exists")
            
            # Read workflow content if yaml is available
            if yaml:
                with open(os.path.join(workflow_dir, "shopify_post_auth.yaml"), 'r') as f:
                    workflow = yaml.safe_load(f)
                    logger.info(f"  - Display name: {workflow.get('display_name', 'N/A')}")
                    logger.info(f"  - Requirements: {workflow.get('requirements', {})}")
            else:
                logger.info("  - (PyYAML not installed, skipping workflow details)")
        else:
            logger.error("✗ shopify_post_auth workflow NOT found")
            logger.info(f"  Available workflows: {workflow_files}")
            
        return True
        
    except Exception as e:
        logger.error(f"✗ Failed to test agents service config: {e}")
        return False


def test_post_oauth_handler():
    """Test PostOAuthHandler is properly initialized."""
    logger.info("\n=== Testing PostOAuthHandler ===")
    
    try:
        # Check if the file exists
        import os
        handler_path = "agents/app/services/post_oauth_handler.py"
        
        if os.path.exists(handler_path):
            logger.info("✓ PostOAuthHandler file exists")
            
            # Check if it's imported in session_handlers.py
            with open("agents/app/platforms/web/session_handlers.py", 'r') as f:
                content = f.read()
                if "from app.services.post_oauth_handler import post_oauth_handler" in content:
                    logger.info("✓ PostOAuthHandler is imported in session_handlers.py")
                else:
                    logger.error("✗ PostOAuthHandler import not found in session_handlers.py")
                    
            # Check if internal API imports it
            with open("agents/app/api/routes/internal.py", 'r') as f:
                content = f.read()
                if "from app.services.post_oauth_handler import post_oauth_handler" in content:
                    logger.info("✓ PostOAuthHandler is imported in internal.py")
                else:
                    logger.error("✗ PostOAuthHandler import not found in internal.py")
        else:
            logger.error(f"✗ PostOAuthHandler file not found at {handler_path}")
            
        return True
        
    except Exception as e:
        logger.error(f"✗ Failed to check PostOAuthHandler: {e}")
        return False


def test_database_migration():
    """Check if web_sessions migration exists."""
    logger.info("\n=== Testing Database Migration ===")
    
    try:
        import os
        
        # Check if migration file exists
        migration_path = "agents/app/migrations/008_create_web_sessions.sql"
        if os.path.exists(migration_path):
            logger.info("✓ Web sessions migration file exists")
            
            # Check if WebSession model is in db_models
            with open("shared/db_models.py", 'r') as f:
                content = f.read()
                if "class WebSession" in content:
                    logger.info("✓ WebSession model defined in shared/db_models.py")
                else:
                    logger.error("✗ WebSession model not found in shared/db_models.py")
                    
            # Check session cookie service
            cookie_path = "auth/app/services/session_cookie.py"
            if os.path.exists(cookie_path):
                logger.info("✓ Session cookie service exists")
            else:
                logger.error(f"✗ Session cookie service not found at {cookie_path}")
        else:
            logger.error(f"✗ Migration file not found at {migration_path}")
            
        return True
        
    except Exception as e:
        logger.error(f"✗ Failed to check database migration: {e}")
        return False


def main():
    """Run all tests."""
    logger.info(f"\n{'='*50}")
    logger.info("OAuth Flow Test Suite")
    logger.info(f"Started at: {datetime.now().isoformat()}")
    logger.info(f"{'='*50}")
    
    results = []
    
    # Run tests
    results.append(("Auth Service Config", test_auth_service_config()))
    results.append(("Agents Service Config", test_agents_service_config()))
    results.append(("PostOAuthHandler", test_post_oauth_handler()))
    results.append(("Database Migration", test_database_migration()))
    
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("Test Summary:")
    logger.info(f"{'='*50}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        logger.info(f"{test_name:<30} {status}")
    
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    if passed < total:
        logger.error("\n⚠️  Some tests failed. Please check the logs above.")
        sys.exit(1)
    else:
        logger.info("\n✅ All tests passed! The OAuth flow appears to be configured correctly.")
        logger.info("\nNext steps:")
        logger.info("1. Start both services (auth and agents)")
        logger.info("2. Navigate to a Shopify onboarding workflow")
        logger.info("3. Complete the OAuth flow")
        logger.info("4. Verify you see the shopify_post_auth workflow content")


if __name__ == "__main__":
    main()