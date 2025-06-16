#!/usr/bin/env python3
"""
Test script for Phase 1.3: Enhanced Ingestion
Tests JSON support, URL fetching, and universal ingestion
"""
import asyncio
import aiohttp
import json
import sys
import subprocess
from pathlib import Path

API_BASE = "http://localhost:8004"
TEST_FILES_DIR = Path(__file__).parent.parent / "data" / "test_files"

async def test_enhanced_ingestion():
    """Test enhanced ingestion features"""
    async with aiohttp.ClientSession() as session:
        print("🧪 Testing Phase 1.3: Enhanced Ingestion\n")
        
        # Setup: Create test namespace
        print("Setup: Creating test namespace...")
        async with session.post(
            f"{API_BASE}/api/namespaces?namespace_id=test_enhanced",
            json={
                "name": "Test Enhanced Ingestion",
                "description": "Namespace for testing enhanced ingestion features"
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
        
        # Test 1: JSON file upload
        print("Test 1: JSON file upload")
        json_file = TEST_FILES_DIR / "sample_data.json"
        
        if not json_file.exists():
            print(f"   ❌ Test file not found: {json_file}")
            return
        
        with open(json_file, 'rb') as f:
            data = aiohttp.FormData()
            data.add_field('file', f, filename='sample_data.json', content_type='application/json')
            
            async with session.post(
                f"{API_BASE}/api/test_enhanced/documents/upload",
                data=data
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"   ✅ JSON file uploaded successfully")
                    print(f"      - Content length: {result['content_length']} chars")
                    print(f"      - Extracted metadata: {', '.join(k for k in result['metadata'] if k not in ['source', 'file_size', 'upload_time', 'file_type'])}")
                else:
                    print(f"   ❌ Upload failed: {await resp.text()}")
                    return
        print()
        
        # Test 2: URL content fetching
        print("Test 2: URL content fetching")
        test_url = "https://httpbin.org/html"
        
        async with session.post(
            f"{API_BASE}/api/test_enhanced/documents/url",
            json={
                "url": test_url,
                "metadata": {"test": "true", "source": "httpbin"}
            }
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                print(f"   ✅ URL content fetched and ingested")
                print(f"      - URL: {result['url']}")
                print(f"      - Content length: {result['content_length']} chars")
                print(f"      - Domain: {result['metadata']['domain']}")
            else:
                print(f"   ❌ URL fetch failed: {await resp.text()}")
        print()
        
        # Test 3: URL with JSON response
        print("Test 3: URL with JSON response")
        json_url = "https://httpbin.org/json"
        
        async with session.post(
            f"{API_BASE}/api/test_enhanced/documents/url",
            json={"url": json_url}
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                print(f"   ✅ JSON URL content processed")
                print(f"      - Content length: {result['content_length']} chars")
            else:
                print(f"   ❌ JSON URL fetch failed: {await resp.text()}")
        print()
        
        # Test 4: Query with different content types
        print("Test 4: Query across different content types")
        query_text = "configuration settings embedding model"
        
        async with session.post(
            f"{API_BASE}/api/test_enhanced/query",
            json={
                "query": query_text,
                "mode": "hybrid"
            }
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                print(f"   ✅ Query successful")
                print(f"      - Found relevant content from ingested data")
                if result['result']:
                    print(f"      - Result preview: {result['result'][:150]}...")
            else:
                print(f"   ❌ Query failed: {await resp.text()}")
        print()
        
        # Test 5: Universal ingestion script - dry run
        print("Test 5: Universal ingestion script - directory dry run")
        cmd = [
            sys.executable,
            str(Path(__file__).parent / "universal_ingest.py"),
            "--namespace", "test_enhanced",
            "--type", "directory",
            "--dry-run",
            str(TEST_FILES_DIR)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print("   ✅ Universal ingestion script dry run successful")
                # Count files that would be ingested
                dry_run_lines = [l for l in result.stdout.split('\n') if '[DRY RUN]' in l]
                print(f"      - Would ingest {len(dry_run_lines)} files")
            else:
                print(f"   ❌ Script failed: {result.stderr}")
        except Exception as e:
            print(f"   ❌ Error running script: {e}")
        print()
        
        # Test 6: Universal ingestion script - single file
        print("Test 6: Universal ingestion script - single file")
        new_file = TEST_FILES_DIR / "universal_test.json"
        new_file.write_text(json.dumps({
            "test": "Universal ingestion test",
            "timestamp": "2024-01-15",
            "data": ["item1", "item2", "item3"]
        }))
        
        cmd = [
            sys.executable,
            str(Path(__file__).parent / "universal_ingest.py"),
            "--namespace", "test_enhanced",
            "--type", "file",
            str(new_file)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print("   ✅ Universal ingestion of single file successful")
                if "✅ Uploaded:" in result.stdout:
                    print("      - File uploaded successfully via script")
            else:
                print(f"   ❌ Script failed: {result.stderr}")
        except Exception as e:
            print(f"   ❌ Error running script: {e}")
        finally:
            # Clean up
            if new_file.exists():
                new_file.unlink()
        
        print("\n✅ Enhanced ingestion tests completed!")

async def main():
    """Main test runner"""
    try:
        await test_enhanced_ingestion()
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
    print("Phase 1.3 Enhanced Ingestion Test Script")
    print("=======================================\n")
    asyncio.run(main())