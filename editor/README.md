# HireCJ Agent Editor

A visual interface for building, testing, and refining AI agents for the HireCJ platform.

## Overview

The Agent Editor provides a unified environment to:
- Test agent conversations in the Playground
- Create and manage user personas
- Edit system prompts with version control
- Design conversation workflows visually
- Configure agent tools and functions

## Getting Started

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start the editor backend (in a separate terminal):
   ```bash
   cd ../editor-backend
   make dev
   ```

3. Start the editor frontend:
   ```bash
   npm run dev
   ```

4. Open http://localhost:3458 in your browser

## Features

### Playground View
- Split-pane interface for testing conversations
- Real-time workflow and prompt editing
- Merchant persona simulation
- Feedback buttons for AI-driven improvements

### User Personas Editor
- Create realistic merchant personas
- Configure communication styles and business metrics
- Test agents against different merchant types

### System Prompts Editor
- Version-controlled prompt management
- Variable/placeholder support
- Category and status organization

### Workflow Editor
- Visual workflow designer
- Drag-and-drop step management
- Decision nodes and branching logic
- Step configuration panel

### Tool Editor
- API endpoint configuration
- Parameter definition
- Response handling setup
- Authentication configuration

## Architecture

- **React 18** with TypeScript
- **Vite** for fast development
- **Tailwind CSS** for styling
- **Radix UI** for accessible components
- **Wouter** for client-side routing

## File Structure

```
editor/
├── src/
│   ├── components/     # Reusable UI components
│   ├── layouts/        # Page layouts
│   ├── views/          # Main editor views
│   ├── lib/            # Utilities and mock data
│   └── App.tsx         # Main app component
├── public/             # Static assets
└── package.json        # Dependencies
```

## Development

The editor consists of two parts:
- **Frontend**: React/Vite application running on port 3458
- **Backend**: FastAPI service running on port 8001 (separate from agent service)

### Running Both Services

From the root directory:
```bash
# Terminal 1: Start editor backend
make dev-editor-backend

# Terminal 2: Start editor frontend  
make dev-editor
```

Or use tmux to run everything:
```bash
make dev-all
```

### API Integration

The frontend communicates with the backend via:
- Direct API calls to `http://localhost:8001/api/v1/*`
- Vite proxy configuration for development
- CORS is configured to allow the frontend origin