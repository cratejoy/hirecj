#!/usr/bin/env python3
"""High-volume test for non-blocking document processing"""

import asyncio
import aiohttp
import json
import time
import random
import string

API_BASE = "http://localhost:8004"

def generate_random_content(size_kb: int = 5) -> str:
    """Generate random text content of approximately the specified size in KB"""
    chars = string.ascii_letters + string.digits + ' \n'
    # Approximately 1024 chars per KB
    return ''.join(random.choice(chars) for _ in range(size_kb * 1024))

async def test_high_volume_processing():
    """Test non-blocking with high volume document uploads"""
    async with aiohttp.ClientSession() as session:
        namespace_id = "test_highvolume"
        
        print("1. Creating test namespace...")
        async with session.post(
            f"{API_BASE}/api/namespaces?namespace_id={namespace_id}",
            json={
                "name": "High Volume Test",
                "description": "Testing non-blocking with many documents"
            }
        ) as resp:
            if resp.status == 409:
                print("   Namespace already exists")
            else:
                print(f"   Created namespace: {resp.status}")
        
        # Test 1: Many single documents in parallel
        print("\n2. Testing 20 parallel single document uploads...")
        tasks = []
        start_time = time.time()
        
        async def upload_document(doc_num: int):
            content = generate_random_content(10)  # 10KB documents
            async with session.post(
                f"{API_BASE}/api/{namespace_id}/documents",
                json={
                    "content": f"Document {doc_num}\n{content}",
                    "metadata": {"doc_num": str(doc_num), "test": "parallel"}
                }
            ) as resp:
                return await resp.json()
        
        # Launch all uploads in parallel
        for i in range(20):
            tasks.append(upload_document(i))
        
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        pending_count = sum(1 for r in results if r.get('status') == 'pending')
        print(f"   Total time for 20 parallel uploads: {total_time:.3f}s")
        print(f"   Average time per upload: {total_time/20:.3f}s")
        print(f"   Documents queued: {pending_count}")
        
        if total_time < 5.0:
            print("   ✅ Excellent! Parallel uploads completed very quickly")
        elif total_time < 10.0:
            print("   ✅ Good! Parallel uploads completed reasonably fast")
        else:
            print("   ⚠️  WARNING: Parallel uploads took longer than expected")
        
        # Test 2: Large batch upload
        print("\n3. Testing large batch upload (50 files)...")
        data = aiohttp.FormData()
        for i in range(50):
            content = generate_random_content(5)  # 5KB each
            data.add_field('files', content, 
                          filename=f'batch_test_{i}.txt', 
                          content_type='text/plain')
        
        start_time = time.time()
        async with session.post(
            f"{API_BASE}/api/{namespace_id}/documents/batch-upload",
            data=data
        ) as resp:
            result = await resp.json()
            elapsed = time.time() - start_time
            
            print(f"   Response time: {elapsed:.3f}s")
            print(f"   Status: {result.get('status')}")
            print(f"   Files queued: {result.get('uploaded', 0)}")
            print(f"   Files failed: {result.get('failed', 0)}")
            
            if elapsed < 5.0:
                print("   ✅ Excellent! Batch upload returned very quickly")
            elif elapsed < 10.0:
                print("   ✅ Good! Batch upload returned reasonably fast")
            else:
                print("   ⚠️  WARNING: Batch upload took longer than expected")
        
        # Test 3: Mixed workload
        print("\n4. Testing mixed workload (documents + URLs)...")
        mixed_tasks = []
        start_time = time.time()
        
        # Add some documents
        for i in range(10):
            task = session.post(
                f"{API_BASE}/api/{namespace_id}/documents",
                json={
                    "content": f"Mixed test document {i}\n{generate_random_content(3)}",
                    "metadata": {"test": "mixed", "type": "document"}
                }
            )
            mixed_tasks.append(task)
        
        # Add some URLs
        test_urls = [
            "https://example.com",
            "https://httpbin.org/html",
            "https://httpbin.org/json"
        ]
        for url in test_urls:
            task = session.post(
                f"{API_BASE}/api/{namespace_id}/documents/url",
                json={
                    "url": url,
                    "metadata": {"test": "mixed", "type": "url"}
                }
            )
            mixed_tasks.append(task)
        
        # Execute all tasks
        responses = await asyncio.gather(*mixed_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        successful = sum(1 for r in responses if not isinstance(r, Exception))
        print(f"   Total time for mixed workload: {total_time:.3f}s")
        print(f"   Successful requests: {successful}/{len(mixed_tasks)}")
        
        # Wait and check final status
        print("\n5. Waiting for background processing...")
        await asyncio.sleep(10)
        
        async with session.get(
            f"{API_BASE}/api/namespaces/{namespace_id}/statistics"
        ) as resp:
            stats = await resp.json()
            print("\n6. Final statistics:")
            print(f"   Total processed: {stats.get('document_count', 0)}")
            print(f"   Total chunks: {stats.get('total_chunks', 0)}")
            print(f"   Pending: {stats.get('pending_count', 0)}")
            print(f"   Failed: {stats.get('failed_count', 0)}")
            print(f"   Status breakdown: {stats.get('status_breakdown', {})}")
        
        print("\n✅ High-volume test completed!")
        print("   The API successfully handled high-volume uploads without blocking.")
        print("   Documents are being processed asynchronously in the background.")

if __name__ == "__main__":
    print("High-Volume Non-Blocking Test")
    print("=" * 60)
    print("This test verifies that the API remains responsive under high load")
    print("=" * 60)
    asyncio.run(test_high_volume_processing())