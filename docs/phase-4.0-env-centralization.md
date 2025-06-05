# Phase 4.0: True Environment Centralization - Implementation Plan

## 🎯 Phase Objectives

Implement TRUE single .env file management for developers with zero exceptions. Scripts handle distribution to services automatically.

**Core Principles:**
- **ONE .env file**: Developers edit exactly one file
- **Zero Fallbacks**: No service can load its own .env
- **Automated Distribution**: Scripts copy values to services
- **No Hidden Loading**: All env access goes through one path
- **Complete Coverage**: Every service, utility, and script follows this

## ✅ Implementation Checklist

Phase 4.0 is complete when:

- [ ] **Phase 4.0.1**: Audit and consolidate all environment variables
- [ ] **Phase 4.0.2**: Create master .env.example with ALL variables
- [ ] **Phase 4.0.3**: Rewrite env_loader to enforce single source
- [ ] **Phase 4.0.4**: Create distribution scripts
- [ ] **Phase 4.0.5**: Update all services to use new pattern
- [ ] **Phase 4.0.6**: Remove all bypass paths
- [ ] **Phase 4.0.7**: Update documentation and tooling
- [ ] **End-to-End**: Developer can manage everything from one .env

## 🏗️ Architecture

### Current State (Broken)
```
Developer manages:
├── .env
├── .env.local
├── auth/.env
├── auth/.env.secrets
├── agents/.env
├── agents/.env.secrets
├── database/.env
├── homepage/.env
└── 10+ more files...
```

### Target State (Fixed)
```
Developer manages:
└── .env (ONLY THIS!)

Scripts generate (git-ignored):
├── auth/.env
├── agents/.env
├── database/.env
└── homepage/.env
```

## 📋 Detailed Implementation Plan

### Phase 4.0.1: Audit All Environment Variables

**Goal**: Find every single environment variable across the entire codebase

#### Step 1: Automated Scan

```python
# scripts/audit_env_vars.py
"""Find all environment variables in the codebase."""

import os
import re
from pathlib import Path
from collections import defaultdict

def find_env_vars():
    """Scan codebase for all environment variable usage."""
    env_vars = defaultdict(set)
    
    patterns = [
        r'os\.environ\.get\(["\'](\w+)["\']\)',
        r'os\.environ\[["\'](\w+)["\']\]',
        r'process\.env\.(\w+)',
        r'import\.meta\.env\.(\w+)',
        r'(\w+):\s*str\s*=\s*Field\(',  # Pydantic fields
    ]
    
    for root, dirs, files in os.walk('.'):
        # Skip node_modules, venv, etc
        dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', 'venv', '__pycache__'}]
        
        for file in files:
            if file.endswith(('.py', '.js', '.ts', '.tsx')):
                filepath = Path(root) / file
                try:
                    content = filepath.read_text()
                    for pattern in patterns:
                        matches = re.findall(pattern, content)
                        for match in matches:
                            env_vars[match].add(str(filepath))
                except:
                    pass
    
    return env_vars

# Generate report
vars_by_file = find_env_vars()
print(f"Found {len(vars_by_file)} unique environment variables")

# Save comprehensive list
with open('docs/all_env_vars.md', 'w') as f:
    f.write("# All Environment Variables\n\n")
    for var, files in sorted(vars_by_file.items()):
        f.write(f"## {var}\n")
        f.write(f"Used in: {len(files)} files\n")
        for file in sorted(files):
            f.write(f"- {file}\n")
        f.write("\n")
```

#### Step 2: Manual Review

Review all .env.example files to catch any missed variables:
- `.env.example`
- `auth/.env.example`
- `auth/.env.secrets.example`
- `agents/.env.secrets.example`
- `database/.env.example`
- `homepage/.env.example`

### Phase 4.0.2: Create Master .env.example

**Goal**: Single file with every environment variable needed

```bash
# .env.example - THE ONLY ENV FILE DEVELOPERS TOUCH

# ================================================
# ENVIRONMENT
# ================================================
ENVIRONMENT=development
DEBUG=True
LOG_LEVEL=INFO

# ================================================
# SERVICE URLS & PORTS
# ================================================
# Local Development
AUTH_SERVICE_URL=http://localhost:8103
AUTH_SERVICE_PORT=8103
AGENTS_SERVICE_URL=http://localhost:8000
AGENTS_SERVICE_PORT=8000
DATABASE_SERVICE_URL=http://localhost:8002
DATABASE_SERVICE_PORT=8002
HOMEPAGE_URL=http://localhost:3456
HOMEPAGE_PORT=3456

# External URLs (for OAuth callbacks etc)
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3456
DOMAIN=localhost

# ================================================
# DATABASES
# ================================================
# PostgreSQL
DATABASE_URL=postgresql://hirecj:hirecj_dev_password@localhost:5435/hirecj
AUTH_DATABASE_URL=postgresql://hirecj:hirecj_dev_password@localhost:5435/hirecj_auth

# Redis
REDIS_URL=redis://localhost:6379
REDIS_SESSION_TTL=86400

# Supabase - ETL/Ticket Data
SUPABASE_CONNECTION_STRING=postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres

# Supabase - Identity Data (Phase 4.5)
IDENTITY_SUPABASE_URL=postgresql://postgres:[password]@db.[identity-project].supabase.co:5432/postgres
IDENTITY_SUPABASE_ANON_KEY=eyJ...

# ================================================
# API KEYS & SECRETS
# ================================================
# LLMs
OPENAI_API_KEY=sk-proj-xxx
ANTHROPIC_API_KEY=sk-ant-api03-xxx

# OAuth
SHOPIFY_CLIENT_ID=xxx
SHOPIFY_CLIENT_SECRET=xxx
SHOPIFY_SCOPES=read_products,read_customers,read_orders

# Session
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=43200

# ================================================
# FEATURES
# ================================================
ENABLE_OAUTH=true
ENABLE_FACT_CHECKING=true
ENABLE_PERFORMANCE_METRICS=true
ENABLE_PROMPT_CACHING=false
ENABLE_LITELLM_CACHE=false

# ================================================
# THIRD PARTY SERVICES
# ================================================
# Sentry
SENTRY_DSN=

# Analytics
ANALYTICS_ENABLED=false

# ================================================
# VITE / FRONTEND
# ================================================
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_AUTH_URL=http://localhost:8103
```

### Phase 4.0.3: Rewrite env_loader

**Goal**: Single source, no fallbacks, no hidden loading

```python
# shared/env_loader.py
"""
Centralized environment loader - SINGLE SOURCE OF TRUTH

This module ensures ALL environment variables come from ONE place:
the root .env file. No fallbacks, no service overrides, no hidden loading.
"""

import os
from pathlib import Path
from typing import Dict, Optional
import sys

# CRITICAL: Only ONE source
ROOT_ENV_FILE = Path(__file__).parent.parent / ".env"

class SingleEnvLoader:
    """Loads environment variables from exactly ONE file."""
    
    def __init__(self):
        self._loaded = False
        self._env_vars: Dict[str, str] = {}
    
    def load(self) -> None:
        """Load environment variables from the single .env file."""
        if self._loaded:
            return
            
        if not ROOT_ENV_FILE.exists():
            print(f"ERROR: {ROOT_ENV_FILE} not found. Run 'make env-setup' first.")
            sys.exit(1)
        
        # Parse .env file
        with open(ROOT_ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    self._env_vars[key] = value
                    # Set in os.environ for compatibility
                    os.environ[key] = value
        
        self._loaded = True
        print(f"✅ Loaded {len(self._env_vars)} variables from {ROOT_ENV_FILE}")
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get an environment variable."""
        if not self._loaded:
            self.load()
        return self._env_vars.get(key, default)
    
    def require(self, key: str) -> str:
        """Get a required environment variable or exit."""
        value = self.get(key)
        if value is None:
            print(f"ERROR: Required environment variable '{key}' not found in .env")
            print(f"Add it to {ROOT_ENV_FILE} and try again.")
            sys.exit(1)
        return value

# Global singleton
env_loader = SingleEnvLoader()

# Compatibility functions
def load_env_for_service(service_name: str) -> None:
    """Legacy compatibility - just loads the single .env file."""
    env_loader.load()

def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable from single source."""
    return env_loader.get(key, default)

def require_env(key: str) -> str:
    """Get required environment variable from single source."""
    return env_loader.require(key)

# Auto-load on import
env_loader.load()
```

### Phase 4.0.4: Distribution Scripts

**Goal**: Automatically distribute variables to services as needed

```python
# scripts/distribute_env.py
"""
Distribute environment variables from single .env to services.

This script reads the master .env file and creates service-specific
.env files with only the variables each service needs.
"""

import os
import sys
from pathlib import Path

# Service variable mappings
SERVICE_VARS = {
    "auth": {
        "direct": [
            "ENVIRONMENT", "DEBUG", "LOG_LEVEL",
            "AUTH_SERVICE_PORT", "AUTH_DATABASE_URL",
            "REDIS_URL", "SECRET_KEY", "JWT_SECRET_KEY",
            "JWT_ALGORITHM", "JWT_EXPIRATION_MINUTES",
            "SHOPIFY_CLIENT_ID", "SHOPIFY_CLIENT_SECRET",
            "SHOPIFY_SCOPES", "FRONTEND_URL", "BACKEND_URL",
            "AGENTS_SERVICE_URL", "DATABASE_SERVICE_URL"
        ]
    },
    "agents": {
        "direct": [
            "ENVIRONMENT", "DEBUG", "LOG_LEVEL",
            "AGENTS_SERVICE_PORT", "REDIS_URL", "REDIS_SESSION_TTL",
            "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
            "SUPABASE_CONNECTION_STRING", "IDENTITY_SUPABASE_URL",
            "IDENTITY_SUPABASE_ANON_KEY", "AUTH_SERVICE_URL",
            "DATABASE_SERVICE_URL", "ENABLE_FACT_CHECKING",
            "ENABLE_PERFORMANCE_METRICS", "ENABLE_PROMPT_CACHING",
            "ENABLE_LITELLM_CACHE"
        ]
    },
    "database": {
        "direct": [
            "ENVIRONMENT", "DEBUG", "LOG_LEVEL",
            "DATABASE_SERVICE_PORT", "DATABASE_URL"
        ]
    },
    "homepage": {
        "direct": [
            "VITE_API_URL", "VITE_WS_URL", "VITE_AUTH_URL"
        ],
        "mappings": {
            "VITE_API_URL": "AGENTS_SERVICE_URL",
            "VITE_WS_URL": lambda vars: vars.get("AGENTS_SERVICE_URL", "").replace("http://", "ws://"),
            "VITE_AUTH_URL": "AUTH_SERVICE_URL"
        }
    }
}

def load_master_env():
    """Load variables from master .env file."""
    env_vars = {}
    env_path = Path(".env")
    
    if not env_path.exists():
        print("ERROR: .env file not found. Copy .env.example to .env first.")
        sys.exit(1)
    
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip().strip('"').strip("'")
    
    return env_vars

def write_service_env(service: str, variables: dict):
    """Write service-specific .env file."""
    service_env_path = Path(service) / ".env"
    
    # Ensure directory exists
    service_env_path.parent.mkdir(exist_ok=True)
    
    with open(service_env_path, 'w') as f:
        f.write(f"# Auto-generated from root .env - DO NOT EDIT\n")
        f.write(f"# Edit the root .env file instead\n\n")
        
        for key, value in sorted(variables.items()):
            f.write(f"{key}={value}\n")
    
    print(f"✅ Created {service_env_path} with {len(variables)} variables")

def distribute_env():
    """Distribute environment variables to all services."""
    print("🔄 Distributing environment variables from .env to services...")
    
    # Load master env
    master_vars = load_master_env()
    print(f"📖 Loaded {len(master_vars)} variables from .env")
    
    # Distribute to each service
    for service, config in SERVICE_VARS.items():
        service_vars = {}
        
        # Direct variables
        for var in config.get("direct", []):
            if var in master_vars:
                service_vars[var] = master_vars[var]
        
        # Mapped variables
        for target, source in config.get("mappings", {}).items():
            if callable(source):
                service_vars[target] = source(master_vars)
            elif source in master_vars:
                service_vars[target] = master_vars[source]
        
        # Write service env
        write_service_env(service, service_vars)
    
    print("\n✅ Environment distribution complete!")

if __name__ == "__main__":
    distribute_env()
```

```bash
# scripts/start_services.sh
#!/bin/bash
# Start services with fresh environment distribution

echo "🚀 Starting HireCJ services..."

# Always distribute env first
echo "📦 Distributing environment variables..."
python scripts/distribute_env.py

# Start services
echo "🔧 Starting services..."
make dev

# Detect tunnels if needed
if [[ "$1" == "--tunnel" ]]; then
    echo "🌐 Detecting tunnels..."
    python shared/detect_tunnels.py
fi
```

### Phase 4.0.5: Update All Services

**Goal**: Every service uses the centralized pattern with no exceptions

#### Update Service Configs

```python
# agents/app/config.py
"""Agent service configuration - uses centralized env."""

from pydantic import BaseSettings, Field
from shared.env_loader import get_env, require_env

class Settings(BaseSettings):
    """Settings loaded from centralized environment."""
    
    # Required settings
    redis_url: str = Field(default_factory=lambda: require_env("REDIS_URL"))
    anthropic_api_key: str = Field(default_factory=lambda: require_env("ANTHROPIC_API_KEY"))
    
    # Optional settings with defaults
    environment: str = Field(default_factory=lambda: get_env("ENVIRONMENT", "development"))
    debug: bool = Field(default_factory=lambda: get_env("DEBUG", "False").lower() == "true")
    
    # Prevent any local env loading
    class Config:
        env_file = None  # CRITICAL: No local .env files
        env_file_encoding = None
        
settings = Settings()
```

#### Fix Utility Files

```python
# agents/app/utils/supabase_util.py
"""Supabase utilities - uses centralized config."""

from shared.env_loader import get_env, require_env
# Remove ALL load_dotenv() calls!

def get_connection_string():
    """Get Supabase connection string from central config."""
    return require_env("SUPABASE_CONNECTION_STRING")
```

#### Fix Homepage/Vite

```typescript
// homepage/vite.config.ts
import { defineConfig } from 'vite';

// Vite will only see variables in its local .env
// which is auto-generated by distribute_env.py
export default defineConfig({
  envDir: '.',  // Use local .env (auto-generated)
  envPrefix: 'VITE_',
});
```

### Phase 4.0.6: Remove All Bypass Paths

**Goal**: No service can accidentally load its own environment

#### Step 1: Delete All Service .env Files

```bash
# scripts/cleanup_old_env.sh
#!/bin/bash
# Remove all service-specific env files that shouldn't be edited

echo "🧹 Cleaning up old .env files..."

# Remove service env files (will be auto-generated)
rm -f auth/.env.local
rm -f auth/.env.secrets
rm -f auth/.env.tunnel
rm -f agents/.env.local  
rm -f agents/.env.secrets
rm -f agents/.env.tunnel
rm -f database/.env.local
rm -f database/.env.tunnel
rm -f homepage/.env.tunnel

# Remove example files that promote the anti-pattern
rm -f auth/.env.example
rm -f auth/.env.secrets.example
rm -f agents/.env.example
rm -f agents/.env.secrets.example
rm -f database/.env.example
rm -f homepage/.env.example

echo "✅ Cleanup complete - only root .env remains"
```

#### Step 2: Add Git Ignores

```gitignore
# .gitignore additions

# Service .env files are auto-generated - never commit
auth/.env
agents/.env
database/.env
homepage/.env

# Only the root .env.example should exist
*/.env.example
*/.env.secrets.example
```

#### Step 3: Add Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash
# Prevent committing service-specific env files

if git diff --cached --name-only | grep -E '(auth|agents|database|homepage)/\.env'; then
    echo "❌ ERROR: Trying to commit service-specific .env files!"
    echo "These files are auto-generated and should not be committed."
    echo "Only edit the root .env file."
    exit 1
fi
```

### Phase 4.0.7: Update Documentation

**Goal**: Clear documentation that enforces the single .env pattern

```markdown
# Environment Configuration

## For Developers: ONE Rule

**You only edit ONE file: `.env` in the root directory**

That's it. No exceptions.

## Setup

1. Copy the example:
   ```bash
   cp .env.example .env
   ```

2. Fill in your values in `.env`

3. Start services (this auto-distributes your config):
   ```bash
   make dev
   # or
   ./scripts/start_services.sh
   ```

## How It Works

1. You edit `.env`
2. `distribute_env.py` copies relevant variables to each service
3. Services read from their auto-generated `.env` files
4. You never touch service-specific files

## Adding New Variables

1. Add to `.env.example` with a descriptive comment
2. Add to the root `.env` 
3. Update `scripts/distribute_env.py` to include it for relevant services
4. That's it!

## Troubleshooting

**Q: A service can't find an environment variable**
A: Add it to SERVICE_VARS in `scripts/distribute_env.py`

**Q: I see old .env files in service directories**
A: Run `./scripts/cleanup_old_env.sh` to remove them

**Q: Can I override a variable for just one service?**
A: No. Use different variable names if services need different values.
```

### Makefile Updates

```makefile
# Root Makefile

# Single env setup - no service copies!
env-setup:
	@echo "📝 Setting up THE environment file..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ Created .env from .env.example"; \
		echo "📝 Edit .env with your configuration"; \
	else \
		echo "✅ .env already exists"; \
	fi

# Clean development environment
clean-env:
	@echo "🧹 Cleaning environment files..."
	@./scripts/cleanup_old_env.sh

# Start with fresh env distribution
dev: env-setup
	@echo "🚀 Starting development environment..."
	@python scripts/distribute_env.py
	@make -j4 dev-agents dev-auth dev-database dev-homepage

# Verify env setup
verify-env:
	@echo "🔍 Verifying environment setup..."
	@python scripts/verify_single_env.py
```

### Verification Script

```python
# scripts/verify_single_env.py
"""Verify the single .env pattern is properly implemented."""

import os
import sys
from pathlib import Path

def verify_single_env():
    """Check that only root .env exists and no bypasses remain."""
    issues = []
    
    # Check root .env exists
    if not Path(".env").exists():
        issues.append("❌ Root .env file missing")
    
    # Check no service .env.example files
    for service in ["auth", "agents", "database", "homepage"]:
        for pattern in [".env.example", ".env.secrets.example", ".env.local"]:
            if (Path(service) / pattern).exists():
                issues.append(f"❌ Found {service}/{pattern} - should not exist")
    
    # Check no load_dotenv usage
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', 'venv'}]
        for file in files:
            if file.endswith('.py'):
                path = Path(root) / file
                if 'env_loader.py' not in str(path):
                    content = path.read_text()
                    if 'load_dotenv' in content:
                        issues.append(f"❌ Found load_dotenv in {path}")
    
    if issues:
        print("❌ Single .env pattern violations found:")
        for issue in issues:
            print(f"  {issue}")
        sys.exit(1)
    else:
        print("✅ Single .env pattern properly implemented!")

if __name__ == "__main__":
    verify_single_env()
```

## 🎯 Success Criteria

1. **Developers edit exactly ONE file**: `/hirecj/.env`
2. **No service has .env.example files**
3. **No code uses load_dotenv() directly**
4. **All environment access goes through shared.env_loader**
5. **Services cannot override or fallback**
6. **make dev automatically distributes configuration**
7. **Git prevents committing service .env files**

## 🚀 Migration Steps

1. Run audit script to find all variables
2. Create comprehensive .env.example
3. Update shared/env_loader.py
4. Create distribute_env.py script
5. Update all service configs
6. Fix all utility files
7. Run cleanup script
8. Update Makefile
9. Test everything
10. Update documentation

This ensures developers have ONE place to manage ALL configuration with zero exceptions.