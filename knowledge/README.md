# Knowledge Service

LightRAG-based knowledge management system for HireCJ.

## Phase 0.1: Core API Infrastructure ✅

This phase implements a basic FastAPI server with health check endpoint.

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

- `GET /` - Root endpoint with API information
- `GET /health` - Health check endpoint
- `GET /docs` - Interactive API documentation (provided by FastAPI)

### Success Criteria ✅

- [x] Server starts successfully on port 8004
- [x] Health check endpoint returns 200 OK with JSON response
- [x] No errors in console output

### Next Steps

Phase 0.2 will add:
- Dynamic namespace registry
- Namespace CRUD operations  
- Namespace persistence to disk
- Data isolation testing