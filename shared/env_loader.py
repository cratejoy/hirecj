"""
Hierarchical Environment Configuration Loader

Provides a consistent way to load environment variables across all services
in the monorepo, following the hierarchy (later files override earlier):
1. Root .env (shared configuration)
2. Service .env.secrets (sensitive data)
3. Service .env (service-specific overrides)
4. Root .env.local (local overrides)
5. Root .env.tunnel (auto-generated tunnel URLs - highest priority)
"""

from pathlib import Path
from typing import List, Optional
import os
import sys


def get_monorepo_root() -> Path:
    """Get the monorepo root directory."""
    # This file is in /shared, so parent is the monorepo root
    return Path(__file__).parent.parent


def get_env_files(service_name: Optional[str] = None) -> List[Path]:
    """
    Get ordered list of env files to load for a service.
    
    Args:
        service_name: Name of the service (auth, agents, homepage, database).
                     If None, only returns root env files.
    
    Returns:
        List of Path objects to env files in load order.
    """
    root = get_monorepo_root()
    env_files = []
    
    # Load order (later files override earlier ones in Pydantic):
    # 1. Root .env - base shared configuration
    if (root / ".env").exists():
        env_files.append(root / ".env")
    
    # 2. Service-specific files
    if service_name:
        service_dir = root / service_name
        service_files = [
            service_dir / ".env.secrets",  # Service secrets
            service_dir / ".env",          # Service overrides
        ]
        
        for file in service_files:
            if file.exists():
                env_files.append(file)
    
    # 3. Local overrides (higher priority)
    if (root / ".env.local").exists():
        env_files.append(root / ".env.local")
    
    # 4. Tunnel URLs (highest priority - loaded last)
    if (root / ".env.tunnel").exists():
        env_files.append(root / ".env.tunnel")
    
    return env_files


def get_pydantic_env_files(service_name: str) -> List[str]:
    """
    Get env file paths formatted for Pydantic BaseSettings.
    
    Args:
        service_name: Name of the service (auth, agents, homepage, database)
    
    Returns:
        List of relative paths from the service directory.
    """
    root = get_monorepo_root()
    service_dir = root / service_name
    env_files = []
    
    # Calculate relative paths from service directory to root env files
    for file in get_env_files(service_name):
        try:
            # Try to get relative path from service directory
            if file.is_absolute():
                rel_path = os.path.relpath(file, service_dir)
                env_files.append(rel_path)
            else:
                env_files.append(str(file))
        except ValueError:
            # If on different drives (Windows), use absolute path
            env_files.append(str(file))
    
    return env_files


def ensure_python_path():
    """Ensure the monorepo root and shared directory are in Python path."""
    root = get_monorepo_root()
    shared_dir = root / "shared"
    
    # Add to Python path if not already there
    root_str = str(root)
    shared_str = str(shared_dir)
    
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    
    if shared_str not in sys.path:
        sys.path.insert(0, shared_str)


# Convenience function for services to use
def load_env_for_service(service_name: str) -> List[str]:
    """
    Load environment files for a service and return paths for Pydantic.
    
    This is the main function services should use in their config.py files.
    
    Args:
        service_name: Name of the service (auth, agents, homepage, database)
    
    Returns:
        List of env file paths for Pydantic BaseSettings
    """
    ensure_python_path()
    return get_pydantic_env_files(service_name)