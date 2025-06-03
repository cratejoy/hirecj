import os
import sys
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import gpt_4o_mini_complete, openai_embed
from lightrag.utils import logger, set_verbose_debug
from lightrag.kg.shared_storage import initialize_pipeline_status

# Load environment variables
load_dotenv()

# Configuration
WORKING_DIR = project_root / "lightrag_transcripts_db"
TRANSCRIPTS_DIR = project_root / "transcripts"

def configure_logging():
    """Configure logging for the application"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger.setLevel(logging.INFO)

async def initialize_rag():
    """Initialize LightRAG with OpenAI models"""
    if not WORKING_DIR.exists():
        WORKING_DIR.mkdir(parents=True)
    
    rag = LightRAG(
        working_dir=str(WORKING_DIR),
        embedding_func=openai_embed,
        llm_model_func=gpt_4o_mini_complete,
    )
    
    await rag.initialize_storages()
    await initialize_pipeline_status()
    return rag

async def load_transcripts(rag, transcripts_dir):
    """Load all transcript files into LightRAG"""
    transcript_path = Path(transcripts_dir)
    
    if not transcript_path.exists():
        print(f"Error: Transcripts directory not found at {transcripts_dir}")
        return False
    
    txt_files = list(transcript_path.glob("*.txt"))
    
    # Filter out non-transcript files
    txt_files = [f for f in txt_files if f.name not in ['requirements.txt', 'runtime.txt', 'aider.txt', 'scripts.txt', 'analysis_iteration_0.txt', 'overall_summary.txt']]
    
    if not txt_files:
        print(f"No transcript files found in {transcripts_dir}")
        return False
    
    print(f"\nFound {len(txt_files)} transcript files")
    print("Loading transcripts into LightRAG...\n")
    
    for i, file_path in enumerate(txt_files, 1):
        try:
            print(f"[{i}/{len(txt_files)}] Processing: {file_path.name}")
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                await rag.ainsert(content)
        except Exception as e:
            print(f"Error processing {file_path.name}: {e}")
    
    print("\nAll transcripts loaded!")
    print("Note: LightRAG processes documents asynchronously. The knowledge graph may take a few minutes to build.")
    print("For best results, wait a moment before querying.")
    
    # Give some time for initial processing
    await asyncio.sleep(5)
    
    return True

async def interactive_query(rag):
    """Interactive query session"""
    print("\n" + "="*50)
    print("Interactive Query Mode")
    print("="*50)
    print("Enter your questions about the video transcripts.")
    print("Type 'quit' to exit.")
    print("Available query modes: naive, local, global, hybrid")
    print("="*50 + "\n")
    
    while True:
        query = input("\nYour question: ").strip()
        
        if query.lower() in ['quit', 'exit', 'q']:
            print("Exiting query mode...")
            break
        
        if not query:
            continue
        
        mode = input("Query mode (default: hybrid): ").strip().lower()
        if mode not in ['naive', 'local', 'global', 'hybrid']:
            mode = 'hybrid'
        
        print(f"\nSearching in '{mode}' mode...")
        try:
            result = await rag.aquery(query, param=QueryParam(mode=mode))
            print(f"\nResult:\n{result}")
        except Exception as e:
            print(f"Error during query: {e}")

async def run_sample_queries(rag):
    """Run some sample queries to demonstrate functionality"""
    sample_queries = [
        ("What are the main topics covered in these marketing/copywriting videos?", "global"),
        ("What specific email copywriting techniques are mentioned?", "local"),
        ("How do these videos suggest building a brand or community?", "hybrid"),
        ("What tools or platforms are recommended for marketing?", "local"),
    ]
    
    print("\n" + "="*50)
    print("Running Sample Queries")
    print("="*50)
    
    for query, mode in sample_queries:
        print(f"\nQuery: {query}")
        print(f"Mode: {mode}")
        print("-" * 30)
        
        try:
            result = await rag.aquery(query, param=QueryParam(mode=mode))
            print(f"Result:\n{result}\n")
        except Exception as e:
            print(f"Error: {e}\n")

async def main():
    """Main function"""
    # Check if OPENAI_API_KEY is set
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable is not set.")
        print("Please set it by running:")
        print("  export OPENAI_API_KEY='your-openai-api-key'")
        return
    
    configure_logging()
    
    try:
        # Initialize LightRAG
        print("Initializing LightRAG...")
        rag = await initialize_rag()
        
        # Check if we need to load transcripts
        need_to_load = True
        db_file = WORKING_DIR / "vdb_entities.json"
        if db_file.exists():
            response = input("\nExisting database found. Reload transcripts? (y/n): ").strip().lower()
            need_to_load = response == 'y'
        
        if need_to_load:
            # Load transcripts
            success = await load_transcripts(rag, str(TRANSCRIPTS_DIR))
            if not success:
                return
        
        # Menu
        while True:
            print("\n" + "="*50)
            print("LightRAG Video Transcripts Demo")
            print("="*50)
            print("1. Run sample queries")
            print("2. Interactive query mode")
            print("3. Reload transcripts")
            print("4. Exit")
            print("="*50)
            
            choice = input("\nSelect option (1-4): ").strip()
            
            if choice == '1':
                await run_sample_queries(rag)
            elif choice == '2':
                await interactive_query(rag)
            elif choice == '3':
                await load_transcripts(rag, str(TRANSCRIPTS_DIR))
            elif choice == '4':
                print("Exiting...")
                break
            else:
                print("Invalid option. Please try again.")
        
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if 'rag' in locals():
            await rag.finalize_storages()

if __name__ == "__main__":
    import sys
    
    # Check if running in non-interactive mode
    if len(sys.argv) > 1 and sys.argv[1] == "--sample":
        async def run_sample_only():
            configure_logging()
            try:
                print("Initializing LightRAG...")
                rag = await initialize_rag()
                
                # Check if data exists
                db_file = WORKING_DIR / "vdb_entities.json"
                if not db_file.exists():
                    print("\nLoading transcripts for the first time...")
                    success = await load_transcripts(rag, str(TRANSCRIPTS_DIR))
                    if not success:
                        return
                
                # Run sample queries
                await run_sample_queries(rag)
                
            except Exception as e:
                print(f"An error occurred: {e}")
            finally:
                if 'rag' in locals():
                    await rag.finalize_storages()
        
        asyncio.run(run_sample_only())
    else:
        asyncio.run(main())
    
    print("\nDemo completed!")