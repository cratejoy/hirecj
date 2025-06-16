# Knowledge Service Makefile

.PHONY: help install dev test clean setup example test-namespace test-operations test-file-upload test-enhanced-ingestion

help:
	@echo "Knowledge Service - Available commands:"
	@echo "  make install        - Install dependencies"
	@echo "  make dev            - Run development server"
	@echo "  make test           - Test the health endpoint"
	@echo "  make setup          - Run setup script"
	@echo "  make example        - Run example usage (Phase 0.3)"
	@echo "  make test-namespace - Test namespace operations (Phase 0.2)"
	@echo "  make test-operations - Test document operations (Phase 0.3)"
	@echo "  make test-file-upload - Test file upload operations (Phase 1.1)"
	@echo "  make test-enhanced-ingestion - Test enhanced ingestion (Phase 1.3)"
	@echo "  make clean          - Clean up files"

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

# Phase 0.3 targets
setup:
	@echo "🔧 Running setup script..."
	@bash scripts/setup.sh

example:
	@echo "🚀 Running example usage..."
	@venv/bin/python scripts/example_usage.py

test-namespace:
	@echo "🧪 Testing namespace operations..."
	@venv/bin/python scripts/test_namespaces.py

test-operations:
	@echo "🧪 Testing document operations..."
	@venv/bin/python scripts/test_basic_operations.py

test-file-upload:
	@echo "🧪 Testing file upload operations..."
	@venv/bin/python scripts/test_file_upload.py

test-enhanced-ingestion:
	@echo "🧪 Testing enhanced ingestion features..."
	@venv/bin/python scripts/test_enhanced_ingestion.py