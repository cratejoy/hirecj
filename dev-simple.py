#!/usr/bin/env python3
"""
Simple HireCJ Dev Runner
Runs both servers with auto-reload in tmux or separate terminals
"""

import os
import sys
import subprocess
import signal
import time
from pathlib import Path

# Colors
BLUE = '\033[94m'
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BOLD = '\033[1m'
END = '\033[0m'

def main():
    print(f"{BOLD}HireCJ Simple Dev Runner{END}")
    print("=" * 50)
    
    # Check if we're in tmux
    in_tmux = os.environ.get('TMUX') is not None
    
    if in_tmux:
        print(f"{GREEN}[INFO]{END} Running in tmux - will create split panes")
        
        # Create horizontal split for backend
        subprocess.run(['tmux', 'split-window', '-h', '-p', '50'])
        
        # Run backend in right pane
        backend_cmd = """
cd hirecj-agents && 
source venv/bin/activate && 
export FLASK_APP=cj_test_server.py && 
export FLASK_ENV=development && 
export FLASK_DEBUG=1 && 
python -m flask run --host=0.0.0.0 --port=5001 --reload
"""
        subprocess.run(['tmux', 'send-keys', '-t', '1', backend_cmd, 'Enter'])
        
        # Run frontend in left pane (current)
        print(f"{GREEN}[FRONTEND]{END} Starting in current pane...")
        os.chdir('hirecj-homepage')
        os.execvp('npm', ['npm', 'run', 'dev'])
        
    else:
        # Not in tmux - provide instructions
        print(f"{YELLOW}[RECOMMENDED]{END} Use tmux for best experience:")
        print(f"  1. Install tmux: brew install tmux")
        print(f"  2. Start tmux: tmux new -s hirecj")
        print(f"  3. Run this script again: ./dev-simple.py\n")
        
        print(f"{YELLOW}[ALTERNATIVE]{END} Open two terminal windows and run:")
        print(f"\n{BLUE}Terminal 1 (Backend):{END}")
        print("  cd hirecj-agents")
        print("  source venv/bin/activate")
        print("  export FLASK_ENV=development")
        print("  export FLASK_DEBUG=1")
        print("  python -m flask run --host=0.0.0.0 --port=5001 --reload")
        
        print(f"\n{GREEN}Terminal 2 (Frontend):{END}")
        print("  cd hirecj-homepage")
        print("  npm run dev")
        
        print(f"\n{BOLD}URLs:{END}")
        print(f"  Backend:  http://localhost:5001")
        print(f"  Frontend: http://localhost:3456")

if __name__ == "__main__":
    main()