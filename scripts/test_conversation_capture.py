#!/usr/bin/env python3
"""
Test script to verify conversation capture integration.
Tests both direct connection to agents service and through editor-backend proxy.
"""

import requests
import json
from datetime import datetime
from pathlib import Path
import sys

# Test data matching the expected format
test_conversation = {
    "conversation": {
        "id": f"test_capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
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
            "cj_prompt": """You are CJ, an autonomous CX & Growth Officer for e-commerce brands. You're proactive, data-driven, and dedicated to helping merchants grow their business. Your role combines customer experience optimization with strategic growth initiatives.

Core Principles:
- Always be helpful, proactive, and solution-oriented
- Use data to inform recommendations
- Focus on actionable insights that drive growth
- Maintain a professional yet friendly tone
- Anticipate merchant needs and offer relevant suggestions

This is a test of the full prompt capture to ensure nothing gets truncated when exporting conversations for evaluation purposes.""",
            "cj_prompt_file": "prompts/cj/versions/v6.0.1.yaml",
            "workflow_prompt": "Support the merchant with their questions", 
            "workflow_prompt_file": "prompts/workflows/ad_hoc_support.yaml",
            "tool_definitions": []
        },
        "messages": [
            {
                "turn": 1,
                "user_input": "Can you test the tool selection for me?",
                "agent_processing": {
                    "thinking": "The user is asking me to test tool selection...",
                    "intermediate_responses": [],
                    "tool_calls": [
                        {
                            "tool": "get_shopify_store_counts",
                            "args": {},
                            "result": {"total_stores": 42},
                            "error": None,
                            "duration_ms": 523
                        }
                    ],
                    "grounding_queries": [],
                    "final_response": "I'll test the tool selection for you. I'm using the Shopify store counts tool to demonstrate. I found that you have 42 stores in total."
                },
                "metrics": {
                    "latency_ms": 1247,
                    "tokens": {
                        "prompt": 1523,
                        "completion": 89,
                        "thinking": 45
                    }
                }
            }
        ]
    },
    "source": "playground"
}


def test_direct_to_agents():
    """Test direct connection to agents service."""
    print("🔍 Testing direct connection to agents service...")
    
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
            print(f"✅ Direct test passed! Conversation saved to: {result.get('path')}")
            return True
        else:
            print(f"❌ Direct test failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Could not connect to agents service: {e}")
        return False


def test_through_proxy():
    """Test through editor-backend proxy."""
    print("\n🔍 Testing through editor-backend proxy...")
    
    try:
        response = requests.post(
            "http://localhost:8001/api/v1/conversations/capture",
            json=test_conversation,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Proxy test passed! Conversation saved to: {result.get('path')}")
            
            # Verify file exists
            project_root = Path(__file__).parent.parent
            file_path = project_root / result.get('path')
            
            if file_path.exists():
                print(f"✅ File verified at: {file_path}")
                
                # Show a snippet of the saved conversation
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    print(f"\n📄 Saved conversation ID: {data.get('id')}")
                    print(f"📅 Timestamp: {data.get('timestamp')}")
                    print(f"💬 Messages: {len(data.get('messages', []))}")
            else:
                print(f"❌ File not found at expected path: {file_path}")
                
            return True
        else:
            print(f"❌ Proxy test failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Could not connect to editor-backend: {e}")
        return False


def main():
    """Run all tests."""
    print("🚀 Testing conversation capture integration...\n")
    
    print("Prerequisites:")
    print("1. Agents service running on http://localhost:8100")
    print("2. Editor-backend running on http://localhost:8001")
    print("\nIf services are not running, use:")
    print("  Terminal 1: make dev-agents")
    print("  Terminal 2: make dev-editor-backend")
    print("\n" + "="*60 + "\n")
    
    # Test direct connection first
    direct_ok = test_direct_to_agents()
    
    if direct_ok:
        # Test through proxy
        proxy_ok = test_through_proxy()
        
        if proxy_ok:
            print("\n✅ All tests passed! Conversation capture is working correctly.")
            print("\nNext steps:")
            print("1. Start the editor frontend: make dev-editor")
            print("2. Go to the playground and have a conversation")
            print("3. Click 'Export for Eval' button")
            print("4. Check hirecj_evals/conversations/playground/ for saved files")
        else:
            print("\n⚠️  Proxy test failed but direct test passed.")
            print("Check that editor-backend is running and the proxy is configured correctly.")
            sys.exit(1)
    else:
        print("\n❌ Direct test failed. Make sure the agents service is running.")
        sys.exit(1)


if __name__ == "__main__":
    main()