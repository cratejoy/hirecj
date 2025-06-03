.PHONY: help install dev dev-noreload dev-tunnel run test lint clean db-up db-down db-upgrade
.PHONY: tunnel tunnel-status tunnel-info setup-tunnel

# Default target
help:
	@echo "HireCJ Auth Service Commands:"
	@echo ""
	@echo "📦 Setup:"
	@echo "  make install       - Install dependencies"
	@echo "  make setup-tunnel  - Configure ngrok tunnel (first time)"
	@echo ""
	@echo "🚀 Development:"
	@echo "  make dev          - Run development server (localhost only)"
	@echo "  make dev-tunnel   - Run dev server + ngrok tunnel"
	@echo "  make dev-noreload - Run development server without hot reload"
	@echo "  make run          - Run production server"
	@echo ""
	@echo "🌐 Tunnel Management:"
	@echo "  make tunnel       - Start ngrok tunnel (if server already running)"
	@echo "  make tunnel-status - Check tunnel status"
	@echo "  make tunnel-info  - Show tunnel URLs and OAuth callbacks"
	@echo ""
	@echo "🧪 Quality:"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Run linter"
	@echo "  make clean        - Clean build artifacts"
	@echo ""
	@echo "🗄️  Database:"
	@echo "  make db-up        - Start PostgreSQL with Docker"
	@echo "  make db-down      - Stop PostgreSQL"
	@echo "  make db-upgrade   - Run database migrations"

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	@if [ ! -d "venv" ]; then \
		echo "Creating virtual environment..."; \
		python -m venv venv; \
	fi
	@echo "Activating virtual environment and installing packages..."
	@. venv/bin/activate && pip install --upgrade pip
	@. venv/bin/activate && pip install -r requirements.txt
	@. venv/bin/activate && pip install -r requirements-dev.txt
	@echo "✅ Dependencies installed!"

# Setup ngrok tunnel configuration
setup-tunnel:
	@echo "🌐 Setting up ngrok tunnel..."
	@if ! command -v ngrok &> /dev/null; then \
		echo "❌ ngrok not found. Please install from https://ngrok.com/download"; \
		exit 1; \
	fi
	@if [ -f .env.local ]; then \
		echo "✅ .env.local already exists"; \
	else \
		echo "Creating .env.local from template..."; \
		cp .env.example .env.local; \
		echo "" >> .env.local; \
		echo "# Ngrok Configuration" >> .env.local; \
		echo "NGROK_DOMAIN=your-domain.ngrok-free.app" >> .env.local; \
		echo "NGROK_ENABLED=true" >> .env.local; \
		echo ""; \
		echo "📝 Please edit .env.local and set your NGROK_DOMAIN"; \
	fi
	@echo ""
	@echo "🔧 Ngrok Configuration:"
	@echo "  1. Set NGROK_DOMAIN in .env.local (e.g., amir-auth.hirecj.ai)"
	@echo "  2. Run 'make dev-tunnel' to start with tunnel"
	@echo "  3. OAuth callbacks will use your tunnel URL automatically"

# Run development server with hot reload
dev:
	@echo "🚀 Starting HireCJ Auth Service (development mode with hot reload)..."
	@if [ -f .env.local ] && grep -q "NGROK_ENABLED=true" .env.local 2>/dev/null; then \
		echo "💡 Ngrok is enabled. Run 'make dev-tunnel' for external access."; \
		echo ""; \
	fi
	@. venv/bin/activate && \
		export DEBUG=True && \
		export LOG_LEVEL=DEBUG && \
		python -m uvicorn app.main:app --host 0.0.0.0 --port 8103 --reload

# Run development server with ngrok tunnel
dev-tunnel:
	@echo "🚀 Starting HireCJ Auth Service with ngrok tunnel..."
	@if [ ! -f .env.local ]; then \
		echo "❌ .env.local not found. Run 'make setup-tunnel' first."; \
		exit 1; \
	fi
	@echo "Loading environment from .env and .env.local..."
	@. venv/bin/activate && \
		export DEBUG=True && \
		export LOG_LEVEL=DEBUG && \
		honcho start -f Procfile.dev -e .env,.env.local

# Run development server without hot reload
dev-noreload:
	@echo "🚀 Starting HireCJ Auth Service (development mode)..."
	@. venv/bin/activate && \
		export DEBUG=True && \
		export LOG_LEVEL=DEBUG && \
		python -m uvicorn app.main:app --host 0.0.0.0 --port 8103

# Run production server
run:
	@echo "🚀 Starting HireCJ Auth Service (production mode)..."
	@. venv/bin/activate && \
		python -m uvicorn app.main:app --host 0.0.0.0 --port 8103

# Start just the ngrok tunnel
tunnel:
	@echo "🌐 Starting ngrok tunnel..."
	@if [ ! -f .env.local ]; then \
		echo "❌ .env.local not found. Run 'make setup-tunnel' first."; \
		exit 1; \
	fi
	@. venv/bin/activate && \
		. .env.local && \
		ngrok http 8103 --domain=$$NGROK_DOMAIN

# Check tunnel status
tunnel-status:
	@echo "🔍 Checking tunnel status..."
	@if curl -s http://localhost:4040/api/tunnels > /dev/null 2>&1; then \
		echo "✅ Ngrok tunnel is running"; \
		curl -s http://localhost:4040/api/tunnels | python -m json.tool | grep -E "public_url|proto" | head -4; \
	else \
		echo "❌ No tunnel detected"; \
		echo "💡 Run 'make dev-tunnel' or 'make tunnel' to start"; \
	fi

# Show tunnel info and OAuth URLs
tunnel-info:
	@echo "🌐 Tunnel Information:"
	@if [ -f .env.local ]; then \
		. .env.local && echo "  Domain: $$NGROK_DOMAIN"; \
	fi
	@echo ""
	@if curl -s http://localhost:4040/api/tunnels > /dev/null 2>&1; then \
		TUNNEL_URL=$$(python scripts/tunnel_detector.py 2>/dev/null); \
		if [ -n "$$TUNNEL_URL" ]; then \
			echo "📡 Active Tunnel: $$TUNNEL_URL"; \
			echo ""; \
			echo "🔐 OAuth Callback URLs:"; \
			echo "  Shopify:  $$TUNNEL_URL/api/v1/auth/callback/shopify"; \
			echo "  Google:   $$TUNNEL_URL/api/v1/auth/callback/google"; \
			echo "  Klaviyo:  $$TUNNEL_URL/api/v1/oauth/callback/klaviyo"; \
			echo ""; \
			echo "📋 Copy these URLs to your OAuth app settings"; \
		fi \
	else \
		echo "❌ No active tunnel"; \
		echo "💡 Run 'make dev-tunnel' to start"; \
	fi

# Run tests
test:
	@echo "🧪 Running tests..."
	@. venv/bin/activate && python -m pytest tests/ -v

# Run linter
lint:
	@echo "🔍 Running linter..."
	@. venv/bin/activate && ruff check app/ tests/
	@. venv/bin/activate && black --check app/ tests/

# Format code
format:
	@echo "✨ Formatting code..."
	@. venv/bin/activate && black app/ tests/
	@. venv/bin/activate && ruff check --fix app/ tests/

# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type f -name ".coverage" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleanup complete!"

# Database commands (using same PostgreSQL as hirecj-database)
db-up:
	@echo "🗄️  Starting PostgreSQL with Docker..."
	@cd ../hirecj-database && docker-compose up -d
	@echo "✅ PostgreSQL started on port 5435"

db-down:
	@echo "🗄️  Stopping PostgreSQL..."
	@cd ../hirecj-database && docker-compose down
	@echo "✅ PostgreSQL stopped"

db-upgrade:
	@echo "🔄 Running database migrations..."
	@. venv/bin/activate && alembic upgrade head
	@echo "✅ Migrations complete!"

# Stop the service (for consistency with other services)
stop:
	@echo "🛑 Stopping HireCJ Auth Service..."
	@pkill -f "uvicorn app.main:app" || true
	@echo "✅ Service stopped!"