#!/bin/bash
# Simple HireCJ Development Runner

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}HireCJ Development Runner${NC}"
echo "=============================="

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down servers...${NC}"
    # Kill all child processes
    pkill -P $$
    # Kill specific ports just in case
    lsof -ti:5001 | xargs kill -9 2>/dev/null || true
    lsof -ti:3456 | xargs kill -9 2>/dev/null || true
    echo -e "${GREEN}✅ Servers stopped${NC}"
    exit 0
}

# Trap Ctrl+C
trap cleanup INT TERM

# Check if in tmux
if [ -n "$TMUX" ]; then
    echo -e "${GREEN}Running in tmux - creating panes${NC}"
    
    # Create vertical split
    tmux split-window -h
    
    # Send backend command to right pane
    tmux send-keys -t 1 "cd $(pwd)/hirecj-data && source venv/bin/activate && PORT=5001 python -m uvicorn src.api.server:app --host 0.0.0.0 --port 5001 --reload" C-m
    
    # Run frontend in current pane
    cd hirecj-homepage && npm run dev
else
    # Not in tmux - use background processes
    echo -e "${BLUE}Starting Backend (port 5001)...${NC}"
    (
        cd hirecj-data
        source venv/bin/activate
        export PORT=5001
        python -m uvicorn src.api.server:app --host 0.0.0.0 --port 5001 --reload 2>&1 | sed "s/^/[BACKEND] /"
    ) &
    
    sleep 2
    
    echo -e "${GREEN}Starting Frontend (port 3456)...${NC}"
    (
        cd hirecj-homepage
        npm run dev 2>&1 | sed "s/^/[FRONTEND] /"
    ) &
    
    sleep 2
    
    echo -e "\n${GREEN}=============================="
    echo -e "✅ Servers running!"
    echo -e "Backend:  http://localhost:5001"
    echo -e "Frontend: http://localhost:3456"
    echo -e "Press Ctrl+C to stop"
    echo -e "==============================${NC}\n"
    
    # Wait for background processes
    wait
fi