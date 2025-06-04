# Environment Configuration Setup

This monorepo uses a hierarchical environment configuration system to minimize duplication and simplify management.

## Structure

```
/hirecj/
├── .env                    # Shared configuration (service URLs, ports, feature flags)
├── .env.local             # Local overrides (optional, gitignored)
├── .env.tunnel            # Auto-generated tunnel URLs (gitignored)
├── auth/
│   ├── .env               # Service-specific overrides (minimal)
│   └── .env.secrets       # Sensitive auth credentials (gitignored)
├── agents/
│   ├── .env               # Service-specific overrides (minimal)
│   └── .env.secrets       # API keys (gitignored)
└── homepage/
    └── .env               # Required by Vite, maps from shared config
```

## Quick Start

1. **Copy the root example file:**
   ```bash
   cp .env.example .env
   ```

2. **Create service secrets:**
   ```bash
   # Auth service secrets
   cp auth/.env.secrets.example auth/.env.secrets
   # Edit auth/.env.secrets with your Shopify OAuth credentials

   # Agents service secrets
   cp agents/.env.secrets.example agents/.env.secrets
   # Edit agents/.env.secrets with your OpenAI/Anthropic API keys
   ```

3. **That's it!** The services will automatically load configuration in this order:
   - Root `.env` (shared config)
   - Root `.env.local` (local overrides if exists)
   - Root `.env.tunnel` (auto-generated tunnel URLs)
   - Service `.env.secrets` (sensitive data)
   - Service `.env` (service-specific overrides)

## Key Benefits

- **Single source of truth** for service URLs and ports
- **No duplication** of configuration across services
- **Secrets stay isolated** in service-specific files
- **Tunnel detection** only needs to update one file
- **Easy local development** - just copy and edit root `.env`

## Environment Variables

### Shared Configuration (root `.env`)
- Service URLs and ports
- Database connections
- Feature flags
- Model configurations
- CORS settings

### Service Secrets (`.env.secrets`)
- **Auth**: JWT secrets, OAuth client credentials
- **Agents**: OpenAI/Anthropic API keys
- **Homepage**: (uses root config via Vite)

## Verification

To verify that your environment configuration is working correctly:

```bash
python scripts/verify_env_config.py
```

This will check:
- Root `.env` file exists
- Each service can load configuration
- Service URLs are properly shared
- Secrets are configured (without displaying them)

## For Production

1. Set environment variables in your deployment platform
2. Ensure secrets are properly secured
3. Update service URLs to production values
4. Disable debug mode and adjust log levels

## Migration from Old Structure

If you're upgrading from the old structure where each service had its own complete `.env`:

1. Your existing configurations have been preserved
2. Secrets have been moved to `.env.secrets` files
3. Shared configuration is now in the root `.env`
4. Service `.env` files now only contain overrides
5. Run the verification script to ensure everything works