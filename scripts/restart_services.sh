#!/bin/bash
# Restart services to pick up tunnel URLs

echo "🔄 Restarting services to pick up tunnel URLs..."

# Check if tunnel URLs exist
if [ ! -f "../.env.tunnel" ]; then
    echo "❌ No .env.tunnel file found. Run tunnel detection first."
    exit 1
fi

echo "📡 Tunnel URLs detected:"
grep -E "(HOMEPAGE_URL|AUTH_SERVICE_URL|AGENTS_SERVICE_URL)" ../.env.tunnel

echo ""
echo "⚠️  Please restart your services in this order:"
echo ""
echo "1️⃣  Agents service (Terminal 1):"
echo "   make dev-agents"
echo ""
echo "2️⃣  Auth service (Terminal 2):"
echo "   make dev-auth"
echo ""
echo "3️⃣  Homepage (Terminal 3):"
echo "   make dev-homepage"
echo ""
echo "The services will now use the tunnel URLs from .env.tunnel"
echo ""
echo "✅ After restarting, check the service logs for:"
echo "   - Auth: 'Frontend URL: https://amir.hirecj.ai'"
echo "   - Homepage: Should make API calls to ngrok URLs"