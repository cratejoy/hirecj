# LightRAG Implementation Plan & Roadmap for HireCJ Knowledge Graphs

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                     HIRECJ EDITOR UI                                      │
│  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ Knowledge Graphs│  │ Graph Detail View│  │ Processing View │  │  Query Interface│  │
│  │   List View     │  │  (Sources/Upload)│  │  (Live Updates) │  │  (RAG Search)   │  │
│  └────────┬────────┘  └─────────┬────────┘  └────────┬────────┘  └────────┬────────┘  │
└───────────┼──────────────────────┼───────────────────┼───────────────────┼─────────────┘
            │                      │                    │                    │
            ▼                      ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    API GATEWAY LAYER                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │ Graph CRUD   │  │ Source Mgmt  │  │  Processing  │  │ Query/Search │   WebSocket    │
│  │  Endpoints   │  │  Endpoints   │  │   Control    │  │  Endpoints   │   ┌─────────┐  │
│  │ /api/graphs  │  │ /api/sources │  │ /api/process │  │  /api/query  │───│ WS:/ws  │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   └────┬────┘  │
└─────────┼──────────────────┼─────────────────┼─────────────────┼──────────────┼────────┘
          │                  │                 │                 │              │
          ▼                  ▼                 ▼                 ▼              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                 CORE SERVICES LAYER                                       │
│                                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                              CORPUS MANAGER                                        │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  ┌────────────┐             │   │
│  │  │   Product   │  │  Customer   │  │   Technical  │  │  Industry  │  │ More...  │   │
│  │  │  Knowledge  │  │   Support   │  │Documentation│  │  Research  │  │ Corpora  │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬───────┘  └─────┬──────┘             │   │
│  └─────────┼─────────────────┼─────────────────┼────────────────┼───────────────────┘   │
│            │                 │                 │                │                        │
│  ┌─────────▼─────────────────▼─────────────────▼────────────────▼───────────────────┐   │
│  │                           INGEST MANAGER                                           │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐ │   │
│  │  │File Upload │  │Web Crawler │  │RSS Monitor │  │  YouTube   │  │ URL List   │ │   │
│  │  │ Processor  │  │            │  │            │  │Transcriber │  │ Processor  │ │   │
│  │  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘ │   │
│  └────────┼───────────────┼───────────────┼───────────────┼───────────────┼────────┘   │
│           │               │               │               │               │             │
│  ┌────────▼───────────────▼───────────────▼───────────────▼───────────────▼────────┐   │
│  │                    LIGHTRAG PROCESSING PIPELINE                                  │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │   │
│  │  │   Chunking  │→ │  Embedding  │→ │Graph Build  │→ │   Status    │           │   │
│  │  │             │  │ Generation  │  │             │  │   Update    │           │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘           │   │
│  └──────────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                               STORAGE LAYER (PostgreSQL)                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐   │
│  │ PGVectorStorage │  │ PGGraphStorage  │  │  PGKVStorage    │  │PGDocStatusStore │   │
│  │   (pgvector)    │  │ (Relationships) │  │  (Documents)    │  │  (Processing)   │   │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘   │
│                                                                                           │
│  Namespace Isolation: product_* | support_* | tech_* | research_* | competitor_*         │
└─────────────────────────────────────────────────────────────────────────────────────────┘

DATA FLOW:
═══════════
1. Content Input:    Editor UI → API → Ingest Manager → Processors → LightRAG Pipeline
2. Query Flow:       Editor UI → API → Corpus Manager → LightRAG → PostgreSQL → Results
3. Status Updates:   Processing Pipeline → WebSocket → Editor UI (Real-time)
```

## Overview

This document outlines the implementation plan for integrating LightRAG as the knowledge backend for HireCJ's AI agent system. Using LightRAG's native namespace feature, we create a flexible system supporting both e-commerce knowledge and personality-based responses without infrastructure complexity.

## Architecture

### 1. Namespace-Based Knowledge System

The system uses LightRAG's built-in `namespace_prefix` feature to create logically isolated knowledge domains within a single instance:

**Dynamic Namespace System:**
- **No Predefined Namespaces** - System starts empty
- **Create on Demand** - Namespaces created via API as needed
- **Flexible Categories** - Support any type of knowledge domain:
  - Product knowledge (e.g., `products`, `catalog`, `inventory`)
  - Support documentation (e.g., `support`, `faqs`, `troubleshooting`)
  - Personality traits (e.g., `assistant_friendly`, `assistant_technical`)
  - Custom domains (e.g., `policies`, `training`, `releases`)

**Key Benefits:**
- Single LightRAG instance with dynamic namespace switching
- Shared resources (connection pools, caches) for efficiency
- Natural data isolation without complex infrastructure
- Create/delete namespaces without code changes
- Namespace configurations persisted to disk

### 2. Storage Architecture

```
PostgreSQL Backend (Recommended for Production)
├── PGVectorStorage       # Embeddings with pgvector extension
├── PGGraphStorage        # Knowledge graph relationships
├── PGKVStorage          # Key-value document storage
└── PGDocStatusStorage   # Processing status tracking

Benefits:
- ACID compliance for data integrity
- Built-in backup and replication
- Multi-tenant isolation via schemas
- Scalable for production workloads
```

### 3. Directory Structure

```
knowledge/
├── corpora/                    # Corpus-specific data
│   ├── product/
│   │   ├── config.yaml        # Corpus configuration
│   │   ├── sources.yaml       # Data source definitions
│   │   └── processing/        # Temporary processing files
│   ├── support/
│   ├── tech_docs/
│   ├── research/
│   └── competitors/
├── src/
│   ├── corpus_manager.py      # Multi-corpus orchestration
│   ├── ingest_manager.py      # Enhanced ingestion pipeline
│   ├── api/
│   │   ├── __init__.py
│   │   ├── graphs.py          # Knowledge graph CRUD
│   │   ├── sources.py         # Data source management
│   │   ├── processing.py      # Queue and status endpoints
│   │   └── query.py           # Unified query interface
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── base.py            # Base processor class
│   │   ├── file_processor.py  # PDF, TXT, MD, JSON, CSV
│   │   ├── web_crawler.py     # Website crawling
│   │   ├── rss_monitor.py     # RSS feed monitoring
│   │   ├── youtube_processor.py # YouTube transcription
│   │   └── url_list_processor.py # Bulk URL processing
│   └── models/
│       ├── corpus.py          # Corpus data models
│       ├── source.py          # Source configuration models
│       └── processing.py      # Processing status models
├── config/
│   ├── default_config.yaml    # Default settings
│   └── corpus_templates/      # Pre-configured corpus types
│       ├── product.yaml
│       ├── support.yaml
│       └── documentation.yaml
└── tests/
    ├── test_corpus_manager.py
    ├── test_processors.py
    └── test_api.py
```

## Implementation Components

### 1. Corpus Manager (`corpus_manager.py`)

```python
class CorpusManager:
    """Manages multiple LightRAG instances for different knowledge domains"""
    
    def __init__(self, base_config: dict):
        self.corpora = {}
        self.base_config = base_config
    
    def create_corpus(self, name: str, config: dict) -> Corpus:
        """Create a new knowledge corpus with isolated namespace"""
        
    def get_corpus(self, name: str) -> Corpus:
        """Retrieve a specific corpus for querying/updating"""
        
    def list_corpora(self) -> List[CorpusInfo]:
        """List all available corpora with metadata"""
        
    def query(self, corpus_names: List[str], query: str, mode: str = "hybrid"):
        """Query one or more corpora"""
```

### 2. Enhanced Ingestion Pipeline

The ingestion system will extend the current `ingest.py` with:

```python
class IngestManager:
    """Unified ingestion pipeline for all content types"""
    
    def __init__(self, corpus_manager: CorpusManager):
        self.corpus_manager = corpus_manager
        self.processors = {
            'file': FileProcessor(),
            'web': WebCrawler(),
            'rss': RSSMonitor(),
            'youtube': YouTubeProcessor(),
            'url_list': URLListProcessor()
        }
    
    def add_source(self, corpus: str, source_type: str, config: dict):
        """Add a new data source to a corpus"""
        
    def process_queue(self, corpus: str = None):
        """Process pending items for one or all corpora"""
        
    def get_status(self, corpus: str) -> ProcessingStatus:
        """Get processing status for a corpus"""
```

### 3. Processing Pipeline Features

- **Parallel Processing**: Multiple sources processed concurrently
- **Incremental Updates**: Only process new/changed content
- **Retry Logic**: Automatic retry with exponential backoff
- **Deduplication**: Content fingerprinting to avoid duplicates
- **Status Tracking**: Real-time progress updates via WebSocket

### 4. API Endpoints

```python
# Knowledge Graph Management
POST   /api/graphs                 # Create new corpus
GET    /api/graphs                 # List all corpora
GET    /api/graphs/{corpus_id}     # Get corpus details
PUT    /api/graphs/{corpus_id}     # Update corpus config
DELETE /api/graphs/{corpus_id}     # Delete corpus

# Data Source Management
POST   /api/graphs/{corpus_id}/sources     # Add data source
GET    /api/graphs/{corpus_id}/sources     # List sources
PUT    /api/graphs/{corpus_id}/sources/{source_id}  # Update source
DELETE /api/graphs/{corpus_id}/sources/{source_id}  # Remove source

# Processing Control
POST   /api/graphs/{corpus_id}/process     # Start processing
POST   /api/graphs/{corpus_id}/pause       # Pause processing
GET    /api/graphs/{corpus_id}/status      # Get status
GET    /api/processing/queue               # View global queue

# Querying
POST   /api/query                          # Query across corpora
GET    /api/graphs/{corpus_id}/search      # Search specific corpus

# WebSocket
WS     /ws/processing/{corpus_id}          # Real-time updates
```

## Data Flow

### 1. Content Ingestion Flow

```
User adds source → API validates → Creates source config → 
Adds to processing queue → Processor picks up → 
Downloads/extracts content → Chunks text → 
Creates embeddings → Updates graph → 
Updates status → Notifies via WebSocket
```

### 2. Query Flow

```
User query → API receives → Determines target corpora →
Routes to appropriate LightRAG instances →
Aggregates results → Returns unified response
```

## Configuration Examples

### Dynamic Namespace Creation

```python
# Example: Create a product knowledge namespace
POST /api/namespaces?namespace_id=products
{
  "name": "Product Knowledge Base",
  "description": "Product catalogs, specifications, and documentation"
}

# Example: Create a support namespace  
POST /api/namespaces?namespace_id=support
{
  "name": "Customer Support",
  "description": "FAQs, troubleshooting guides, and support articles"
}

# Example: Create a personality namespace
POST /api/namespaces?namespace_id=assistant_professional
{
  "name": "Professional Assistant",
  "description": "Professional and formal communication style"
}
```

### Namespace Registry Storage (`namespace_registry.json`)

```json
{
  "products": {
    "name": "Product Knowledge Base",
    "description": "Product catalogs, specifications, and documentation",
    "created_at": "2024-01-20T10:30:00"
  },
  "support": {
    "name": "Customer Support",
    "description": "FAQs, troubleshooting guides, and support articles",
    "created_at": "2024-01-20T10:35:00"
  },
  "assistant_professional": {
    "name": "Professional Assistant",
    "description": "Professional and formal communication style",
    "created_at": "2024-01-20T10:40:00"
  }
}
```

### Environment Configuration (`.env`)

```bash
# LightRAG Configuration
KNOWLEDGE_DIR=./knowledge_base
KNOWLEDGE_API_PORT=9620

# Model Configuration  
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small

# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=lightrag_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=yourpassword
```

## Integration with Editor UI

The editor's Grounding views will integrate as follows:

1. **Knowledge Graphs List View**: 
   - Calls `GET /api/graphs` to display corpus cards
   - Shows real-time status via WebSocket connection
   - Corpus metrics pulled from LightRAG statistics

2. **Knowledge Graph Detail View**:
   - Source management via `/api/graphs/{id}/sources` endpoints
   - Drag-and-drop file upload to file processor
   - Processing queue visualization from `/api/graphs/{id}/status`

3. **Processing Status View**:
   - WebSocket connection for live updates
   - Pause/resume controls via API
   - Error handling and retry options

## Security Considerations

1. **Corpus Isolation**: Namespace prefixing prevents cross-corpus data leakage
2. **Access Control**: Integration with HireCJ auth for corpus-level permissions
3. **Rate Limiting**: API endpoints protected against abuse
4. **Content Validation**: Sanitization of ingested content
5. **Storage Encryption**: Sensitive data encrypted at rest

## Performance Optimizations

1. **Caching Layer**: Redis cache for frequent queries
2. **Batch Processing**: Group similar documents for efficient embedding
3. **Incremental Indexing**: Only process changed content
4. **Query Optimization**: Corpus-specific indices in PostgreSQL
5. **Connection Pooling**: Efficient database connection management

## Implementation Roadmap

### Overview

This roadmap defines progressive milestones to prove out the LightRAG knowledge graph system, starting with fundamental concepts and gradually adding complexity. Each milestone delivers working functionality that validates core assumptions before moving forward.

---

### Phase 0: Operational Setup - Dynamic Namespace Management

**Goal: Create an API server with dynamic namespace creation and management**

We'll build a FastAPI server that manages namespaces dynamically. Users start with zero namespaces and create them as needed through the API. Each namespace uses LightRAG's `namespace_prefix` for data isolation.

#### Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Knowledge API Server (Port 9620)                   │
│                         FastAPI Application                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Dynamic Namespace Registry:                                          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  namespace_registry.json                                         │   │
│  │  {}  <- Starts empty, populated via API                         │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  LightRAG Instance (Single):                                          │
│    working_dir="./knowledge_base"                                    │
│    namespace_prefix=<dynamic based on request>                       │
│                                                                       │
│  API Routes:                                                          │
│    POST   /api/namespaces             - Create namespace             │
│    GET    /api/namespaces             - List all namespaces          │
│    DELETE /api/namespaces/{id}        - Delete namespace             │
│    POST   /api/{namespace}/documents  - Add to namespace             │
│    GET    /api/{namespace}/query      - Query namespace              │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

#### Directory Structure

```
knowledge/
├── knowledge_base/              # Single working directory
│   └── (LightRAG manages internal structure with namespaces)
├── gateway/                     # API server
│   ├── __init__.py
│   └── main.py                 # FastAPI app with namespace logic
├── data/                       # Source documents
│   ├── ecommerce/             # E-commerce docs to ingest
│   └── personalities/         # Personality trait definitions
├── scripts/
│   ├── setup.sh               # Initial setup
│   └── ingest_personality.py  # Personality ingestion helper
└── logs/
    └── api.log                # API server logs
```

#### Implementation

**1. API Server (`gateway/main.py`)**
```python
from fastapi import FastAPI, HTTPException, BackgroundTasks
from lightrag import LightRAG, QueryParam
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List
import json
import re
import os
import logging

app = FastAPI(title="Knowledge API")
logger = logging.getLogger(__name__)

# Configuration
PORT = int(os.getenv("KNOWLEDGE_SERVICE_PORT", "8004"))
KNOWLEDGE_DIR = Path(os.getenv("KNOWLEDGE_DIR", "./knowledge_base"))
BASE_CONFIG = {
    "working_dir": str(KNOWLEDGE_DIR),
    "llm_model_name": os.getenv("LLM_MODEL", "gpt-4o-mini"),
    "embedding_model_name": os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
}

# Models
class NamespaceConfig(BaseModel):
    name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="Namespace description")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class Document(BaseModel):
    content: str
    metadata: Dict[str, str] = Field(default_factory=dict)

class QueryRequest(BaseModel):
    query: str
    mode: str = Field(default="hybrid", description="Query mode: naive, local, global, hybrid")

# Dynamic Namespace Registry
class NamespaceRegistry:
    def __init__(self, storage_path: Path = KNOWLEDGE_DIR / "namespace_registry.json"):
        self.storage_path = storage_path
        self.namespaces: Dict[str, NamespaceConfig] = {}
        self._load_from_disk()
    
    def _load_from_disk(self):
        """Load namespace registry from persistent storage"""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if self.storage_path.exists():
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                self.namespaces = {
                    k: NamespaceConfig(**v) for k, v in data.items()
                }
    
    def _save_to_disk(self):
        """Persist namespace registry to disk"""
        with open(self.storage_path, 'w') as f:
            data = {k: v.dict() for k, v in self.namespaces.items()}
            json.dump(data, f, indent=2)
    
    def create_namespace(self, namespace_id: str, config: NamespaceConfig) -> bool:
        """Create a new namespace"""
        # Validate namespace ID format
        if not re.match(r'^[a-z0-9_]+$', namespace_id):
            raise ValueError("Namespace ID must contain only lowercase letters, numbers, and underscores")
        
        if namespace_id in self.namespaces:
            return False
        
        self.namespaces[namespace_id] = config
        self._save_to_disk()
        return True
    
    def delete_namespace(self, namespace_id: str) -> bool:
        """Delete a namespace"""
        if namespace_id not in self.namespaces:
            return False
        
        del self.namespaces[namespace_id]
        self._save_to_disk()
        
        # TODO: Clean up namespace data from LightRAG storage
        return True
    
    def get_namespace(self, namespace_id: str) -> Optional[NamespaceConfig]:
        """Get namespace configuration"""
        return self.namespaces.get(namespace_id)
    
    def list_namespaces(self) -> Dict[str, NamespaceConfig]:
        """List all namespaces"""
        return self.namespaces.copy()

# Initialize registry
namespace_registry = NamespaceRegistry()

# LightRAG instance cache
lightrag_instances: Dict[str, LightRAG] = {}

@asynccontextmanager
async def get_lightrag_instance(namespace_id: str):
    """Get or create a LightRAG instance for the namespace"""
    if namespace_id not in namespace_registry.namespaces:
        raise HTTPException(status_code=404, detail=f"Namespace '{namespace_id}' not found")
    
    # Cache instances to avoid recreation
    if namespace_id not in lightrag_instances:
        lightrag_instances[namespace_id] = LightRAG(
            **BASE_CONFIG,
            namespace_prefix=namespace_id
        )
        await lightrag_instances[namespace_id].initialize_storages()
    
    yield lightrag_instances[namespace_id]

# Namespace CRUD endpoints
@app.post("/api/namespaces")
async def create_namespace(
    namespace_id: str = Field(..., regex="^[a-z0-9_]+$"),
    config: NamespaceConfig = ...
):
    """Create a new namespace"""
    try:
        created = namespace_registry.create_namespace(namespace_id, config)
        if not created:
            raise HTTPException(status_code=409, detail="Namespace already exists")
        
        return {
            "namespace_id": namespace_id,
            "config": config.dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/namespaces")
async def list_namespaces():
    """List all namespaces"""
    return {
        "namespaces": [
            {"id": k, **v.dict()} 
            for k, v in namespace_registry.list_namespaces().items()
        ]
    }

@app.delete("/api/namespaces/{namespace_id}")
async def delete_namespace(namespace_id: str):
    """Delete a namespace"""
    deleted = namespace_registry.delete_namespace(namespace_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Namespace not found")
    
    # Remove cached instance
    if namespace_id in lightrag_instances:
        del lightrag_instances[namespace_id]
    
    return {"message": f"Namespace '{namespace_id}' deleted"}

# Document operations
@app.post("/api/{namespace_id}/documents")
async def add_document(namespace_id: str, doc: Document):
    """Add document to namespace"""
    async with get_lightrag_instance(namespace_id) as rag:
        await rag.ainsert(doc.content)
    return {
        "message": "Document added",
        "namespace": namespace_id,
        "content_length": len(doc.content),
        "metadata": doc.metadata
    }

@app.post("/api/{namespace_id}/query")
async def query_knowledge(namespace_id: str, req: QueryRequest):
    """Query specific namespace"""
    async with get_lightrag_instance(namespace_id) as rag:
        result = await rag.aquery(req.query, param=QueryParam(mode=req.mode))
    return {
        "namespace": namespace_id,
        "query": req.query,
        "result": result,
        "mode": req.mode
    }

@app.get("/health")
async def health():
    """API health check"""
    return {
        "status": "healthy",
        "namespaces_count": len(namespace_registry.namespaces),
        "working_dir": BASE_CONFIG["working_dir"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
```

**2. Example Usage Script (`scripts/example_usage.py`)**
```python
import asyncio
import aiohttp
import json

API_BASE = "http://localhost:8004"

async def example_usage():
    """Example of creating namespaces and using them"""
    async with aiohttp.ClientSession() as session:
        # 1. Create an e-commerce namespace
        async with session.post(
            f"{API_BASE}/api/namespaces?namespace_id=products",
            json={
                "name": "Product Catalog",
                "description": "Product information and specifications"
            }
        ) as resp:
            print(f"Created namespace: {await resp.json()}")
        
        # 2. Create a personality namespace
        async with session.post(
            f"{API_BASE}/api/namespaces?namespace_id=assistant_friendly",
            json={
                "name": "Friendly Assistant",
                "description": "Warm and helpful personality traits"
            }
        ) as resp:
            print(f"Created namespace: {await resp.json()}")
        
        # 3. Add content to products namespace
        async with session.post(
            f"{API_BASE}/api/products/documents",
            json={
                "content": "The XYZ Pro laptop features 16GB RAM, 512GB SSD, and a 14-inch display.",
                "metadata": {"source": "product_spec.md", "sku": "XYZ-PRO-001"}
            }
        ) as resp:
            print(f"Added document: {await resp.json()}")
        
        # 4. Add personality traits
        async with session.post(
            f"{API_BASE}/api/assistant_friendly/documents",
            json={
                "content": "I am a friendly assistant who uses warm language and encouragement.",
                "metadata": {"type": "personality_trait"}
            }
        ) as resp:
            print(f"Added personality: {await resp.json()}")
        
        # 5. Query the product namespace
        async with session.post(
            f"{API_BASE}/api/products/query",
            json={"query": "What are the specs of XYZ Pro?", "mode": "hybrid"}
        ) as resp:
            print(f"Query result: {await resp.json()}")
        
        # 6. List all namespaces
        async with session.get(f"{API_BASE}/api/namespaces") as resp:
            print(f"All namespaces: {await resp.json()}")

if __name__ == "__main__":
    asyncio.run(example_usage())
```

**3. Setup Script (`scripts/setup.sh`)**
```bash
#!/bin/bash
echo "🔧 Setting up Knowledge API with Dynamic Namespaces..."

# Create directory structure
mkdir -p knowledge_base
mkdir -p gateway logs scripts

# Create __init__.py
touch gateway/__init__.py

# Install dependencies
pip install lightrag-hku fastapi uvicorn pydantic aiohttp

echo "✅ Setup complete!"
echo ""
echo "To start the API:"
echo "  python -m uvicorn gateway.main:app --reload --port 8004"
echo ""
echo "The system starts with no namespaces. Create them dynamically via API!"
```

**4. Makefile Updates**
```makefile
# Start the API server
dev:
	venv/bin/python scripts/run_api_server.py

# Setup environment
setup:
	./scripts/setup.sh

# Ingest personalities
ingest-personalities:
	venv/bin/python scripts/ingest_personality.py friendly data/personalities/friendly.txt
	venv/bin/python scripts/ingest_personality.py technical data/personalities/technical.txt
	venv/bin/python scripts/ingest_personality.py supportive data/personalities/supportive.txt

# Test commands
test-create-namespace:
	curl -X POST "http://localhost:8004/api/namespaces?namespace_id=products" \
		-H "Content-Type: application/json" \
		-d '{"name": "Product Knowledge", "description": "Product documentation"}'

test-add-document:
	curl -X POST "http://localhost:8004/api/products/documents" \
		-H "Content-Type: application/json" \
		-d '{"content": "Our product supports user upgrades..."}'

test-query:
	curl -X POST "http://localhost:8004/api/products/query" \
		-H "Content-Type: application/json" \
		-d '{"query": "How do I upgrade?", "mode": "hybrid"}'

test-list:
	curl "http://localhost:8004/api/namespaces"

test-delete:
	curl -X DELETE "http://localhost:8004/api/namespaces/products"

# Run example script
run-example:
	venv/bin/python scripts/example_usage.py
```

**5. Environment Configuration**
```bash
# .env
OPENAI_API_KEY=${OPENAI_API_KEY}
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small

# Start with simple storage, migrate to PostgreSQL later
KV_STORAGE=JsonKVStorage
VECTOR_STORAGE=NanoVectorDBStorage
GRAPH_STORAGE=NetworkXStorage
```

#### PostgreSQL Migration (Future)

When ready for production with PostgreSQL:
```bash
# Update .env
KV_STORAGE=PostgresKVStorage
VECTOR_STORAGE=PostgresVectorStorage
GRAPH_STORAGE=PostgresGraphStorage
DOC_STATUS_STORAGE=PostgresDocStatusStorage
DATABASE_URL=postgresql://user:pass@localhost/lightrag
```

The namespace prefixes ensure data isolation even in shared tables.

#### Full Dev Environment Integration

##### Port Assignment
- **Use Port 8004** - Following HireCJ's port allocation pattern:
  - 8000: Agents service
  - 8001: Editor backend
  - 8002: Database service
  - 8004: Knowledge service (reserved in ngrok.yml)
  - 8103: Auth service
  - 3456: Homepage
  - 3458: Editor frontend (NOTE: running on 3458, not 3457)

##### Environment Variable Management

**1. Update `scripts/distribute_env.py`** to add knowledge service:
```python
"knowledge": {
    "direct": [
        # Core configuration
        "ENVIRONMENT", "DEBUG", "LOG_LEVEL",
        
        # Service identity
        "KNOWLEDGE_SERVICE_PORT",
        
        # LightRAG configuration
        "KNOWLEDGE_DIR",
        "KNOWLEDGE_API_PORT",
        
        # Model configuration (shared with agents)
        "OPENAI_API_KEY",
        "LLM_MODEL",
        "EMBEDDING_MODEL",
        
        # PostgreSQL for LightRAG storage
        "POSTGRES_HOST",
        "POSTGRES_PORT", 
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        
        # Service URLs for integration
        "AUTH_SERVICE_URL",
        "AGENTS_SERVICE_URL",
    ]
}
```

**2. Add to `.env.master.example`**:
```bash
# Knowledge Service
KNOWLEDGE_SERVICE_PORT=8004
KNOWLEDGE_DIR=./knowledge/knowledge_base
KNOWLEDGE_API_PORT=8004

# LightRAG Models (shared with agents)
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small

# PostgreSQL for LightRAG (if using postgres backend)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=lightrag_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

##### Service Integration

**1. Create Python startup script** (`knowledge/scripts/run_api_server.py`):
```python
#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import and run the FastAPI app
import uvicorn
from gateway.main import app

if __name__ == "__main__":
    port = int(os.getenv("KNOWLEDGE_SERVICE_PORT", "8004"))
    uvicorn.run(
        "gateway.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
```

**2. Update root `Makefile`**:
```makefile
# Development - Knowledge Service
dev-knowledge: env-distribute
	@echo "🧠 Starting knowledge service..."
	@cd knowledge && venv/bin/python scripts/run_api_server.py

# Add to dev-all target
dev-all: env-distribute
	@echo "🚀 Starting all services locally..."
	@make -j dev-agents dev-auth dev-database dev-homepage dev-editor-backend dev-editor dev-knowledge

# Add port 8004 to clean-ports (and fix missing 3458)
clean-ports:
	@echo "🧹 Cleaning up ports..."
	@lsof -ti:8000 | xargs kill -9 2>/dev/null || echo "Port 8000 clear"
	@lsof -ti:8103 | xargs kill -9 2>/dev/null || echo "Port 8103 clear"
	@lsof -ti:8002 | xargs kill -9 2>/dev/null || echo "Port 8002 clear"
	@lsof -ti:8001 | xargs kill -9 2>/dev/null || echo "Port 8001 clear"
	@lsof -ti:8004 | xargs kill -9 2>/dev/null || echo "Port 8004 clear"
	@lsof -ti:3456 | xargs kill -9 2>/dev/null || echo "Port 3456 clear"
	@lsof -ti:3458 | xargs kill -9 2>/dev/null || echo "Port 3458 clear"
	@echo "✅ All ports cleaned"

# Add install target
install-knowledge:
	@echo "📦 Installing knowledge dependencies..."
	@cd knowledge && python -m venv venv && venv/bin/pip install -r requirements.txt
```

**3. Tmux Integration** - Update `dev-tunnels-tmux` in root Makefile:
```makefile
# Add after editor frontend window (window 7)
@tmux new-window -t hirecj-tunnels:10 -n knowledge
@tmux send-keys -t hirecj-tunnels:10 'sleep 3 && make dev-knowledge' C-m

# Update help text in window 0 to include:
echo "  10 - Knowledge service"
```

##### Code Updates Required

**1. Update `gateway/main.py`**:
- Change default port from 9620 to 8004
- Use environment variables:
```python
PORT = int(os.getenv("KNOWLEDGE_SERVICE_PORT", "8004"))
KNOWLEDGE_DIR = Path(os.getenv("KNOWLEDGE_DIR", "./knowledge_base"))
```

**2. Create `knowledge/requirements.txt`**:
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
lightrag-hku==0.1.0
pydantic==2.5.0
aiohttp==3.9.1
psycopg2-binary==2.9.9
python-multipart==0.0.6
```

**3. Update knowledge Makefile**:
```makefile
# Remove server target, use Python script instead
dev:
	venv/bin/python scripts/run_api_server.py
```

##### Service Discovery

The knowledge service will automatically be included in tunnel detection since it's already configured in `ngrok.yml.example` on port 8004.

**Note**: The ngrok.yml.example incorrectly lists the editor on port 3457, but it actually runs on 3458. This should be fixed in ngrok.yml.example.

#### Success Criteria for Phase 0

- ✓ API server starts on port 8004 (aligned with HireCJ standards)
- ✓ Integrates with tmux dev environment (window 10)
- ✓ Environment variables distributed from root .env
- ✓ Appears in tunnel URLs when using ngrok
- ✓ Namespace switching works correctly
- ✓ Can ingest documents into different namespaces
- ✓ Data isolation between namespaces verified
- ✓ Simple to start with `make dev-knowledge` or full stack with `make dev-tunnels-tmux`

#### Quick Start Commands

```bash
# Setup
cd knowledge
make setup

# Start API (standalone)
make dev

# Or from root directory:
make dev-knowledge

# Or start everything:
make dev-tunnels-tmux

# Create a namespace
curl -X POST "http://localhost:8004/api/namespaces?namespace_id=products" \
  -H "Content-Type: application/json" \
  -d '{"name": "Product Knowledge", "description": "Product specs and documentation"}'

# Add product knowledge
curl -X POST "http://localhost:9620/api/products/documents" \
  -H "Content-Type: application/json" \
  -d '{"content": "Our product supports RAM upgrades up to 64GB..."}'

# Query the namespace
curl -X POST "http://localhost:9620/api/products/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I upgrade RAM?", "mode": "hybrid"}'

# List all namespaces
curl "http://localhost:9620/api/namespaces"

# Delete a namespace
curl -X DELETE "http://localhost:9620/api/namespaces/products"
```

#### Key Advantages

1. **Dynamic Management**: Create/delete namespaces on demand via API
2. **Zero Initial State**: System starts empty, populated as needed
3. **Native LightRAG Feature**: Uses `namespace_prefix` as designed
4. **Single Instance**: Efficient resource usage
5. **Persistent Registry**: Namespace configurations saved to disk
6. **Flexible Architecture**: Easy to add namespace types later
3. **Dynamic Switching**: No restart needed for namespace changes
4. **Personality System**: Flexible personality management
5. **Simple Architecture**: One working directory, one configuration

This approach leverages LightRAG's built-in capabilities without any modifications, providing a clean foundation for all future enhancements.

---

### Milestone 1: Generic Knowledge Management

**Goal: Build comprehensive knowledge management capabilities for any namespace**

Building on Phase 0's dynamic namespace infrastructure, we'll add powerful ingestion and query capabilities that work across all namespaces.

#### Core Functionality
- **Universal Ingestion**: 
  - Support for multiple file formats (TXT, PDF, Markdown, JSON)
  - Batch file upload for any namespace
  - URL content fetching
  - Content preprocessing pipeline
- **Advanced Query Interface**:
  - Context-aware queries across any domain
  - Multi-namespace search capability
  - Relevance ranking and filtering
  - All 4 query modes (naive, local, global, hybrid)
- **Content Organization**:
  - Automatic metadata extraction
  - Source tracking
  - Version history support
  - Content categorization

#### Success Criteria
- ✓ Support 10+ different namespace types
- ✓ Query response time < 1 second
- ✓ Accurate information retrieval across domains
- ✓ Batch ingestion for 100+ documents
- ✓ Cross-namespace query capability

#### New API Endpoints

```python
# Additional endpoints for gateway/main.py

@app.post("/api/{namespace_id}/batch-ingest")
async def batch_ingest(namespace_id: str, files: List[UploadFile]):
    """Batch ingest multiple files into any namespace"""
    results = []
    async with get_lightrag_instance(namespace_id) as rag:
        for file in files:
            content = await file.read()
            try:
                text_content = content.decode('utf-8')
                await rag.ainsert(text_content)
                results.append({
                    "file": file.filename,
                    "status": "ingested",
                    "size": len(text_content)
                })
            except Exception as e:
                results.append({
                    "file": file.filename,
                    "status": "failed",
                    "error": str(e)
                })
    return {"namespace": namespace_id, "results": results}

@app.post("/api/{namespace_id}/ingest-url")
async def ingest_from_url(namespace_id: str, request: dict):
    """Fetch and ingest content from URL"""
    url = request.get("url")
    metadata = request.get("metadata", {})
    
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            content = await response.text()
    
    async with get_lightrag_instance(namespace_id) as rag:
        await rag.ainsert(content)
    
    return {
        "namespace": namespace_id,
        "url": url,
        "content_length": len(content),
        "metadata": metadata
    }

@app.post("/api/multi-namespace/search")
async def search_across_namespaces(request: dict):
    """Search across multiple namespaces"""
    query = request.get("query")
    namespaces = request.get("namespaces", [])
    mode = request.get("mode", "hybrid")
    
    results = {}
    for namespace_id in namespaces:
        if namespace_id in namespace_registry.namespaces:
            async with get_lightrag_instance(namespace_id) as rag:
                results[namespace_id] = await rag.aquery(
                    query, 
                    param=QueryParam(mode=mode)
                )
    
    return {
        "query": query,
        "namespaces_searched": namespaces,
        "results": results
    }
```

#### Interface at Completion

```bash
# Batch ingest into any namespace
curl -X POST "http://localhost:8004/api/products/batch-ingest" \
  -F "files=@docs/product-catalog.pdf" \
  -F "files=@docs/specifications.txt" \
  -F "files=@docs/user-guide.md"

# Ingest from URL with metadata
curl -X POST "http://localhost:8004/api/support/ingest-url" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://docs.example.com/troubleshooting",
    "metadata": {"category": "troubleshooting", "version": "2.0"}
  }'

# Search across multiple namespaces
curl -X POST "http://localhost:8004/api/multi-namespace/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How to upgrade memory?",
    "namespaces": ["products", "support", "tutorials"],
    "mode": "hybrid"
  }'

# Regular namespace query
curl -X POST "http://localhost:8004/api/products/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "warranty policy", "mode": "global"}'
```

#### Implementation Details

**1. Content Preprocessor**
```python
# scripts/preprocess_content.py
def preprocess_content(content: str, metadata: dict) -> str:
    """Universal content preprocessor"""
    doc_type = metadata.get('type', 'generic')
    
    # Extract structure based on content type
    if doc_type == "faq":
        # Format Q&A pairs for optimal retrieval
        content = extract_qa_pairs(content)
    elif doc_type == "technical":
        # Extract code blocks, examples
        content = format_technical_content(content)
    elif doc_type == "guide":
        # Structure step-by-step instructions
        content = format_guide_content(content)
    
    # Add metadata tags for better retrieval
    return f"[{doc_type}]\n{content}"
```

**2. Universal Ingestion Script**
```bash
#!/bin/bash
# scripts/ingest_knowledge.sh

# Usage: ./ingest_knowledge.sh <namespace> <directory>
NAMESPACE=$1
DIRECTORY=$2

echo "Ingesting knowledge into namespace: $NAMESPACE"

# Find and ingest all supported files
find "$DIRECTORY" -type f \( -name "*.pdf" -o -name "*.txt" -o -name "*.md" \) | \
while read -r file; do
    echo "Ingesting: $file"
    curl -X POST "http://localhost:8004/api/$NAMESPACE/batch-ingest" \
        -F "files=@$file"
done
```

#### Key Learnings to Capture
- Optimal chunk sizes for different content types
- Query patterns that work best across domains
- Performance with different storage backends
- Cross-namespace search effectiveness
- Metadata strategies for improved retrieval

---

### Milestone 2: Multi-Corpus & Basic Management

**Goal: Prove corpus isolation and management at scale**

#### New Functionality
- **Multiple Corpora**:
  - Add "Customer Support" and "Technical Documentation"
  - Namespace isolation between corpora
  - Corpus switching in query interface
- **Enhanced Ingestion**:
  - PDF and Markdown support
  - Batch file processing
  - Basic deduplication
- **Web API Layer**:
  - REST endpoints for corpus management
  - Simple web UI for corpus selection
  - Basic authentication
- **PostgreSQL Storage**: 
  - Migrate from file-based to PostgreSQL
  - Test backup/restore procedures

#### Success Criteria
- ✓ 3 isolated corpora functioning independently
- ✓ Can query across corpora or individually
- ✓ No data leakage between namespaces
- ✓ PostgreSQL performs equal or better than file storage
- ✓ Basic web UI for non-technical users

#### Interface at Completion

```
Basic Web UI - Knowledge Graphs List View (simplified from editor_design.md lines 404-439)
+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                                    KNOWLEDGE GRAPHS                                                 |
|  HireCJ RAG      +-----------------------------------------------------------------------------------------------------+
|                  | Manage your knowledge bases                                                        [+ New Graph] |
+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                                                                                                     |
| Navigation:      | AVAILABLE KNOWLEDGE GRAPHS                                                                          |
|                  | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
| [Knowledge]      | │                                                                                              │   |
| [Query]          | │ ┌────────────────────────────┐  ┌────────────────────────────┐  ┌──────────────────────┐   │   |
| [Status]         | │ │    Product Knowledge         │  │    Customer Support          │  │   Tech Docs        │   │   |
|                  | │ │                              │  │                              │  │                    │   │   |
|                  | │ │ 📚 247 documents            │  │ 💬 0 documents               │  │ 🔧 0 documents     │   │   |
|                  | │ │ 📊 Last updated: 5m ago     │  │ 📊 Empty                     │  │ 📊 Empty           │   │   |
|                  | │ │                              │  │                              │  │                    │   │   |
|                  | │ │ Status: ✅ Active            │  │ Status: 🆕 New               │  │ Status: 🆕 New     │   │   |
|                  | │ │                              │  │                              │  │                    │   │   |
|                  | │ │ [Upload Files →]            │  │ [Upload Files →]            │  │ [Upload Files →]  │   │   |
|                  | │ └────────────────────────────┘  └────────────────────────────┘  └──────────────────────┘   │   |
|                  | │                                                                                              │   |
|                  | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
+------------------+-----------------------------------------------------------------------------------------------------+

Query Interface:
+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                                    QUERY INTERFACE                                                  |
|  HireCJ RAG      +-----------------------------------------------------------------------------------------------------+
|                  | Search across knowledge graphs                                                                      |
+------------------+-----------------------------------------------------------------------------------------------------+
|                  | Query: [What are the laptop RAM upgrade options?                                              ]    |
|                  | Corpus: [All ▼]  [Product Knowledge] [Customer Support] [Tech Docs]     Mode: [Hybrid ▼]           |
|                  | [🔍 Search]                                                                                         |
|                  |                                                                                                     |
|                  | Results from: Product Knowledge                                                                     |
|                  | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
|                  | │ 1. Dell XPS 15 supports user-upgradeable RAM up to 64GB using standard SO-DIMM slots...     │   |
|                  | │ 2. MacBook Pro models from 2022 onwards have soldered RAM that cannot be upgraded...        │   |
|                  | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
+------------------+-----------------------------------------------------------------------------------------------------+
```

#### Key Learnings to Capture
- Namespace strategy effectiveness
- PostgreSQL configuration optimizations
- Cross-corpus query strategies
- Storage migration challenges

---

### Milestone 3: Dynamic Sources & Processing Pipeline

**Goal: Prove automated ingestion and real-time processing**

#### New Functionality
- **Dynamic Source Management**:
  - Web crawler for documentation sites
  - RSS feed monitor for blogs/updates
  - URL list batch processor
- **Processing Pipeline**:
  - Visual processing queue
  - Pause/resume functionality
  - Error handling and retry logic
  - Processing status API
- **Real-time Updates**:
  - WebSocket for live status
  - Progress tracking per source
  - Processing history log
- **Incremental Updates**:
  - Change detection for web sources
  - Only process new RSS items
  - Update scheduling

#### Success Criteria
- ✓ Can crawl and index entire documentation site
- ✓ RSS feeds update automatically
- ✓ Processing queue handles 100+ items smoothly
- ✓ Real-time updates with < 500ms latency
- ✓ Failed items retry successfully

#### Interface at Completion

```
Knowledge Graph Detail with Sources (based on editor_design.md lines 447-492)
+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                              KNOWLEDGE GRAPH: Product Knowledge                                     |
|  HireCJ RAG      +-----------------------------------------------------------------------------------------------------+
|                  | [← Back to Graphs]                                                            [⚙️ Settings] [🗑️ Delete] |
+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                                                                                                     |
| Navigation:      | DATA SOURCES                                                                      [+ Add Source] |
|                  | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
| [Knowledge]      | │ Source                     Type        Documents    Last Sync    Status         Actions     │   |
| [Query]          | │ ─────────────────────────────────────────────────────────────────────────────────────────── │   |
| [Status]         | │ products.cratejoy.com      Website     1,245        2h ago       ✅             [🔄] [✏️]  │   |
| [Processing]     | │ /docs/product-catalog      Files       892         1d ago       ✅             [🔄] [✏️]  │   |
|                  | │ Product Updates RSS        RSS Feed    387         2h ago       ✅             [🔄] [✏️]  │   |
|                  | │ competitor-features.txt    URL List    100         1w ago       ⚠️ Partial     [🔄] [✏️]  │   |
|                  | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
|                  |                                                                                                     |
|                  | ADD NEW SOURCE                                                                                      |
|                  | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
|                  | │ Source Type: [Website ▼]                                                                      │   |
|                  | │ URL: [https://docs.example.com                                                          ]     │   |
|                  | │ Crawl Depth: [3 ▼]    Include: [/products/*                    ]                             │   |
|                  | │ Schedule: [Every 6 hours ▼]                                                                   │   |
|                  | │ [➕ Add Source]                                                                               │   |
|                  | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
+------------------+-----------------------------------------------------------------------------------------------------+

Processing Status View (based on editor_design.md lines 499-543)
+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                              PROCESSING STATUS - Product Knowledge                                  |
|  HireCJ RAG      +-----------------------------------------------------------------------------------------------------+
|                  | Real-time processing status                                                   [⏸️ Pause] [❌ Cancel] |
+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                                                                                                     |
| Navigation:      | PROCESSING QUEUE                                                                                    |
|                  | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
| [Knowledge]      | │ Overall Progress: ████████████░░░░░░░░░░ 62% (186/300 items)                              │   |
| [Query]          | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
| [Status]         |                                                                                                     |
| [Processing]     | ACTIVE PROCESSING                                                                                   |
|                  | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
|                  | │ Source                          Status                 Progress        ETA                  │   |
|                  | │ ─────────────────────────────────────────────────────────────────────────────────────────── │   |
|                  | │ 🌐 docs.example.com/api         Crawling pages        ████░░░░░░ 43%  ~5 min              │   |
|                  | │ 📰 Product Updates RSS          Fetching entries      ██████████ 100% Processing...       │   |
|                  | │ 📄 feature-guide-v3.pdf         Extracting text       ███████░░░ 71%  ~1 min              │   |
|                  | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
|                  |                                                                                                     |
|                  | LIVE LOG (WebSocket Connected ●)                                                                   |
|                  | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
|                  | │ [14:23:15] Starting crawl of docs.example.com/api                                            │   |
|                  | │ [14:23:16] Found 47 pages to process                                                         │   |
|                  | │ [14:23:18] Processing page 1/47: /api/overview                                               │   |
|                  | │ [14:23:19] Extracted 2,341 words, creating chunks...                                         │   |
|                  | │ [14:23:20] Created 3 chunks, generating embeddings...                                        │   |
|                  | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
+------------------+-----------------------------------------------------------------------------------------------------+
```

#### Key Learnings to Capture
- Optimal crawl depth and patterns
- Rate limiting strategies
- Queue performance under load
- Incremental update efficiency

---

### Milestone 4: Advanced Features & Production Readiness

**Goal: Complete feature set for production deployment**

#### New Functionality
- **Advanced Processors**:
  - YouTube video transcription
  - Podcast/audio processing
  - Structured data extraction (JSON, CSV)
- **Smart Features**:
  - Auto-categorization of content
  - Quality scoring for sources
  - Duplicate detection across sources
  - Content freshness tracking
- **Production Features**:
  - Scheduled processing (cron-like)
  - Multi-user corpus permissions
  - Audit logging
  - Performance monitoring dashboard
- **Advanced Query**:
  - Query result explanations
  - Source attribution in results
  - Relevance tuning interface
  - Query analytics

#### Success Criteria
- ✓ YouTube videos transcribed and indexed accurately
- ✓ System handles 1M+ documents across all corpora
- ✓ 99.9% uptime for query API
- ✓ Full integration with HireCJ editor
- ✓ Non-technical users can manage sources

#### Interface at Completion

```
Full Knowledge Graph System (matching editor_design.md grounding views)
+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                                    KNOWLEDGE GRAPHS                                                 |
|  HireCJ Editor   +-----------------------------------------------------------------------------------------------------+
|                  | Manage your RAG knowledge bases for enhanced agent capabilities                                     |
+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                                                                                                     |
| ┌──────────────┐ | AVAILABLE KNOWLEDGE GRAPHS                                                          [+ New Graph] |
| │              │ | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
| │ ▶ Playground │ | │                                                                                              │   |
| │              │ | │ ┌────────────────────────────┐  ┌────────────────────────────┐  ┌──────────────────────┐   │   |
| ├──────────────┤ | │ │    Product Knowledge         │  │    Customer Support          │  │   Tech Docs        │   │   |
| │              │ | │ │                              │  │                              │  │                    │   │   |
| │   User       │ | │ │ 📚 2,847 documents          │  │ 💬 5,432 conversations       │  │ 🔧 892 articles    │   │   |
| │   Personas   │ | │ │ 📊 Last updated: 2h ago     │  │ 📊 Last updated: 15m ago    │  │ 📊 Updated: 1d ago │   │   |
| │              │ | │ │                              │  │                              │  │                    │   │   |
| ├──────────────┤ | │ │ Sources:                     │  │ Sources:                     │  │ Sources:           │   │   |
| │              │ | │ │ • Product catalogs           │  │ • Support tickets            │  │ • API docs         │   │   |
| │   System     │ | │ │ • Feature docs               │  │ • Chat transcripts           │  │ • GitHub wikis     │   │   |
| │   Prompts    │ | │ │ • Release notes              │  │ • FAQ database               │  │ • Blog posts       │   │   |
| │              │ | │ │ • YouTube demos              │  │ • Email threads              │  │ • Stack Overflow   │   │   |
| ├──────────────┤ | │ │                              │  │                              │  │                    │   │   |
| │              │ | │ │ Status: ✅ Active            │  │ Status: ✅ Active            │  │ Status: 🔄 Syncing │   │   |
| │   Workflow   │ | │ │ Quality: ⭐⭐⭐⭐⭐           │  │ Quality: ⭐⭐⭐⭐             │  │ Quality: ⭐⭐⭐⭐⭐  │   │   |
| │   Editor     │ | │ │                              │  │                              │  │                    │   │   |
| │              │ | │ │ [View Details →]            │  │ [View Details →]            │  │ [View Details →]  │   │   |
| ├──────────────┤ | │ └────────────────────────────┘  └────────────────────────────┘  └──────────────────────┘   │   |
| │              │ | │                                                                                              │   |
| │   Tool       │ | │ ┌────────────────────────────┐  ┌────────────────────────────┐                            │   |
| │   Editor     │ | │ │    Industry Research         │  │    Competitor Analysis       │                            │   |
| │              │ | │ │                              │  │                              │                            │   |
| ├──────────────┤ | │ │ 🔬 1,203 sources             │  │ 📈 756 documents             │                            │   |
| │              │ | │ │ 📊 Last updated: 3d ago     │  │ 📊 Last updated: 1w ago     │                            │   |
| │ ▶ Grounding   │ | │ │ 📹 312 videos processed     │  │ 🎙️ 89 podcasts              │                            │   |
| │   (current)   │ | │ │                              │  │                              │                            │   |
| │              │ | │ │ Status: ⏸️ Paused            │  │ Status: ✅ Active            │                            │   |
| ├──────────────┤ | │ │ Quality: ⭐⭐⭐              │  │ Quality: ⭐⭐⭐⭐             │                            │   |
| │              │ | │ │                              │  │                              │                            │   |
| │   Settings   │ | │ │ [View Details →]            │  │ [View Details →]            │                            │   |
| │              │ | │ └────────────────────────────┘  └────────────────────────────┘                            │   |
| └──────────────┘ | │                                                                                              │   |
|                  | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
+------------------+-----------------------------------------------------------------------------------------------------+

Advanced Processing with YouTube Support
+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                              KNOWLEDGE GRAPH: Industry Research                                     |
|  HireCJ Editor   +-----------------------------------------------------------------------------------------------------+
|                  | Processing YouTube content...                                                 [⏸️ Pause] [❌ Cancel] |
+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                                                                                                     |
|   [Navigation]   | ACTIVE PROCESSING                                                                                   |
|                  | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
|                  | │ Source                          Status                 Progress        ETA                  │   |
|                  | │ ─────────────────────────────────────────────────────────────────────────────────────────── │   |
|                  | │ 🎥 YouTube: AI Future Talk 2024 Transcribing          ████████░░ 82%  ~2 min              │   |
|                  | │ 🎙️ Podcast: Tech Weekly Ep 142  Audio Processing      ███░░░░░░░ 31%  ~5 min              │   |
|                  | │ 📊 market-analysis-2024.csv     Structured Extract    ██████████ 100% Analyzing...        │   |
|                  | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
|                  |                                                                                                     |
|                  | QUALITY ANALYSIS                                                                                    |
|                  | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
|                  | │ Content Quality Scoring:                                                                      │   |
|                  | │ • Relevance: ████████░░ 85%  (Highly relevant to AI trends)                                 │   |
|                  | │ • Freshness: █████████░ 92%  (Published 3 days ago)                                         │   |
|                  | │ • Authority: ███████░░░ 78%  (Recognized expert speaker)                                    │   |
|                  | │ • Uniqueness: ██████░░░░ 65%  (Some overlap with existing content)                          │   |
|                  | │                                                                                               │   |
|                  | │ Duplicate Detection: Found 3 similar topics in existing corpus                               │   |
|                  | │ [View Duplicates] [Merge Similar] [Keep All]                                                │   |
|                  | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
+------------------+-----------------------------------------------------------------------------------------------------+

Advanced Query Interface with Explanations
+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                                    ADVANCED QUERY                                                   |
|  HireCJ Editor   +-----------------------------------------------------------------------------------------------------+
|                  | Query with source attribution and explanations                                                      |
+------------------+-----------------------------------------------------------------------------------------------------+
|                  | Query: [How are competitors handling AI-powered customer support?                              ]    |
|                  | Corpora: [✓] Product [✓] Support [✓] Research [✓] Competitors    Mode: [Hybrid ▼]                 |
|                  | [🔍 Search]  [🎯 Tune Relevance]  [📊 Analytics]                                                  |
|                  |                                                                                                     |
|                  | Results (Relevance: 94%)                                                                           |
|                  | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
|                  | │ 📍 From Competitor Analysis (2 days ago):                                                     │   |
|                  | │ "Zendesk has integrated GPT-4 for automatic ticket categorization and response drafting..."  │   |
|                  | │ Sources: competitor-analysis-2024.pdf (page 47), zendesk-blog-ai-update.html                │   |
|                  | │                                                                                               │   |
|                  | │ 🎥 From Industry Research (1 week ago) - YouTube: "Future of Support AI":                    │   |
|                  | │ "The panel discussed how Intercom's Resolution Bot now handles 67% of queries..."            │   |
|                  | │ Timestamp: 23:45-25:12                                                                       │   |
|                  | │                                                                                               │   |
|                  | │ 💬 From Customer Support (3 hours ago):                                                      │   |
|                  | │ "Customer asked about our AI capabilities compared to Freshdesk's Freddy AI..."              │   |
|                  | │ Related tickets: #4521, #4498, #4476                                                        │   |
|                  | │                                                                                               │   |
|                  | │ Knowledge Graph Connections:                                                                  │   |
|                  | │ • "AI Support" → "Zendesk" → "GPT Integration" → "Ticket Automation"                        │   |
|                  | │ • "Competitor Features" → "Intercom" → "Resolution Bot" → "Query Handling"                  │   |
|                  | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
+------------------+-----------------------------------------------------------------------------------------------------+
```

#### Key Learnings to Capture
- Transcription accuracy vs. cost
- Performance at scale
- User behavior patterns
- Most valuable content sources

---

### Progressive Complexity Overview

```
MVP
├── Single corpus
├── Text files only
├── CLI interface
└── File storage

Milestone 2
├── 3 corpora with isolation
├── PDF/Markdown support
├── Web API + basic UI
└── PostgreSQL storage

Milestone 3
├── Web crawling & RSS
├── Processing pipeline
├── Real-time updates
└── Incremental processing

Milestone 4
├── YouTube/audio processing
├── Smart categorization
├── Production monitoring
└── Advanced query features
```

---

### Risk Mitigation Strategy

#### Technical Risks
1. **LightRAG Performance**: Test with increasing data volumes at each milestone
2. **Storage Scaling**: PostgreSQL optimization in Milestone 2
3. **Processing Bottlenecks**: Queue system in Milestone 3
4. **Transcription Costs**: Evaluate in Milestone 4, consider alternatives

#### Product Risks
1. **User Adoption**: Simple UI in Milestone 2 for early feedback
2. **Query Relevance**: A/B test query modes throughout
3. **Source Quality**: Quality scoring in Milestone 4
4. **Integration Complexity**: API-first approach from Milestone 2

---

### Success Metrics by Milestone

| Milestone | Documents | Query Latency | Uptime | User Satisfaction |
|-----------|-----------|---------------|---------|-------------------|
| MVP       | 1K+       | < 2s          | 95%     | Internal testing  |
| 2         | 10K+      | < 1s          | 98%     | Beta users        |
| 3         | 100K+     | < 500ms       | 99%     | Early adopters    |
| 4         | 1M+       | < 500ms       | 99.9%   | Production ready  |

---

### Go/No-Go Decision Points

**After MVP**: 
- Does LightRAG provide better results than traditional search?
- Is the knowledge graph approach valuable for our use case?

**After Milestone 2**:
- Can we effectively isolate and manage multiple corpora?
- Does PostgreSQL meet our performance needs?

**After Milestone 3**:
- Is automated ingestion reliable enough?
- Do users find the processing pipeline intuitive?

**After Milestone 4**:
- Is the system ready for production scale?
- Have we proven ROI on the knowledge graph approach?

This roadmap allows us to prove core concepts early, gather feedback, and adjust course as needed while building toward a production-ready system.

## Success Metrics

- Support for 10+ concurrent corpora
- < 500ms query latency for hybrid search
- 95%+ uptime for ingestion pipeline
- Real-time processing updates with < 100ms latency
- Support for 100k+ documents per corpus

This architecture provides the flexibility, scalability, and isolation required for the HireCJ agent editor's knowledge graph system while leveraging LightRAG's powerful capabilities.