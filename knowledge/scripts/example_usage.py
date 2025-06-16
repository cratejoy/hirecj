#!/usr/bin/env python3
"""
Example usage of the Knowledge API with dynamic namespaces
Phase 0.3: Basic Operations demonstration
"""
import asyncio
import aiohttp
import json

API_BASE = "http://localhost:8004"

async def example_usage():
    """Example of creating namespaces and using them"""
    async with aiohttp.ClientSession() as session:
        print("🚀 Knowledge API Example Usage - Phase 0.3\n")
        
        # 1. Create an e-commerce namespace
        print("1. Creating 'products' namespace...")
        async with session.post(
            f"{API_BASE}/api/namespaces?namespace_id=products",
            json={
                "name": "Product Catalog",
                "description": "Product information and specifications"
            }
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                print(f"   ✅ Created: {result['message']}")
            else:
                print(f"   ❌ Error: {await resp.text()}")
        print()
        
        # 2. Create a personality namespace
        print("2. Creating 'assistant_friendly' namespace...")
        async with session.post(
            f"{API_BASE}/api/namespaces?namespace_id=assistant_friendly",
            json={
                "name": "Friendly Assistant",
                "description": "Warm and helpful personality traits"
            }
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                print(f"   ✅ Created: {result['message']}")
            else:
                print(f"   ❌ Error: {await resp.text()}")
        print()
        
        # 3. Add content to products namespace
        print("3. Adding product documentation...")
        async with session.post(
            f"{API_BASE}/api/products/documents",
            json={
                "content": """The XYZ Pro laptop is our flagship model designed for professionals.
                
Key Specifications:
- Processor: Intel Core i7-12700H (14 cores, up to 4.7GHz)
- Memory: 16GB DDR5 RAM (expandable to 64GB)
- Storage: 512GB NVMe SSD (2 slots available)
- Display: 14-inch 2.8K (2880x1800) IPS, 120Hz refresh rate
- Graphics: NVIDIA RTX 3050 Ti (4GB GDDR6)
- Battery: 70Wh with fast charging (80% in 30 minutes)
- Connectivity: WiFi 6E, Bluetooth 5.2, Thunderbolt 4
- Weight: 1.4kg (3.1 lbs)

The XYZ Pro combines portability with performance, making it ideal for 
developers, designers, and content creators who need power on the go.""",
                "metadata": {"source": "product_spec.md", "sku": "XYZ-PRO-001"}
            }
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                print(f"   ✅ Added document: {result['content_length']} chars")
            else:
                print(f"   ❌ Error: {await resp.text()}")
        print()
        
        # 4. Add personality traits
        print("4. Adding personality traits...")
        async with session.post(
            f"{API_BASE}/api/assistant_friendly/documents",
            json={
                "content": """I am a friendly and approachable AI assistant who values:
- Using warm, conversational language
- Offering encouragement and positive reinforcement
- Being patient and understanding with users
- Celebrating small wins and progress
- Using appropriate emojis to convey friendliness 😊
- Asking clarifying questions in a gentle way
- Showing enthusiasm for helping users succeed""",
                "metadata": {"type": "personality_trait", "tone": "friendly"}
            }
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                print(f"   ✅ Added personality: {result['content_length']} chars")
            else:
                print(f"   ❌ Error: {await resp.text()}")
        print()
        
        # 5. Query the product namespace
        print("5. Querying product information...")
        queries = [
            ("What are the specs of XYZ Pro?", "hybrid"),
            ("How much RAM does the laptop have?", "local"),
            ("What makes this laptop good for developers?", "global")
        ]
        
        for query, mode in queries:
            print(f"\n   Query: '{query}' (mode: {mode})")
            async with session.post(
                f"{API_BASE}/api/products/query",
                json={"query": query, "mode": mode}
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"   Result: {result['result'][:200]}..." if len(result['result']) > 200 else f"   Result: {result['result']}")
                else:
                    print(f"   ❌ Error: {await resp.text()}")
        print()
        
        # 6. Query the personality namespace
        print("\n6. Querying personality traits...")
        async with session.post(
            f"{API_BASE}/api/assistant_friendly/query",
            json={"query": "How should I interact with users?", "mode": "hybrid"}
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                print(f"   Result: {result['result'][:200]}..." if len(result['result']) > 200 else f"   Result: {result['result']}")
            else:
                print(f"   ❌ Error: {await resp.text()}")
        print()
        
        # 7. List all namespaces
        print("7. Listing all namespaces...")
        async with session.get(f"{API_BASE}/api/namespaces") as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"   Total namespaces: {data['count']}")
                for ns in data['namespaces']:
                    print(f"   - {ns['id']}: {ns['name']} ({ns['description']})")
            else:
                print(f"   ❌ Error: {await resp.text()}")
        
        print("\n✅ Example usage completed!")

if __name__ == "__main__":
    asyncio.run(example_usage())