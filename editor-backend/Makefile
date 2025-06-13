.PHONY: help install dev test clean

# Default target
help:
	@echo "HireCJ Editor Backend Commands:"
	@echo ""
	@echo "📦 Setup:"
	@echo "  make install      - Install dependencies"
	@echo "  make clean        - Clean build artifacts and dependencies"
	@echo ""
	@echo "🚀 Development:"
	@echo "  make dev          - Start the editor backend server"
	@echo "  make test         - Run tests"

# Install dependencies
install:
	@echo "📦 Installing editor backend dependencies..."
	python -m venv venv
	. venv/bin/activate && pip install -r requirements.txt
	@echo "✅ Editor backend dependencies installed!"

# Development
dev:
	@echo "🚀 Starting editor backend server on port 8001..."
	. venv/bin/activate && python -m app

# Run tests
test:
	@echo "🧪 Running editor backend tests..."
	. venv/bin/activate && pytest

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	rm -rf venv
	rm -rf __pycache__
	rm -rf app/__pycache__
	rm -rf app/api/__pycache__
	rm -rf app/api/routes/__pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "✅ Cleanup complete!"