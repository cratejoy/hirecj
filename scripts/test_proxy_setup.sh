#!/bin/bash
# Test script to verify WebSocket proxy setup

echo "=== WebSocket Proxy Test Script ==="
echo

# Check if services are running
echo "1. Checking services..."
echo -n "   Homepage (3456): "
curl -s http://localhost:3456 > /dev/null && echo "✅ Running" || echo "❌ Not running"

echo -n "   Agents (8000): "
curl -s http://localhost:8000 > /dev/null && echo "✅ Running" || echo "❌ Not running"

echo

# Check environment variables
echo "2. Environment variables:"
echo "   AGENTS_SERVICE_URL: ${AGENTS_SERVICE_URL:-Not set}"
echo "   HOMEPAGE_URL: ${HOMEPAGE_URL:-Not set}"

echo

# Test API proxy
echo "3. Testing API proxy..."
echo -n "   /api/v1/test-cors: "
response=$(curl -s -w "\n%{http_code}" http://localhost:3456/api/v1/test-cors)
status=$(echo "$response" | tail -n1)
if [ "$status" = "200" ]; then
    echo "✅ Working (Status: $status)"
else
    echo "❌ Failed (Status: $status)"
fi

echo

# Test WebSocket endpoint directly
echo "4. Testing direct WebSocket endpoint..."
echo "   ws://localhost:8000/ws/chat/test-direct"
echo "   (This should work if agents service is running)"

echo

# Test proxied WebSocket endpoint
echo "5. Testing proxied WebSocket endpoint..."
echo "   ws://localhost:3456/ws/chat/test-proxy"
echo "   (This should work if proxy is configured correctly)"

echo
echo "To test WebSocket connections manually:"
echo "  1. Open browser DevTools console"
echo "  2. Run: new WebSocket('ws://localhost:3456/ws/chat/test-123')"
echo "  3. Check for connection success"

echo
echo "For production test:"
echo "  1. Visit https://amir.hirecj.ai/scripts/test_websocket_proxy.html"
echo "  2. Click 'Test WebSocket Connection'"
echo "  3. Check logs for success"