# HireCJ Monorepo Makefile
# Orchestrates all services from the root

.PHONY: help install dev test deploy-all clean

# Default target
help:
	@echo "HireCJ Development Commands:"
	@echo ""
	@echo "🔑 Environment Management (Single .env pattern):"
	@echo "  make env-setup    - Create .env from template (ONE file to manage!)"
	@echo "  make env-distribute - Distribute variables to services (auto-run by dev)"
	@echo "  make env-verify   - Verify single .env pattern is working"
	@echo "  make env-cleanup  - Remove old service .env files"
	@echo ""
	@echo "🚀 Development:"
	@echo "  make install      - Install all dependencies"
	@echo "  make dev          - Start all services locally (auto-distributes env)"
	@echo "  make dev-all      - Start all services with tmux"
	@echo "  make test         - Run all tests"
	@echo ""
	@echo "🌐 Tunnel commands (for HTTPS development):"
	@echo "  make dev-tunnels-tmux - Start everything with tunnels (recommended)"
	@echo "  make tunnels      - Start ngrok tunnels"
	@echo "  make detect-tunnels - Auto-detect tunnel URLs"
	@echo ""
	@echo "📦 Service-specific commands:"
	@echo "  make dev-auth     - Start auth service only"
	@echo "  make dev-agents   - Start agents service only"
	@echo "  make dev-homepage - Start homepage service only"
	@echo "  make dev-editor-backend - Start editor backend service only"
	@echo "  make dev-editor   - Start editor frontend only"
	@echo "  make dev-knowledge - Start knowledge service only"
	@echo "  make test-auth    - Test auth service"
	@echo "  make test-agents  - Test agents service"
	@echo ""
	@echo "🚢 Deployment:"
	@echo "  make deploy-all   - Deploy all services to Heroku"
	@echo "  make deploy-auth  - Deploy auth to Heroku"
	@echo "  make deploy-agents - Deploy agents to Heroku"
	@echo ""
	@echo "🗄️ Database commands (agents service):"
	@echo "  make clear-db     - Clear all data from agents database"
	@echo "  make fill-db      - Fill database with migrations and test data"
	@echo "  make reset-db     - Clear and refill agents database"
	@echo "  make migrate-agents - Run agents database migrations"
	@echo ""
	@echo "🧪 Evaluation System:"
	@echo "  make evals        - Interactive eval menu (recommended)"
	@echo "  make evals-test   - Quick test to verify setup"
	@echo "  make evals-again  - Re-run last evaluation"
	@echo "  make evals-today  - Eval conversations from today"
	@echo "  make evals-all    - Run all evaluations on today's conversations"
	@echo "  make evals-history - View recent eval runs"
	@echo ""
	@echo "🔧 Development tools:"
	@echo "  make generate-protocol - Generate TypeScript types from Pydantic models"
	@echo ""
	@echo "🔄 Freshdesk sync commands:"
	@echo "  make sync-freshdesk - Sync all Freshdesk data"
	@echo "  make test-freshdesk-sync - Test the sync functionality"

# Install all dependencies
install:
	@echo "📦 Installing all dependencies..."
	cd auth && python -m venv venv && . venv/bin/activate && pip install -r requirements.txt
	cd agents && python -m venv venv && . venv/bin/activate && pip install -r requirements.txt -r requirements-dev.txt
	cd database && python -m venv venv && . venv/bin/activate && pip install -r requirements.txt
	cd knowledge && python -m venv venv && . venv/bin/activate && pip install -r requirements.txt
	cd editor-backend && python -m venv venv && . venv/bin/activate && pip install -r requirements.txt
	cd homepage && npm install
	cd editor && npm install
	@echo "✅ All dependencies installed!"

# Development commands
dev: env-distribute
	@echo "🚀 Starting development environment..."
	@echo "Prerequisites: PostgreSQL and Redis must be running locally"
	@echo ""
	@echo "✅ Environment variables distributed to services"
	@echo ""
	@echo "Start services in separate terminals:"
	@echo "  Terminal 1: make dev-agents"
	@echo "  Terminal 2: make dev-homepage"
	@echo "  Terminal 3: make dev-auth (if needed)"
	@echo ""
	@echo "Or use: make dev-all (requires tmux)"

dev-all: env-distribute
	@echo "🚀 Starting all services with tmux..."
	@command -v tmux >/dev/null 2>&1 || { echo "tmux is required but not installed. Install with: brew install tmux"; exit 1; }
	@if tmux has-session -t hirecj-dev 2>/dev/null; then \
		echo "Session hirecj-dev already exists, killing it..."; \
		tmux kill-session -t hirecj-dev; \
	fi
	tmux new-session -d -s hirecj-dev
	tmux send-keys -t hirecj-dev:0 'make dev-agents' C-m
	tmux new-window -t hirecj-dev:1 -n homepage
	tmux send-keys -t hirecj-dev:1 'make dev-homepage' C-m
	tmux new-window -t hirecj-dev:2 -n auth
	tmux send-keys -t hirecj-dev:2 'make dev-auth' C-m
	tmux new-window -t hirecj-dev:3 -n editor-backend
	tmux send-keys -t hirecj-dev:3 'make dev-editor-backend' C-m
	tmux new-window -t hirecj-dev:4 -n editor
	tmux send-keys -t hirecj-dev:4 'make dev-editor' C-m
	tmux new-window -t hirecj-dev:5 -n tool-calls
	tmux send-keys -t hirecj-dev:5 'tail -f logs/tool_calls.log' C-m
	@if [ -z "$$TMUX" ]; then \
		tmux attach -t hirecj-dev; \
	else \
		echo "Already in tmux. Use 'tmux switch -t hirecj-dev' to switch to the new session"; \
	fi

dev-services: env-distribute
	@echo "🚀 Starting all services..."
	@echo "This will start services in separate processes"
	@echo ""
	@echo "✅ Environment variables distributed to services"
	@echo ""
	@echo "Starting agents on port 8100..."
	@cd agents && . venv/bin/activate && python -m app.main &
	@echo "Starting homepage on port 3456..."
	@cd homepage && npm run dev &
	@echo ""
	@echo "Services are starting in the background."
	@echo "Press Ctrl+C to stop all services."
	@wait

dev-auth: env-distribute
	@echo "🔐 Starting auth service..."
	cd auth && . venv/bin/activate && python -m app.main

dev-agents: env-distribute
	@echo "🤖 Starting agents service with file watcher..."
	cd agents && . venv/bin/activate && python scripts/dev_watcher.py

dev-agents-debug: env-distribute
	@echo "🤖 Starting agents service with file watcher (DEBUG mode)..."
	cd agents && . venv/bin/activate && python scripts/dev_watcher.py --debug

dev-homepage: env-distribute
	@echo "🌐 Starting homepage..."
	cd homepage && npm run dev

dev-database: env-distribute
	@echo "💾 Starting database service..."
	cd database && . venv/bin/activate && python -m app.main

dev-editor-backend: env-distribute
	@echo "🔧 Starting editor backend service with hot reload..."
	cd editor-backend && . venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

dev-editor: env-distribute
	@echo "🎨 Starting editor frontend..."
	cd editor && npm run dev

dev-knowledge: env-distribute
	@echo "🧠 Starting knowledge service..."
	@cd knowledge && venv/bin/python scripts/run_api_server.py

# Stop all services
stop:
	@echo "🛑 Stopping all services..."
	@if tmux has-session -t hirecj-dev 2>/dev/null; then \
		tmux kill-session -t hirecj-dev; \
		echo "✅ Stopped hirecj-dev session"; \
	fi
	@if tmux has-session -t hirecj-tunnels 2>/dev/null; then \
		tmux kill-session -t hirecj-tunnels; \
		echo "✅ Stopped hirecj-tunnels session"; \
	fi

# Clean up ports
clean-ports:
	@echo "🧹 Cleaning up ports..."
	@lsof -ti:8100 | xargs kill -9 2>/dev/null || echo "Port 8100 clear"
	@lsof -ti:8103 | xargs kill -9 2>/dev/null || echo "Port 8103 clear"
	@lsof -ti:8002 | xargs kill -9 2>/dev/null || echo "Port 8002 clear"
	@lsof -ti:8001 | xargs kill -9 2>/dev/null || echo "Port 8001 clear"
	@lsof -ti:8004 | xargs kill -9 2>/dev/null || echo "Port 8004 clear"
	@lsof -ti:3456 | xargs kill -9 2>/dev/null || echo "Port 3456 clear"
	@lsof -ti:3458 | xargs kill -9 2>/dev/null || echo "Port 3458 clear"
	@echo "✅ All ports cleaned"

# Stop tunnels and services
stop-tunnels:
	@echo "🛑 Stopping tunnel session..."
	@if tmux has-session -t hirecj-tunnels 2>/dev/null; then \
		tmux kill-session -t hirecj-tunnels; \
		echo "✅ Stopped hirecj-tunnels session (ngrok + services)"; \
	else \
		echo "No tunnel session running"; \
	fi
	@sleep 1

kill-ports:
	@echo "🧹 Killing processes on HireCJ service ports..."
	@bash scripts/kill-ports.sh
	@make clean-ports

# Tunnel management
tunnels:
	@echo "🌐 Starting ngrok tunnels..."
	@if ! grep -q "NGROK_AUTHTOKEN=" .env 2>/dev/null || [ -z "$$(grep NGROK_AUTHTOKEN= .env | cut -d= -f2)" ]; then \
		echo "❌ Error: NGROK_AUTHTOKEN not found in .env"; \
		echo ""; \
		echo "Please add your ngrok authtoken to .env:"; \
		echo "  NGROK_AUTHTOKEN=your-token-here"; \
		echo ""; \
		echo "Get your token from: https://dashboard.ngrok.com/get-started/your-authtoken"; \
		exit 1; \
	fi
	@if [ ! -f ngrok.yml ]; then \
		echo "Creating ngrok.yml from template..."; \
		cp ngrok.yml.example ngrok.yml; \
	fi
	@echo "Starting ngrok (this will block - use Ctrl+C to stop)..."
	@echo ""
	@bash -c 'source .env && ngrok start --all --config ngrok.yml --authtoken $$NGROK_AUTHTOKEN'

# Detect tunnels (run in separate terminal)
detect-tunnels:
	@echo "🔍 Detecting tunnel URLs..."
	@python shared/detect_tunnels.py

# Development with tunnels (recommended workflow)
dev-tunnels:
	@echo "🚀 Development with tunnels:"
	@echo ""
	@echo "1. Terminal 1: make tunnels"
	@echo "2. Terminal 2: make detect-tunnels" 
	@echo "3. Terminal 3: make dev-all"
	@echo ""
	@echo "Or use tmux: make dev-tunnels-tmux"

# All-in-one with tmux
dev-tunnels-tmux: env-distribute
	@command -v tmux >/dev/null 2>&1 || { echo "tmux required: brew install tmux"; exit 1; }
	@if tmux has-session -t hirecj-tunnels 2>/dev/null; then \
		echo "❌ Error: hirecj-tunnels session is already running!"; \
		echo ""; \
		echo "You can:"; \
		echo "  1. Attach to it: tmux attach -t hirecj-tunnels"; \
		echo "  2. Stop it first: make stop-tunnels"; \
		echo ""; \
		echo "Then run this command again."; \
		exit 1; \
	fi
	@echo "🧹 Cleaning up any existing services on ports..."
	@bash scripts/kill-ports.sh
	@if ! grep -q "NGROK_AUTHTOKEN=" .env 2>/dev/null || [ -z "$$(grep NGROK_AUTHTOKEN= .env | cut -d= -f2)" ]; then \
		echo "❌ Error: NGROK_AUTHTOKEN not found in .env"; \
		echo ""; \
		echo "Please add your ngrok authtoken to .env:"; \
		echo "  NGROK_AUTHTOKEN=your-token-here"; \
		echo ""; \
		echo "Get your token from: https://dashboard.ngrok.com/get-started/your-authtoken"; \
		exit 1; \
	fi
	@tmux new-session -d -s hirecj-tunnels -n urls
	@tmux send-keys -t hirecj-tunnels:0 'sleep 2 && make detect-tunnels && echo "" && echo "✅ Tunnels configured! Service URLs are shown above." && echo "" && echo "Press Ctrl+b then a number to switch windows:" && echo "  0 - This URL list" && echo "  1 - Ngrok tunnels" && echo "  2 - Agents service" && echo "  3 - Auth service" && echo "  4 - Database service" && echo "  5 - Homepage" && echo "  6 - Editor backend" && echo "  7 - Editor frontend" && echo "  8 - Knowledge service" && echo "  9 - Tool calls" && echo "  10 - Logs" && echo ""' C-m
	@tmux new-window -t hirecj-tunnels:1 -n ngrok
	@tmux send-keys -t hirecj-tunnels:1 'make tunnels' C-m
	@tmux new-window -t hirecj-tunnels:2 -n agents
	@tmux send-keys -t hirecj-tunnels:2 'sleep 3 && make dev-agents' C-m
	@tmux new-window -t hirecj-tunnels:3 -n auth
	@tmux send-keys -t hirecj-tunnels:3 'sleep 3 && make dev-auth' C-m
	@tmux new-window -t hirecj-tunnels:4 -n database  
	@tmux send-keys -t hirecj-tunnels:4 'sleep 3 && make dev-database' C-m
	@tmux new-window -t hirecj-tunnels:5 -n homepage  
	@tmux send-keys -t hirecj-tunnels:5 'sleep 3 && make dev-homepage' C-m
	@tmux new-window -t hirecj-tunnels:6 -n editor-backend
	@tmux send-keys -t hirecj-tunnels:6 'sleep 3 && make dev-editor-backend' C-m
	@tmux new-window -t hirecj-tunnels:7 -n editor-frontend  
	@tmux send-keys -t hirecj-tunnels:7 'sleep 3 && make dev-editor' C-m
	@tmux new-window -t hirecj-tunnels:8 -n knowledge
	@tmux send-keys -t hirecj-tunnels:8 'sleep 3 && make dev-knowledge' C-m
	@tmux new-window -t hirecj-tunnels:9 -n tool-calls
	@tmux send-keys -t hirecj-tunnels:9 'sleep 5 && tail -f logs/tool_calls.log' C-m
	@tmux new-window -t hirecj-tunnels:10 -n logs
	@tmux send-keys -t hirecj-tunnels:10 'sleep 10 && find agents/logs auth/logs homepage/logs database/logs editor/logs knowledge/logs -name "*.log" -type f 2>/dev/null | xargs tail -f' C-m
	@tmux select-window -t hirecj-tunnels:0
	@tmux attach -t hirecj-tunnels

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

# Heroku logs
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

# HireCJ Data Database Management (agents service)
clear-db:
	@echo "⚠️  WARNING: This will delete all data from the agents database!"
	@echo "Press Ctrl+C to cancel, or wait 3 seconds to continue..."
	@sleep 3
	cd agents && . venv/bin/activate && python scripts/clear_database.py --force

fill-db:
	@echo "🚀 Filling agents database with fresh data..."
	cd agents && . venv/bin/activate && python scripts/fill_database.py

reset-db: clear-db fill-db
	@echo "✨ Agents database reset complete!"

# Run migrations for agents database
migrate-agents:
	@echo "🔄 Running agents database migrations..."
	cd agents && . venv/bin/activate && python scripts/run_migration.py

# Evaluation System
.PHONY: evals evals-test evals-again evals-today evals-all evals-history evals-list evals-results evals-convert

# Main interactive interface
evals:
	@python scripts/evals_cli.py

# Quick test to verify everything works
evals-test:
	@python scripts/evals_cli.py test

# Re-run the last evaluation  
evals-again:
	@python scripts/evals_cli.py again

# Evaluate conversations from today
evals-today:
	@echo "📊 Evaluating today's conversations..."
	@python scripts/evals_cli.py convert && python scripts/evals_cli.py again

# Run all evaluations on today's conversations
evals-all:
	@echo "📊 Running all evaluations..."
	@python scripts/evals_cli.py all

# View evaluation history
evals-history:
	@python scripts/evals_cli.py history

# List all available evaluations
evals-list:
	@python scripts/evals_cli.py list

# Jump to results viewer
evals-results:
	@python scripts/evals_cli.py history

# Convert conversations to eval format
evals-convert:
	@python scripts/evals_cli.py convert

# Generate TypeScript types from protocol
generate-protocol:
	@echo "🔧 Generating TypeScript types from Pydantic models..."
	@chmod +x shared/protocol/generate.sh
	@./shared/protocol/generate.sh
	@echo "✅ TypeScript types generated in homepage/src/protocol/"

# Sync Freshdesk data
sync-freshdesk:
	@echo "🔄 Syncing Freshdesk data (all components)..."
	cd agents && . venv/bin/activate && python scripts/sync_freshdesk.py


sync-conversations:
	@echo "💬 Syncing Freshdesk conversations for specific tickets..."
	@echo "Usage: make sync-conversations TICKETS='ticket_id1 ticket_id2'"
	cd agents && . venv/bin/activate && python scripts/sync_freshdesk.py --conversations-for $(TICKETS)

sync-ratings:
	@echo "⭐ Syncing Freshdesk ratings only..."
	@echo "Note: Ratings are synced as part of the regular sync"
	cd agents && . venv/bin/activate && python scripts/sync_freshdesk.py

test-freshdesk-sync:
	@echo "🧪 Testing Freshdesk sync functionality..."
	cd agents && . venv/bin/activate && python scripts/test_freshdesk_sync.py

# Utilities
clean:
	@echo "🧹 Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "venv" -exec rm -rf {} +
	find . -type d -name "node_modules" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".DS_Store" -delete

# Environment setup - Phase 4.0: Single .env pattern
env-setup:
	@echo "📝 Setting up THE environment file..."
	@if [ ! -f .env ]; then \
		cp .env.master.example .env; \
		echo "✅ Created .env from .env.master.example"; \
		echo "📝 Edit .env with your configuration"; \
		echo ""; \
		echo "⚠️  IMPORTANT: You only need to edit this ONE file!"; \
	else \
		echo "✅ .env already exists"; \
	fi

# Clean up old environment files
env-cleanup:
	@echo "🧹 Cleaning old environment files..."
	@./scripts/cleanup_old_env.sh

# Distribute environment variables to services
env-distribute:
	@echo "📦 Distributing environment variables to services..."
	@python scripts/distribute_env.py

# Verify single env pattern
env-verify:
	@echo "🔍 Verifying single .env pattern..."
	@python scripts/verify_single_env.py
