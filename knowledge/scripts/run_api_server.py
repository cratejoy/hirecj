#!/usr/bin/env python3
"""
Run the Knowledge API server
This script is used for integration with the HireCJ dev environment
"""
import os
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import and run the FastAPI app
import uvicorn
from gateway.main import app

if __name__ == "__main__":
    port = int(os.getenv("KNOWLEDGE_SERVICE_PORT", "8004"))
    print(f"Starting Knowledge API on port {port}...")
    uvicorn.run(
        "gateway.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )