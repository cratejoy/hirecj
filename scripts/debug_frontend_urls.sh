#!/bin/bash
# Script to debug frontend URL configuration

echo "=== Frontend URL Debug Script ==="
echo

# Check what the frontend is actually using
echo "1. Starting frontend briefly to capture configuration..."
echo

cd homepage

# Start the frontend and capture the first 30 lines of output
timeout 3 npm run dev 2>&1 | head -30 > /tmp/vite_output.txt || true

echo "2. Vite Configuration Output:"
echo "================================"
grep -A20 "Vite Proxy Configuration" /tmp/vite_output.txt || echo "Configuration not found in output"
echo

echo "3. Environment Variables in homepage/.env:"
echo "=========================================="
if [ -f .env ]; then
    echo "File contents:"
    cat .env
else
    echo "❌ homepage/.env not found!"
fi
echo

echo "4. What the browser will see:"
echo "============================="
if grep -q "PROXY MODE ACTIVE" /tmp/vite_output.txt; then
    echo "✅ Frontend will use PROXY MODE"
    echo "  - API calls: /api/v1/* (relative URLs)"
    echo "  - WebSocket: /ws/* (relative URLs)"
    echo "  - All requests proxied through frontend domain"
else
    echo "❌ Frontend will use DIRECT MODE"
    echo "  - API calls will go directly to backend URL"
    echo "  - WebSocket will connect directly to backend"
    echo "  - Cookies may not work cross-domain"
fi

echo
echo "5. To fix issues:"
echo "================="
echo "  1. Check that .env.tunnel has correct URLs"
echo "  2. Run: make env-distribute"
echo "  3. Restart: make stop && make dev-tunnels-tmux"
echo "  4. Clear browser cache and reload"

# Cleanup
rm -f /tmp/vite_output.txt