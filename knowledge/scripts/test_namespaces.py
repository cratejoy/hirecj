#!/usr/bin/env python3
"""
Test script for namespace management functionality
"""
import asyncio
import aiohttp
import json
import sys

API_BASE = "http://localhost:8004"

async def test_namespace_operations():
    """Test namespace CRUD operations"""
    async with aiohttp.ClientSession() as session:
        print("🧪 Testing Namespace Management...\n")
        
        # 1. Health check
        print("1. Health Check")
        async with session.get(f"{API_BASE}/health") as resp:
            health = await resp.json()
            print(f"   Status: {health['status']}")
            print(f"   Phase: {health['phase']}")
            print(f"   Namespaces: {health['namespaces_count']}")
            print(f"   Working Dir: {health['working_dir']}\n")
        
        # 2. List namespaces (should be empty initially)
        print("2. List Namespaces (initial)")
        async with session.get(f"{API_BASE}/api/namespaces") as resp:
            data = await resp.json()
            print(f"   Count: {data['count']}")
            print(f"   Namespaces: {data['namespaces']}\n")
        
        # 3. Create a product namespace
        print("3. Create 'products' namespace")
        async with session.post(
            f"{API_BASE}/api/namespaces?namespace_id=products",
            json={
                "name": "Product Catalog",
                "description": "Product information and specifications"
            }
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                print(f"   ✅ Created: {result['message']}")
            else:
                error = await resp.text()
                print(f"   ❌ Error: {error}")
        print()
        
        # 4. Create a support namespace
        print("4. Create 'support' namespace")
        async with session.post(
            f"{API_BASE}/api/namespaces?namespace_id=support",
            json={
                "name": "Customer Support",
                "description": "FAQs and troubleshooting guides"
            }
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                print(f"   ✅ Created: {result['message']}")
            else:
                error = await resp.text()
                print(f"   ❌ Error: {error}")
        print()
        
        # 5. Try to create duplicate namespace (should fail)
        print("5. Try to create duplicate 'products' namespace")
        async with session.post(
            f"{API_BASE}/api/namespaces?namespace_id=products",
            json={
                "name": "Duplicate Products",
                "description": "This should fail"
            }
        ) as resp:
            if resp.status == 409:
                error = await resp.json()
                print(f"   ✅ Expected error: {error['detail']}")
            else:
                print(f"   ❌ Unexpected status: {resp.status}")
        print()
        
        # 6. Get specific namespace
        print("6. Get 'products' namespace")
        async with session.get(f"{API_BASE}/api/namespaces/products") as resp:
            if resp.status == 200:
                namespace = await resp.json()
                print(f"   ID: {namespace['id']}")
                print(f"   Name: {namespace['name']}")
                print(f"   Description: {namespace['description']}")
                print(f"   Created: {namespace['created_at']}")
            else:
                error = await resp.text()
                print(f"   ❌ Error: {error}")
        print()
        
        # 7. List all namespaces
        print("7. List all namespaces")
        async with session.get(f"{API_BASE}/api/namespaces") as resp:
            data = await resp.json()
            print(f"   Count: {data['count']}")
            for ns in data['namespaces']:
                print(f"   - {ns['id']}: {ns['name']}")
        print()
        
        # 8. Delete a namespace
        print("8. Delete 'support' namespace")
        async with session.delete(f"{API_BASE}/api/namespaces/support") as resp:
            if resp.status == 200:
                result = await resp.json()
                print(f"   ✅ {result['message']}")
            else:
                error = await resp.text()
                print(f"   ❌ Error: {error}")
        print()
        
        # 9. Verify deletion
        print("9. List namespaces after deletion")
        async with session.get(f"{API_BASE}/api/namespaces") as resp:
            data = await resp.json()
            print(f"   Count: {data['count']}")
            for ns in data['namespaces']:
                print(f"   - {ns['id']}: {ns['name']}")
        print()
        
        # 10. Try invalid namespace ID
        print("10. Try to create namespace with invalid ID")
        async with session.post(
            f"{API_BASE}/api/namespaces?namespace_id=Invalid-Name!",
            json={
                "name": "Invalid",
                "description": "Should fail due to invalid ID"
            }
        ) as resp:
            if resp.status == 422:
                print(f"   ✅ Expected validation error")
            else:
                print(f"   ❌ Unexpected status: {resp.status}")
        
        print("\n✅ Namespace management tests completed!")

if __name__ == "__main__":
    asyncio.run(test_namespace_operations())