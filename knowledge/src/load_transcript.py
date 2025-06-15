#!/usr/bin/env python
"""
Standalone script to load transcript into LightRAG
"""
import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lightrag import LightRAG
from lightrag.llm.openai import gpt_4o_mini_complete, openai_embed


async def load_transcript(transcript_path: str):
    """Load a transcript file into LightRAG"""
    # Read transcript
    with open(transcript_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Initialize LightRAG
    working_dir = project_root / "lightrag_transcripts_db"
    
    rag = LightRAG(
        working_dir=str(working_dir),
        embedding_func=openai_embed,
        llm_model_func=gpt_4o_mini_complete,
    )
    
    # Insert content
    print(f"Inserting {len(content)} characters...")
    await rag.ainsert(content)
    print("✅ Successfully loaded into LightRAG!")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: load_transcript.py <transcript_file>")
        sys.exit(1)
    
    transcript_file = sys.argv[1]
    asyncio.run(load_transcript(transcript_file))