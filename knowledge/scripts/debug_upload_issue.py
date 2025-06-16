#!/usr/bin/env python3
"""
Debug script for upload failures
"""
import asyncio
import aiohttp
import json
import os
import sys

EDITOR_BACKEND_URL = "http://localhost:8001"
KNOWLEDGE_SERVICE_URL = "http://localhost:8004"

async def test_upload_directly():
    """Test upload directly to knowledge service to isolate the issue"""
    
    print("🔍 Debugging Upload Issue\n" + "="*50)
    
    async with aiohttp.ClientSession() as session:
        # 1. First check if namespace exists
        print("\n1. Checking if test_enhanced namespace exists...")
        try:
            async with session.get(f"{KNOWLEDGE_SERVICE_URL}/api/namespaces/test_enhanced") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✓ Namespace exists: {data['name']}")
                else:
                    print(f"✗ Namespace not found: {resp.status}")
                    return
        except Exception as e:
            print(f"✗ Error checking namespace: {e}")
            return
        
        # 2. Create a test file to upload
        print("\n2. Creating test file...")
        test_content = "This is a test upload to debug the 503 error."
        test_filename = "test_debug.txt"
        
        # 3. Test direct upload to knowledge service
        print("\n3. Testing direct upload to knowledge service...")
        try:
            # Create form data
            form_data = aiohttp.FormData()
            form_data.add_field(
                'files',
                test_content.encode('utf-8'),
                filename=test_filename,
                content_type='text/plain'
            )
            
            async with session.post(
                f"{KNOWLEDGE_SERVICE_URL}/api/test_enhanced/documents/batch-upload",
                data=form_data
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✓ Direct upload successful:")
                    print(f"  - Status: {data.get('status')}")
                    print(f"  - Message: {data.get('message')}")
                    print(f"  - Successful: {len(data.get('successful_uploads', []))}")
                    print(f"  - Failed: {len(data.get('failed_uploads', []))}")
                else:
                    error_text = await resp.text()
                    print(f"✗ Direct upload failed: {resp.status}")
                    print(f"  Error: {error_text}")
        except Exception as e:
            print(f"✗ Exception during direct upload: {type(e).__name__}: {e}")
        
        # 4. Test upload via editor-backend
        print("\n4. Testing upload via editor-backend proxy...")
        try:
            # Create form data for editor-backend
            form_data = aiohttp.FormData()
            form_data.add_field(
                'files',
                test_content.encode('utf-8'),
                filename=test_filename,
                content_type='text/plain'
            )
            
            async with session.post(
                f"{EDITOR_BACKEND_URL}/api/v1/knowledge/graphs/test_enhanced/upload",
                data=form_data,
                timeout=aiohttp.ClientTimeout(total=60)  # Increase timeout
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✓ Proxy upload successful:")
                    print(f"  - Status: {data.get('status')}")
                    print(f"  - Message: {data.get('message')}")
                    print(f"  - Uploaded: {data.get('uploaded')}")
                    print(f"  - Failed: {data.get('failed')}")
                else:
                    error_text = await resp.text()
                    print(f"✗ Proxy upload failed: {resp.status}")
                    print(f"  Error: {error_text}")
                    
                    # Try to parse error details
                    try:
                        error_json = json.loads(error_text)
                        print(f"  Detail: {error_json.get('detail', 'No detail provided')}")
                    except:
                        pass
                        
        except asyncio.TimeoutError:
            print(f"✗ Timeout error during proxy upload (exceeded 60s)")
        except Exception as e:
            print(f"✗ Exception during proxy upload: {type(e).__name__}: {e}")
        
        # 5. Test health check endpoints
        print("\n5. Testing health endpoints...")
        for url, name in [
            (f"{KNOWLEDGE_SERVICE_URL}/health", "Knowledge Service"),
            (f"{EDITOR_BACKEND_URL}/api/v1/knowledge/health", "Editor Backend Proxy")
        ]:
            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        print(f"✓ {name} is healthy")
                    else:
                        print(f"✗ {name} health check failed: {resp.status}")
            except Exception as e:
                print(f"✗ {name} unreachable: {e}")
        
        print("\n" + "="*50)
        print("Debug complete!")

if __name__ == "__main__":
    asyncio.run(test_upload_directly())