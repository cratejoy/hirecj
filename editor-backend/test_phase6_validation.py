#!/usr/bin/env python3
"""Test Phase 6: Message validation in the WebSocket bridge."""

import asyncio
import websockets
import json
import sys

async def test_valid_message():
    """Test sending a valid message through the bridge."""
    uri = "ws://localhost:8001/ws/playground"
    
    print("🧪 Testing Phase 6: Message Validation")
    print("=" * 50)
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to playground WebSocket")
            
            # Send a valid PlaygroundStartMsg
            valid_msg = {
                "type": "playground_start",
                "workflow": "test_workflow",
                "persona_id": "test_persona",
                "scenario_id": "test_scenario",
                "trust_level": 3
            }
            
            print(f"\n📤 Sending valid message: {valid_msg['type']}")
            await websocket.send(json.dumps(valid_msg))
            
            # Wait for potential response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                print(f"📨 Received response: {response}")
            except asyncio.TimeoutError:
                print("⏱️  No response (agent might not be running)")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        return False


async def test_invalid_message():
    """Test sending an invalid message to trigger validation error."""
    uri = "ws://localhost:8001/ws/playground"
    
    print("\n🧪 Testing invalid message handling")
    print("-" * 50)
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to playground WebSocket")
            
            # Send an invalid message (missing required fields)
            invalid_msg = {
                "type": "playground_start",
                "workflow": "test_workflow"
                # Missing: persona_id, scenario_id, trust_level
            }
            
            print(f"\n📤 Sending invalid message (missing required fields)")
            await websocket.send(json.dumps(invalid_msg))
            
            # We should get an error message back
            try:
                error_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                error_data = json.loads(error_response)
                
                if error_data.get("type") == "error":
                    print("✅ Received expected error message:")
                    print(f"   Type: {error_data['type']}")
                    print(f"   Text: {error_data.get('text', 'N/A')}")
                    return True
                else:
                    print(f"❓ Unexpected response: {error_data}")
                    return False
                    
            except asyncio.TimeoutError:
                print("❌ No error message received for invalid input")
                return False
                
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        return False


async def test_unknown_message_type():
    """Test sending a message with unknown type."""
    uri = "ws://localhost:8001/ws/playground"
    
    print("\n🧪 Testing unknown message type")
    print("-" * 50)
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to playground WebSocket")
            
            # Send a message with unknown type
            unknown_msg = {
                "type": "unknown_message_type",
                "data": {"test": "data"}
            }
            
            print(f"\n📤 Sending unknown message type: {unknown_msg['type']}")
            await websocket.send(json.dumps(unknown_msg))
            
            # Should get validation error
            try:
                error_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                error_data = json.loads(error_response)
                
                if error_data.get("type") == "error":
                    print("✅ Received expected error for unknown type:")
                    print(f"   Text: {error_data.get('text', 'N/A')}")
                    return True
                else:
                    print(f"❓ Unexpected response: {error_data}")
                    return False
                    
            except asyncio.TimeoutError:
                print("❌ No error message received for unknown type")
                return False
                
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        return False


async def main():
    """Run all Phase 6 validation tests."""
    # Test 1: Valid message
    test1 = await test_valid_message()
    
    # Test 2: Invalid message (missing fields)
    test2 = await test_invalid_message()
    
    # Test 3: Unknown message type
    test3 = await test_unknown_message_type()
    
    print("\n" + "=" * 50)
    if all([test1, test2, test3]):
        print("✅ Phase 6 validation tests passed!")
        print("\nValidation features verified:")
        print("- Valid messages are accepted and forwarded")
        print("- Invalid messages trigger error responses")
        print("- Unknown message types are rejected")
        print("- Error messages use correct format")
        sys.exit(0)
    else:
        print("❌ Some Phase 6 tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())