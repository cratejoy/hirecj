# HireCJ Backend Configuration Guide

## Overview

All backend feature flags and settings are centralized in `app/config.py` following the North Star principle of "Simplify, Simplify, Simplify". This provides a single source of truth for all configuration.

## Feature Flags

All feature flags can be controlled via environment variables:

### Caching Configuration
- `ENABLE_PROMPT_CACHING` (default: `false`) - Controls Anthropic prompt caching headers
- `ENABLE_LITELLM_CACHE` (default: `false`) - Controls LiteLLM response caching (Redis/in-memory)
- `ENABLE_CACHE_WARMING` (default: `false`) - Controls startup cache pre-warming

### Feature Toggles
- `ENABLE_FACT_CHECKING` (default: `true`) - Controls fact checking features
- `ENABLE_PERFORMANCE_METRICS` (default: `true`) - Controls performance tracking
- `ENABLE_VERBOSE_LOGGING` (default: `false`) - Controls LiteLLM debug logging

## Usage

### 1. Global Settings
All components automatically respect global settings from `app.config.settings`:

```python
from app.config import settings

if settings.enable_litellm_cache:
    # Enable caching logic
```

### 2. Environment Variables
Override any setting via environment variables:
```bash
export ENABLE_LITELLM_CACHE=true
export ENABLE_PROMPT_CACHING=true
export ENABLE_VERBOSE_LOGGING=false
```

### 3. Component Overrides
Components can accept explicit overrides but default to global settings:

```python
# In CJ Agent
def __init__(self, enable_caching: bool = None):
    # Use global setting if not explicitly provided
    self.enable_caching = enable_caching if enable_caching is not None else settings.enable_prompt_caching
```

## Architecture

### Centralized Configuration (`app/config.py`)
- Single `Settings` class using Pydantic
- Environment variable support with defaults
- Type-safe configuration

### Automatic Wiring
- `app/cache_config.py` - Respects `enable_litellm_cache`
- `app/agents/cj_agent.py` - Respects `enable_prompt_caching`
- `src/api/server.py` - Respects all logging and cache settings
- `app/main.py` - Respects cache warming settings

## Adding New Settings

1. Add to `app/config.py`:
```python
class Settings(BaseSettings):
    # Feature Flags
    enable_new_feature: bool = Field(False, env="ENABLE_NEW_FEATURE")
```

2. Use in your component:
```python
from app.config import settings

if settings.enable_new_feature:
    # New feature logic
```

## Best Practices

1. **Always use global settings** - Don't hardcode feature flags
2. **Provide explicit overrides sparingly** - Only when needed for testing
3. **Document new settings** - Add to this file when adding new flags
4. **Follow naming convention** - `enable_` prefix for feature flags
5. **Set safe defaults** - New features should be `False` by default
