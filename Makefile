# HireCJ Monorepo Makefile
# Orchestrates all services from the root

.PHONY: help install dev test deploy-all clean

# Default target
help:
	@echo "HireCJ Development Commands:"
	@echo "  make install      - Install all dependencies"
	@echo "  make dev          - Start all services locally"
	@echo "  make test         - Run all tests"
	@echo "  make deploy-all   - Deploy all services to Heroku"
	@echo ""
	@echo "Service-specific commands:"
	@echo "  make dev-auth     - Start auth service only"
	@echo "  make dev-agents   - Start agents service only"
	@echo "  make dev-homepage - Start homepage service only"
	@echo "  make test-auth    - Test auth service"
	@echo "  make test-agents  - Test agents service"
	@echo "  make deploy-auth  - Deploy auth to Heroku"
	@echo "  make deploy-agents - Deploy agents to Heroku"

# Install all dependencies
install:
	@echo "📦 Installing all dependencies..."
	cd auth && python -m venv venv && . venv/bin/activate && pip install -r requirements.txt
	cd agents && python -m venv venv && . venv/bin/activate && pip install -r requirements.txt
	cd database && python -m venv venv && . venv/bin/activate && pip install -r requirements.txt
	cd knowledge && python -m venv venv && . venv/bin/activate && pip install -r requirements.txt
	cd homepage && npm install
	@echo "✅ All dependencies installed!"

# Development commands
dev:
	@echo "🚀 Starting development environment..."
	@echo "Prerequisites: PostgreSQL and Redis must be running locally"
	@echo ""
	@echo "Start services in separate terminals:"
	@echo "  Terminal 1: make dev-agents"
	@echo "  Terminal 2: make dev-homepage"
	@echo "  Terminal 3: make dev-auth (if needed)"
	@echo ""
	@echo "Or use: make dev-all (requires tmux)"

dev-all:
	@echo "🚀 Starting all services with tmux..."
	@command -v tmux >/dev/null 2>&1 || { echo "tmux is required but not installed. Install with: brew install tmux"; exit 1; }
	tmux new-session -d -s hirecj-dev
	tmux send-keys -t hirecj-dev:0 'make dev-agents' C-m
	tmux new-window -t hirecj-dev:1 -n homepage
	tmux send-keys -t hirecj-dev:1 'make dev-homepage' C-m
	tmux new-window -t hirecj-dev:2 -n auth
	tmux send-keys -t hirecj-dev:2 'make dev-auth' C-m
	tmux attach -t hirecj-dev

dev-auth:
	@echo "🔐 Starting auth service..."
	cd auth && . venv/bin/activate && python -m app.main

dev-agents:
	@echo "🤖 Starting agents service..."
	cd agents && . venv/bin/activate && python -m app.main

dev-homepage:
	@echo "🌐 Starting homepage..."
	cd homepage && npm run dev

dev-database:
	@echo "💾 Starting database service..."
	cd database && . venv/bin/activate && python -m app.main

# Stop all services
stop:
	@echo "🛑 Stopping all services..."
	@if tmux has-session -t hirecj-dev 2>/dev/null; then \
		tmux kill-session -t hirecj-dev; \
		echo "✅ Stopped tmux session"; \
	fi

# Testing commands
test:
	@echo "🧪 Running all tests..."
	make test-auth
	make test-agents
	make test-database
	make test-homepage

test-auth:
	@echo "🧪 Testing auth service..."
	cd auth && . venv/bin/activate && pytest

test-agents:
	@echo "🧪 Testing agents service..."
	cd agents && . venv/bin/activate && pytest

test-database:
	@echo "🧪 Testing database service..."
	cd database && . venv/bin/activate && pytest

test-homepage:
	@echo "🧪 Testing homepage..."
	cd homepage && npm test

# Deployment commands
deploy-all:
	@echo "🚀 Deploying all services..."
	make deploy-auth
	make deploy-agents
	make deploy-homepage
	make deploy-database

deploy-auth:
	@echo "🚀 Deploying auth service to Heroku..."
	git subtree push --prefix auth heroku-auth main

deploy-agents:
	@echo "🚀 Deploying agents service to Heroku..."
	git subtree push --prefix agents heroku-agents main

deploy-homepage:
	@echo "🚀 Deploying homepage to Heroku..."
	git subtree push --prefix homepage heroku-homepage main

deploy-database:
	@echo "🚀 Deploying database service to Heroku..."
	git subtree push --prefix database heroku-database main

# Heroku setup (one-time)
heroku-setup:
	@echo "🔧 Setting up Heroku remotes..."
	git remote add heroku-auth https://git.heroku.com/hirecj-auth.git
	git remote add heroku-agents https://git.heroku.com/hirecj-agents.git
	git remote add heroku-homepage https://git.heroku.com/hirecj-homepage.git
	git remote add heroku-database https://git.heroku.com/hirecj-database.git

# Logs
logs-auth:
	heroku logs --tail --app hirecj-auth

logs-agents:
	heroku logs --tail --app hirecj-agents

logs-homepage:
	heroku logs --tail --app hirecj-homepage

# Database management
db-migrate:
	@echo "🔄 Running database migrations..."
	cd database && . venv/bin/activate && alembic upgrade head

db-reset:
	@echo "⚠️  Resetting database..."
	@echo "Please manually reset your local PostgreSQL database"
	make db-migrate

# Utilities
clean:
	@echo "🧹 Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "venv" -exec rm -rf {} +
	find . -type d -name "node_modules" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".DS_Store" -delete

# Environment setup
env-setup:
	@echo "📝 Setting up environment files..."
	cp .env.example .env
	cp auth/.env.example auth/.env
	cp agents/.env.example agents/.env
	cp homepage/.env.example homepage/.env
	cp database/.env.example database/.env
	@echo "✅ Environment files created. Please update them with your values."