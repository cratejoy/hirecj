# Knowledge Service

LightRAG-based knowledge management system for HireCJ.

## Phase 0.1: Core API Infrastructure ✅

This phase implements a basic FastAPI server with health check endpoint.

## Phase 0.2: Namespace Management ✅

This phase adds namespace CRUD operations with LightRAG integration.

## Phase 0.3: Basic Operations ✅

This phase adds document ingestion and query functionality.

## Phase 1.1: Basic Document Ingestion ✅

This phase adds file upload support for text files (.txt, .md).

## Phase 1.3: Enhanced Ingestion ✅

This phase adds JSON support, URL content fetching, and a universal ingestion script.

### New Features
- **JSON File Support**: Upload and parse .json files with metadata extraction
- **URL Content Fetching**: Fetch and ingest content from web URLs
- **Content Preprocessing**: Clean and normalize text, convert HTML to text
- **Universal Ingestion Script**: Command-line tool for batch ingestion

### Directory Structure

```
knowledge/
├── knowledge_base/          # LightRAG working directory (empty for now)
├── gateway/                 # API server code
│   ├── __init__.py
│   └── main.py            # FastAPI application  
├── scripts/                # Utility scripts
│   └── run_api_server.py  # Server startup script
├── data/                   # Source documents (empty for now)
├── logs/                   # Log files
├── requirements.txt        # Python dependencies
├── Makefile               # Development commands
└── README.md              # This file
```

### Setup

1. Install dependencies:
   ```bash
   cd knowledge
   make install
   ```

2. Start the server:
   ```bash
   make dev
   ```

3. Test the health endpoint:
   ```bash
   make test
   ```

### API Endpoints

#### Core Endpoints
- `GET /` - Root endpoint with API information
- `GET /health` - Health check endpoint (includes namespace count)
- `GET /docs` - Interactive API documentation (provided by FastAPI)

#### Namespace Management (Phase 0.2)
- `POST /api/namespaces?namespace_id={id}` - Create a new namespace
- `GET /api/namespaces` - List all namespaces
- `GET /api/namespaces/{namespace_id}` - Get specific namespace details
- `GET /api/namespaces/{namespace_id}/statistics` - Get namespace statistics (document count, last updated, etc.)
- `DELETE /api/namespaces/{namespace_id}` - Delete a namespace

#### Document Operations (Phase 0.3, 1.1 & 1.3)
- `POST /api/{namespace_id}/documents` - Add documents to a namespace (JSON)
- `POST /api/{namespace_id}/documents/upload` - Upload single file (Phase 1.1)
- `POST /api/{namespace_id}/documents/batch-upload` - Upload multiple files (Phase 1.1)
- `POST /api/{namespace_id}/documents/url` - Fetch and ingest URL content (Phase 1.3)
- `POST /api/{namespace_id}/query` - Query knowledge in a namespace

### Phase 0.1 Success Criteria ✅

- [x] Server starts successfully on port 8004
- [x] Health check endpoint returns 200 OK with JSON response
- [x] No errors in console output

### Phase 0.2 Features

- **Dynamic Namespace Registry**: Manages namespaces with persistence to disk
- **Namespace CRUD Operations**: Create, read, update, and delete namespaces via API
- **LightRAG Integration**: Each namespace gets its own isolated LightRAG instance
- **Namespace Validation**: IDs must be lowercase letters, numbers, and underscores

### Testing Phase 0.2

Run the namespace test script:
```bash
cd knowledge
venv/bin/python scripts/test_namespaces.py
```

Or test manually with curl:
```bash
# Create a namespace
curl -X POST "http://localhost:8004/api/namespaces?namespace_id=products" \
  -H "Content-Type: application/json" \
  -d '{"name": "Product Knowledge", "description": "Product documentation"}'

# List namespaces
curl http://localhost:8004/api/namespaces

# Get specific namespace
curl http://localhost:8004/api/namespaces/products

# Get namespace statistics (document count, last updated, etc.)
curl http://localhost:8004/api/namespaces/products/statistics

# Delete namespace
curl -X DELETE http://localhost:8004/api/namespaces/products
```

### Phase 0.2 Success Criteria ✅

- [x] Can create, list, and delete namespaces via API
- [x] Namespaces persist to disk (namespace_registry.json)
- [x] Each namespace has isolated data storage
- [x] Proper error handling and HTTP status codes

### Phase 0.3 Features

- **Document Ingestion**: Add documents to any namespace with metadata
- **Query Interface**: Query documents with multiple modes (naive, local, global, hybrid)
- **Example Scripts**: Comprehensive examples showing namespace and document usage
- **Setup Automation**: Automated setup script for easy deployment

### Testing Phase 0.3

Run the example usage script:
```bash
cd knowledge
make example
```

Run the basic operations test:
```bash
cd knowledge
make test-operations
```

### Phase 0.3 Success Criteria ✅

- [x] Document ingestion endpoint works for all namespaces
- [x] Query endpoint returns relevant results
- [x] All query modes (naive, local, global, hybrid) function properly
- [x] Example scripts demonstrate full workflow
- [x] Setup script prepares environment correctly

### Testing Phase 1.3

Run the enhanced ingestion test:
```bash
cd knowledge
make test-enhanced-ingestion
```

### Universal Ingestion Script

The universal ingestion script (`scripts/universal_ingest.py`) supports various ingestion scenarios:

```bash
# Ingest a single file
venv/bin/python scripts/universal_ingest.py --namespace products --type file data/test_files/sample_data.json

# Ingest all files in a directory
venv/bin/python scripts/universal_ingest.py --namespace docs --type directory data/test_files/

# Ingest files recursively
venv/bin/python scripts/universal_ingest.py --namespace docs --type directory --recursive /path/to/docs/ "*.md"

# Ingest a single URL
venv/bin/python scripts/universal_ingest.py --namespace web --type url https://example.com/article

# Ingest URLs from a file
venv/bin/python scripts/universal_ingest.py --namespace web --type urls data/test_files/test_urls.txt

# Dry run to preview what would be ingested
venv/bin/python scripts/universal_ingest.py --namespace test --type directory --dry-run data/test_files/
```

### Supported File Types

- `.txt` - Plain text files
- `.md` - Markdown files
- `.json` - JSON files with automatic structure parsing

### Next Steps

Phase 0.4 will integrate with HireCJ's development environment.