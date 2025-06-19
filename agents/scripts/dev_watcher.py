#!/usr/bin/env python3
"""
Development server with watchdog-based file monitoring.
"""

import os
import sys
import subprocess
import signal
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import logging

# Load environment variables from .env file
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if '--debug' in sys.argv else logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class ServerManager:
    """Manages the uvicorn server process."""
    
    def __init__(self):
        self.process = None
        self.restarting = False
        
    def start(self):
        """Start the server."""
        if self.process and self.process.poll() is None:
            logger.warning(f"Server already running (PID: {self.process.pid})")
            return
            
        logger.info("🚀 Starting server...")
        
        env = os.environ.copy()
        # env['LOG_LEVEL'] = 'DEBUG'  # Commented out to reduce WebSocket header spam
        
        agents_dir = Path(__file__).parent.parent
        
        cmd = [sys.executable, '-m', 'uvicorn', 'app.main:app', 
               '--host', '0.0.0.0', '--port', os.environ.get('AGENTS_SERVICE_PORT', '8000'), '--log-level', 'info']  # Changed from 'debug' to 'info'
        
        logger.debug(f"Running command: {' '.join(cmd)}")
        logger.debug(f"Working directory: {agents_dir}")
        
        self.process = subprocess.Popen(
            cmd,
            env=env,
            cwd=agents_dir
        )
        
        # Wait a moment to ensure process started
        time.sleep(0.5)
        
        # Check if process is still running
        if self.process.poll() is not None:
            logger.error(f"❌ Server failed to start! Exit code: {self.process.returncode}")
        else:
            logger.info(f"✅ Server started (PID: {self.process.pid})")
        
    def stop(self):
        """Stop the server."""
        if not self.process:
            logger.debug("No process to stop")
            return
            
        logger.info(f"🛑 Stopping server (PID: {self.process.pid})...")
        self.process.terminate()
        
        try:
            self.process.wait(timeout=5)
            logger.info("✅ Server stopped gracefully")
        except subprocess.TimeoutExpired:
            logger.warning("⚠️  Server didn't stop gracefully, killing...")
            self.process.kill()
            self.process.wait()
            logger.info("✅ Server killed")
            
    def restart(self):
        """Restart the server."""
        if self.restarting:
            logger.debug("Already restarting, skipping...")
            return
            
        logger.info("🔄 Restarting server...")
        self.restarting = True
        self.stop()
        time.sleep(0.5)
        self.start()
        self.restarting = False
        logger.info("✅ Restart complete")


class ChangeHandler(FileSystemEventHandler):
    """Handles file system events."""
    
    def __init__(self, server_manager):
        self.server_manager = server_manager
        self.last_restart = 0
        self.debounce_seconds = 1.0
        
    def on_any_event(self, event):
        """Debug: log all events."""
        if not event.is_directory:
            logger.debug(f"Event: {event.event_type} - {event.src_path}")
    
    def on_modified(self, event):
        # Skip directories and non-Python files
        if event.is_directory:
            return
            
        if not event.src_path.endswith('.py'):
            logger.debug(f"Skipping non-Python file: {event.src_path}")
            return
            
        # Skip certain paths
        ignore_patterns = ['__pycache__', '.git', 'venv', 'logs']
        # Special handling for 'data' - only ignore if it's a directory, not part of filename
        path_parts = Path(event.src_path).parts
        for pattern in ignore_patterns:
            if pattern in event.src_path:
                logger.debug(f"Ignoring {pattern} file: {event.src_path}")
                return
        
        # Check if 'data' is an actual directory in the path, not part of a filename
        if 'data' in path_parts:
            logger.debug(f"Ignoring file in data directory: {event.src_path}")
            return
            
        # Debounce
        current_time = time.time()
        if current_time - self.last_restart < self.debounce_seconds:
            logger.debug(f"Debouncing change in: {event.src_path}")
            return
            
        self.last_restart = current_time
        
        # Log the change
        try:
            agents_dir = Path(__file__).parent.parent
            rel_path = Path(event.src_path).relative_to(agents_dir)
            logger.info(f"📝 Change detected: {rel_path}")
        except Exception as e:
            logger.info(f"📝 Change detected: {Path(event.src_path).name}")
            logger.debug(f"Path resolution error: {e}")
            
        # Restart server in a separate thread to avoid blocking
        logger.info("🔄 Triggering server restart...")
        restart_thread = threading.Thread(target=self.server_manager.restart)
        restart_thread.start()


def monitor_crashes(server_manager):
    """Monitor for server crashes and restart."""
    while True:
        time.sleep(2)
        if server_manager.process and server_manager.process.poll() is not None:
            exit_code = server_manager.process.returncode
            if exit_code != 0 and not server_manager.restarting:
                logger.error(f"❌ Server crashed (exit code: {exit_code})")
                logger.info("🔄 Restarting in 2 seconds...")
                time.sleep(2)
                server_manager.start()


def main():
    logger.info("🔧 HireCJ Development Server")
    logger.info("👀 Watching for Python file changes...")
    logger.info(f"🌐 Server: http://localhost:{os.environ.get('AGENTS_SERVICE_PORT', '8000')}")
    logger.info("Press Ctrl+C to stop\n")
    
    # Create server manager
    server = ServerManager()
    
    # Set up file watcher
    event_handler = ChangeHandler(server)
    observer = Observer()
    
    # Watch directories
    agents_dir = Path(__file__).parent.parent
    watch_dirs = [
        agents_dir / "app",
        agents_dir / "scripts",
    ]
    
    for watch_dir in watch_dirs:
        if watch_dir.exists():
            observer.schedule(event_handler, str(watch_dir), recursive=True)
            logger.info(f"📁 Watching: {watch_dir} (recursive)")
            # Log subdirectories being watched
            subdirs = [d for d in watch_dir.rglob('*') if d.is_dir() and '__pycache__' not in str(d) and 'venv' not in str(d)]
            if subdirs:
                logger.debug(f"  Subdirectories: {len(subdirs)} total")
                for subdir in subdirs[:5]:  # Show first 5
                    logger.debug(f"    - {subdir.relative_to(agents_dir)}")
                if len(subdirs) > 5:
                    logger.debug(f"    ... and {len(subdirs) - 5} more")
    
    # Start observer
    observer.start()
    
    # Start server
    server.start()
    
    # Start crash monitor
    crash_thread = threading.Thread(target=monitor_crashes, args=(server,), daemon=True)
    crash_thread.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down...")
        observer.stop()
        server.stop()
        
    observer.join()
    logger.info("✅ Done!")


if __name__ == "__main__":
    main()