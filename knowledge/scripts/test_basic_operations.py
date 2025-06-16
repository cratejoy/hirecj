#!/usr/bin/env python3
"""
Test script for Phase 0.3: Basic Operations
Tests document ingestion and query functionality
"""
import asyncio
import aiohttp
import json
import sys
import time

API_BASE = "http://localhost:8004"

async def test_basic_operations():
    """Test document ingestion and query operations"""
    async with aiohttp.ClientSession() as session:
        print("🧪 Testing Phase 0.3: Basic Operations\n")
        
        # Setup: Create test namespace
        print("Setup: Creating test namespace...")
        async with session.post(
            f"{API_BASE}/api/namespaces?namespace_id=test_docs",
            json={
                "name": "Test Documents",
                "description": "Namespace for testing document operations"
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
        
        # Test 1: Add single document
        print("Test 1: Add single document")
        test_content = """LightRAG is a powerful knowledge management system that combines:
        - Vector embeddings for semantic search
        - Knowledge graphs for relationship mapping
        - Multiple query modes for different use cases
        - Namespace isolation for multi-tenant applications"""
        
        async with session.post(
            f"{API_BASE}/api/test_docs/documents",
            json={
                "content": test_content,
                "metadata": {"source": "test_doc_1.md", "type": "technical"}
            }
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                print(f"   ✅ Document added: {result['content_length']} chars")
                assert result['namespace'] == "test_docs"
                assert result['content_length'] == len(test_content)
            else:
                print(f"   ❌ Failed: {await resp.text()}")
                return
        print()
        
        # Test 2: Add multiple documents
        print("Test 2: Add multiple documents")
        documents = [
            {
                "content": "The quick brown fox jumps over the lazy dog. This is a test sentence for semantic search.",
                "metadata": {"source": "test_doc_2.txt", "type": "sample"}
            },
            {
                "content": "Python is a versatile programming language used for web development, data science, and automation.",
                "metadata": {"source": "test_doc_3.md", "type": "technical"}
            },
            {
                "content": "Machine learning models can learn patterns from data without explicit programming.",
                "metadata": {"source": "test_doc_4.md", "type": "ai"}
            }
        ]
        
        for i, doc in enumerate(documents):
            async with session.post(
                f"{API_BASE}/api/test_docs/documents",
                json=doc
            ) as resp:
                if resp.status == 200:
                    print(f"   ✅ Document {i+2} added")
                else:
                    print(f"   ❌ Failed to add document {i+2}: {await resp.text()}")
        print()
        
        # Wait a moment for indexing
        print("Waiting for indexing...")
        await asyncio.sleep(2)
        print()
        
        # Test 3: Query with different modes
        print("Test 3: Query with different modes")
        test_queries = [
            ("What is LightRAG?", "naive"),
            ("Tell me about vector embeddings", "local"),
            ("How does knowledge management work?", "global"),
            ("What programming languages were mentioned?", "hybrid")
        ]
        
        for query, mode in test_queries:
            print(f"\n   Query: '{query}' (mode: {mode})")
            async with session.post(
                f"{API_BASE}/api/test_docs/query",
                json={"query": query, "mode": mode}
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    assert result['namespace'] == "test_docs"
                    assert result['query'] == query
                    assert result['mode'] == mode
                    print(f"   ✅ Got response: {len(result['result'])} chars")
                    if result['result']:
                        preview = result['result'][:100] + "..." if len(result['result']) > 100 else result['result']
                        print(f"   Preview: {preview}")
                else:
                    print(f"   ❌ Query failed: {await resp.text()}")
        print()
        
        # Test 4: Query non-existent namespace
        print("\nTest 4: Query non-existent namespace")
        async with session.post(
            f"{API_BASE}/api/nonexistent/query",
            json={"query": "test", "mode": "hybrid"}
        ) as resp:
            if resp.status == 404:
                error = await resp.json()
                print(f"   ✅ Expected error: {error['detail']}")
            else:
                print(f"   ❌ Unexpected status: {resp.status}")
        print()
        
        # Test 5: Invalid query mode
        print("Test 5: Invalid query mode")
        async with session.post(
            f"{API_BASE}/api/test_docs/query",
            json={"query": "test", "mode": "invalid_mode"}
        ) as resp:
            if resp.status in [400, 422, 500]:  # Could be validation or runtime error
                print(f"   ✅ Expected error for invalid mode")
            else:
                print(f"   ❌ Unexpected status: {resp.status}")
        print()
        
        # Test 6: Add document to non-existent namespace
        print("Test 6: Add document to non-existent namespace")
        async with session.post(
            f"{API_BASE}/api/nonexistent/documents",
            json={"content": "test", "metadata": {}}
        ) as resp:
            if resp.status == 404:
                error = await resp.json()
                print(f"   ✅ Expected error: {error['detail']}")
            else:
                print(f"   ❌ Unexpected status: {resp.status}")
        print()
        
        # Test 7: Empty document content
        print("Test 7: Empty document content")
        async with session.post(
            f"{API_BASE}/api/test_docs/documents",
            json={"content": "", "metadata": {"note": "empty"}}
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                print(f"   ✅ Empty document accepted: {result['content_length']} chars")
            else:
                print(f"   ℹ️  Empty document rejected: {resp.status}")
        print()
        
        # Cleanup: List final state
        print("Cleanup: Final namespace state")
        async with session.get(f"{API_BASE}/api/namespaces") as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"   Total namespaces: {data['count']}")
                test_ns = next((ns for ns in data['namespaces'] if ns['id'] == 'test_docs'), None)
                if test_ns:
                    print(f"   Test namespace exists: {test_ns['name']}")
        
        print("\n✅ Basic operations tests completed!")
        return True

if __name__ == "__main__":
    try:
        success = asyncio.run(test_basic_operations())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)