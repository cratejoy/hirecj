#!/bin/bash
# Script to verify proxy mode is configured correctly

echo "=== Verifying Proxy Mode Configuration ==="
echo

# Check if services are on different domains
if [ -f .env.tunnel ]; then
    HOMEPAGE_URL=$(grep "^HOMEPAGE_URL=" .env.tunnel | cut -d'=' -f2)
    AGENTS_URL=$(grep "^AGENTS_SERVICE_URL=" .env.tunnel | cut -d'=' -f2)
    
    echo "📍 Service URLs from .env.tunnel:"
    echo "  Homepage: $HOMEPAGE_URL"
    echo "  Agents: $AGENTS_URL"
    echo
    
    # Extract domains using awk for better reliability
    HOMEPAGE_DOMAIN=$(echo $HOMEPAGE_URL | awk -F[/:] '{print $4}')
    AGENTS_DOMAIN=$(echo $AGENTS_URL | awk -F[/:] '{print $4}')
    
    echo "🌐 Domains:"
    echo "  Homepage domain: $HOMEPAGE_DOMAIN"
    echo "  Agents domain: $AGENTS_DOMAIN"
    echo
    
    # Check if proxy should be used
    if [[ $HOMEPAGE_URL == *"amir.hirecj.ai"* ]]; then
        echo "✅ Homepage is on amir.hirecj.ai - proxy mode SHOULD be active"
        EXPECTED_PROXY=true
    elif [[ $HOMEPAGE_DOMAIN == $AGENTS_DOMAIN ]]; then
        echo "✅ Services are on same domain - proxy mode SHOULD be active"
        EXPECTED_PROXY=true
    else
        echo "❌ Services are on different domains - proxy mode would NOT work"
        EXPECTED_PROXY=false
    fi
else
    echo "❌ .env.tunnel not found"
    exit 1
fi

echo
echo "📄 Checking homepage/.env configuration:"
if [ -f homepage/.env ]; then
    if grep -q "^VITE_API_URL=" homepage/.env || grep -q "^VITE_WS_URL=" homepage/.env; then
        echo "❌ Found VITE_API_URL or VITE_WS_URL in homepage/.env - proxy mode is DISABLED"
        grep -E "^VITE_API_URL=|^VITE_WS_URL=" homepage/.env
    else
        echo "✅ No VITE_API_URL or VITE_WS_URL in homepage/.env - proxy mode is ENABLED"
    fi
else
    echo "❌ homepage/.env not found"
fi

echo
echo "🔍 Expected behavior:"
if [ "$EXPECTED_PROXY" = true ]; then
    echo "  ✅ All API requests should go to: $HOMEPAGE_URL/api/v1/*"
    echo "  ✅ WebSocket should connect to: wss://$HOMEPAGE_DOMAIN/ws/chat/*"
    echo "  ✅ Cookies will work because everything is same-origin"
else
    echo "  ❌ API requests would go directly to: $AGENTS_URL"
    echo "  ❌ WebSocket would connect to: $AGENTS_URL"
    echo "  ❌ Cookies won't work due to cross-domain restrictions"
fi

echo
echo "📝 To fix issues:"
echo "  1. Run: make env-distribute"
echo "  2. Restart services: make stop && make dev-tunnels-tmux"
echo "  3. Check browser console for the Vite configuration logs"