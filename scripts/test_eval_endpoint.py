#!/usr/bin/env python3
"""
Test script to verify the eval endpoint produces the same responses as WebSocket.
"""

import asyncio
import httpx
import json
from rich.console import Console

console = Console()

# Agents service URL
AGENTS_URL = "http://localhost:8100"

async def test_eval_endpoint():
    """Test the eval endpoint with a simple message."""
    
    # Test data
    test_cases = [
        {
            "name": "Simple greeting",
            "request": {
                "messages": [
                    {"role": "user", "content": "sup guy"}
                ],
                "workflow": "ad_hoc_support",
                "persona": "jessica"
            }
        },
        {
            "name": "Follow-up question",
            "request": {
                "messages": [
                    {"role": "user", "content": "sup guy"},
                    {"role": "assistant", "content": "Hey there! CJ here – ready to help. What's on your mind?"},
                    {"role": "user", "content": "what day is it"}
                ],
                "workflow": "ad_hoc_support",
                "persona": "jessica"
            }
        }
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for test_case in test_cases:
            console.print(f"\n[bold cyan]Testing: {test_case['name']}[/bold cyan]")
            console.print(f"Request: {json.dumps(test_case['request'], indent=2)}")
            
            try:
                response = await client.post(
                    f"{AGENTS_URL}/api/v1/eval/chat",
                    json=test_case["request"]
                )
                
                if response.status_code == 200:
                    result = response.json()
                    console.print(f"[green]✓ Success![/green]")
                    console.print(f"Response: {result['response']}")
                else:
                    console.print(f"[red]✗ Failed with status {response.status_code}[/red]")
                    console.print(f"Error: {response.text}")
                    
            except Exception as e:
                console.print(f"[red]✗ Error: {str(e)}[/red]")
    
    console.print("\n[yellow]Note: To fully verify responses match WebSocket, you should:[/yellow]")
    console.print("1. Send the same message through WebSocket chat")
    console.print("2. Compare the response text (ignoring UI elements)")
    console.print("3. Ensure they are semantically identical")

if __name__ == "__main__":
    console.print("[bold]Testing Eval Endpoint[/bold]")
    console.print(f"Agents URL: {AGENTS_URL}\n")
    
    asyncio.run(test_eval_endpoint())