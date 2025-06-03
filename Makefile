.PHONY: help install-all dev stop test-all clean status

# Default target
help:
	@echo "HireCJ Monorepo Commands:"
	@echo "  make install-all    - Install dependencies for all components"
	@echo "  make dev           - Start all services in development mode"
	@echo "  make stop          - Stop all services"
	@echo "  make test-all      - Run tests across all components"
	@echo "  make clean         - Clean build artifacts and caches"
	@echo "  make status        - Show status of all components"
	@echo "  make health-check  - Check health of all services"

# Install dependencies for all components
install-all:
	@echo "📦 Installing dependencies for all HireCJ components..."
	@if [ -d "hirecj-agents" ]; then \
		echo "Installing hirecj-agents dependencies..."; \
		cd hirecj-agents && make install; \
	fi
	@if [ -d "hirecj-database" ]; then \
		echo "Installing hirecj-database dependencies..."; \
		cd hirecj-database && make install; \
	fi
	@if [ -d "hirecj-homepage" ]; then \
		echo "Installing hirecj-homepage dependencies..."; \
		cd hirecj-homepage && npm install; \
	fi
	@if [ -d "hirecj-knowledge" ]; then \
		echo "Installing hirecj-knowledge dependencies..."; \
		cd hirecj-knowledge && make install; \
	fi
	@if [ -d "hirecj-auth" ]; then \
		echo "Installing hirecj-auth dependencies..."; \
		cd hirecj-auth && make install; \
	fi
	@echo "✅ All dependencies installed!"

# Start all services in development mode
dev:
	@echo "🚀 Starting HireCJ development environment..."
	@if [ -f "dev.py" ]; then \
		python dev.py; \
	else \
		echo "Development runner not found. Starting services individually..."; \
		$(MAKE) dev-agents & \
		$(MAKE) dev-homepage & \
		wait; \
	fi

# Start individual services
dev-agents:
	@if [ -d "hirecj-agents" ]; then \
		cd hirecj-agents && make dev; \
	fi

dev-database:
	@if [ -d "hirecj-database" ]; then \
		cd hirecj-database && make dev; \
	fi

dev-homepage:
	@if [ -d "hirecj-homepage" ]; then \
		cd hirecj-homepage && npm run dev; \
	fi

dev-knowledge:
	@if [ -d "hirecj-knowledge" ]; then \
		cd hirecj-knowledge && make dev; \
	fi

# Stop all services
stop:
	@echo "🛑 Stopping all HireCJ services..."
	@if [ -d "hirecj-agents" ]; then \
		cd hirecj-agents && make stop 2>/dev/null || true; \
	fi
	@if [ -d "hirecj-database" ]; then \
		cd hirecj-database && make stop 2>/dev/null || true; \
	fi
	@if [ -d "hirecj-homepage" ]; then \
		pkill -f "npm run dev" 2>/dev/null || true; \
	fi
	@if [ -d "hirecj-knowledge" ]; then \
		cd hirecj-knowledge && make stop 2>/dev/null || true; \
	fi
	@echo "✅ All services stopped!"

# Run tests across all components
test-all:
	@echo "🧪 Running tests for all HireCJ components..."
	@if [ -d "hirecj-agents" ]; then \
		echo "Testing hirecj-agents..."; \
		cd hirecj-agents && make test; \
	fi
	@if [ -d "hirecj-database" ]; then \
		echo "Testing hirecj-database..."; \
		cd hirecj-database && make test; \
	fi
	@if [ -d "hirecj-homepage" ]; then \
		echo "Testing hirecj-homepage..."; \
		cd hirecj-homepage && npm test; \
	fi
	@if [ -d "hirecj-knowledge" ]; then \
		echo "Testing hirecj-knowledge..."; \
		cd hirecj-knowledge && make test; \
	fi
	@echo "✅ All tests completed!"

# Clean build artifacts and caches
clean:
	@echo "🧹 Cleaning build artifacts and caches..."
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@find . -name "node_modules" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name "dist" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name "build" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name ".cache" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleanup completed!"

# Show status of all components
status:
	@echo "📊 HireCJ Component Status:"
	@echo "========================="
	@if [ -d "hirecj-agents" ]; then \
		echo "✅ hirecj-agents: Available"; \
	else \
		echo "❌ hirecj-agents: Not found"; \
	fi
	@if [ -d "hirecj-database" ]; then \
		echo "✅ hirecj-database: Available"; \
	else \
		echo "❌ hirecj-database: Not found"; \
	fi
	@if [ -d "hirecj-homepage" ]; then \
		echo "✅ hirecj-homepage: Available"; \
	else \
		echo "❌ hirecj-homepage: Not found"; \
	fi
	@if [ -d "hirecj-knowledge" ]; then \
		echo "✅ hirecj-knowledge: Available"; \
	else \
		echo "❌ hirecj-knowledge: Not found"; \
	fi
	@if [ -d "third-party" ]; then \
		echo "✅ third-party: Available"; \
	else \
		echo "❌ third-party: Not found"; \
	fi

# Health check for all services
health-check:
	@echo "🏥 Running health checks..."
	@echo "Checking if ports are available..."
	@if lsof -i:5001 > /dev/null 2>&1; then \
		echo "⚠️  Port 5001 (agents backend) is in use"; \
	else \
		echo "✅ Port 5001 is available"; \
	fi
	@if lsof -i:8002 > /dev/null 2>&1; then \
		echo "⚠️  Port 8002 (database service) is in use"; \
	else \
		echo "✅ Port 8002 is available"; \
	fi
	@if lsof -i:3456 > /dev/null 2>&1; then \
		echo "⚠️  Port 3456 (homepage frontend) is in use"; \
	else \
		echo "✅ Port 3456 is available"; \
	fi
	@if lsof -i:8000 > /dev/null 2>&1; then \
		echo "⚠️  Port 8000 (knowledge service) is in use"; \
	else \
		echo "✅ Port 8000 is available"; \
	fi