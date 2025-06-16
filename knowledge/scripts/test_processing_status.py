#!/usr/bin/env python3
"""
Test script for processing status endpoints
"""
import asyncio
import aiohttp
import json
import time
from datetime import datetime

EDITOR_BACKEND_URL = "http://localhost:8001"
KNOWLEDGE_SERVICE_URL = "http://localhost:8004"

async def test_processing_status_endpoints():
    """Test the new processing status endpoints"""
    
    async with aiohttp.ClientSession() as session:
        print("Testing Processing Status Endpoints\n" + "="*50)
        
        namespace_id = "test_enhanced"
        
        # 1. Test processing status endpoint
        print("\n1. Testing processing status endpoint...")
        try:
            async with session.get(
                f"{EDITOR_BACKEND_URL}/api/v1/knowledge/graphs/{namespace_id}/processing"
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✓ Processing status retrieved")
                    print(f"  - Total documents: {data['total']}")
                    print(f"  - Pending: {data['pending']}")
                    print(f"  - Processing: {data['processing']}")
                    print(f"  - Failed: {data['failed']}")
                    
                    if data['documents']:
                        print(f"\n  First 3 documents:")
                        for doc in data['documents'][:3]:
                            print(f"    - {doc['id'][:20]}... Status: {doc['status']}")
                            if doc.get('error'):
                                print(f"      Error: {doc['error']}")
                else:
                    print(f"✗ Failed to get processing status: {resp.status}")
                    error = await resp.text()
                    print(f"  Error: {error}")
        except Exception as e:
            print(f"✗ Exception: {type(e).__name__}: {e}")
        
        # 2. Test recent activity endpoint
        print("\n2. Testing recent activity endpoint...")
        try:
            async with session.get(
                f"{EDITOR_BACKEND_URL}/api/v1/knowledge/graphs/{namespace_id}/recent",
                params={"hours": 24}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✓ Recent activity retrieved (last 24 hours)")
                    print(f"  - Total documents: {data['total']}")
                    print(f"  - Processed: {data['processed']}")
                    print(f"  - Failed: {data['failed']}")
                    print(f"  - Cutoff time: {data['cutoff_time']}")
                    
                    if data['documents']:
                        print(f"\n  Most recent 3 documents:")
                        for doc in data['documents'][:3]:
                            print(f"    - {doc['id'][:20]}... Status: {doc['status']}")
                            print(f"      Updated: {doc['updated_at']}")
                else:
                    print(f"✗ Failed to get recent activity: {resp.status}")
        except Exception as e:
            print(f"✗ Exception: {type(e).__name__}: {e}")
        
        # 3. Upload files and test batch tracking
        print("\n3. Testing batch upload with tracking...")
        
        # Create test files
        form_data = aiohttp.FormData()
        for i in range(3):
            content = f"Test document {i} for processing status tracking - {datetime.now()}"
            form_data.add_field(
                'files',
                content.encode('utf-8'),
                filename=f'test_processing_{i}.txt',
                content_type='text/plain'
            )
        
        batch_id = None
        document_ids = []
        
        try:
            async with session.post(
                f"{EDITOR_BACKEND_URL}/api/v1/knowledge/graphs/{namespace_id}/upload",
                data=form_data
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    batch_id = data.get('batch_id')
                    document_ids = data.get('document_ids', [])
                    print(f"✓ Batch upload successful")
                    print(f"  - Batch ID: {batch_id}")
                    print(f"  - Uploaded: {data.get('uploaded', 0)}")
                    print(f"  - Failed: {data.get('failed', 0)}")
                    print(f"  - Document IDs: {len(document_ids)}")
                else:
                    print(f"✗ Batch upload failed: {resp.status}")
                    error = await resp.text()
                    print(f"  Error: {error}")
        except Exception as e:
            print(f"✗ Exception during upload: {type(e).__name__}: {e}")
        
        # 4. Test batch status endpoint
        if batch_id:
            print("\n4. Testing batch status endpoint...")
            await asyncio.sleep(2)  # Give it time to process
            
            try:
                async with session.get(
                    f"{EDITOR_BACKEND_URL}/api/v1/knowledge/batches/{batch_id}"
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"✓ Batch status retrieved")
                        print(f"  - Batch status: {data['status']}")
                        print(f"  - Status summary: {json.dumps(data['status_summary'], indent=4)}")
                        
                        if data.get('documents'):
                            print(f"\n  Document statuses:")
                            for doc in data['documents']:
                                print(f"    - {doc['id'][:20]}... Status: {doc['status']}")
                    else:
                        print(f"✗ Failed to get batch status: {resp.status}")
            except Exception as e:
                print(f"✗ Exception: {type(e).__name__}: {e}")
        
        # 5. Test individual document status
        if document_ids:
            print("\n5. Testing individual document status...")
            doc_id = document_ids[0]
            
            try:
                async with session.get(
                    f"{EDITOR_BACKEND_URL}/api/v1/knowledge/graphs/{namespace_id}/documents/{doc_id}"
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"✓ Document status retrieved")
                        print(f"  - Document ID: {data['id'][:30]}...")
                        print(f"  - Status: {data['status']}")
                        print(f"  - Chunks: {data['chunks_count']}")
                        print(f"  - Content length: {data['content_length']}")
                        print(f"  - Created: {data['created_at']}")
                        print(f"  - Updated: {data['updated_at']}")
                        if data.get('error'):
                            print(f"  - Error: {data['error']}")
                    else:
                        print(f"✗ Failed to get document status: {resp.status}")
            except Exception as e:
                print(f"✗ Exception: {type(e).__name__}: {e}")
        
        # 6. Test with non-existent document
        print("\n6. Testing error handling (non-existent document)...")
        try:
            async with session.get(
                f"{EDITOR_BACKEND_URL}/api/v1/knowledge/graphs/{namespace_id}/documents/doc-nonexistent"
            ) as resp:
                if resp.status == 404:
                    print("✓ Correctly returned 404 for non-existent document")
                    error = await resp.text()
                    if "not found" in error.lower():
                        print("  ✓ Error message indicates document not found")
                else:
                    print(f"✗ Unexpected status: {resp.status}")
        except Exception as e:
            print(f"✗ Exception: {type(e).__name__}: {e}")
        
        print("\n" + "="*50)
        print("Processing status endpoint tests complete!")

if __name__ == "__main__":
    asyncio.run(test_processing_status_endpoints())