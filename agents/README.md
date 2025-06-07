# HireCJ Agents

FastAPI backend for HireCJ - the AI customer support agent with intelligent conversation management and merchant memory.

## 🏗️ Architecture Overview

This service implements a sophisticated agent architecture with two distinct usage patterns:

### 1. Direct CJ Agent (Internal Server)
- **Module**: `app.agents.cj_agent`
- **Used by**: Server components (MessageProcessor)
- **Purpose**: Actual CJ agent implementation using CrewAI
- **Features**: Full agent capabilities, tool access, merchant memory integration

### 2. API Adapter (External Clients)
- **Module**: `app.agents.api_adapter`
- **Used by**: Scripts, demos, external clients
- **Purpose**: CrewAI-compatible interface that routes through WebSocket API
- **Benefits**: Centralized session management, persistence, consistent behavior

### Message Flow Architecture

```
External Clients (scripts/web/demos)
    ↓
API Adapter (mimics CrewAI interface)
    ↓
WebSocket Connection (/ws/chat/{conversation_id})
    ↓
API Server (WebPlatform)
    ↓
SessionManager (loads universe data & merchant memory)
    ↓
MessageProcessor
    ↓
Direct CJ Agent (actual implementation)
    ↓
Response via WebSocket
```

### Key Design Decisions

1. **Separation of Concerns**: External clients never directly instantiate CJ agents
2. **Session Management**: All state (including merchant memory) managed server-side
3. **Backward Compatibility**: Scripts using CrewAI interface work unchanged
4. **Single Source of Truth**: One session, one state, managed by the server
5. **Prompt Transparency**: No runtime prompt mutations - all behavior visible in static YAML files

## 🔐 User Identity Management

**CRITICAL: Backend is the SOLE AUTHORITY for user identity generation**

### The Pattern
1. **Frontend**: Sends only raw data (`shop_domain`, `merchant_id`)
2. **Backend**: Generates user IDs using `shared.user_identity.get_or_create_user()`
3. **Format**: All user IDs follow pattern `usr_xxxxxxxx` (8-char hex from SHA256)

### Where User IDs are Generated
- **OAuth Callback** (auth service): When merchant completes Shopify OAuth
- **start_conversation** (agents service): When session begins with shop_domain
- **oauth_complete** (agents service): When OAuth completion is reported

### Common Mistakes to Avoid
```python
# ❌ WRONG - Never generate IDs manually
user_id = f"shop_{shop_domain.replace('.myshopify.com', '')}"  # NO!
user_id = f"user_{merchant_id}"  # NO!

# ✅ CORRECT - Always use the authoritative function
from shared.user_identity import get_or_create_user
user_id, is_new = get_or_create_user(shop_domain)
```

### Frontend Guidelines
- NEVER attempt to generate user IDs
- Store only `merchantId` and `shopDomain` in localStorage
- Send these raw values to backend via `session_update`
- Backend will handle all ID generation and user creation

## 🎯 Prompt Transparency Principle

**Critical for Debuggability**: All CJ behavior must be understandable by reading static files. No hidden prompt mutations at runtime.

### What CJ Sees
CJ's complete prompt consists of exactly two parts:
1. **Base Prompt**: `agents/prompts/cj/versions/v{version}.yaml` - Core identity and principles
2. **Workflow Prompt**: `agents/prompts/workflows/{workflow}.yaml` - Workflow-specific instructions

### The Golden Rules
✅ **DO**: 
- Put all instructions in YAML files
- Use simple template variable substitution ({merchant_name}, {workflow_name})
- Keep base + workflow separation clear
- Make system event handling visible in workflow YAML

❌ **DON'T**:
- Dynamically modify prompts at runtime
- Inject hidden context that's not in YAML files
- Use complex conditional logic to build prompts
- Hide behavior in code instead of prompts

### Example: System Events
Instead of complex code to handle OAuth completion, we simply add to the workflow YAML:
```yaml
SYSTEM EVENT HANDLING:
When you receive a message from sender "system":
  For "New Shopify merchant authenticated from [store]":
    - Respond: "Perfect! I've connected to [store]..."
```

This principle ensures developers can always understand CJ's behavior by reading two YAML files.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Virtual environment

### Installation
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
make install
```

### Running the Server

#### Development with Hot Reload (Recommended)
```bash
make dev
```
This starts the server with automatic hot reload - any changes to Python files will automatically restart the server.

#### Development without Hot Reload
If hot reload causes issues (e.g., with certain async operations):
```bash
make dev-noreload
```

#### Production
```bash
make run
```

### Key Features
- **Hot Reload**: The development server automatically restarts when you modify Python files
- **Debug Logging**: Development mode enables DEBUG level logging
- **Port**: Server runs on http://localhost:8000
- **API Docs**: Available at http://localhost:8000/docs

### Stopping the Server
```bash
make stop
```

### Testing
```bash
# Run all tests
make test

# Run Python tests only
make test-python

# Run YAML behavioral tests
make test-cj
```

## 📁 Project Structure
```
app/
├── agents/         # Agent implementations
│   ├── cj_agent.py         # Direct CJ agent (server-side)
│   ├── api_adapter.py      # API adapter for external clients
│   ├── merchant_agent.py   # Merchant simulation agent
│   └── universe_data_agent.py  # Universe data access
├── api/           # REST API endpoints
├── platforms/     # Platform integrations
│   └── web_platform.py     # WebSocket handler
├── services/      # Core services
│   ├── session_manager.py  # Session lifecycle management
│   ├── message_processor.py # Message handling with CJ
│   ├── merchant_memory.py  # Merchant memory persistence
│   └── conversation_storage.py # Conversation persistence
├── models.py      # Data models
├── config.py      # Configuration
└── main.py        # FastAPI application

data/
├── merchant_memory/  # Persistent merchant facts (YAML)
├── conversations/    # Conversation history (JSON)
└── universe/        # Scenario-specific universe data
```

## 🎯 Usage Patterns

### For Web Interface Users
The web interface automatically uses the WebSocket API. Sessions are managed server-side with proper memory and universe data loading.

### For Script Writers
Always use the API adapter for external scripts:
```python
# ✅ Correct - Uses API adapter
from app.agents.api_adapter import create_cj_agent, Crew, Task

# ❌ Wrong - Direct import only for server internals
from app.agents.cj_agent import create_cj_agent
```

### For Server Development
When working on server components (MessageProcessor, etc.), use direct imports:
```python
# Server-side code uses direct agent
from app.agents.cj_agent import create_cj_agent
```

## 🧠 Merchant Memory

The system maintains persistent memory about each merchant across conversations:

### How It Works
1. **Automatic Loading**: Memory loads when a session starts
2. **Fact Accumulation**: Facts extracted from conversations (Phase 8-9, coming soon)
3. **Context Injection**: Facts included in CJ's context (Phase 7, in progress)
4. **Persistence**: YAML files in `data/merchant_memory/`

### Memory Architecture
```
Session Creation
    ↓
SessionManager loads MerchantMemory
    ↓
MessageProcessor passes memory to CJ Agent
    ↓
CJ Agent uses facts in responses (Phase 7)
    ↓
FactExtractor extracts new facts (Phase 8-9)
    ↓
Memory saved to disk
```

## 🔧 Configuration
See `app/config.py` for all configuration options. Key environment variables:
- `LOG_LEVEL`: Logging level (default: INFO, dev: DEBUG)
- `API_HOST`: Host to bind to (default: 0.0.0.0)
- `API_PORT`: Port to bind to (default: 8000)
- `HIRECJ_API_URL`: WebSocket URL for API adapter (default: ws://localhost:8000)

## 🏛️ Architectural Principles

### North Star Principles
1. **Simplify**: One way to do things, no alternatives
2. **No Cruft**: Remove redundant code and complexity
3. **Break & Fix Right**: No compatibility shims
4. **Long-term Elegance**: Performant, type-safe solutions
5. **Backend-Driven**: Server handles complexity
6. **Single Source of Truth**: One session, one state

### Why Two CJ Agent Interfaces?
- **Not technical debt**: This is intentional architecture
- **External access**: Always through API for proper state management
- **Internal processing**: Direct agent for efficiency
- **Benefits**: Centralized sessions, persistence, consistency
