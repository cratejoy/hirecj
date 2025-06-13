# Deployment Notes for WebSocket Proxy

## Current Setup (Development)
- Homepage: `https://amir.hirecj.ai` 
- Auth: `https://amir-auth.hirecj.ai`
- Agents: `https://184adbb511c7.ngrok.app` (ngrok tunnel)

## Required Changes for Production

### Option 1: Internal Network Proxy (Recommended)
Keep agents service on internal network, proxy through homepage:

```bash
# On homepage server
AGENTS_SERVICE_URL=http://agents-service.internal:8000 npm start
```

Benefits:
- Agents service not exposed to internet
- All traffic goes through homepage domain
- Cookies work perfectly

### Option 2: Subdomain for Agents Service
Deploy agents service on a hirecj.ai subdomain:

1. Set up DNS: `amir-api.hirecj.ai` → Agents service
2. No proxy needed, but update frontend to use subdomain
3. Ensure cookie domain is `.hirecj.ai`

### Current Proxy Routes
The homepage server now proxies:
- `/api/v1/*` → HTTP API requests to agents service
- `/ws/*` → WebSocket connections to agents service

### Environment Variables
The proxy uses `AGENTS_SERVICE_URL` to determine where to forward requests:

```bash
# Example for production
AGENTS_SERVICE_URL=http://10.0.0.5:8000  # Internal IP
# or
AGENTS_SERVICE_URL=http://agents-service:8000  # Docker/K8s service name
```

### Testing the Setup
1. Ensure homepage server has `AGENTS_SERVICE_URL` set correctly
2. Restart homepage server
3. Test with: `curl https://amir.hirecj.ai/api/v1/test-cors`
4. Test WebSocket with the test page at `/scripts/test_websocket_proxy.html`

### Monitoring
Watch the homepage server logs for proxy activity:
```
[Proxy] Forwarding: GET /api/v1/test-cors -> /api/v1/test-cors
[WebSocket Proxy] Upgrade request: /ws/chat/123
```