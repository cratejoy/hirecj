# HireCJ - Your AI Customer Support Agent for E-commerce

[![License](https://img.shields.io/badge/license-proprietary-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://python.org)
[![TypeScript](https://img.shields.io/badge/typescript-5.0-blue.svg)](https://www.typescriptlang.org/)

HireCJ is an AI-powered customer support platform that acts as your virtual Customer Experience & Growth Officer. Designed specifically for e-commerce merchants, CJ handles 60-80% of support tickets autonomously while providing actionable business insights.

## 🎯 What HireCJ Does

HireCJ transforms customer support from a cost center into a growth engine by:

- **Automating Support**: Handles common customer inquiries 24/7 without human intervention
- **Providing Insights**: Identifies patterns, trends, and opportunities in your support data
- **Saving Time**: Reduces support workload by 60-80%, freeing merchants to focus on growth
- **Learning Continuously**: Remembers past interactions and improves responses over time
- **Integrating Seamlessly**: Connects with Shopify, support systems, and other e-commerce tools

## 🚀 User Experience

### Getting Started
1. **Visit the Landing Page**: Professional LinkedIn-style interface at hirecj.ai
2. **Connect Your Store**: One-click Shopify OAuth integration
3. **Meet CJ**: Your AI agent introduces itself and begins learning about your business
4. **Start Chatting**: Natural conversation interface for all support and business needs

### Key Workflows

#### 🌅 Daily Briefings
Start each day with a scannable update covering:
- Overnight tickets and their resolutions
- Key metrics and trends
- Actionable opportunities
- One-click actions for urgent items

#### 🚨 Crisis Management
When issues spike, CJ automatically:
- Detects unusual patterns
- Provides root cause analysis
- Suggests immediate actions
- Handles customer communications

#### 💬 Ad-Hoc Support
Ask CJ anything about:
- Customer inquiries
- Order issues
- Product questions
- Business metrics
- Support trends

### Interface Features
- **Clean Chat UI**: Streamlined interface with markdown support
- **Smart Actions**: Buttons for common tasks like "Handle Support Queue"
- **Visual Feedback**: Loading states, progress indicators, and clear status updates
- **Mobile Responsive**: Works seamlessly on all devices

## 🏗️ Architecture

### System Overview
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Homepage  │────▶│    Auth     │────▶│   Agents    │
│  (React/TS) │     │  (FastAPI)  │     │  (FastAPI)  │
└─────────────┘     └─────────────┘     └─────────────┘
       │                    │                    │
       └────────────────────┴────────────────────┘
                            │
                    ┌───────────────┐
                    │   Database    │
                    │  (PostgreSQL) │
                    └───────────────┘
                            
┌─────────────┐     ┌─────────────┐
│   Editor    │────▶│Editor Backend│
│  (React/TS) │     │  (FastAPI)  │
└─────────────┘     └─────────────┘
```

### Services

#### 1. **Homepage Service** (`/homepage`)
- **Tech Stack**: React 18, TypeScript, Vite, Tailwind CSS
- **Purpose**: User interface and real-time chat
- **Key Features**:
  - WebSocket-based real-time communication
  - OAuth flow handling
  - Responsive chat interface
  - Session management

#### 2. **Auth Service** (`/auth`)
- **Tech Stack**: FastAPI, PostgreSQL, JWT
- **Purpose**: Authentication and OAuth management
- **Key Features**:
  - Shopify OAuth integration
  - JWT-based state management
  - Secure token storage
  - CORS handling for cross-domain requests

#### 3. **Agents Service** (`/agents`)
- **Tech Stack**: FastAPI, CrewAI, Anthropic Claude, OpenAI
- **Purpose**: AI agent orchestration and business logic
- **Key Features**:
  - Multi-agent architecture with CrewAI
  - Conversation memory system
  - Workflow orchestration
  - Pattern detection and insights
  - WebSocket API for real-time updates

#### 4. **Database Service** (`/database`)
- **Tech Stack**: PostgreSQL, SQLAlchemy, Alembic
- **Purpose**: Data persistence and ETL
- **Key Features**:
  - Merchant data management
  - Conversation history
  - Integration tokens
  - Analytics data

#### 5. **Editor Backend Service** (`/editor-backend`)
- **Tech Stack**: FastAPI, PyYAML
- **Purpose**: API backend for the Agent Editor tool
- **Key Features**:
  - System prompt version management
  - User persona CRUD operations
  - Workflow definition management
  - Tool configuration

#### 6. **Editor Frontend** (`/editor`)
- **Tech Stack**: React 18, TypeScript, Vite, Tailwind CSS
- **Purpose**: Visual interface for configuring AI agents
- **Key Features**:
  - Playground for testing conversations
  - System prompt editor with version control
  - User persona builder
  - Visual workflow designer
  - Tool configuration interface

#### 7. **Shared Module** (`/shared`)
- **Purpose**: Common utilities and configurations
- **Features**:
  - Environment configuration
  - Logging setup
  - Database models
  - API models

### Communication Flow
1. User interacts with Homepage
2. Homepage authenticates via Auth Service
3. Homepage establishes WebSocket with Agents Service
4. Agents Service processes requests using AI
5. All services persist data in Database

## 📁 Data-Driven Configuration

### Workflow Definitions (`/agents/app/workflows/`)
```yaml
# Example: onboarding.yaml
workflow:
  id: "onboarding"
  name: "Merchant Onboarding"
  triggers:
    - "oauth_complete"
  actions:
    - analyze_store
    - introduce_capabilities
    - offer_next_steps
```

### Agent Prompts (`/agents/prompts/`)
Versioned prompt templates (v1.0.0 → v6.0.1) that define CJ's:
- Personality and tone
- Response formatting
- Business logic
- Tool usage

### Test Scenarios (`/agents/tests/scenarios/`)
YAML-based behavioral tests with LLM evaluation:
```yaml
test:
  name: "Crisis Detection"
  scenario: "Ticket spike with angry customers"
  expected_behaviors:
    - detects_urgency: true
    - provides_root_cause: true
    - suggests_actions: true
```

### Merchant Personas (`/agents/tests/test_merchants/`)
Test data for different merchant types:
- Small businesses
- Growing brands
- Enterprise stores
- Crisis situations

## 🔧 Current Capabilities

### Integrations
- ✅ **Shopify**: Full OAuth, order/customer/product data access
- 🚧 **Freshdesk**: Ticket management (in development)
- 🚧 **Klaviyo**: Email marketing (planned)
- 🚧 **Slack**: Team notifications (planned)

### AI Features
- **Smart Context**: Maintains conversation history and merchant knowledge
- **Pattern Detection**: Identifies trends in support tickets
- **Automated Responses**: Handles common inquiries without templates
- **Business Insights**: ROI tracking, opportunity identification
- **Proactive Alerts**: Detects and alerts on unusual patterns

### Unique Differentiators
1. **Memory System**: Persistent knowledge across all conversations
2. **Business Intelligence**: Goes beyond support to provide growth insights
3. **Natural Language**: No rigid templates or decision trees
4. **Extensible Workflows**: YAML-based configuration for easy customization
5. **LLM-Evaluated Testing**: Ensures quality through AI-powered test evaluation

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis (optional, for caching)

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/hirecj.git
   cd hirecj
   ```

2. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Install dependencies**
   ```bash
   make install-all
   ```

4. **Run database migrations**
   ```bash
   make migrate
   ```

5. **Start services**
   ```bash
   make dev  # Starts all services
   ```

6. **Access the application**
   - Homepage: http://localhost:3456
   - Agents API: http://localhost:8000
   - Editor Backend API: http://localhost:8001
   - Database API: http://localhost:8002
   - Auth API: http://localhost:8103
   - Editor Frontend: http://localhost:3458

### Environment Variables
Key configuration variables:
```env
# OAuth
SHOPIFY_CLIENT_ID=your_client_id
SHOPIFY_CLIENT_SECRET=your_client_secret

# AI Models
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key

# Database
DATABASE_URL=postgresql://user:pass@localhost/hirecj

# Services
AUTH_SERVICE_URL=http://localhost:8103
AGENTS_SERVICE_URL=http://localhost:8000
EDITOR_BACKEND_URL=http://localhost:8001
```

## 📚 Documentation

- [API Documentation](docs/api.md)
- [Deployment Guide](docs/deployment.md)
- [Testing Guide](docs/testing.md)
- [Contributing Guidelines](CONTRIBUTING.md)

## 🧪 Testing

### Unit Tests
```bash
make test
```

### Behavioral Tests
```bash
cd agents && pytest tests/scenarios/
```

### End-to-End Tests
```bash
make test-e2e
```

## 🚢 Deployment

HireCJ can be deployed to:
- **Heroku**: Using git subtree push for each service
- **AWS**: Using ECS or Kubernetes
- **Docker**: Full docker-compose setup available

See [Deployment Guide](docs/deployment.md) for detailed instructions.

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

## 📄 License

This project is proprietary software. See [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

Built with:
- [Anthropic Claude](https://anthropic.com) - Primary AI model
- [CrewAI](https://crewai.io) - Agent orchestration
- [FastAPI](https://fastapi.tiangolo.com) - Backend framework
- [React](https://reactjs.org) - Frontend framework

---

**Built with ❤️ by the HireCJ team**