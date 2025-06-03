# Ngrok Integration Test Guide

## Quick Start (For Amir with Reserved Domains)

```bash
# 1. Setup ngrok authtoken (one-time)
cp .env.ngrok.example .env.ngrok
# Edit .env.ngrok and add your authtoken

# 2. Setup ngrok config (one-time) 
cp ngrok.yml.amir ngrok.yml

# 3. Start everything with one command
make dev-tunnels-tmux
```

This will open tmux with 3 windows:
- Window 0: Ngrok tunnels
- Window 1: Tunnel detection
- Window 2: All services

Your reserved domains:
- Homepage: https://amir.hirecj.ai
- Auth: https://amir-auth.hirecj.ai
- Other services: https://[random].ngrok-free.app

## Verify Everything Works

### 1. Check Tunnel Detection
Look for `.env.tunnel` files created in each service directory:
```bash
cat agents/.env.tunnel
cat auth/.env.tunnel
cat homepage/.env.tunnel
cat database/.env.tunnel
```

### 2. Test CORS Configuration
1. Open https://amir.hirecj.ai in your browser
2. Open Developer Tools (F12)
3. Check Network tab - no CORS errors should appear
4. Check Console - WebSocket should connect via wss://

### 3. Test Hot Module Replacement (HMR)
1. Make a change to `homepage/src/App.tsx`
2. Save the file
3. Browser should update without refreshing

### 4. Test API Calls
API calls should work seamlessly through ngrok URLs with proper headers.

## Troubleshooting

### "Tunnel URL header not found" warning
This is handled automatically by the `ngrok-skip-browser-warning` header.

### CORS errors
1. Check service logs for allowed origins list
2. Ensure `make detect-tunnels` ran successfully
3. Restart services after tunnel detection

### WebSocket connection fails
1. Check browser console for WebSocket URL
2. Should be `wss://amir.hirecj.ai` not `ws://localhost:8000`

### HMR not working
1. Check browser console for WebSocket errors
2. Vite config should detect ngrok and use wss://

## Manual Testing Commands

```bash
# Check ngrok status
curl http://localhost:4040/api/tunnels | jq

# Check detected URLs
cat .env.tunnel

# Test API directly
curl https://amir.hirecj.ai/api/v1/health

# Check service logs
make logs-agents
```

## How It Works

1. **Ngrok starts** with your reserved domains
2. **Tunnel detector** finds all running tunnels
3. **Services** auto-detect their public URLs from `.env.tunnel`
4. **CORS** dynamically allows detected URLs
5. **Frontend** uses public URLs for API and WebSocket
6. **HMR** works via wss:// protocol

All of this happens automatically with `make dev-tunnels-tmux`!