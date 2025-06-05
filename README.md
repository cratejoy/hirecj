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

For local development across all components:

```bash
# Install dependencies for all components
make install-all

# Start all services in development mode
make dev

# Run tests across all components
make test-all

# Start with ngrok tunnels (recommended for OAuth testing)
make dev-tunnels-tmux
```

### Important Development Notes

- **Environment Setup**: See [Environment Configuration Setup](README_ENV_SETUP.md)
- **Tunnel Setup**: See [Ngrok Setup Guide](NGROK_SETUP.md) for HTTPS development
- **Recent Changes**: See [Development Environment Changes](docs/DEV_ENVIRONMENT_CHANGES.md) for OAuth and debug features

## License

Copyright © 2025 Cratejoy, Inc. All rights reserved.

## Support

For questions or support, please contact the development team.