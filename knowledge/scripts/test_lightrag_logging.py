#!/usr/bin/env python3
"""Test script to verify LightRAG logging is working"""

import asyncio
import aiohttp
import json

API_BASE = "http://localhost:8004"

async def test_logging():
    """Test LightRAG logging by triggering various operations"""
    async with aiohttp.ClientSession() as session:
        namespace_id = "test_logging"
        
        print("1. Creating test namespace...")
        async with session.post(
            f"{API_BASE}/api/namespaces?namespace_id={namespace_id}",
            json={
                "name": "Test Logging",
                "description": "Testing LightRAG logging functionality"
            }
        ) as resp:
            if resp.status == 409:
                print("   Namespace already exists")
            else:
                print(f"   Created namespace: {await resp.json()}")
        
        print("\n2. Adding a document to trigger LightRAG processing...")
        async with session.post(
            f"{API_BASE}/api/{namespace_id}/documents",
            json={
                "content": """
                This is a test document to observe LightRAG logging.
                
                It contains information about testing the logging system.
                We want to see entity extraction, chunking, and storage operations.
                
                The document mentions several entities like Python, LightRAG, and logging.
                It also discusses relationships between these entities.
                """,
                "metadata": {"purpose": "logging_test"}
            }
        ) as resp:
            result = await resp.json()
            print(f"   Document added: {result}")
        
        print("\n3. Querying to trigger retrieval operations...")
        async with session.post(
            f"{API_BASE}/api/{namespace_id}/query",
            json={
                "query": "What entities are mentioned in the logging test?",
                "mode": "hybrid"
            }
        ) as resp:
            result = await resp.json()
            print(f"   Query result preview: {result['result'][:200]}...")
        
        print("\n4. Checking processing status...")
        async with session.get(
            f"{API_BASE}/api/namespaces/{namespace_id}/processing"
        ) as resp:
            result = await resp.json()
            print(f"   Processing status: {result}")
        
        print("\n5. Getting statistics...")
        async with session.get(
            f"{API_BASE}/api/namespaces/{namespace_id}/statistics"
        ) as resp:
            result = await resp.json()
            print(f"   Statistics: {result}")
        
        print("\n✅ Test completed! Check the knowledge service logs for LightRAG output.")

if __name__ == "__main__":
    print("Testing LightRAG logging...")
    print("Make sure the knowledge service is running with LIGHTRAG_LOG_LEVEL=DEBUG")
    print("-" * 60)
    asyncio.run(test_logging())