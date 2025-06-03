#!/usr/bin/env python3
"""
HireCJ Development Runner
Manages both backend and frontend servers with auto-reload
"""

import os
import sys
import subprocess
import signal
import time
from pathlib import Path

# Configuration
BACKEND_DIR = Path(__file__).parent / "hirecj-agents"
FRONTEND_DIR = Path(__file__).parent / "hirecj-homepage"
BACKEND_PORT = 5001
FRONTEND_PORT = 3456

# Colors for output
class Colors:
    BACKEND = '\033[94m'  # Blue
    FRONTEND = '\033[92m' # Green
    ERROR = '\033[91m'    # Red
    WARNING = '\033[93m'  # Yellow
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_colored(color, prefix, message):
    """Print colored output with prefix"""
    print(f"{color}{prefix}{Colors.ENDC} {message}")

def check_dependencies():
    """Check if required dependencies are available"""
    # Check for Python
    try:
        subprocess.run(["python", "--version"], capture_output=True, check=True)
    except:
        print_colored(Colors.ERROR, "[ERROR]", "Python not found")
        return False
    
    # Check for Node/npm
    try:
        subprocess.run(["npm", "--version"], capture_output=True, check=True)
    except:
        print_colored(Colors.ERROR, "[ERROR]", "npm not found")
        return False
    
    # Check if backend venv exists
    venv_path = BACKEND_DIR / "venv"
    if not venv_path.exists():
        print_colored(Colors.WARNING, "[WARNING]", f"Virtual environment not found at {venv_path}")
        print_colored(Colors.WARNING, "[WARNING]", "Create it with: cd hirecj-agents && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt")
        return False
    
    return True

def run_backend():
    """Run the backend server with auto-reload"""
    print_colored(Colors.BACKEND, "[BACKEND]", f"Starting on port {BACKEND_PORT}...")
    
    # Activate venv and run with watchdog
    activate_script = BACKEND_DIR / "venv" / "bin" / "activate"
    
    # Create a wrapper script to run uvicorn with auto-reload
    wrapper_content = f"""#!/bin/bash
source {activate_script}
cd {BACKEND_DIR}

# Export port
export PORT={BACKEND_PORT}

# Run uvicorn with auto-reload
python -m uvicorn app.main:app --host 0.0.0.0 --port {BACKEND_PORT} --reload
"""
    
    wrapper_path = BACKEND_DIR / ".dev_backend_wrapper.sh"
    with open(wrapper_path, 'w') as f:
        f.write(wrapper_content)
    
    os.chmod(wrapper_path, 0o755)
    
    # Run the wrapper
    process = subprocess.Popen(
        [str(wrapper_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )
    
    return process

def run_frontend():
    """Run the frontend server with Vite"""
    print_colored(Colors.FRONTEND, "[FRONTEND]", f"Starting on port {FRONTEND_PORT}...")
    
    process = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=FRONTEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )
    
    return process

def stream_output(process, color, prefix):
    """Stream output from a process with color coding"""
    for line in iter(process.stdout.readline, ''):
        if line:
            print_colored(color, prefix, line.rstrip())

def main():
    """Main runner"""
    print(f"{Colors.BOLD}HireCJ Development Runner{Colors.ENDC}")
    print("=" * 50)
    
    if not check_dependencies():
        sys.exit(1)
    
    backend_process = None
    frontend_process = None
    
    def cleanup(signum=None, frame=None):
        """Clean up processes on exit"""
        print("\n")
        print_colored(Colors.WARNING, "[SHUTDOWN]", "Stopping servers...")
        
        if backend_process:
            backend_process.terminate()
            try:
                backend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                backend_process.kill()
            print_colored(Colors.BACKEND, "[BACKEND]", "Stopped")
        
        if frontend_process:
            frontend_process.terminate()
            try:
                frontend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                frontend_process.kill()
            print_colored(Colors.FRONTEND, "[FRONTEND]", "Stopped")
        
        # Clean up wrapper script
        wrapper_path = BACKEND_DIR / ".dev_backend_wrapper.sh"
        if wrapper_path.exists():
            os.remove(wrapper_path)
        
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    try:
        # Start backend
        backend_process = run_backend()
        time.sleep(2)  # Give backend time to start
        
        # Start frontend
        frontend_process = run_frontend()
        time.sleep(2)  # Give frontend time to start
        
        print("\n" + "=" * 50)
        print_colored(Colors.BOLD, "[READY]", f"Backend: http://localhost:{BACKEND_PORT}")
        print_colored(Colors.BOLD, "[READY]", f"Frontend: http://localhost:{FRONTEND_PORT}")
        print_colored(Colors.WARNING, "[INFO]", "Press Ctrl+C to stop all servers")
        print("=" * 50 + "\n")
        
        # Monitor processes
        import threading
        
        # Stream backend output
        backend_thread = threading.Thread(
            target=stream_output,
            args=(backend_process, Colors.BACKEND, "[BACKEND]")
        )
        backend_thread.daemon = True
        backend_thread.start()
        
        # Stream frontend output
        frontend_thread = threading.Thread(
            target=stream_output,
            args=(frontend_process, Colors.FRONTEND, "[FRONTEND]")
        )
        frontend_thread.daemon = True
        frontend_thread.start()
        
        # Wait for processes
        while True:
            # Check if processes are still running
            if backend_process.poll() is not None:
                print_colored(Colors.ERROR, "[ERROR]", "Backend process died")
                cleanup()
            
            if frontend_process.poll() is not None:
                print_colored(Colors.ERROR, "[ERROR]", "Frontend process died")
                cleanup()
            
            time.sleep(1)
    
    except Exception as e:
        print_colored(Colors.ERROR, "[ERROR]", str(e))
        cleanup()

if __name__ == "__main__":
    main()