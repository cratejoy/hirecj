#!/usr/bin/env python3
"""
Test script for Phase 1.1: File Upload Functionality
Tests single and batch file upload endpoints
"""
import asyncio
import aiohttp
import json
import sys
import os
from pathlib import Path

API_BASE = "http://localhost:8004"
TEST_FILES_DIR = Path(__file__).parent.parent / "data" / "test_files"

async def test_file_upload():
    """Test file upload functionality"""
    async with aiohttp.ClientSession() as session:
        print("🧪 Testing Phase 1.1: File Upload Functionality\n")
        
        # Setup: Create test namespace
        print("Setup: Creating test namespace...")
        async with session.post(
            f"{API_BASE}/api/namespaces?namespace_id=test_uploads",
            json={
                "name": "Test File Uploads",
                "description": "Namespace for testing file upload operations"
            }
        ) as resp:
            if resp.status == 200:
                print("   ✅ Test namespace created")
            elif resp.status == 409:
                print("   ℹ️  Test namespace already exists")
            else:
                print(f"   ❌ Failed to create namespace: {await resp.text()}")
                return
        print()
        
        # Test 1: Single file upload
        print("Test 1: Single file upload (.txt)")
        txt_file = TEST_FILES_DIR / "sample_document.txt"
        
        if not txt_file.exists():
            print(f"   ❌ Test file not found: {txt_file}")
            return
            
        with open(txt_file, 'rb') as f:
            data = aiohttp.FormData()
            data.add_field('file', f, filename='sample_document.txt', content_type='text/plain')
            
            async with session.post(
                f"{API_BASE}/api/test_uploads/documents/upload",
                data=data
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"   ✅ File uploaded successfully")
                    print(f"      - Filename: {result['filename']}")
                    print(f"      - Content length: {result['content_length']} chars")
                    print(f"      - Metadata: {json.dumps(result['metadata'], indent=8)}")
                else:
                    print(f"   ❌ Upload failed: {await resp.text()}")
                    return
        print()
        
        # Test 2: Single file upload (.md)
        print("Test 2: Single file upload (.md)")
        md_file = TEST_FILES_DIR / "technical_guide.md"
        
        with open(md_file, 'rb') as f:
            data = aiohttp.FormData()
            data.add_field('file', f, filename='technical_guide.md', content_type='text/markdown')
            
            async with session.post(
                f"{API_BASE}/api/test_uploads/documents/upload",
                data=data
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"   ✅ Markdown file uploaded successfully")
                    print(f"      - Content length: {result['content_length']} chars")
                else:
                    print(f"   ❌ Upload failed: {await resp.text()}")
        print()
        
        # Test 3: Batch file upload
        print("Test 3: Batch file upload")
        data = aiohttp.FormData()
        
        # Read files and add to form data
        with open(txt_file, 'rb') as f:
            txt_content = f.read()
        with open(md_file, 'rb') as f:
            md_content = f.read()
            
        data.add_field('files', txt_content, filename='sample_document.txt', content_type='text/plain')
        data.add_field('files', md_content, filename='technical_guide.md', content_type='text/markdown')
        
        async with session.post(
            f"{API_BASE}/api/test_uploads/documents/batch-upload",
            data=data
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                print(f"   ✅ Batch upload: {result['status']}")
                print(f"      - Message: {result['message']}")
                print(f"      - Successful uploads: {len(result['successful_uploads'])}")
                for upload in result['successful_uploads']:
                    print(f"        • {upload['filename']} ({upload['content_length']} chars)")
                if result['failed_uploads']:
                    print(f"      - Failed uploads: {len(result['failed_uploads'])}")
                    for fail in result['failed_uploads']:
                        print(f"        • {fail['filename']}: {fail['error']}")
            else:
                print(f"   ❌ Batch upload failed: {await resp.text()}")
        print()
        
        # Test 4: Unsupported file type
        print("Test 4: Unsupported file type validation")
        
        # Create a temporary unsupported file
        unsupported_file = TEST_FILES_DIR / "test.pdf"
        unsupported_file.write_text("Fake PDF content")
        
        try:
            with open(unsupported_file, 'rb') as f:
                data = aiohttp.FormData()
                data.add_field('file', f, filename='test.pdf', content_type='application/pdf')
                
                async with session.post(
                    f"{API_BASE}/api/test_uploads/documents/upload",
                    data=data
                ) as resp:
                    if resp.status == 400:
                        error = await resp.json()
                        print(f"   ✅ Correctly rejected unsupported file type")
                        print(f"      - Error: {error['detail']}")
                    else:
                        print(f"   ❌ Should have rejected PDF file")
        finally:
            # Clean up temp file
            if unsupported_file.exists():
                unsupported_file.unlink()
        print()
        
        # Test 5: Query uploaded content
        print("Test 5: Query uploaded content")
        query_text = "What are the query modes in LightRAG?"
        
        async with session.post(
            f"{API_BASE}/api/test_uploads/query",
            json={
                "query": query_text,
                "mode": "hybrid"
            }
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                print(f"   ✅ Query successful")
                print(f"      - Query: {query_text}")
                print(f"      - Mode: {result['mode']}")
                print(f"      - Result preview: {result['result'][:200]}...")
            else:
                print(f"   ❌ Query failed: {await resp.text()}")
        
        print("\n✅ File upload tests completed!")

async def main():
    """Main test runner"""
    try:
        # Check if test files exist
        if not TEST_FILES_DIR.exists():
            print(f"❌ Test files directory not found: {TEST_FILES_DIR}")
            print("Please ensure test files are created in data/test_files/")
            sys.exit(1)
        
        await test_file_upload()
    except aiohttp.ClientError as e:
        print(f"\n❌ Connection error: {e}")
        print("Make sure the API server is running on port 8004")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    print("Phase 1.1 File Upload Test Script")
    print("=================================\n")
    asyncio.run(main())