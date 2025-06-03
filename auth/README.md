# HireCJ Auth Service

A clean, extensible authentication and OAuth service for HireCJ platform, supporting both user authentication and third-party data integrations.

## Overview

This service provides a unified interface for:
- 🔐 **User Authentication** - Login with OAuth providers (Shopify, Google, etc.)
- 🔌 **Data Integrations** - OAuth connections for data ingestion (Klaviyo, Google Analytics, etc.)
- 🎯 **Token Management** - Secure storage and refresh of OAuth tokens
- 🚀 **Multi-Provider Support** - Pluggable architecture for adding new providers

## Features

- **Dual Purpose OAuth** - Supports both login flows and data access flows
- **Provider Registry** - Easy to add new OAuth providers
- **Secure Token Storage** - Encrypted credential management
- **Automatic Token Refresh** - Handles OAuth token lifecycle
- **Simple API** - Clean REST endpoints for all operations

## Quick Start

```bash
# Install dependencies
make install

# Run development server
make dev

# Server will be available at http://localhost:8103
# API documentation at http://localhost:8103/docs
```

## API Endpoints

### Health Check
- `GET /health` - Service health check
- `GET /` - API information

### Authentication
- `POST /api/v1/auth/login/{provider}` - Initiate OAuth login flow
- `GET /api/v1/auth/callback/{provider}` - OAuth callback handler
- `POST /api/v1/auth/logout` - Logout user
- `GET /api/v1/auth/session` - Get current session info

### OAuth Connections (for data integrations)
- `GET /api/v1/oauth/providers` - List available OAuth providers
- `POST /api/v1/oauth/connect/{provider}` - Start OAuth connection flow
- `GET /api/v1/oauth/callback/{provider}` - OAuth callback for data connections
- `DELETE /api/v1/oauth/disconnect/{provider}` - Disconnect OAuth integration
- `POST /api/v1/oauth/refresh/{provider}` - Refresh OAuth token

## Supported Providers

### Login Providers
- **Shopify** - Login with Shopify account (merchant authentication)
- More coming soon...

### Data Integration Providers
- **Klaviyo** - Email marketing data
- **Google Analytics** - Website analytics
- **Freshdesk** - Customer support data
- More coming soon...

## Adding New Providers

1. Create a new provider in `app/providers/`
2. Inherit from appropriate base class (`LoginProvider` or `DataProvider`)
3. Implement required OAuth methods
4. Register in provider registry

Example:
```python
from app.providers.base import LoginProvider

class ShopifyProvider(LoginProvider):
    """Shopify OAuth provider for merchant login."""
    
    def __init__(self):
        super().__init__(
            name="shopify",
            client_id=settings.shopify_client_id,
            client_secret=settings.shopify_client_secret,
            authorize_url="https://{shop}.myshopify.com/admin/oauth/authorize",
            token_url="https://{shop}.myshopify.com/admin/oauth/access_token",
            scopes=["read_products", "read_orders"]
        )
```

## Configuration

Environment variables:
- `APP_HOST` - Server host (default: 0.0.0.0)
- `APP_PORT` - Server port (default: 8003)
- `DATABASE_URL` - PostgreSQL connection string
- `JWT_SECRET` - Secret key for JWT tokens
- `ENCRYPTION_KEY` - Key for encrypting stored credentials

Provider-specific:
- `SHOPIFY_CLIENT_ID` - Shopify app client ID
- `SHOPIFY_CLIENT_SECRET` - Shopify app client secret
- `KLAVIYO_CLIENT_ID` - Klaviyo OAuth client ID
- `KLAVIYO_CLIENT_SECRET` - Klaviyo OAuth client secret

## Development

```bash
# Run tests
make test

# Run linter
make lint

# Clean build files
make clean
```

## 🌐 Ngrok Tunnel Setup (Local OAuth Testing)

Testing OAuth flows locally requires a public URL. We've integrated ngrok tunnel support for seamless development.

### First-Time Setup

1. **Install ngrok**: https://ngrok.com/download
2. **Configure your domain**: 
   ```bash
   # Set up your ngrok authtoken (if not already done)
   ngrok config add-authtoken YOUR_AUTH_TOKEN
   ```
3. **Configure the app**:
   ```bash
   make setup-tunnel
   ```
4. **Edit `.env.local`** and set your `NGROK_DOMAIN`

### Development with Tunnel

```bash
# Start server + tunnel together
make dev-tunnel

# Or run them separately:
make dev          # In terminal 1
make tunnel       # In terminal 2

# Check tunnel status
make tunnel-status

# Get OAuth callback URLs
make tunnel-info
```

### How It Works

1. **Automatic Detection**: When running with tunnel, the app automatically detects the public URL
2. **Dynamic OAuth URLs**: OAuth callback URLs use your tunnel domain automatically
3. **Smart Fallback**: Works without tunnel for non-OAuth development
4. **Team Friendly**: Each developer can use their own ngrok domain

### Example Workflow

```bash
# 1. Start development with tunnel
make dev-tunnel

# 2. Get your OAuth URLs
make tunnel-info
# Output:
# 🔐 OAuth Callback URLs:
#   Shopify: https://your-domain.ngrok.io/api/v1/auth/callback/shopify
#   Google:  https://your-domain.ngrok.io/api/v1/auth/callback/google
#   ...

# 3. Copy these URLs to your OAuth app settings

# 4. Test OAuth flows with real providers!
```

### Custom Domains

For consistent URLs across sessions:
1. Get a reserved ngrok domain or use a custom domain
2. Set it in `.env.local`:
   ```
   NGROK_DOMAIN=your-auth.example.com
   ```

### Shopify OAuth Setup

1. Go to https://partners.shopify.com
2. Create or select your app
3. Under "App setup" → "URLs":
   - **App URL**: `https://your-domain.ngrok.io` (or production URL)
   - **Allowed redirection URL(s)**: Add your callback URL from `make tunnel-info`
     - For local dev: `https://your-domain.ngrok.io/api/v1/auth/callback/shopify`
     - For production: `https://auth.hirecj.ai/api/v1/auth/callback/shopify`
4. Copy your credentials to `.env.local`

## Architecture Notes

Following HireCJ North Star principles:
- **Simplicity** - One clear way to add providers
- **No Cruft** - Minimal dependencies, clean interfaces
- **Type Safety** - Full typing with Pydantic models
- **Backend-Driven** - All OAuth complexity handled server-side
- **Single Source of Truth** - One place for auth state

## Security

- JWT tokens for session management
- Encrypted storage of OAuth credentials
- PKCE flow for public clients
- Automatic token refresh before expiry
- Secure session handling

## License

Copyright © 2025 Cratejoy, Inc. All rights reserved.