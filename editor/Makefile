.PHONY: help install dev build test clean dev-frontend

# Default target
help:
	@echo "HireCJ Editor Commands:"
	@echo ""
	@echo "📦 Setup:"
	@echo "  make install      - Install dependencies"
	@echo "  make clean        - Clean build artifacts and dependencies"
	@echo ""
	@echo "🚀 Development:"
	@echo "  make dev          - Start editor frontend"
	@echo "  make build        - Build for production"
	@echo "  make test         - Run tests"

# Install dependencies
install:
	@echo "📦 Installing editor dependencies..."
	npm install
	@echo "✅ Editor dependencies installed!"

# Development
dev:
	@echo "🎨 Starting editor frontend..."
	@echo "Note: This requires the editor backend service to be running on port 8001"
	npm run dev

# Build for production
build:
	@echo "🏗️ Building editor for production..."
	npm run build
	@echo "✅ Build complete! Output in ./dist"

# Run tests
test:
	@echo "🧪 Running editor tests..."
	npm run check

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	rm -rf node_modules
	rm -rf dist
	rm -f package-lock.json
	@echo "✅ Cleanup complete!"

# Stop editor session
stop:
	@echo "🛑 Stopping editor services..."
	@if tmux has-session -t hirecj-editor 2>/dev/null; then \
		tmux kill-session -t hirecj-editor; \
		echo "✅ Stopped hirecj-editor session"; \
	else \
		echo "No editor session running"; \
	fi