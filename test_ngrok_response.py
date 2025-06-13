#!/usr/bin/env python3
"""Test ngrok response path to identify where responses get stuck."""

import asyncio
import httpx
import json
import time

async def test_response_path():
    base_url = "https://f58bd4552333.ngrok.app"
    
    print("=== Testing Ngrok Response Path ===\n")
    
    # Test 1: Simple GET (we know this works from ngrok logs)
    print("1. Testing simple GET request:")
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            start = time.time()
            response = await client.get(f"{base_url}/api/v1/test-cors")
            elapsed = time.time() - start
            print(f"   ✓ Success in {elapsed:.2f}s - Status: {response.status_code}")
        except Exception as e:
            elapsed = time.time() - start
            print(f"   ✗ Failed after {elapsed:.2f}s - {type(e).__name__}: {e}")
    
    # Test 2: POST with invalid data (to trigger 422)
    print("\n2. Testing POST with invalid data (expect 422):")
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            start = time.time()
            response = await client.post(
                f"{base_url}/api/v1/internal/oauth/completed",
                json={"invalid": "data"}
            )
            elapsed = time.time() - start
            print(f"   ✓ Got response in {elapsed:.2f}s - Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
        except Exception as e:
            elapsed = time.time() - start
            print(f"   ✗ Failed after {elapsed:.2f}s - {type(e).__name__}: {e}")
    
    # Test 3: POST with extra field (like auth service)
    print("\n3. Testing POST with extra field (like auth service):")
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            start = time.time()
            data = {
                "shop_domain": "test.myshopify.com",
                "is_new": False,
                "conversation_id": "test-123",
                "user_id": "usr_test",  # Extra field!
                "email": None
            }
            response = await client.post(
                f"{base_url}/api/v1/internal/oauth/completed",
                json=data
            )
            elapsed = time.time() - start
            print(f"   ✓ Got response in {elapsed:.2f}s - Status: {response.status_code}")
            if response.status_code == 422:
                print(f"   Validation error: {response.text[:300]}")
        except Exception as e:
            elapsed = time.time() - start
            print(f"   ✗ Failed after {elapsed:.2f}s - {type(e).__name__}: {e}")
    
    # Test 4: Same request with different timeout values
    print("\n4. Testing different timeout values:")
    data = {
        "shop_domain": "test.myshopify.com",
        "is_new": False,
        "conversation_id": "test-123",
        "user_id": "usr_test",
        "email": None
    }
    
    for timeout in [1, 3, 5, 10, 20]:
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                start = time.time()
                print(f"   - Timeout {timeout}s: ", end="", flush=True)
                response = await client.post(
                    f"{base_url}/api/v1/internal/oauth/completed",
                    json=data
                )
                elapsed = time.time() - start
                print(f"✓ Status {response.status_code} in {elapsed:.2f}s")
            except httpx.TimeoutException:
                elapsed = time.time() - start
                print(f"✗ Timeout after {elapsed:.2f}s")
            except Exception as e:
                print(f"✗ Error: {type(e).__name__}")

if __name__ == "__main__":
    asyncio.run(test_response_path())