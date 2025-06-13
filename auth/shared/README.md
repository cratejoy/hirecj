# Shared Utilities

This directory contains code shared across all HireCJ services.

## Contents

- `logging_config.py` - Unified logging configuration
- `config_base.py` - Base Pydantic configuration class

## Usage

### Logging

```python
from shared.logging_config import setup_logging, get_logger

# In your service's main.py
setup_logging("agents", "DEBUG")

# In any module
logger = get_logger(__name__)
logger.info("Service started")
```

### Configuration

```python
from shared.config_base import ServiceConfig

class AgentsConfig(ServiceConfig):
    """Configuration for agents service."""
    service_name: str = "agents"
    port: int = 8000
    
    # Add service-specific config here
    max_workers: int = 4

# Usage
config = AgentsConfig()
print(f"Starting {config.service_name} on {config.get_bind_address()}")
```

## Adding New Shared Code

1. Create new module in this directory
2. Add appropriate docstrings
3. Update this README
4. Import in services as needed

## Note

To use shared code in services during development, you may need to:
- Add the parent directory to PYTHONPATH
- Or use symlinks (handled by migration script)
- Or install in editable mode: `pip install -e ../shared`