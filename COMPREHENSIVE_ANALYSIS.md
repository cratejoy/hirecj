# HireCJ Comprehensive Analysis

## 1. What It Does

### Main Purpose
HireCJ is an AI-powered customer support agent platform that provides autonomous customer service automation for e-commerce merchants. The system centers around "CJ" - an intelligent AI agent that acts as a virtual Customer Experience (CX) & Growth Officer.

### Problems It Solves
- **Support Overload**: Automates 60-80% of customer support tickets without human intervention
- **Time Poverty**: Saves founders/merchants hours by handling support operations autonomously
- **Growth Insights**: Transforms support data into actionable business intelligence
- **24/7 Coverage**: Provides round-the-clock support coverage so merchants can truly disconnect
- **Pattern Detection**: Identifies trends and issues in support tickets before they become major problems

### Target Audience
- **E-commerce Merchants**: Primarily targeting Shopify store owners
- **Subscription Box Businesses**: Special focus on recurring revenue businesses
- **Solo Entrepreneurs/Small Teams**: Businesses that need support help but can't afford large teams
- **Growth-Stage Companies**: Merchants dealing with scaling challenges and operational complexity

## 2. User Experience

### Onboarding Flow
1. **Initial Landing**: Users arrive at LinkedIn-style profile page showcasing CJ's capabilities
2. **Chat Initiation**: Users can start chatting with CJ immediately
3. **Natural Detection**: CJ naturally determines if user is new or returning
4. **Shopify OAuth**: Seamless connection to Shopify store (read-only access)
5. **Quick Value Demo**: CJ immediately provides insights about the store
6. **Support System Connection**: Optional connection to Freshdesk/Zendesk/Gorgias
7. **Notification Setup**: Choose how to receive updates (email/browser)

### Interaction Model
- **Chat-First Interface**: Primary interaction through WebSocket-based real-time chat
- **Workflow-Driven**: Different conversation flows for different needs (daily briefings, crisis response, etc.)
- **Progress Indicators**: Visual feedback while CJ processes requests
- **One-Click Actions**: Actionable buttons for quick decisions
- **Persistent Memory**: CJ remembers merchant-specific information across conversations

### Available Features
- **Daily Flash Briefings**: Morning metrics reports with key insights
- **Crisis Management**: Rapid response to urgent business situations  
- **Pattern Detection**: Automatic identification of trending issues
- **Ticket Automation**: Handles common support requests autonomously
- **Weekly Reviews**: Comprehensive performance analysis
- **ROI Tracking**: Quantifies value in hours saved and dollars recovered

## 3. Architecture

### Main Services/Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React)                           │
│                 homepage/ (port 3456)                         │
│  - LinkedIn-style landing page                                │
│  - Real-time chat interface                                   │
│  - OAuth integration UI                                       │
│  - Progress indicators                                        │
└─────────────────────┬───────────────────────────────────────┘
                      │ WebSocket
┌─────────────────────┴───────────────────────────────────────┐
│                 Agents Service (FastAPI)                      │
│                 agents/ (port 8000)                           │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ CJ Agent    │  │ Message      │  │ Session          │   │
│  │ (CrewAI)    │  │ Processor    │  │ Manager          │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
│  - AI agent orchestration                                     │
│  - Workflow management                                        │
│  - Tool execution                                            │
│  - Memory persistence                                         │
└─────────────────────────────────────────────────────────────┘
        │                    │                    │
┌───────┴────────┐  ┌───────┴────────┐  ┌───────┴────────┐
│ Auth Service   │  │ Database       │  │ Knowledge      │
│ auth/          │  │ Service        │  │ Service        │
│ (port 8103)    │  │ (port 8002)    │  │ (port 8001)    │
│                │  │                │  │                │
│ - OAuth flows  │  │ - PostgreSQL   │  │ - LightRAG     │
│ - JWT tokens   │  │ - ETL pipeline │  │ - Transcripts  │
│ - User mgmt    │  │ - Migrations   │  │ - Knowledge    │
└────────────────┘  └────────────────┘  └────────────────┘
```

### Communication Flow
1. **WebSocket Connection**: Frontend establishes persistent connection to agents service
2. **Session Management**: Backend loads workflow requirements, merchant memory, and universe data
3. **Message Processing**: Creates CJ agent instance with appropriate context
4. **Tool Execution**: CJ uses available tools (Shopify API, database queries, etc.)
5. **Response Streaming**: Real-time updates sent back through WebSocket

### Tech Stack

**Backend:**
- Python 3.11+ with FastAPI for high-performance async APIs
- CrewAI for agent orchestration and tool management
- LiteLLM/OpenAI for LLM integration (supports multiple models)
- PostgreSQL for persistent data storage
- Redis for caching and session management
- SQLAlchemy ORM for database operations
- Pydantic for data validation

**Frontend:**
- React 18 with TypeScript for type safety
- Vite for fast development and optimized builds
- TailwindCSS for utility-first styling
- Radix UI for accessible components
- Framer Motion for animations
- WebSocket for real-time communication

### Code Organization

```
hirecj/
├── agents/                 # Core AI agent service
│   ├── app/
│   │   ├── agents/        # Agent implementations
│   │   ├── api/           # REST endpoints
│   │   ├── services/      # Business logic
│   │   └── migrations/    # Database schemas
│   ├── prompts/           # AI prompts and workflows
│   ├── data/              # Test data and universes
│   └── tests/             # YAML-based behavioral tests
├── homepage/              # Frontend application
│   ├── src/               # React source code
│   ├── server/            # Express backend
│   └── public/            # Static assets
├── auth/                  # Authentication service
├── database/              # Database service
├── knowledge/             # LightRAG knowledge service
└── shared/                # Shared utilities
```

## 4. Data-Driven Files

### Configuration Files

**Workflow Definitions** (`agents/prompts/workflows/`):
- `shopify_onboarding.yaml` - New user onboarding flow
- `daily_briefing.yaml` - Morning metrics workflow
- `crisis_response.yaml` - Emergency handling workflow
- `weekly_review.yaml` - Performance analysis workflow
- `ad_hoc_support.yaml` - General chat workflow
- `support_daily.yaml` - Database-connected support

**Agent Prompts** (`agents/prompts/cj/versions/`):
- Versioned prompt files (v1.0.0 to v6.0.1)
- Each defines CJ's personality, capabilities, and boundaries
- Clear separation between base identity and workflow-specific behavior

**Merchant Personas** (`agents/prompts/merchants/personas/`):
- `marcus_thompson` - Direct, data-driven BBQ business owner
- `sarah_chen` - Thoughtful, process-oriented tech accessories
- `zoe_martinez` - Scattered, emoji-heavy wellness influencer

**Universe Data** (`agents/data/universes/`):
- Complete business scenarios with timeline events
- Customer records with support history
- Metrics and KPIs for simulation
- Used for testing and demonstrations

### Data Models

**Database Schema** (PostgreSQL):
- `merchants` - Merchant accounts
- `etl_shopify_customers` - Shopify customer data (JSONB)
- `etl_freshdesk_tickets` - Support ticket data (JSONB)
- `etl_freshdesk_conversations` - Ticket conversations
- `etl_freshdesk_ratings` - Customer satisfaction ratings
- `merchant_integrations` - API keys and configs
- `web_sessions` - User session management
- `merchant_tokens` - OAuth tokens

**Session Data**:
- Conversation history (JSON files)
- Merchant memory (YAML files)
- WebSocket session state
- OAuth completion tracking

### Prompt Engineering

**Principles**:
- Static YAML files for transparency
- No runtime prompt mutations
- Clear base + workflow separation
- Template variables for customization
- Version control for prompt evolution

**Structure**:
```yaml
Base Prompt (identity) + Workflow Prompt (behavior) = Complete Context
```

## 5. Current Capabilities

### Integrations

**Shopify (Production Ready)**:
- OAuth 2.0 authentication flow
- GraphQL API integration
- Read-only access to:
  - Store overview and counts
  - Customer data
  - Order history
  - Product information
- Real-time data fetching tools

**Freshdesk (In Development)**:
- Ticket management
- Customer support history
- Satisfaction ratings
- Conversation threads

**Planned Integrations**:
- Zendesk
- Gorgias
- Slack notifications
- Email notifications

### AI/Automation Features

**Conversation Management**:
- Context-aware responses
- Workflow-driven behavior
- Multi-turn conversations
- Natural language understanding
- Dynamic UI component rendering

**Business Intelligence**:
- Pattern detection in support tickets
- Trend analysis
- Customer sentiment tracking
- Issue categorization
- Proactive alerts

**Automation Capabilities**:
- Ticket resolution suggestions
- Auto-categorization
- Response drafting
- Escalation detection
- ROI calculation

**Testing Framework**:
- YAML-based behavioral tests
- LLM-powered evaluation
- Automated test running
- Mock and real evaluators
- Comprehensive test coverage

### System Intelligence

**Memory System**:
- Persistent merchant facts
- Automatic fact extraction
- Context injection
- Cross-conversation learning
- Deduplication

**Universe/Scenario System**:
- Rich business simulations
- Multiple merchant personas
- Timeline-based events
- Detailed customer records
- Testing and demo environments

**Fact Checking**:
- Real-time verification
- Source tracking
- Accuracy reporting
- UI integration

### Unique Features

**Prompt Transparency**:
- All behavior visible in static files
- No hidden logic
- Easy debugging
- Version control

**Workflow Engine**:
- Declarative workflow definitions
- State management
- Transition handling
- Tool availability control

**Testing Innovation**:
- Natural language test criteria
- LLM evaluation of responses
- Behavioral validation
- Edge case coverage

**Backend-Driven Architecture**:
- Single source of truth
- Centralized state management
- Consistent user identity
- No frontend ID generation

## Key Differentiators

1. **Not Just a Chatbot**: CJ is positioned as an autonomous team member, not a tool
2. **Outcome-Focused**: Every interaction quantifies value in time saved or dollars recovered
3. **Merchant-Centric Design**: Built specifically for e-commerce pain points
4. **Transparent AI**: All behavior traceable to static configuration files
5. **Production-Ready OAuth**: Seamless Shopify integration with proper state management
6. **Sophisticated Testing**: YAML-based tests with LLM evaluation ensure quality
7. **Growth + Support**: Combines customer service with business intelligence

## Technical Excellence

- **Clean Architecture**: Clear separation of concerns across services
- **Type Safety**: TypeScript frontend, Pydantic backend
- **Modern Async**: FastAPI with proper async/await patterns
- **Comprehensive Testing**: Unit, integration, and behavioral tests
- **Developer Experience**: Hot reload, clear logging, good documentation
- **Security First**: JWT tokens, OAuth state validation, encrypted storage
- **Scalable Design**: Microservices architecture ready for growth