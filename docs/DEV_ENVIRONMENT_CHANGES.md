# Development Environment Changes

This document outlines significant development environment changes made during the Shopify OAuth implementation (Phase 3.7) and subsequent fixes (Phase 5).

## Summary of Changes

### 1. New Required Environment Variables

#### Auth Service
```bash
# Required for Shopify OAuth flow
SHOPIFY_CLIENT_ID=your_client_id_here
SHOPIFY_CLIENT_SECRET=your_client_secret_here
```

These must be added to `auth/.env.secrets` for the OAuth flow to work.

### 2. Environment Loading Order Fix

The environment loading system now properly respects precedence:

1. Service `.env` (base defaults)
2. Root `.env` (shared configuration)
3. Root `.env.local` (local overrides if exists)
4. **Root `.env.tunnel` (highest priority - auto-generated tunnel URLs)**
5. Service `.env.secrets` (sensitive data)

Key changes:
- Added `env_ignore_empty=True` to all Pydantic SettingsConfigDict
- Prevents empty strings from overriding actual values
- Ensures tunnel URLs properly override localhost defaults

### 3. OAuth Redirect URL Configuration

The auth service now intelligently determines frontend URLs:

```python
# In auth/app/config.py
def __init__(self, **kwargs):
    super().__init__(**kwargs)
    # If homepage_url is set and looks like a tunnel URL, use it for frontend_url
    if self.homepage_url and ("ngrok" in self.homepage_url or "hirecj.ai" in self.homepage_url):
        self.frontend_url = self.homepage_url
```

This ensures OAuth callbacks redirect to the correct frontend URL when using tunnels.

### 4. CORS Configuration Updates

Both agents and auth services now:
- Include both `frontend_url` AND `homepage_url` in allowed origins
- Automatically detect and allow hirecj.ai domains
- Properly handle WebSocket CORS for WSS connections

### 5. Debug Interface

A new browser console debug interface is available:

```javascript
// Available commands
cj.debug()    // Full state snapshot
cj.session()  // Session & auth details
cj.prompts()  // Recent prompts to CJ
cj.context()  // Conversation context
cj.events()   // Start live event stream
cj.stop()     // Stop event stream
cj.help()     // Show help
```

Backend changes:
- New `debug_request` WebSocket message handler
- Safe attribute access with getattr() defaults
- Returns session, state, metrics, and prompt data

### 6. JSON Serialization Fix

Fixed datetime serialization in merchant storage:

```python
# When creating merchants
"created_at": datetime.utcnow().isoformat()  # Not datetime object

# In merchant storage - removed datetime conversion
# Keep datetime as ISO string for consistency
```

## OAuth Testing Requirements

### Prerequisites
1. **Shopify Partner Account** - Required for OAuth app creation
2. **Tunnels Required** - OAuth won't work with localhost redirects
3. **App Configuration** - Redirect URLs must match your tunnel URLs

### Setting Up OAuth

1. Create a Shopify Partner account
2. Create a development app
3. Configure redirect URLs:
   ```
   https://your-auth-tunnel.ngrok.app/api/v1/shopify/callback
   ```
4. Add credentials to `auth/.env.secrets`

### Common Issues and Solutions

**Issue: Redirect to localhost:3456 after OAuth**
- **Cause**: Frontend URL not properly detected
- **Fix**: Ensure `.env.tunnel` is generated and contains HOMEPAGE_URL

**Issue: JSON serialization error**
- **Cause**: datetime objects in merchant data
- **Fix**: Use `.isoformat()` for all datetime values

**Issue: CORS errors during OAuth**
- **Cause**: Tunnel URLs not in allowed origins
- **Fix**: Restart services after tunnel detection

## Development Workflow

### Recommended Setup

```bash
# 1. Start everything with tunnels
make dev-tunnels-tmux

# 2. Verify tunnel URLs are detected
cat .env.tunnel

# 3. Check service logs for URL configuration
# Look for "🔧 Configured URLs:" in auth service logs
```

### Debugging OAuth Issues

1. Check auth service logs for:
   - `[OAUTH_INSTALL] Frontend URL configured as:`
   - `[OAUTH_CALLBACK] Will redirect to:`

2. Use browser debug console:
   ```javascript
   cj.session()  // Check current session state
   ```

3. Verify environment loading:
   ```bash
   python scripts/verify_env_config.py
   ```

## Migration Notes

If upgrading from an older branch:

1. **Add Shopify credentials** to `auth/.env.secrets`
2. **Restart all services** after tunnel detection
3. **Clear browser cache** if experiencing redirect issues
4. **Check CORS** - both frontend and homepage URLs should be allowed

## Security Considerations

- Never commit `.env.secrets` files
- Keep OAuth credentials secure
- Use different apps for dev/staging/production
- Rotate credentials regularly

## Future Improvements

- Automatic OAuth app configuration via API
- Better error messages for missing credentials
- Unified tunnel URL management across services
- OAuth state persistence across restarts