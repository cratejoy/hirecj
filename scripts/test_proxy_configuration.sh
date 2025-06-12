#!/bin/bash
# Test script to verify proxy configuration

echo "=== Proxy Configuration Test ==="
echo

# Check environment files
echo "1. Checking environment configuration..."
echo

echo "📄 Homepage .env:"
if [ -f homepage/.env ]; then
    grep -E "VITE_API_URL|VITE_WS_URL|VITE_AUTH_URL" homepage/.env || echo "  (No VITE_API_URL or VITE_WS_URL - using proxy mode ✅)"
else
    echo "  ❌ homepage/.env not found"
fi

echo
echo "📄 .env.tunnel:"
if [ -f .env.tunnel ]; then
    grep -E "HOMEPAGE_URL|AGENTS_SERVICE_URL" .env.tunnel
else
    echo "  ❌ .env.tunnel not found"
fi

echo
echo "2. Checking if services are configured for proxy mode..."
echo

# Check if homepage is on amir.hirecj.ai
if grep -q "amir.hirecj.ai" .env.tunnel 2>/dev/null && grep -q "HOMEPAGE_URL=.*amir.hirecj.ai" .env.tunnel 2>/dev/null; then
    echo "✅ Homepage is configured for amir.hirecj.ai"
    echo "✅ Proxy mode should be active (all traffic through same domain)"
else
    echo "❌ Homepage is not on amir.hirecj.ai - proxy mode may not work"
fi

echo
echo "3. Expected behavior:"
echo "  - Frontend at https://amir.hirecj.ai"
echo "  - API requests to /api/v1/* are proxied to agents service"
echo "  - WebSocket connections to /ws/* are proxied to agents service"
echo "  - All cookies work because everything is same-origin"

echo
echo "4. To test:"
echo "  1. Start services: make dev-tunnels-tmux"
echo "  2. Visit https://amir.hirecj.ai"
echo "  3. Complete OAuth flow"
echo "  4. Check that WebSocket connections work"