"""
Centralized environment loader - SINGLE SOURCE OF TRUTH

This module ensures ALL environment variables come from ONE place:
the root .env file. No fallbacks, no service overrides, no hidden loading.

Phase 4.0: True Environment Centralization
"""

import os
from pathlib import Path
from typing import Dict, Optional, Set
import sys

# CRITICAL: Only ONE source
ROOT_ENV_FILE = Path(__file__).parent.parent / ".env"

class SingleEnvLoader:
    """Loads environment variables from exactly ONE file."""
    
    def __init__(self):
        self._loaded = False
        self._env_vars: Dict[str, str] = {}
        self._tunnel_vars: Dict[str, str] = {}
    
    def load(self) -> None:
        """Load environment variables from the single .env file."""
        if self._loaded:
            return
            
        if not ROOT_ENV_FILE.exists():
            print(f"ERROR: {ROOT_ENV_FILE} not found.")
            print("Run 'cp .env.master.example .env' and configure your environment.")
            sys.exit(1)
        
        # Parse .env file
        self._load_file(ROOT_ENV_FILE, self._env_vars)
        
        # Load tunnel vars if they exist (auto-generated, read-only)
        tunnel_file = ROOT_ENV_FILE.parent / ".env.tunnel"
        if tunnel_file.exists():
            self._load_file(tunnel_file, self._tunnel_vars)
            print(f"✅ Loaded tunnel configuration from {tunnel_file}")
        
        # Apply to os.environ (tunnel vars override base vars)
        for key, value in self._env_vars.items():
            os.environ[key] = value
        for key, value in self._tunnel_vars.items():
            os.environ[key] = value
        
        self._loaded = True
        total_vars = len(self._env_vars) + len(self._tunnel_vars)
        print(f"✅ Loaded {total_vars} variables from {ROOT_ENV_FILE}")
    
    def _load_file(self, filepath: Path, target_dict: Dict[str, str]) -> None:
        """Parse an env file into the target dictionary."""
        with open(filepath) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse KEY=VALUE
                if '=' not in line:
                    print(f"WARNING: Invalid line {line_num} in {filepath}: {line}")
                    continue
                
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Remove quotes if present
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                
                target_dict[key] = value
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get an environment variable."""
        if not self._loaded:
            self.load()
        
        # Tunnel vars take precedence
        if key in self._tunnel_vars:
            return self._tunnel_vars[key]
        
        return self._env_vars.get(key, default)
    
    def require(self, key: str) -> str:
        """Get a required environment variable or exit."""
        value = self.get(key)
        if value is None:
            print(f"ERROR: Required environment variable '{key}' not found")
            print(f"Add it to {ROOT_ENV_FILE} and try again.")
            sys.exit(1)
        return value
    
    def get_service_vars(self, service_name: str) -> Dict[str, str]:
        """Get all variables for a specific service (for distribution)."""
        if not self._loaded:
            self.load()
        
        # Combine base and tunnel vars
        all_vars = {}
        all_vars.update(self._env_vars)
        all_vars.update(self._tunnel_vars)
        
        return all_vars

# Global singleton
env_loader = SingleEnvLoader()

# ============================================
# LEGACY COMPATIBILITY FUNCTIONS
# ============================================
# These maintain API compatibility during migration

def load_env_for_service(service_name: str) -> None:
    """
    Legacy compatibility - just loads the single .env file.
    Service name is ignored since we have one source.
    """
    env_loader.load()

def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable from single source."""
    return env_loader.get(key, default)

def require_env(key: str) -> str:
    """Get required environment variable from single source."""
    return env_loader.require(key)

def load_dotenv(*args, **kwargs) -> None:
    """
    Override for any direct load_dotenv calls.
    This ensures they go through our single source.
    """
    env_loader.load()

# Auto-load on import
env_loader.load()"""
Centralized environment loader - SINGLE SOURCE OF TRUTH

This module ensures ALL environment variables come from ONE place:
the root .env file. No fallbacks, no service overrides, no hidden loading.

The logic here is now simplified because this `shared` module lives at the
top level of the repository.
"""

import os
from pathlib import Path
from typing import Dict, Optional, Set
import sys

# Get monorepo root (the parent of this file's directory)
MONOREPO_ROOT = Path(__file__).parent.parent

# CRITICAL: Only ONE source
ROOT_ENV_FILE = MONOREPO_ROOT / ".env"
TUNNEL_ENV_FILE = MONOREPO_ROOT / ".env.tunnel"


class SingleEnvLoader:
    """Loads environment variables from the root .env and .env.tunnel files."""
    
    def __init__(self):
        self._loaded = False
        self._env_vars: Dict[str, str] = {}
        self._tunnel_vars: Dict[str, str] = {}
    
    def load(self) -> None:
        """Load environment variables into os.environ."""
        if self._loaded:
            return
            
        # 1. Load from the root .env file
        if ROOT_ENV_FILE.exists():
            self._load_file(ROOT_ENV_FILE, self._env_vars)
        else:
            # In a deployed environment (like Heroku), env vars are set directly.
            # Only fail if the file is missing in a local environment.
            if not os.environ.get('DYNO'):
                print(f"ERROR: Root configuration file '{ROOT_ENV_FILE}' not found.", file=sys.stderr)
                print("Please copy '.env.master.example' to '.env' and configure it.", file=sys.stderr)
                sys.exit(1)

        # 2. Load from the auto-generated .env.tunnel file, which overrides .env
        if TUNNEL_ENV_FILE.exists():
            self._load_file(TUNNEL_ENV_FILE, self._tunnel_vars)
            print(f"✅ Loaded tunnel configuration from {TUNNEL_ENV_FILE}")
        
        # 3. Apply to os.environ, with tunnel vars taking precedence
        for key, value in self._env_vars.items():
            os.environ.setdefault(key, value)
        for key, value in self._tunnel_vars.items():
            os.environ[key] = value
        
        self._loaded = True
        total_vars = len(self._env_vars) + len(self._tunnel_vars)
        print(f"✅ Loaded {total_vars} variables from config files.")
    
    def _load_file(self, filepath: Path, target_dict: Dict[str, str]) -> None:
        """Parse a .env file into the target dictionary."""
        with open(filepath) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' not in line:
                    print(f"WARNING: Invalid line {line_num} in {filepath}: {line}", file=sys.stderr)
                    continue
                
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Remove quotes
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                
                target_dict[key] = value

# Global singleton instance
env_loader = SingleEnvLoader()

# ============================================
# LEGACY COMPATIBILITY FUNCTIONS
# ============================================

def load_env_for_service(service_name: str) -> Optional[str]:
    """
    Legacy compatibility function. Loads the environment and returns the path
    to the main .env file for Pydantic, or None if it doesn't exist.
    """
    env_loader.load()
    
    # Ensure the monorepo root is in the Python path for imports
    if str(MONOREPO_ROOT) not in sys.path:
        sys.path.insert(0, str(MONOREPO_ROOT))

    return str(ROOT_ENV_FILE) if ROOT_ENV_FILE.exists() else None

def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get an environment variable from the single source, falling back to os.environ."""
    env_loader.load()
    # os.environ is now the single source of truth after loading
    return os.environ.get(key, default)

# Auto-load on import to ensure env vars are set early
env_loader.load()
