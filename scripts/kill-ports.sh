#!/bin/bash
# Kill processes on HireCJ service ports

PORTS=(8000 8001 8002 8100 8103 8004 3000 3456 3458 5173 9621)

echo "🔍 Checking for processes on HireCJ ports..."

for port in "${PORTS[@]}"; do
    pids=$(lsof -ti:$port 2>/dev/null)
    if [ -n "$pids" ]; then
        echo "❌ Killing process on port $port (PIDs: $pids)"
        echo "$pids" | xargs kill -9 2>/dev/null
    fi
done

echo "✅ All ports cleared"