#!/usr/bin/env python3
"""
Test LightRAG with a single transcript
"""
import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add LightRAG to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "third-party" / "LightRAG"))

from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import gpt_4o_mini_complete, openai_embed
from lightrag.kg.shared_storage import initialize_pipeline_status

async def main():
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: Please set OPENAI_API_KEY")
        return
    
    # Use a fresh directory
    working_dir = "./test_lightrag_db"
    
    print("Initializing LightRAG...")
    rag = LightRAG(
        working_dir=working_dir,
        llm_model_func=gpt_4o_mini_complete,
        embedding_func=openai_embed,
    )
    
    # Initialize storages
    await rag.initialize_storages()
    await initialize_pipeline_status()
    
    # Simple test content
    test_content = """
    This is a guide about copywriting and email marketing.
    
    Key copywriting tips:
    1. Write compelling headlines that grab attention
    2. Focus on benefits, not features
    3. Use emotional triggers
    4. Keep it simple and clear
    5. Test different variations
    
    Email marketing best practices:
    - Build a quality email list
    - Segment your audience
    - Write engaging subject lines
    - Provide value in every email
    - Include clear calls to action
    
    Remember: Good copywriting is about understanding your audience and speaking their language.
    """
    
    print("\nInserting test content...")
    await rag.ainsert(test_content)
    
    print("\nWaiting for processing...")
    await asyncio.sleep(5)
    
    print("\nTesting queries...")
    
    # Test query
    query = "What are the copywriting tips mentioned?"
    print(f"\nQuery: {query}")
    
    try:
        # Try different modes
        for mode in ["naive", "local", "global", "hybrid"]:
            print(f"\nMode: {mode}")
            result = await rag.aquery(query, param=QueryParam(mode=mode))
            print(f"Result: {result[:200]}..." if len(str(result)) > 200 else f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())