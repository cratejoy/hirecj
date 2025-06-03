# CJ - Cratejoy's Autonomous CX & Growth Officer

## Overview

This project is a web application for "CJ", a fictional AI-powered customer experience and growth officer for Cratejoy. The application showcases CJ's capabilities through an interactive LinkedIn-style profile page with a chat interface that demonstrates the AI assistant's functionality.

The application is built using a modern stack:
- Frontend: React with TypeScript, Tailwind CSS, shadcn/ui components
- Backend: Express.js server
- Database: PostgreSQL (using Drizzle ORM)
- Build tools: Vite

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture

The frontend is a single-page React application built with TypeScript. It uses:

1. **Component Structure**: Modular components following a clear hierarchy
2. **Styling**: Tailwind CSS with shadcn/ui component library for consistent design
3. **State Management**: React hooks for local state, React Query for server state
4. **Routing**: Simple routing with Wouter
5. **Animations**: Framer Motion for smooth transitions and effects

The UI is designed to mimic a professional LinkedIn profile with a custom chat interface that showcases the AI assistant's capabilities.

### Backend Architecture

The backend is a Node.js Express server that:

1. Serves the static frontend assets in production
2. Provides API endpoints for the chat functionality and lead capture
3. Manages database interactions through Drizzle ORM
4. Handles session management for the chat

### Database Architecture

The database schema (PostgreSQL) includes tables for:

1. `users`: Authentication and user management
2. `leads`: Potential customers who engage with the chat
3. `chat_messages`: Message history between leads and the AI assistant

## Key Components

### Frontend Components

1. **Profile Sections**:
   - Hero component with profile summary
   - AboutSection displaying CJ's background
   - ExperienceSection showing work history
   - SkillsSection highlighting capabilities
   - RecommendationsSection with testimonials
   - WhatIDoSection listing services
   - FAQSection answering common questions
   - CTASection for conversion

2. **Chat Interface**:
   - ChatPill: Floating button to initiate chat
   - ChatDrawer: Slide-in panel for the conversation
   - EmailCaptureModal: Form to collect lead information

3. **UI Components**:
   - Extensive library of UI components from shadcn/ui
   - Custom components built on Radix UI primitives

### Backend Components

1. **API Routes**:
   - Chat endpoints for message handling
   - Lead capture endpoints
   - User authentication (not fully implemented)

2. **Storage Interface**:
   - Database abstraction layer for CRUD operations
   - Memory-based implementation for development

## Data Flow

1. **Chat Interaction**:
   - User clicks the ChatPill to initiate conversation
   - ChatDrawer opens, showing initial greeting from CJ
   - User sends messages, server responds with appropriate responses
   - After meaningful engagement, EmailCaptureModal collects lead information
   - Lead and conversation data are stored in the database

2. **Profile Browsing**:
   - User scrolls through the profile sections
   - Animations trigger as sections come into view
   - Interactive elements respond to user interaction

## External Dependencies

The application relies on several key external libraries:

1. **UI and Styling**:
   - Tailwind CSS for styling
   - shadcn/ui and Radix UI for components
   - Framer Motion for animations

2. **Data Management**:
   - React Query for server state management
   - Drizzle ORM for database interactions
   - Zod for schema validation

3. **Development Tools**:
   - Vite for building and development
   - TypeScript for type safety
   - ESBuild for production builds

## Deployment Strategy

The application is configured for deployment on Replit with:

1. **Build Process**:
   - The frontend is built using Vite
   - The server code is bundled with ESBuild
   - Static assets are served by the Express server

2. **Database**:
   - PostgreSQL for data persistence
   - Connection via environment variables

3. **Environment Configuration**:
   - Development mode with hot reloading
   - Production mode for optimized performance

## Development Workflow

To work on this project:

1. Run `npm run dev` to start the development server
2. Frontend code is in `client/src/`
3. Backend API routes are in `server/routes.ts`
4. Database schema is defined in `shared/schema.ts`
5. Run `npm run db:push` to apply schema changes to the database

The application uses a combined workflow where the Express server also serves as a development server for the frontend during development.