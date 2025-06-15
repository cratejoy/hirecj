# HireCJ Editor Backend

Backend API service for the HireCJ Agent Editor, providing endpoints for managing prompts, personas, workflows, and tools.

## Overview

The Editor Backend is a FastAPI service that provides:
- System prompt version management
- User persona CRUD operations
- Workflow definition management
- Tool configuration (coming soon)
- Scenario management (coming soon)

## Architecture

This service is designed to be separate from the main agent service to maintain clean service boundaries:
- Runs on port 8001 (agent service runs on 8000)
- Manages editor-specific resources
- Provides APIs for the editor frontend (port 3457)

## Getting Started

1. Install dependencies:
   ```bash
   make install
   ```

2. Start the development server:
   ```bash
   make dev
   ```

3. The API will be available at http://localhost:8001

## API Endpoints

### Prompts
- `GET /api/v1/prompts/` - List all prompt versions
- `GET /api/v1/prompts/{version}` - Get prompt content
- `PUT /api/v1/prompts/{version}` - Update prompt content

### Personas
- `GET /api/v1/personas/` - List all personas
- `GET /api/v1/personas/{id}` - Get persona details
- `POST /api/v1/personas/` - Create new persona
- `PUT /api/v1/personas/{id}` - Update persona
- `DELETE /api/v1/personas/{id}` - Delete persona

### Workflows
- `GET /api/v1/workflows/` - List all workflows
- `GET /api/v1/workflows/{id}` - Get workflow details
- `POST /api/v1/workflows/` - Create new workflow
- `PUT /api/v1/workflows/{id}` - Update workflow

### Health & Info
- `GET /` - Service information
- `GET /health` - Health check
- `GET /api/v1/test-cors` - CORS test endpoint

## Configuration

The service uses environment variables from the root `.env` file:
- `API_PORT` - Port to run on (default: 8001)
- `LOG_LEVEL` - Logging level (default: INFO)
- `ENVIRONMENT` - Environment name (development/staging/production)

## Development

### Running Tests
```bash
make test
```

### API Documentation
When running, visit http://localhost:8001/docs for interactive API documentation.

## File Structure

```
editor-backend/
├── app/
│   ├── api/
│   │   └── routes/       # API endpoint definitions
│   ├── config.py         # Configuration management
│   ├── logging_config.py # Logging setup
│   └── main.py           # FastAPI application
├── tests/                # Test files
├── requirements.txt      # Python dependencies
└── Makefile             # Development commands
```