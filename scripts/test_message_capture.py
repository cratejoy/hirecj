#!/usr/bin/env python3
"""
Test script to verify message capture is working in conversation exports.
This creates a conversation with multiple messages to test the capture logic.
"""

import requests
import json
from datetime import datetime
from pathlib import Path
import sys

# Test data with multiple messages
test_conversation = {
    "conversation": {
        "id": f"test_message_capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now().isoformat(),
        "context": {
            "workflow": {
                "name": "ad_hoc_support",
                "description": "General support workflow for ad-hoc merchant questions",
                "behavior": {
                    "initial_action": {
                        "type": "wait_for_user"
                    }
                }
            },
            "persona": {
                "id": "jessica_chen",
                "name": "Jessica Chen",
                "business": "Artisan Jewelry Box",
                "role": "Founder",
                "industry": "E-commerce",
                "communicationStyle": ["direct", "brief"],
                "traits": ["data-driven", "growth-focused"]
            },
            "scenario": {
                "id": "steady",
                "name": "Steady Operations",
                "description": "Normal business operations"
            },
            "trustLevel": 3,
            "model": "gpt-4-turbo",
            "temperature": 0.7
        },
        "prompts": {
            "cj_prompt": "You are CJ, an autonomous CX & Growth Officer...",
            "cj_prompt_file": "prompts/cj/versions/v6.0.1.yaml",
            "workflow_prompt": "Support the merchant with their questions", 
            "workflow_prompt_file": "prompts/workflows/ad_hoc_support.yaml",
            "tool_definitions": []
        },
        "messages": [
            {
                "turn": 1,
                "user_input": "Can you test the message capture for me?",
                "agent_processing": {
                    "thinking": "The user is asking me to test message capture...",
                    "intermediate_responses": [],
                    "tool_calls": [],
                    "grounding_queries": [],
                    "final_response": "I'll test the message capture for you. This is message 1 of the test conversation."
                },
                "metrics": {
                    "latency_ms": 1247,
                    "tokens": {
                        "prompt": 1523,
                        "completion": 89,
                        "thinking": 45
                    }
                }
            },
            {
                "turn": 2,
                "user_input": "Great! Can you show me another message?",
                "agent_processing": {
                    "thinking": "The user wants to see another message in the capture...",
                    "intermediate_responses": [],
                    "tool_calls": [],
                    "grounding_queries": [],
                    "final_response": "Here's the second message in our test conversation. The capture system should record both messages properly."
                },
                "metrics": {
                    "latency_ms": 987,
                    "tokens": {
                        "prompt": 1612,
                        "completion": 76,
                        "thinking": 38
                    }
                }
            },
            {
                "turn": 3,
                "user_input": "Perfect, one more to make sure it's working well.",
                "agent_processing": {
                    "thinking": "Adding a third message to ensure the capture handles multiple turns...",
                    "intermediate_responses": [],
                    "tool_calls": [],
                    "grounding_queries": [],
                    "final_response": "This is the third and final test message. If you can see all three messages in the exported conversation, then the message capture is working correctly!"
                },
                "metrics": {
                    "latency_ms": 1123,
                    "tokens": {
                        "prompt": 1698,
                        "completion": 92,
                        "thinking": 42
                    }
                }
            }
        ]
    },
    "source": "playground"
}


def test_message_capture():
    """Test conversation capture with multiple messages."""
    print("🔍 Testing message capture with multi-turn conversation...")
    
    try:
        response = requests.post(
            "http://localhost:8100/api/v1/conversations/capture",
            json=test_conversation,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Test passed! Conversation saved to: {result['path']}")
            
            # Verify the file was created and contains messages
            project_root = Path(__file__).parent.parent
            file_path = project_root / result['path']
            
            if file_path.exists():
                with open(file_path, 'r') as f:
                    saved_data = json.load(f)
                    message_count = len(saved_data.get('messages', []))
                    print(f"✅ File verified with {message_count} messages")
                    
                    if message_count == 3:
                        print("✅ All 3 test messages were captured successfully!")
                    else:
                        print(f"⚠️  Expected 3 messages but found {message_count}")
            else:
                print(f"❌ File not found at: {file_path}")
                
        else:
            print(f"❌ Test failed: {response.text}")
            
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Could not connect to agents service: {e}")
        print("\nMake sure the agents service is running:")
        print("  make dev-agents")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def main():
    """Run the message capture test."""
    print("🚀 Testing conversation message capture...\n")
    
    print("This test will:")
    print("1. Send a multi-turn conversation to the capture endpoint")
    print("2. Verify all messages are saved correctly")
    print("3. Check that the exported file contains all message data")
    print("\n" + "="*60 + "\n")
    
    test_message_capture()
    
    print("\nNext steps:")
    print("1. Test real conversation capture in the playground")
    print("2. Send multiple messages back and forth")
    print("3. Export and verify all messages are captured")


if __name__ == "__main__":
    main()