# HireCJ Editor Architecture

## Overview

The editor functionality is properly separated from the agent service with its own dedicated backend.

## Service Architecture

```
┌─────────────────────┐     ┌──────────────────────┐
│   Editor Frontend   │     │    Agent Service     │
│   (React, :3457)    │     │    (FastAPI, :8000)  │
│                     │     │                      │
│  /api/* proxied to  │     │  - Conversations     │
│   editor-backend    │     │  - Scenarios         │
└──────────┬──────────┘     │  - Universes         │
           │                │  - WebSocket Chat    │
           │                └──────────────────────┘
           │                
           │ HTTP/API                      
           │                
           ▼                
┌─────────────────────┐     
│  Editor Backend     │     
│  (FastAPI, :8001)   │     
│                     │     
│  - /api/v1/prompts  │     
│  - /api/v1/personas │     
│  - /api/v1/workflows│     
└─────────────────────┘     
```

## Port Assignments

| Service | Port | Purpose |
|---------|------|---------|
| Agent Service | 8000 | Core agent functionality |
| Editor Backend | 8001 | Editor-specific APIs |
| Database Service | 8002 | Shared database |
| Auth Service | 8103 | Authentication |
| Homepage | 3456 | Public landing page |
| Editor Frontend | 3457 | Editor UI |

## Development Commands

```bash
# Run everything with tunnels (recommended)
make dev-tunnels-tmux

# Run individual services
make dev-agents          # Agent service only
make dev-editor-backend  # Editor backend only
make dev-editor         # Editor frontend only

# Run everything locally (no tunnels)
make dev-all
```

## Key Benefits

1. **Separation of Concerns**: Agent service focuses solely on agent functionality
2. **Independent Scaling**: Each service can be scaled independently
3. **Clear API Boundaries**: Editor has its own API surface
4. **Development Flexibility**: Services can be developed and deployed independently

## File Structure

```
hirecj/
├── agents/           # Agent service (NO editor endpoints)
├── editor-backend/   # Dedicated editor API service
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── prompts.py
│   │   │       ├── personas.py
│   │   │       └── workflows.py
│   │   └── main.py
├── editor/           # Editor frontend
│   ├── src/
│   └── vite.config.ts  # Proxies /api to :8001
```