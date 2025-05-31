.PHONY: dev dev-backend dev-frontend install kill-ports stop help

# Default target
help:
	@echo "HireCJ Development Commands:"
	@echo "  make dev          - Run both backend and frontend with auto-reload"
	@echo "  make dev-backend  - Run only backend with auto-reload"
	@echo "  make dev-frontend - Run only frontend"
	@echo "  make install      - Install all dependencies"
	@echo "  make stop         - Stop all HireCJ servers and free ports"
	@echo "  make kill-ports   - Kill processes on ports 5001 and 3456"
	@echo "  make logs         - Tail backend logs"
	@echo "  make test-backend - Run backend tests"

# Run both servers
dev:
	@echo "Starting HireCJ development servers..."
	@./dev.py

# Run backend only with auto-reload
dev-backend:
	@echo "Starting backend API server with auto-reload..."
	@cd hirecj-data && \
	source venv/bin/activate && \
	export PORT=5001 && \
	python -m uvicorn src.api.server:app --host 0.0.0.0 --port 5001 --reload

# Run frontend only
dev-frontend:
	@echo "Starting frontend server..."
	@cd hirecj-homepage && npm run dev

# Install all dependencies
install:
	@echo "Installing backend dependencies..."
	@cd hirecj-data && \
	python -m venv venv && \
	source venv/bin/activate && \
	pip install -r requirements.txt && \
	pip install -r requirements-dev.txt
	@echo "Installing frontend dependencies..."
	@cd hirecj-homepage && npm install
	@echo "✅ All dependencies installed!"

# Stop all HireCJ servers
stop:
	@echo "Stopping all HireCJ servers..."
	@echo "Killing processes on ports 5001 and 3456..."
	@lsof -ti:5001 | xargs kill -9 2>/dev/null || true
	@lsof -ti:3456 | xargs kill -9 2>/dev/null || true
	@echo "Killing any remaining Python/Node processes for HireCJ..."
	@ps aux | grep -E "(hirecj|uvicorn.*5001|tsx.*3456)" | grep -v grep | awk '{print $$2}' | xargs kill -9 2>/dev/null || true
	@echo "✅ All HireCJ servers stopped!"

# Kill processes on dev ports
kill-ports:
	@echo "Killing processes on ports 5001 and 3456..."
	@lsof -ti:5001 | xargs kill -9 2>/dev/null || true
	@lsof -ti:3456 | xargs kill -9 2>/dev/null || true
	@echo "✅ Ports cleared!"

# Tail backend logs
logs:
	@tail -f hirecj-data/logs/hirecj-backend.log

# Run backend tests
test-backend:
	@cd hirecj-data && make test