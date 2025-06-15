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
	venv/bin/pip install -e ./LightRAG

# Local development commands
demo:
	venv/bin/python -m src demo

ingest:
	venv/bin/python -m src ingest

ingest-add:
	@echo "Usage: make ingest-add URL=<url> [LIMIT=<n>]"
	@echo "Example: make ingest-add URL=https://example.com/feed.rss LIMIT=5"
	@[ -n "$(URL)" ] || (echo "Error: URL is required" && exit 1)
	venv/bin/python -m src ingest add "$(URL)" $(if $(LIMIT),--limit $(LIMIT))

ingest-process:
	venv/bin/python -m src ingest process

ingest-status:
	venv/bin/python -m src ingest status

server:
	./run_lightrag_server.sh

clean:
	rm -rf venv __pycache__ src/__pycache__
	rm -rf lightrag_transcripts_db
	rm -rf content/inbox/* content/downloading/* content/downloaded/* content/audio/* content/chunks/* content/transcribing/* content/transcripts/* content/loaded/* content/failed/*