# HireCJ: AI-Powered Customer Support Agent Platform

HireCJ is a sophisticated AI-powered customer support agent platform designed to provide intelligent, context-aware customer service automation for e-commerce merchants. Built with a modern microservices architecture, it combines the power of large language models with structured business data to deliver personalized support experiences.

## 🌟 Key Features

- **AI-Powered Support Agent**: CJ, an intelligent assistant that can handle customer queries, provide business insights, and manage support workflows
- **Workflow-Driven Architecture**: Configurable workflows for different business scenarios (daily briefings, crisis response, onboarding)
- **Persistent Memory System**: CJ learns and remembers merchant-specific information across conversations
- **Real-time Communication**: WebSocket-based chat interface with progress updates
- **E-commerce Integration**: Native Shopify OAuth integration for seamless merchant authentication
- **Universe/Scenario System**: Sophisticated simulation framework for testing and demonstrations
- **Fact Checking**: Built-in verification system to ensure CJ's claims are accurate

## 🏗 Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                       │
│                    homepage/ (port 3456)                      │
└─────────────────────┬───────────────────────────────────────┘
                      │ WebSocket
┌─────────────────────┴───────────────────────────────────────┐
│                    Agents Service (FastAPI)                  │
│                    agents/ (port 8000)                        │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ CJ Agent    │  │ Message      │  │ Session          │   │
│  │ (CrewAI)    │  │ Processor    │  │ Manager          │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
        │                    │                    │
┌───────┴────────┐  ┌───────┴────────┐  ┌───────┴────────┐
│ Auth Service   │  │ Database       │  │ Knowledge      │
│ auth/          │  │ Service        │  │ Service        │
│ (port 8103)    │  │ database/      │  │ knowledge/     │
│                │  │ (port 8002)    │  │ (port 8001)    │
└────────────────┘  └────────────────┘  └────────────────┘
```

### Data Flow

1. **User Input** → WebSocket connection to Agents Service
2. **Session Manager** → Loads workflow requirements, merchant memory, and universe data
3. **Message Processor** → Creates CJ agent with appropriate context
4. **CJ Agent** → Processes message using available tools and workflow behavior
5. **Response** → Sent back via WebSocket with UI elements and progress updates

### Technology Stack

**Backend:**
- Python 3.11+ with FastAPI
- CrewAI for agent orchestration
- LiteLLM/OpenAI for LLM integration
- PostgreSQL for persistence
- Redis for caching
- SQLAlchemy ORM

**Frontend:**
- React 18 with TypeScript
- Vite for build tooling
- TailwindCSS for styling
- Radix UI components
- WebSocket for real-time chat

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL
- Redis
- tmux (for multi-service development)
- ngrok (optional, for HTTPS development)

### Quick Start

1. **Clone and setup environment:**
```bash
git clone <repository>
cd hirecj
make env-setup
```

2. **Configure environment variables:**
```bash
# Edit .env with your configuration
# Required: OPENAI_API_KEY or ANTHROPIC_API_KEY
# Required: Database URLs
# Optional: OAuth credentials for integrations
```

3. **Start development environment:**
```bash
# Option 1: Start all services in tmux
make dev-all

# Option 2: Start with HTTPS tunnels (requires ngrok)
make dev-tunnels-tmux

# Option 3: Start services individually
make dev  # Shows instructions
```

4. **Access the application:**
- Frontend: http://localhost:3456
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## 🧩 Core Concepts

### Workflows

Workflows define how CJ behaves in different contexts. Each workflow is a YAML file that specifies:
- **Requirements**: What context is needed (merchant, scenario, authentication)
- **Behavior**: Initial actions, transitions, and response patterns
- **Tools**: Available capabilities for that workflow

Current workflows:
- `shopify_onboarding` - Initial merchant setup and OAuth
- `ad_hoc_support` - General assistance mode
- `daily_briefing` - Morning business check-in
- `weekly_review` - Weekly performance analysis
- `crisis_response` - Urgent situation handling
- `support_daily` - Database-connected ticket management

### Universe/Scenario System

The Universe system provides consistent business contexts for testing and demos:
- **Merchants**: Different business personas (e.g., "Marcus Thompson - stressed, data-driven")
- **Scenarios**: Business situations (e.g., "churn_spike", "growth_stall", "normal_operations")
- **Timeline**: Historical events affecting the business
- **Customers**: Detailed customer records with support history

### Merchant Memory

CJ maintains persistent memory about each merchant:
- Facts are automatically extracted from conversations
- Stored in PostgreSQL with source tracking
- Loaded into context for personalized responses
- Deduplicated to avoid redundancy

### Fact Checking

Built-in system to verify CJ's claims:
- Real-time fact checking against universe data
- UI button to trigger fact checks
- Detailed reports on claim accuracy

## 🧪 Testing

The project uses an innovative YAML-based testing framework with LLM evaluation:

```bash
# Run all tests
make test

# Run CJ behavioral tests
make test-cj

# Run specific test category
python -m pytest tests/cj_boundaries/

# Interactive testing
make play
```

### Test Categories
- **Agent Isolation**: Tests for proper agent boundaries
- **CJ Boundaries**: Ensures CJ respects data access limits
- **Workflows**: Validates workflow-specific behaviors
- **Edge Cases**: Handles unusual scenarios
- **Data Consistency**: Verifies universe data integrity

## 🛠 Development

### Environment Management

The project uses a centralized `.env` pattern:
- Single `.env` file in root contains ALL configuration
- `scripts/distribute_env.py` automatically distributes to services
- Service-specific `.env` files are auto-generated (don't edit manually)

### 🚨 Debugging Guidelines

**NO LAZY NETWORK ASSUMPTIONS**: When debugging issues, never conclude they are due to:
- ngrok problems
- Network conditions  
- Packet loss
- "Transient network errors"

These are lazy explanations that avoid real debugging. 99% of problems are code bugs. Always:
- Investigate actual code logic and data flow
- Examine logs and trace execution paths
- Look for configuration issues
- Find the specific, deterministic cause in the code

Network issues are extremely rare - focus on the code.

### Useful Commands

```bash
# Database management
make clear-db        # Clear agents database
make fill-db         # Fill with test data
make migrate-agents  # Run migrations

# Development utilities
make env-verify      # Verify environment setup
make clean-ports     # Clean up stuck ports
make stop           # Stop all services

# Testing and debugging
make test-agents     # Test specific service
make logs-agents     # View service logs
```

### Adding New Features

1. **New Workflow**: Create YAML file in `agents/prompts/workflows/`
2. **New Tool**: Add to `agents/app/agents/universe_tools.py` or `database_tools.py`
3. **New UI Component**: Add to `homepage/src/components/`
4. **New Test**: Create YAML in appropriate `tests/` subdirectory

## 📦 Deployment

The project is designed for Heroku deployment:

```bash
# Deploy all services
make deploy-all

# Deploy specific service
make deploy-agents
make deploy-homepage
make deploy-auth

# View logs
make logs-agents
```

Each service deploys as a separate Heroku app with its own Procfile.

## 🔧 Configuration

### Essential Environment Variables

**Core Settings:**
- `ENVIRONMENT` - development/production
- `DEBUG` - Enable debug logging
- `LOG_LEVEL` - Logging verbosity

**API Keys:**
- `OPENAI_API_KEY` - For GPT models
- `ANTHROPIC_API_KEY` - For Claude models
- `SHOPIFY_CLIENT_ID/SECRET` - OAuth integration
- `SLACK_CLIENT_ID/SECRET` - Slack integration

**Database URLs:**
- `DATABASE_URL` - Main PostgreSQL
- `REDIS_URL` - Redis cache
- `SUPABASE_CONNECTION_STRING` - Production data

**Service URLs:**
- `AGENTS_SERVICE_URL`
- `AUTH_SERVICE_URL`
- `HOMEPAGE_URL`

## 🏛 Design Philosophy

The project follows strict "North Star Principles":

1. **Simplify, Simplify, Simplify** - One way to do things, no alternatives
2. **No Cruft** - Remove redundant code and complexity
3. **Break It & Fix It Right** - No backwards compatibility shims
4. **Long-term Elegance** - Performant, type-safe solutions
5. **Backend-Driven** - Server handles all complexity
6. **Single Source of Truth** - Centralized state management
7. **No Over-Engineering** - Build for current needs only

## 📚 Documentation

- `SINGLE_ENV_GUIDE.md` - Environment management guide
- `NGROK_SETUP.md` - HTTPS development setup
- `docs/architecture_components.md` - Detailed architecture
- `docs/TEST_AUTHORING_GUIDE.md` - Writing behavioral tests
- `agents/CONFIGURATION.md` - Agent configuration

## 🤝 Contributing

See `CONTRIBUTING.md` for guidelines on:
- Code style and standards
- Testing requirements
- Pull request process
- Architecture decisions

## 📄 License

This project is licensed under the terms in the `LICENSE` file.

---

Built with ❤️ using CrewAI, FastAPI, React, and the power of LLMs.