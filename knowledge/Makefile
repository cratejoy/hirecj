# Knowledge Service Makefile

.PHONY: help install dev test clean clean-data clean-all setup example test-namespace test-operations test-file-upload test-enhanced-ingestion

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
	@echo "  make clean          - Clean up Python cache files"
	@echo "  make clean-data     - Wipe all knowledge data"
	@echo "  make clean-all      - Complete cleanup (code + data)"
	@echo ""
	@echo "Knowledge CLI commands:"
	@echo "  make knowledge-help - Show Knowledge CLI help"
	@echo "  make knowledge-list - List all namespaces"
	@echo "  make knowledge-create NAMESPACE=name - Create a namespace"
	@echo "  make knowledge-ingest FILES='file1 file2' NAMESPACE=name - Ingest files"
	@echo "  make knowledge-podcast URL='rss_url' NAMESPACE=name LIMIT=5 - Ingest podcast episodes"

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
	@echo "🧹 Cleaning up Python cache..."
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@echo "✅ Python cache cleaned"

clean-data:
	@echo "🗑️  Wiping all knowledge data..."
	@rm -rf knowledge_base/*
	@echo "✅ All knowledge data removed"

clean-all: clean clean-data
	@echo "✅ Complete cleanup done"

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

# Knowledge CLI commands
knowledge-help:
	@echo "📚 Showing Knowledge CLI help..."
	@venv/bin/python scripts/knowledge.py --help

knowledge-list:
	@echo "📋 Listing namespaces..."
	@venv/bin/python scripts/knowledge.py list

knowledge-create:
	@echo "🆕 Creating namespace..."
	@venv/bin/python scripts/knowledge.py create $(NAMESPACE) --set-default

knowledge-ingest:
	@echo "📥 Ingesting documents..."
	@venv/bin/python scripts/knowledge.py ingest $(FILES) --namespace $(NAMESPACE) --auto-create

knowledge-podcast:
	@echo "🎙️  Ingesting podcast episodes..."
	@venv/bin/python scripts/knowledge.py podcast $(URL) --namespace $(NAMESPACE) $(if $(LIMIT),--limit $(LIMIT),)