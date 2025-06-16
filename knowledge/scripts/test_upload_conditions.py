#!/usr/bin/env python3
"""
Test various upload conditions to reproduce the 503 error
"""
import asyncio
import aiohttp
import time

EDITOR_BACKEND_URL = "http://localhost:8001"

async def test_various_conditions():
    """Test different upload scenarios that might trigger 503"""
    
    print("🧪 Testing Various Upload Conditions\n" + "="*50)
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Large file
        print("\n1. Testing large file upload (5MB)...")
        large_content = "x" * (5 * 1024 * 1024)  # 5MB of 'x'
        
        form_data = aiohttp.FormData()
        form_data.add_field(
            'files',
            large_content.encode('utf-8'),
            filename='large_file.txt',
            content_type='text/plain'
        )
        
        try:
            start = time.time()
            async with session.post(
                f"{EDITOR_BACKEND_URL}/api/v1/knowledge/graphs/test_enhanced/upload",
                data=form_data,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as resp:
                elapsed = time.time() - start
                if resp.status == 200:
                    print(f"✓ Large file upload successful in {elapsed:.1f}s")
                else:
                    print(f"✗ Large file upload failed: {resp.status} in {elapsed:.1f}s")
                    error = await resp.text()
                    print(f"  Error: {error[:200]}...")
        except asyncio.TimeoutError:
            print("✗ Large file upload timed out (>120s)")
        except Exception as e:
            print(f"✗ Large file upload exception: {type(e).__name__}: {e}")
        
        # Test 2: Multiple files at once
        print("\n2. Testing multiple files upload (10 files)...")
        form_data = aiohttp.FormData()
        for i in range(10):
            content = f"Test file {i} content with some data to process"
            form_data.add_field(
                'files',
                content.encode('utf-8'),
                filename=f'test_file_{i}.txt',
                content_type='text/plain'
            )
        
        try:
            start = time.time()
            async with session.post(
                f"{EDITOR_BACKEND_URL}/api/v1/knowledge/graphs/test_enhanced/upload",
                data=form_data,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                elapsed = time.time() - start
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✓ Multiple files upload successful in {elapsed:.1f}s")
                    print(f"  - Uploaded: {data.get('uploaded', 0)}")
                    print(f"  - Failed: {data.get('failed', 0)}")
                else:
                    print(f"✗ Multiple files upload failed: {resp.status} in {elapsed:.1f}s")
                    error = await resp.text()
                    print(f"  Error: {error[:200]}...")
        except Exception as e:
            print(f"✗ Multiple files upload exception: {type(e).__name__}: {e}")
        
        # Test 3: Concurrent uploads
        print("\n3. Testing concurrent uploads (5 parallel requests)...")
        
        async def single_upload(session, index):
            form_data = aiohttp.FormData()
            form_data.add_field(
                'files',
                f"Concurrent upload {index}".encode('utf-8'),
                filename=f'concurrent_{index}.txt',
                content_type='text/plain'
            )
            
            try:
                async with session.post(
                    f"{EDITOR_BACKEND_URL}/api/v1/knowledge/graphs/test_enhanced/upload",
                    data=form_data
                ) as resp:
                    return index, resp.status
            except Exception as e:
                return index, f"Error: {type(e).__name__}"
        
        start = time.time()
        tasks = [single_upload(session, i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start
        
        success_count = sum(1 for _, status in results if status == 200)
        print(f"  Completed in {elapsed:.1f}s")
        print(f"  - Successful: {success_count}/5")
        for index, status in results:
            if status != 200:
                print(f"  - Upload {index}: {status}")
        
        # Test 4: Check if it's a namespace-specific issue
        print("\n4. Testing with different namespace (products)...")
        form_data = aiohttp.FormData()
        form_data.add_field(
            'files',
            "Test content for products namespace".encode('utf-8'),
            filename='products_test.txt',
            content_type='text/plain'
        )
        
        try:
            async with session.post(
                f"{EDITOR_BACKEND_URL}/api/v1/knowledge/graphs/products/upload",
                data=form_data
            ) as resp:
                if resp.status == 200:
                    print("✓ Upload to 'products' namespace successful")
                else:
                    print(f"✗ Upload to 'products' namespace failed: {resp.status}")
        except Exception as e:
            print(f"✗ Products namespace upload exception: {type(e).__name__}: {e}")
        
        print("\n" + "="*50)
        print("Testing complete!")
        print("\nPossible causes of 503 errors:")
        print("1. Large files exceeding timeout limits")
        print("2. Knowledge service temporarily unavailable")
        print("3. Memory/resource issues during processing")
        print("4. Network connectivity issues")

if __name__ == "__main__":
    asyncio.run(test_various_conditions())