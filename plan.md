# HireCJ Project Plan

## Project Overview

HireCJ is an AI-powered customer support agent designed to autonomously handle 60-80% of e-commerce customer inquiries while providing actionable insights to founders.

## Design Philosophy

**"Simplify, Simplify, Simplify" means:**
- Don't add features we don't need yet
- Don't create abstractions for hypothetical use cases
- Build for current requirements, not imagined futures

**It does NOT mean:**
- Remove existing functionality that serves a purpose
- Strip out features that are already implemented and working
- Oversimplify to the point of losing capabilities

### Architecture
- **hirecj-data**: Backend service for synthetic conversation generation and API
- **hirecj-homepage**: Frontend marketing site with interactive chat demo
- **hirecj-knowledge**: Knowledge management system (appears to contain LightRAG integration)

### Key Technologies
- Backend: FastAPI, CrewAI, LiteLLM
- Frontend: React 18, TypeScript, Tailwind CSS
- Models: GPT-4, Claude 3.5 Sonnet
- Communication: WebSocket for real-time chat

## Makefile Cleanup Plan

The current Makefile in hirecj-data needs reorganization. Here's the plan:

### Issues Identified
1. **Server confusion**: Two different servers (`server` and `server-src`) both run on port 8000
2. **Command organization**: Commands are mixed without clear categorization
3. **Documentation**: Help text could be clearer about which server to use when
4. **Redundancy**: Some commands could be consolidated

### Proposed Changes

#### 1. Clarify Server Commands
```makefile
# Primary API server (for web chat and frontend integration)
dev:
	@echo "Starting HireCJ API Server on http://localhost:8000"
	@echo "This is the main server for frontend integration"
	venv/bin/python -m src.api.server

# Synthetic conversation generator (for testing/development)
dev-generator:
	@echo "Starting Conversation Generator Server on http://localhost:8001"
	@echo "This is for generating synthetic conversations"
	venv/bin/python -m app.main
```

#### 2. Reorganize Commands by Category
- **Setup**: install, clean, format, lint
- **Development**: dev, dev-generator, dev-shell
- **Testing**: test, test-api, test-cj (with subcategories)
- **Tools**: conversation, generate-universe, annotate
- **Interactive**: play, conversation-play

#### 3. Simplify Test Commands
Consolidate similar test commands and use clear naming:
- `test` - Run all tests
- `test-quick` - Run tests with mock evaluator
- `test-cj` - Run CJ behavior tests only
- `test-api` - Run API tests only
- `test-single TEST=<file>` - Run single test

#### 4. Remove Docker Commands
The Docker commands (dev-run, dev-shell, etc.) delegate to local/Makefile, which should be handled directly there.

## Next Steps
1. Create new simplified Makefile
2. Update documentation to clarify which server to use
3. Ensure all commands work with the new structure
4. Update README files to reflect changes