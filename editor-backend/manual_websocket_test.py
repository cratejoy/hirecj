#!/usr/bin/env python3
"""
Manual WebSocket test for the playground endpoint.
Run this while the editor-backend server is running.
"""

import asyncio
import websockets
import json
from datetime import datetime

async def test_playground_websocket():
    uri = "ws://localhost:8001/ws/playground"
    
    print(f"📡 Connecting to {uri}")
    print("-" * 50)
    
    async with websockets.connect(uri) as websocket:
        print(f"✅ Connected at {datetime.now().strftime('%H:%M:%S')}")
        print("📝 Connection established - endpoint is working!")
        print("\nPhase 4 implementation verified:")
        print("  - WebSocket endpoint accessible at /ws/playground")
        print("  - Connection accepted successfully")
        print("  - Ready for Phase 5 (message bridging)")
        
        # Keep connection open for a moment
        await asyncio.sleep(2)
        
        print("\n👋 Closing connection...")

if __name__ == "__main__":
    try:
        asyncio.run(test_playground_websocket())
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted")
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        print("\nMake sure the editor-backend is running:")
        print("  make dev-editor-backend")