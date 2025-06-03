#!/usr/bin/env python3
"""
Simple LightRAG demo for video transcripts
"""
import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import gpt_4o_mini_complete, openai_embed
from lightrag.kg.shared_storage import initialize_pipeline_status

# Load environment variables
load_dotenv()

# Configuration
WORKING_DIR = project_root / "lightrag_transcripts_db"
TRANSCRIPTS_DIR = project_root / "transcripts"

async def main():
    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: Please set OPENAI_API_KEY in your .env file")
        return
    
    # Initialize LightRAG
    print("Initializing LightRAG...")
    if not WORKING_DIR.exists():
        WORKING_DIR.mkdir(parents=True)
    
    rag = LightRAG(
        working_dir=str(WORKING_DIR),
        embedding_func=openai_embed,
        llm_model_func=gpt_4o_mini_complete,
    )
    
    await rag.initialize_storages()
    await initialize_pipeline_status()
    
    # Check if we need to load data
    db_file = WORKING_DIR / "vdb_entities.json"
    if not db_file.exists() or db_file.stat().st_size < 100:
        print("\nFirst time setup - loading transcripts...")
        print("This may take a few minutes as LightRAG builds the knowledge graph...")
        
        # Load only actual transcript files
        transcript_files = [
            "5 Copywriting Exercises_ How To Write Better Sales Copy.txt",
            "Email Copywriting For Ecommerce In 2022 _As A Copywriter OR Online Store Owner_.txt",
            "How to build a brand in 7mins _ Gary Vaynerchuk.txt",
            "Marketing on Zero Budget.txt",
            "The Anatomy Of A High Converting Landing Page _ Conversion Rate Optimization Tips.txt",
        ]
        
        for i, filename in enumerate(transcript_files[:5], 1):  # Just load 5 for demo
            filepath = TRANSCRIPTS_DIR / filename
            if filepath.exists():
                print(f"\n[{i}/5] Loading: {filename}")
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    await rag.ainsert(content)
        
        print("\nWaiting for knowledge graph to build...")
        await asyncio.sleep(10)
    
    # Run some queries
    print("\n" + "="*60)
    print("LIGHTRAG DEMO - Video Transcript Analysis")
    print("="*60)
    
    queries = [
        "What copywriting techniques are mentioned for writing better sales copy?",
        "How should someone build a brand according to these videos?",
        "What marketing strategies work with zero budget?",
    ]
    
    for query in queries:
        print(f"\n📝 Query: {query}")
        print("-" * 60)
        
        try:
            # Try hybrid mode for best results
            result = await rag.aquery(query, param=QueryParam(mode="hybrid"))
            
            if "no-context" in str(result):
                # If no results, try naive mode
                result = await rag.aquery(query, param=QueryParam(mode="naive"))
            
            print(f"💡 Answer:\n{result}\n")
            
        except Exception as e:
            print(f"Error: {e}")
    
    # Cleanup
    await rag.finalize_storages()
    print("\nDemo complete! You can run the full interactive demo with:")
    print("python src/scripts/lightrag_transcripts_demo.py")

if __name__ == "__main__":
    asyncio.run(main())