#!/usr/bin/env python3
"""Test how httpx handles redirects with POST requests."""

import asyncio
import httpx

async def test_redirect():
    # Test URL that will show us exactly what's happening
    url = "https://f58bd4552333.ngrok.app/api/v1/internal/oauth/completed"
    
    print(f"Testing POST to: {url}")
    print("-" * 60)
    
    # Test 1: Default behavior
    print("\n1. Default httpx behavior:")
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(url, json={"test": "default"})
            print(f"   Status: {response.status_code}")
            print(f"   URL: {response.url}")
            print(f"   History: {response.history}")
        except Exception as e:
            print(f"   Error: {type(e).__name__}: {e}")
    
    # Test 2: Disable redirect following
    print("\n2. With follow_redirects=False:")
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
        try:
            response = await client.post(url, json={"test": "no-redirect"})
            print(f"   Status: {response.status_code}")
            print(f"   URL: {response.url}")
            if response.status_code in [301, 302, 303, 307, 308]:
                print(f"   Redirect to: {response.headers.get('location')}")
        except Exception as e:
            print(f"   Error: {type(e).__name__}: {e}")
    
    # Test 3: Check headers
    print("\n3. Checking request headers:")
    async with httpx.AsyncClient(timeout=15.0) as client:
        # Build request to inspect it
        request = client.build_request("POST", url, json={"test": "headers"})
        print(f"   Method: {request.method}")
        print(f"   URL: {request.url}")
        print(f"   Headers: {dict(request.headers)}")

if __name__ == "__main__":
    asyncio.run(test_redirect())