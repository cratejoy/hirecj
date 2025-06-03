#!/bin/bash
# Startup script to detect tunnel and prepare environment

# Wait a bit for ngrok to start
sleep 2

# Try to detect tunnel
echo "🔍 Checking for ngrok tunnel..."
python scripts/tunnel_detector.py

# Continue with server startup
exec "$@"