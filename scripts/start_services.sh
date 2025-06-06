#!/bin/bash
# ================================================
# Start HireCJ Services - Phase 4.0
# ================================================
# This script ensures environment is distributed
# before starting services
# ================================================

echo "🚀 Starting HireCJ services..."

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ No .env file found!"
    echo "Run 'make env-setup' first"
    exit 1
fi

# Always distribute env first
echo "📦 Distributing environment variables..."
python scripts/distribute_env.py

if [ $? -ne 0 ]; then
    echo "❌ Failed to distribute environment variables"
    exit 1
fi

# Start services based on argument
if [ "$1" == "--tunnel" ] || [ "$1" == "-t" ]; then
    echo "🌐 Starting with tunnels..."
    make dev-tunnels-tmux
elif [ "$1" == "--tmux" ] || [ "$1" == "-m" ]; then
    echo "🖥️  Starting with tmux..."
    make dev-all
else
    echo "🔧 Starting services..."
    echo ""
    echo "Services ready to start in separate terminals:"
    echo "  Terminal 1: make dev-agents"
    echo "  Terminal 2: make dev-homepage"  
    echo "  Terminal 3: make dev-auth"
    echo ""
    echo "Or run with options:"
    echo "  ./scripts/start_services.sh --tmux    # Start all with tmux"
    echo "  ./scripts/start_services.sh --tunnel  # Start with ngrok tunnels"
fi