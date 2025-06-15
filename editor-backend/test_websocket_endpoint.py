#!/usr/bin/env python3
"""Test the WebSocket endpoint implementation."""

import asyncio
import websockets
import json
import sys

async def test_websocket_connection():
    """Test connecting to the playground WebSocket endpoint."""
    uri = "ws://localhost:8001/ws/playground"
    
    print(f"🔌 Attempting to connect to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Successfully connected to WebSocket endpoint!")
            
            # The endpoint should accept the connection
            # In Phase 4, it just accepts and logs, no messages are sent
            
            # Wait a moment to ensure connection is stable
            await asyncio.sleep(0.5)
            
            # Try sending a ping to verify connection is alive
            await websocket.ping()
            print("✅ WebSocket connection is responsive (ping successful)")
            
            print("✅ All tests passed!")
            return True
            
    except OSError as e:
        if "Connect call failed" in str(e):
            print("❌ Connection refused - is the editor-backend server running?")
            print("   Run: make dev-editor-backend")
        else:
            print(f"❌ Connection error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {type(e).__name__}: {e}")
        return False

async def test_invalid_endpoint():
    """Test that non-existent endpoints properly fail."""
    uri = "ws://localhost:8001/ws/nonexistent"
    
    print(f"\n🔌 Testing invalid endpoint {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("❌ Should not have connected to invalid endpoint!")
            return False
    except websockets.exceptions.InvalidStatusCode as e:
        if e.status_code == 404:
            print("✅ Invalid endpoint correctly returns 404")
            return True
        else:
            print(f"❌ Unexpected status code: {e.status_code}")
            return False
    except Exception as e:
        print(f"❌ Unexpected error: {type(e).__name__}: {e}")
        return False

async def main():
    """Run all WebSocket tests."""
    print("🧪 Testing WebSocket Endpoint Implementation")
    print("=" * 50)
    
    # Test valid connection
    test1 = await test_websocket_connection()
    
    # Test invalid endpoint
    test2 = await test_invalid_endpoint()
    
    print("\n" + "=" * 50)
    if test1 and test2:
        print("✅ All WebSocket tests passed!")
        sys.exit(0)
    else:
        print("❌ Some WebSocket tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())