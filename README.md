# HireCJ

HireCJ is an AI-powered customer support agent platform that provides intelligent, context-aware customer service automation.

## Overview

HireCJ consists of multiple specialized components working together to deliver exceptional customer support experiences:

- **AI Agents**: Intelligent conversational agents that understand context and provide personalized responses
- **Knowledge Base**: Comprehensive knowledge management system for accurate information retrieval
- **Web Platform**: User-friendly interface for managing conversations and monitoring performance
- **Analytics**: Real-time insights into customer interactions and agent performance

## Architecture

This is a monorepo containing several specialized applications:

```
hirecj/
├── hirecj-agents/          # Core AI agent backend
├── hirecj-homepage/        # Frontend web application  
├── hirecj-knowledge/       # Knowledge base management
└── third-party/           # External dependencies and tools
```

## Key Features

- 🤖 **Intelligent AI Agents** - Context-aware conversational AI
- 📚 **Knowledge Management** - Centralized knowledge base with smart retrieval
- 🎯 **Personalization** - Tailored responses based on customer context
- 📊 **Analytics** - Comprehensive performance monitoring
- 🔧 **Easy Integration** - Simple API for existing systems
- 🚀 **Scalable** - Built for enterprise-grade performance

## Getting Started

Each component has its own setup instructions:

1. **AI Agents Backend**: See `hirecj-agents/README.md`
2. **Web Frontend**: See `hirecj-homepage/README.md`  
3. **Knowledge Base**: See `hirecj-knowledge/README.md`

## Development

### Quick Start

```bash
# 1. Set up your environment (ONE file to configure!)
make env-setup
# Edit .env with your configuration

# 2. Install dependencies
make install

# 3. Start development (auto-distributes env vars)
make dev
```

### All Development Commands

```bash
# Install dependencies for all components
make install

# Start all services in development mode
make dev

# Run tests across all components
make test

# Start with ngrok tunnels (recommended for OAuth testing)
make dev-tunnels-tmux
```

### Important Development Notes

- **🔑 Environment Setup**: See [Single .env Guide](SINGLE_ENV_GUIDE.md) - You only manage ONE .env file!
- **Legacy Docs**: [Environment Configuration Setup](README_ENV_SETUP.md) (being phased out)
- **Tunnel Setup**: See [Ngrok Setup Guide](NGROK_SETUP.md) for HTTPS development
- **Recent Changes**: See [Development Environment Changes](docs/DEV_ENVIRONMENT_CHANGES.md) for OAuth and debug features

### Database Setup (Phase 4.5+)

For user identity and persistence features, run the database migration:

```bash
# Ensure IDENTITY_DATABASE_URL is set in your .env
psql $IDENTITY_DATABASE_URL -f agents/app/migrations/003_user_identity.sql
```

See [Migration Guide](./agents/app/migrations/README.md) for detailed instructions.

## License

Copyright © 2025 Cratejoy, Inc. All rights reserved.

## Support

For questions or support, please contact the development team.