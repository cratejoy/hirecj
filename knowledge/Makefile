# Minimal Makefile for hirecj-knowledge
# Most commands should be run from the root monorepo

.PHONY: run test help install

help:
	@echo "This is a minimal Makefile. Use the root Makefile for most operations:"
	@echo "  cd .. && make dev-knowledge  # Run the service"
	@echo "  cd .. && make test-knowledge # Run tests"
	@echo "  cd .. && make install        # Install dependencies"

run:
	@echo "Starting knowledge service..."
	@cd .. && make dev-knowledge

test:
	@echo "Running knowledge tests..."
	@cd .. && make test-knowledge

install:
	@echo "Installing dependencies..."
	python -m venv venv
	venv/bin/pip install -r requirements.txt
	venv/bin/pip install -e ../third-party/LightRAG

# Local development commands
demo:
	venv/bin/python src/scripts/lightrag_transcripts_demo.py

clean:
	rm -rf venv __pycache__ src/__pycache__
	rm -rf lightrag_transcripts_db