# Knowledge Service Makefile

.PHONY: help install dev test clean

help:
	@echo "Knowledge Service - Available commands:"
	@echo "  make install    - Install dependencies"
	@echo "  make dev        - Run development server"
	@echo "  make test       - Test the health endpoint"
	@echo "  make clean      - Clean up files"

install:
	@echo "📦 Installing dependencies..."
	python -m venv venv
	venv/bin/pip install --upgrade pip
	venv/bin/pip install -r requirements.txt

dev:
	@echo "🚀 Starting Knowledge API server..."
	venv/bin/python scripts/run_api_server.py

test:
	@echo "🧪 Testing health endpoint..."
	@curl -s http://localhost:8004/health | python -m json.tool

clean:
	@echo "🧹 Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@rm -rf venv
	@echo "✅ Cleaned"