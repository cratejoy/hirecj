#!/usr/bin/env python3
"""Test script to verify non-blocking document processing"""

import asyncio
import aiohttp
import json
import time

API_BASE = "http://localhost:8004"

async def test_nonblocking_processing():
    """Test that document processing is non-blocking"""
    async with aiohttp.ClientSession() as session:
        namespace_id = "test_nonblocking"
        
        print("1. Creating test namespace...")
        async with session.post(
            f"{API_BASE}/api/namespaces?namespace_id={namespace_id}",
            json={
                "name": "Test Non-Blocking",
                "description": "Testing non-blocking document processing"
            }
        ) as resp:
            if resp.status == 409:
                print("   Namespace already exists")
            else:
                print(f"   Created namespace: {resp.status}")
        
        print("\n2. Testing single document upload (should return immediately)...")
        start_time = time.time()
        async with session.post(
            f"{API_BASE}/api/{namespace_id}/documents",
            json={
                "content": """
                This is a test document to verify non-blocking processing.
                The API should return immediately with a pending status.
                """ * 100,  # Make it larger to ensure processing takes time
                "metadata": {"test": "nonblocking"}
            }
        ) as resp:
            result = await resp.json()
            elapsed = time.time() - start_time
            print(f"   Response time: {elapsed:.3f}s")
            print(f"   Status: {result.get('status')}")
            print(f"   Document ID: {result.get('document_id')}")
            
            if elapsed > 1.0:
                print("   ⚠️  WARNING: Response took >1s, might be blocking!")
            else:
                print("   ✅ Response was fast (non-blocking)")
        
        print("\n3. Testing batch file upload (should return immediately)...")
        # Create form data for multiple files
        data = aiohttp.FormData()
        for i in range(5):
            content = f"Test file {i} content\n" * 50
            data.add_field('files', content, filename=f'test{i}.txt', content_type='text/plain')
        
        start_time = time.time()
        async with session.post(
            f"{API_BASE}/api/{namespace_id}/documents/batch-upload",
            data=data
        ) as resp:
            result = await resp.json()
            elapsed = time.time() - start_time
            print(f"   Response time: {elapsed:.3f}s")
            print(f"   Status: {result.get('status')}")
            print(f"   Queued files: {result.get('uploaded')}")
            
            if elapsed > 2.0:
                print("   ⚠️  WARNING: Response took >2s, might be blocking!")
            else:
                print("   ✅ Response was fast (non-blocking)")
        
        print("\n4. Testing URL ingestion (should return immediately after fetch)...")
        start_time = time.time()
        async with session.post(
            f"{API_BASE}/api/{namespace_id}/documents/url",
            json={
                "url": "https://example.com",
                "metadata": {"source": "test"}
            }
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                elapsed = time.time() - start_time
                print(f"   Response time: {elapsed:.3f}s")
                print(f"   Status: {result.get('status')}")
                print(f"   Document ID: {result.get('document_id')}")
                
                # URL fetch + response should be <2s if processing is non-blocking
                if elapsed > 3.0:
                    print("   ⚠️  WARNING: Response took >3s, might be blocking!")
                else:
                    print("   ✅ Response was reasonably fast")
            else:
                print(f"   URL fetch failed: {resp.status}")
        
        print("\n5. Checking document status after a delay...")
        await asyncio.sleep(3)
        
        async with session.get(
            f"{API_BASE}/api/namespaces/{namespace_id}/statistics"
        ) as resp:
            stats = await resp.json()
            print(f"   Processed documents: {stats.get('document_count', 0)}")
            print(f"   Pending documents: {stats.get('pending_count', 0)}")
            print(f"   Failed documents: {stats.get('failed_count', 0)}")
        
        print("\n✅ Non-blocking test completed!")
        print("   If response times were <1s for documents and <2s for batch,")
        print("   then non-blocking processing is working correctly.")

if __name__ == "__main__":
    print("Testing Non-Blocking Document Processing...")
    print("-" * 60)
    asyncio.run(test_nonblocking_processing())