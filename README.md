# HireCJ - AI Customer Experience Officer

HireCJ is an AI-powered customer support agent that autonomously handles 60-80% of e-commerce customer inquiries while providing actionable insights to founders. This repository contains both the backend conversation engine and the frontend marketing/demo site.

## 🏗️ Project Structure

```
hirecj/
├── hirecj-data/          # Backend: Synthetic conversation generator & API
│   ├── app/              # Core application code
│   ├── prompts/          # YAML-based prompt management
│   ├── data/             # Generated conversations & universes
│   └── tests/            # Comprehensive test suite
│
├── hirecj-homepage/      # Frontend: Marketing site with chat demo
│   ├── client/           # React application
│   ├── server/           # Express backend
│   └── public/           # Static assets
│
└── plan.md              # Technical analysis & integration roadmap
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+ (for backend)
- Node.js 18+ (for frontend)
- OpenAI API key (required for conversation generation)
- Anthropic API key (optional, for Claude-powered features)

### Backend Setup (hirecj-data)

```bash
cd hirecj-data

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY and ANTHROPIC_API_KEY

# Initialize database
make db-init

# Start the API server (port 8000) - REQUIRED for all functionality
make dev
```

### Frontend Setup (hirecj-homepage)

```bash
cd hirecj-homepage

# Install dependencies
npm install

# Start development server (port 3456)
npm run dev
```

### Running the Complete System

1. **Start the backend API server** (port 8000) - REQUIRED
   ```bash
   cd hirecj-data
   make dev
   ```
2. Start the frontend dev server (port 3456)
   ```bash
   cd hirecj-homepage
   npm run dev
   ```
3. Navigate to http://localhost:3456
4. Click "Chat with CJ" to experience the demo

## 🎯 Key Features

### Backend Capabilities
- **Synthetic Conversation Generation**: Create realistic merchant-CJ interactions for training
- **Multi-Agent System**: Uses CrewAI for orchestrating merchant personas and CJ responses
- **Universe Data**: Pre-generated business scenarios with customers, tickets, and metrics
- **RESTful API**: Comprehensive endpoints for all functionality
- **WebSocket Support**: Real-time chat with progress updates
- **Fact-Checking**: Verify CJ's claims against universe data
- **Conversation Management**: Auto-save and retrieval of chat sessions

### Frontend Features
- **LinkedIn-Style Profile**: Professional landing page for HireCJ
- **Interactive Chat Demo**: Live conversation with CJ
- **Scenario Selection**: Choose from pre-generated business contexts
- **Real-time Updates**: See CJ "thinking" with progress indicators
- **Mobile Responsive**: Works on all devices

## 📚 Documentation

### Backend Documentation
- [API Documentation](hirecj-data/API.md) - Complete API reference
- [Quick Start Guide](hirecj-data/QUICKSTART.md) - Get running quickly
- [Architecture Overview](hirecj-data/README.md) - Detailed backend documentation

### Frontend Documentation
- [Chat Integration Plan](hirecj-homepage/CHAT_INTEGRATION.md) - Roadmap for chat features
- [Frontend README](hirecj-homepage/README.md) - Frontend-specific setup

### Integration Analysis
- [Integration Plan](plan.md) - Detailed analysis of backend/frontend divergences

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI (Python)
- **AI Orchestration**: CrewAI
- **LLM Integration**: LiteLLM (not LangChain)
- **Models**: GPT-4, Claude 3.5 Sonnet  
- **API Client**: Unified ConversationAPI with WebSocket support
- **Testing**: Pytest with YAML-driven test framework
- **Data Storage**: File-based (dev), PostgreSQL ready

### Frontend
- **Framework**: React 18 with TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: shadcn/ui, Radix UI
- **Server**: Express.js
- **Build Tool**: Vite
- **WebSocket**: Native WebSocket API

## 🎮 Demo Scenarios

The system includes several pre-generated scenarios:

### Available Merchants
- **Marcus Thompson** (Thompson Craft BBQ) - Direct, numbers-focused, stressed founder
- **Zoe Martinez** (Cosmic Candles) - Creative, optimistic, emoji-loving founder

### Business Scenarios
- **Steady Operations** - Normal business, manageable support volume
- **Growth Stall** - Plateaued growth, rising CAC, moderate stress
- **Memorial Day Weekend** - Holiday rush, high ticket volume

## 🧪 Testing

### Backend Testing
```bash
cd hirecj-data
make test               # Run all tests
make test-conversation  # Test conversation generation
make test-cj           # Test CJ responses with GPT-4 evaluation
```

### Frontend Testing
```bash
cd hirecj-homepage
npm run check          # TypeScript type checking
npm test              # Run test suite (if configured)
```

## 🚦 Current Status

### ✅ What's Working
- **Unified API-based architecture** - All conversation functionality routes through the API server
- Backend conversation generation with CrewAI
- Frontend marketing site with chat UI
- WebSocket communication with real-time updates
- Scenario selection from available universes
- Real-time progress updates during CJ responses
- Fact-checking API integration
- Context persistence across messages in a conversation

### 🚧 In Progress
- Fact-checking UI implementation
- Annotation persistence
- Conversation history viewing

### 📋 Planned
- Authentication system
- Production deployment setup
- Performance optimizations

## 🏛️ Architecture Notes

### Unified API Architecture (As of 2025-05-29)
The project now uses a **unified API-based architecture**:
- All conversation functionality is accessed through the API server running on port 8000
- The `ConversationAPI` client handles WebSocket connections with proper event loop management
- No more conditional imports or `USE_API_ADAPTER` flags
- Context persistence is maintained across messages within a conversation session

### Key Components:
- **API Server**: `src/api/server.py` - Handles all WebSocket and REST endpoints
- **ConversationAPI**: `app/clients/conversation_api.py` - Unified client for all conversation operations
- **ConversationBridge**: `src/services/conversation_bridge.py` - Bridges WebSocket to CrewAI agents

## 🤝 Contributing

This project uses a YAML-first architecture for the backend:
- All prompts, scenarios, and configurations must be in YAML files
- No hardcoded values in code
- Use the existing test framework for new features
- Follow the established patterns in both frontend and backend

### Design Philosophy
- **Simplify, Simplify, Simplify**: Don't add features we don't need yet, but don't remove existing functionality
- **Keep What's Needed**: Preserve all requirements and features that serve a purpose
- **No Over-Engineering**: Build for current needs, not hypothetical futures

## 📄 License

[License details to be added]

## 🆘 Support

For issues or questions:
- Check the [Integration Plan](plan.md) for known issues
- Review API documentation for endpoint details
- Open an issue in the repository

---

Built with ❤️ for e-commerce founders who need a better way to handle customer support.