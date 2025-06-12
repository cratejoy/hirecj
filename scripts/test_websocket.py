#!/usr/bin/env python3
"""Test WebSocket proxy connection"""

import asyncio
import websockets
import json
import sys

async def test_websocket(url):
    print(f"\n🔌 Testing WebSocket connection to: {url}")
    
    try:
        # Connect to WebSocket
        async with websockets.connect(url) as websocket:
            print("✅ Connected successfully!")
            
            # Send start_conversation message
            message = {
                "type": "start_conversation",
                "data": {
                    "conversation_id": "test-proxy-123",
                    "merchant_id": "test_merchant",
                    "scenario": "test",
                    "workflow": "ad_hoc_support"
                }
            }
            
            print(f"📤 Sending: {json.dumps(message, indent=2)}")
            await websocket.send(json.dumps(message))
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)
                print(f"📥 Received: {json.dumps(data, indent=2)}")
                
                if data.get("type") == "conversation_started":
                    print("✅ Conversation started successfully!")
                    return True
                else:
                    print(f"❌ Unexpected response type: {data.get('type')}")
                    return False
                    
            except asyncio.TimeoutError:
                print("❌ Timeout waiting for response")
                return False
                
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

async def main():
    # Test direct connection (should work if agents service is accessible)
    print("\n=== Test 1: Direct WebSocket Connection ===")
    direct_success = await test_websocket("ws://localhost:8000/ws/chat/test-direct")
    
    # Test proxied connection (should work if proxy is configured)
    print("\n=== Test 2: Proxied WebSocket Connection ===")
    proxy_success = await test_websocket("ws://localhost:3456/ws/chat/test-proxy")
    
    # Test production URL (if available)
    print("\n=== Test 3: Production WebSocket Connection ===")
    prod_success = await test_websocket("wss://amir.hirecj.ai/ws/chat/test-prod")
    
    # Summary
    print("\n=== Summary ===")
    print(f"Direct connection: {'✅ Success' if direct_success else '❌ Failed'}")
    print(f"Proxy connection: {'✅ Success' if proxy_success else '❌ Failed'}")
    print(f"Production connection: {'✅ Success' if prod_success else '❌ Failed'}")
    
    if proxy_success or prod_success:
        print("\n🎉 WebSocket proxy is working correctly!")
        return 0
    else:
        print("\n⚠️  WebSocket proxy needs configuration")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)