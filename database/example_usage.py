"""Example usage of the Service Connections API."""

import asyncio
import httpx
from datetime import datetime


async def main():
    """Demonstrate API usage."""
    base_url = "http://localhost:8002"
    
    async with httpx.AsyncClient() as client:
        # 1. Check health
        print("1. Checking service health...")
        response = await client.get(f"{base_url}/health")
        print(f"   Health: {response.json()}\n")
        
        # 2. Get all connections status
        print("2. Getting all service connections...")
        response = await client.get(f"{base_url}/api/v1/connections")
        connections = response.json()
        print(f"   Total services: {connections['total_services']}")
        print(f"   Connected: {connections['connected_count']}")
        print(f"   Services:")
        for service_type, connection in connections['services'].items():
            print(f"     - {service_type}: {connection['status']}")
        print()
        
        # 3. Connect to Freshdesk (example)
        print("3. Connecting to Freshdesk...")
        credentials = {
            "access_token": "example_token_123",
            "refresh_token": "example_refresh_456",
            "token_type": "Bearer",
            "expires_at": None,
            "scope": "read write"
        }
        response = await client.post(
            f"{base_url}/api/v1/connections/freshdesk/connect",
            json=credentials
        )
        connection = response.json()
        print(f"   Status: {connection['status']}")
        print(f"   Connected at: {connection['connected_at']}")
        print()
        
        # 4. Check specific service
        print("4. Checking Google Analytics connection...")
        response = await client.get(f"{base_url}/api/v1/connections/google_analytics")
        connection = response.json()
        print(f"   Status: {connection['status']}")
        print(f"   Last checked: {connection['last_checked']}")
        print()
        
        # 5. Get updated status
        print("5. Getting updated connections status...")
        response = await client.get(f"{base_url}/api/v1/connections")
        connections = response.json()
        print(f"   Connected services: {connections['connected_count']}/{connections['total_services']}")


if __name__ == "__main__":
    print("Service Connections API Example")
    print("=" * 50)
    print("Make sure the server is running: make dev")
    print("=" * 50 + "\n")
    
    asyncio.run(main())