# WebSocket Proxy Architecture

## Overview
This document describes the single-domain proxy architecture that solves the cross-domain cookie issue by routing all connections through `amir.hirecj.ai`.

## Architecture

```
User Browser                    amir.hirecj.ai:3456                 Agents Service:8000
     |                         (Express + Proxy)                    (FastAPI Backend)
     |                                 |                                    |
     |------ HTTP Request ----------->|                                    |
     |       Cookie: sess_xxx         |                                    |
     |                                |------ Forward with Cookie -------->|
     |                                |                                    |
     |                                |<----- Response --------------------|
     |<----- Response ----------------|                                    |
     |                                |                                    |
     |------ WebSocket Upgrade ------>|                                    |
     |       Cookie: sess_xxx         |                                    |
     |                                |------ Forward Upgrade ------------>|
     |                                |       Cookie: sess_xxx             |
     |                                |                                    |
     |<===== WebSocket Connected =====|======= WebSocket Proxied ========>|
```

## Implementation Details

### 1. Express Proxy Configuration
- Uses `http-proxy-middleware` for both HTTP and WebSocket proxying
- API requests: `/api/v1/*` → Backend service
- WebSocket: `/ws/*` → Backend service
- Cookies are automatically forwarded

### 2. Frontend Changes
- WebSocket URL: Uses same origin (`wss://amir.hirecj.ai/ws/chat/{id}`)
- No cross-domain issues
- Cookies sent automatically with upgrade request

### 3. Backend (No Changes Needed)
- LoadUser middleware reads cookies normally
- WebSocket handler receives authenticated requests
- Session management works as designed

## Benefits

1. **Single Domain**: Everything runs through `amir.hirecj.ai`
2. **Automatic Cookie Handling**: Browser sends cookies with all requests
3. **No Workarounds**: Clean, standard web architecture
4. **Production Ready**: Common pattern used by many production apps
5. **Security**: Cookies stay within same domain

## Configuration

### Development
```bash
# Frontend runs on port 3456, proxies to backend on 8000
npm run dev
```

### Production
```bash
# Set AGENTS_SERVICE_URL to internal backend address
AGENTS_SERVICE_URL=http://agents-service:8000 npm start
```

## Testing

1. Open browser to `https://amir.hirecj.ai`
2. Complete OAuth flow
3. Check browser DevTools:
   - Cookie should be set on `.hirecj.ai`
   - WebSocket connects to same domain
   - No CORS or cookie warnings

## Troubleshooting

### WebSocket Not Connecting
- Check proxy logs in Express server
- Verify `/ws/*` path is being proxied
- Ensure backend WebSocket endpoint is running

### Cookies Not Sent
- Verify all services on same domain
- Check cookie domain setting (should be `.hirecj.ai`)
- Ensure HTTPS is used (cookies are secure-only)