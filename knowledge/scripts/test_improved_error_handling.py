#!/usr/bin/env python3
"""
Test the improved error handling for file uploads
"""
import asyncio
import aiohttp
import time
import random
import string

EDITOR_BACKEND_URL = "http://localhost:8001"

async def test_improved_error_handling():
    """Test various scenarios to check improved error handling"""
    
    print("🧪 Testing Improved Error Handling\n" + "="*50)
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Normal upload (should work)
        print("\n1. Testing normal upload...")
        form_data = aiohttp.FormData()
        form_data.add_field(
            'files',
            "Normal test content".encode('utf-8'),
            filename='normal_test.txt',
            content_type='text/plain'
        )
        
        try:
            async with session.post(
                f"{EDITOR_BACKEND_URL}/api/v1/knowledge/graphs/test_enhanced/upload",
                data=form_data
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✓ Normal upload successful")
                    print(f"  - Message: {data.get('message')}")
                else:
                    print(f"✗ Normal upload failed: {resp.status}")
                    error = await resp.text()
                    print(f"  Error: {error}")
        except Exception as e:
            print(f"✗ Exception: {type(e).__name__}: {e}")
        
        # Test 2: Very large file (10MB) - might trigger timeout
        print("\n2. Testing very large file (10MB)...")
        large_content = ''.join(random.choices(string.ascii_letters + string.digits, k=10*1024*1024))
        
        form_data = aiohttp.FormData()
        form_data.add_field(
            'files',
            large_content.encode('utf-8'),
            filename='large_10mb.txt',
            content_type='text/plain'
        )
        
        try:
            start = time.time()
            async with session.post(
                f"{EDITOR_BACKEND_URL}/api/v1/knowledge/graphs/test_enhanced/upload",
                data=form_data,
                timeout=aiohttp.ClientTimeout(total=150)  # Client timeout > server timeout
            ) as resp:
                elapsed = time.time() - start
                if resp.status == 200:
                    print(f"✓ Large file upload successful in {elapsed:.1f}s")
                else:
                    print(f"✗ Large file upload failed: {resp.status} after {elapsed:.1f}s")
                    error = await resp.text()
                    print(f"  Error: {error}")
                    
                    # Check if error message includes timeout info
                    if "120 seconds" in error:
                        print("  ✓ Error message correctly mentions 120-second timeout")
        except asyncio.TimeoutError:
            elapsed = time.time() - start
            print(f"✗ Client-side timeout after {elapsed:.1f}s")
        except Exception as e:
            print(f"✗ Exception: {type(e).__name__}: {e}")
        
        # Test 3: Invalid namespace (should get 404)
        print("\n3. Testing invalid namespace...")
        form_data = aiohttp.FormData()
        form_data.add_field(
            'files',
            "Test content".encode('utf-8'),
            filename='test.txt',
            content_type='text/plain'
        )
        
        try:
            async with session.post(
                f"{EDITOR_BACKEND_URL}/api/v1/knowledge/graphs/nonexistent_namespace/upload",
                data=form_data
            ) as resp:
                if resp.status == 404:
                    print("✓ Correctly returned 404 for invalid namespace")
                    error = await resp.text()
                    if "not found" in error.lower():
                        print("  ✓ Error message indicates namespace not found")
                else:
                    print(f"✗ Unexpected status: {resp.status}")
        except Exception as e:
            print(f"✗ Exception: {type(e).__name__}: {e}")
        
        # Test 4: Multiple medium-sized files
        print("\n4. Testing multiple medium-sized files...")
        form_data = aiohttp.FormData()
        for i in range(5):
            content = ''.join(random.choices(string.ascii_letters, k=500*1024))  # 500KB each
            form_data.add_field(
                'files',
                content.encode('utf-8'),
                filename=f'medium_{i}.txt',
                content_type='text/plain'
            )
        
        try:
            start = time.time()
            async with session.post(
                f"{EDITOR_BACKEND_URL}/api/v1/knowledge/graphs/test_enhanced/upload",
                data=form_data
            ) as resp:
                elapsed = time.time() - start
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✓ Multiple files upload successful in {elapsed:.1f}s")
                    print(f"  - Uploaded: {data.get('uploaded')}")
                    print(f"  - Failed: {data.get('failed')}")
                else:
                    print(f"✗ Multiple files upload failed: {resp.status}")
                    error = await resp.text()
                    print(f"  Error: {error}")
        except Exception as e:
            print(f"✗ Exception: {type(e).__name__}: {e}")
        
        print("\n" + "="*50)
        print("Testing complete!")
        print("\nCheck the editor-backend logs for detailed error information.")

if __name__ == "__main__":
    asyncio.run(test_improved_error_handling())