# Audit Results: Breaks from Single .env Pattern

## 1. Multiple .env Files That Developers Need to Manage

### Service-Specific .env Files Found:
- `agents/.env`
- `agents/.env.secrets`
- `agents/.env.tunnel`
- `auth/.env`
- `auth/.env.local`
- `auth/.env.secrets`
- `auth/.env.tunnel`
- `database/.env.tunnel`
- `homepage/.env.minimal`
- `homepage/.env.tunnel`

### Example Files That Suggest Multiple .env Creation:
- `agents/.env.secrets.example`
- `auth/.env.example`
- `auth/.env.secrets.example`
- `database/.env.example`
- `homepage/.env.example`

## 2. Code That Directly Reads .env Files Without Using shared/env_loader.py

### Utility Files Using dotenv Directly:
- `agents/app/utils/supabase_util.py` - Uses `load_dotenv()` directly
- `agents/app/utils/shopify_util.py` - Uses `load_dotenv()` directly
- `agents/app/utils/freshdesk_util.py` - Uses `load_dotenv()` directly

### Knowledge Service Scripts:
- `knowledge/src/scripts/test_lightrag.py`
- `knowledge/src/scripts/simple_demo.py`
- `knowledge/src/scripts/lightrag_transcripts_demo.py`

## 3. Documentation/Instructions for Multiple .env Files

### Root Makefile (env-setup target):
```makefile
env-setup:
	@echo "📝 Setting up environment files..."
	cp .env.example .env
	cp auth/.env.example auth/.env
	cp agents/.env.example agents/.env
	cp homepage/.env.example homepage/.env
	cp database/.env.example database/.env
```

This explicitly instructs developers to create separate .env files for each service.

### README Files:
- `auth/README.md` - Mentions creating `.env.local` for tunnel configuration
- `agents/README.md` - References service configuration but uses env_loader
- `homepage/README.md` - Mentions creating `.env` file

## 4. Special Cases

### Homepage (Vite):
- `homepage/vite.config.ts` - Has custom logic to load from parent directory and .env.tunnel
- This is partially following the pattern but has custom implementation due to Vite requirements

### Services Using env_loader Correctly:
- `agents/app/config.py` - Uses `load_env_for_service("agents")`
- `auth/app/config.py` - Uses `load_env_for_service("auth")`
- `database/app/config.py` - Uses `load_env_for_service("database")`

## 5. Environment Variables Duplicated Across Services

Based on the example files, these variables appear in multiple places:
- `OPENAI_API_KEY` - in agents/.env.secrets.example
- `SHOPIFY_CLIENT_ID/SECRET` - in auth/.env.secrets.example
- Service URLs (AGENTS_SERVICE_URL, AUTH_SERVICE_URL, etc.) - should be in root .env only

## 6. Services That Bypass Centralized Configuration

### Direct Environment Variable Access:
- Utility files in agents service bypass the settings object
- Knowledge service scripts don't use any centralized config
- Homepage has its own Vite-based configuration system

## 7. Hardcoded Configuration

Some services have hardcoded defaults that should potentially be in .env:
- Database connection strings in config files
- Default ports scattered across config files
- API endpoints

## Summary of Major Issues:

1. **Makefile actively promotes creating multiple .env files** via the `env-setup` target
2. **Utility files bypass the centralized config** and use `load_dotenv()` directly
3. **Knowledge service has no integration** with the shared env_loader system
4. **Homepage requires special handling** due to Vite but could be better integrated
5. **Multiple .env.tunnel files** exist when there should only be one at root
6. **Service-specific .env files still exist** despite having env_loader
7. **No enforcement or validation** that services are using the centralized pattern