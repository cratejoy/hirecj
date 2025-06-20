#!/usr/bin/env python3
"""Test script for conversation capture API."""

import requests
import json
from datetime import datetime

# Test data
test_conversation = {
    "conversation": {
        "id": f"test_conv_{int(datetime.now().timestamp())}",
        "timestamp": datetime.now().isoformat() + "Z",
        "context": {
            "workflow": {
                "name": "ad-hoc-support",
                "description": "Merchant asks specific question"
            },
            "persona": {
                "id": "test-persona",
                "name": "Test User",
                "business": "Test Business",
                "role": "Founder",
                "industry": "E-commerce",
                "communicationStyle": ["direct", "brief"],
                "traits": ["data-driven"]
            },
            "scenario": {
                "id": "test-scenario",
                "name": "Test Scenario",
                "description": "Testing conversation capture"
            },
            "trustLevel": 5,
            "model": "gpt-4-turbo",
            "temperature": 0.7
        },
        "prompts": {
            "cj_prompt": "You are CJ, a helpful AI assistant...",
            "workflow_prompt": "In ad hoc support mode...",
            "tool_definitions": []
        },
        "messages": [
            {
                "turn": 1,
                "user_input": "Can you check my recent orders?",
                "agent_processing": {
                    "thinking": "User wants to see recent orders, I should use the get_orders tool...",
                    "intermediate_responses": [],
                    "tool_calls": [
                        {
                            "tool": "get_orders",
                            "args": {"limit": 10},
                            "result": {"orders": []},
                            "duration_ms": 250
                        }
                    ],
                    "grounding_queries": [],
                    "final_response": "I've checked your recent orders and found..."
                },
                "metrics": {
                    "latency_ms": 1250,
                    "tokens": {
                        "prompt": 450,
                        "completion": 125,
                        "thinking": 85
                    }
                }
            }
        ]
    },
    "source": "playground"
}

# Send request to API
try:
    response = requests.post(
        "http://localhost:8000/api/v1/conversations/capture",
        json=test_conversation,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("\n✅ Conversation capture test successful!")
    else:
        print(f"\n❌ Test failed with status {response.status_code}")
        
except Exception as e:
    print(f"❌ Error testing conversation capture: {e}")