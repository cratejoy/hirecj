#!/usr/bin/env python3
"""Debug network connectivity from auth service to agents service."""

import asyncio
import httpx
import socket
import ssl
import sys
import os

# Test URL
AGENTS_URL = "https://f58bd4552333.ngrok.app"
TEST_ENDPOINT = f"{AGENTS_URL}/api/v1/test-cors"

async def test_dns():
    """Test DNS resolution."""
    print("\n1. Testing DNS Resolution:")
    try:
        hostname = AGENTS_URL.replace("https://", "").replace("http://", "")
        ip = socket.gethostbyname(hostname)
        print(f"   ✓ DNS resolves {hostname} to {ip}")
        return True
    except Exception as e:
        print(f"   ✗ DNS resolution failed: {e}")
        return False

async def test_socket_connection():
    """Test raw socket connection."""
    print("\n2. Testing Socket Connection:")
    try:
        hostname = AGENTS_URL.replace("https://", "").replace("http://", "")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((hostname, 443))
        sock.close()
        
        if result == 0:
            print(f"   ✓ Socket connection successful to {hostname}:443")
            return True
        else:
            print(f"   ✗ Socket connection failed with error code: {result}")
            return False
    except Exception as e:
        print(f"   ✗ Socket test failed: {e}")
        return False

async def test_ssl_handshake():
    """Test SSL/TLS handshake."""
    print("\n3. Testing SSL/TLS:")
    try:
        hostname = AGENTS_URL.replace("https://", "").replace("http://", "")
        context = ssl.create_default_context()
        
        with socket.create_connection((hostname, 443), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                print(f"   ✓ SSL handshake successful")
                print(f"   - Protocol: {ssock.version()}")
                print(f"   - Cipher: {ssock.cipher()}")
                return True
    except Exception as e:
        print(f"   ✗ SSL handshake failed: {e}")
        return False

async def test_httpx_get():
    """Test HTTPX GET request."""
    print("\n4. Testing HTTPX GET Request:")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            print(f"   - Attempting GET {TEST_ENDPOINT}")
            response = await client.get(TEST_ENDPOINT)
            print(f"   ✓ Request successful: Status {response.status_code}")
            return True
    except httpx.TimeoutException as e:
        print(f"   ✗ Request timed out: {e}")
        return False
    except Exception as e:
        print(f"   ✗ Request failed: {type(e).__name__}: {e}")
        return False

async def test_httpx_post():
    """Test HTTPX POST request (like OAuth completion)."""
    print("\n5. Testing HTTPX POST Request:")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            endpoint = f"{AGENTS_URL}/api/v1/internal/oauth/completed"
            print(f"   - Attempting POST {endpoint}")
            
            # Test data similar to OAuth completion
            test_data = {
                "shop_domain": "test-shop.myshopify.com",
                "is_new": False,
                "conversation_id": "test-123",
                "user_id": "usr_test",
                "email": None
            }
            
            response = await client.post(endpoint, json=test_data)
            print(f"   ✓ Request completed: Status {response.status_code}")
            if response.status_code != 200:
                print(f"   - Response: {response.text[:200]}...")
            return True
    except httpx.TimeoutException as e:
        print(f"   ✗ Request timed out: {e}")
        return False
    except Exception as e:
        print(f"   ✗ Request failed: {type(e).__name__}: {e}")
        return False

async def test_with_different_timeouts():
    """Test with various timeout values."""
    print("\n6. Testing Different Timeout Values:")
    
    for timeout in [1, 5, 15, 30]:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                print(f"   - Testing with {timeout}s timeout...", end="", flush=True)
                start = asyncio.get_event_loop().time()
                response = await client.get(TEST_ENDPOINT)
                elapsed = asyncio.get_event_loop().time() - start
                print(f" ✓ Success in {elapsed:.2f}s")
        except httpx.TimeoutException:
            elapsed = asyncio.get_event_loop().time() - start
            print(f" ✗ Timeout after {elapsed:.2f}s")
        except Exception as e:
            print(f" ✗ Error: {type(e).__name__}")

async def main():
    """Run all tests."""
    print(f"=== Network Connectivity Debug ===")
    print(f"Testing from: {os.getcwd()}")
    print(f"Python: {sys.version}")
    print(f"Target: {AGENTS_URL}")
    
    # Run tests
    await test_dns()
    await test_socket_connection()
    await test_ssl_handshake()
    await test_httpx_get()
    await test_httpx_post()
    await test_with_different_timeouts()
    
    print("\n=== Summary ===")
    print("Run this script from both the auth service directory and the root directory")
    print("to compare results and identify environment-specific issues.")

if __name__ == "__main__":
    asyncio.run(main())