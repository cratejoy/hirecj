#!/usr/bin/env python3
"""
Test script for the document statistics API
Tests both the knowledge service and editor-backend proxy endpoints
"""
import asyncio
import aiohttp
import json
from datetime import datetime

KNOWLEDGE_SERVICE_URL = "http://localhost:8004"
EDITOR_BACKEND_URL = "http://localhost:8001"

async def test_statistics_api():
    """Test the statistics API endpoints"""
    
    async with aiohttp.ClientSession() as session:
        print("Testing Document Statistics API\n" + "="*50)
        
        # 1. List all namespaces with statistics via editor-backend
        print("\n1. Listing all knowledge graphs via editor-backend...")
        try:
            async with session.get(f"{EDITOR_BACKEND_URL}/api/v1/knowledge/graphs") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✓ Found {data['count']} knowledge graphs")
                    for graph in data['graphs']:
                        print(f"\n  - {graph['id']}:")
                        print(f"    Name: {graph['name']}")
                        print(f"    Documents: {graph['document_count']}")
                        print(f"    Status: {graph['status']}")
                        print(f"    Last Updated: {graph['last_updated']}")
                else:
                    print(f"✗ Failed to list graphs: {resp.status}")
        except Exception as e:
            print(f"✗ Error listing graphs: {e}")
        
        # 2. Test direct statistics endpoint
        print("\n2. Testing direct statistics endpoint...")
        namespace_id = "products"  # Assuming this exists from previous tests
        
        try:
            # Direct knowledge service endpoint
            async with session.get(f"{KNOWLEDGE_SERVICE_URL}/api/namespaces/{namespace_id}/statistics") as resp:
                if resp.status == 200:
                    stats = await resp.json()
                    print(f"\n✓ Direct statistics for '{namespace_id}':")
                    print(f"  - Document Count: {stats['document_count']}")
                    print(f"  - Total Chunks: {stats['total_chunks']}")
                    print(f"  - Failed Count: {stats['failed_count']}")
                    print(f"  - Pending Count: {stats['pending_count']}")
                    print(f"  - Last Updated: {stats['last_updated']}")
                    if stats.get('status_breakdown'):
                        print(f"  - Status Breakdown: {json.dumps(stats['status_breakdown'], indent=4)}")
                elif resp.status == 404:
                    print(f"✗ Namespace '{namespace_id}' not found")
                else:
                    print(f"✗ Failed to get statistics: {resp.status}")
        except Exception as e:
            print(f"✗ Error getting statistics: {e}")
        
        # 3. Test proxy statistics endpoint
        print(f"\n3. Testing proxy statistics endpoint for '{namespace_id}'...")
        try:
            async with session.get(f"{EDITOR_BACKEND_URL}/api/v1/knowledge/graphs/{namespace_id}/statistics") as resp:
                if resp.status == 200:
                    stats = await resp.json()
                    print(f"✓ Proxy statistics retrieved successfully")
                    print(f"  - Document Count: {stats['document_count']}")
                    print(f"  - Total Chunks: {stats['total_chunks']}")
                else:
                    print(f"✗ Failed to get proxy statistics: {resp.status}")
        except Exception as e:
            print(f"✗ Error getting proxy statistics: {e}")
        
        # 4. Create a test namespace and verify empty statistics
        print("\n4. Testing statistics for new/empty namespace...")
        test_namespace = f"test_stats_{int(datetime.now().timestamp())}"
        
        try:
            # Create namespace
            async with session.post(
                f"{KNOWLEDGE_SERVICE_URL}/api/namespaces",
                params={"namespace_id": test_namespace},
                json={
                    "name": "Test Statistics",
                    "description": "Testing statistics API"
                }
            ) as resp:
                if resp.status == 200:
                    print(f"✓ Created test namespace: {test_namespace}")
                    
                    # Get statistics for empty namespace
                    async with session.get(f"{KNOWLEDGE_SERVICE_URL}/api/namespaces/{test_namespace}/statistics") as stats_resp:
                        if stats_resp.status == 200:
                            stats = await stats_resp.json()
                            print(f"✓ Empty namespace statistics:")
                            print(f"  - Document Count: {stats['document_count']} (should be 0)")
                            print(f"  - Total Chunks: {stats['total_chunks']} (should be 0)")
                            print(f"  - Last Updated: {stats['last_updated']} (should be None)")
                    
                    # Clean up
                    async with session.delete(f"{KNOWLEDGE_SERVICE_URL}/api/namespaces/{test_namespace}") as del_resp:
                        if del_resp.status == 200:
                            print(f"✓ Cleaned up test namespace")
                        
        except Exception as e:
            print(f"✗ Error testing empty namespace: {e}")
        
        print("\n" + "="*50)
        print("Statistics API test complete!")

if __name__ == "__main__":
    asyncio.run(test_statistics_api())