# Knowledge CLI Tool

A powerful command-line interface for managing knowledge bases in the HireCJ system.

## Installation

From the knowledge directory:
```bash
make install
```

## Usage

The CLI provides several commands for managing knowledge bases:

### List Namespaces
```bash
venv/bin/python scripts/knowledge.py list
```

### Create a Namespace
```bash
venv/bin/python scripts/knowledge.py create myproject \
  --name "My Project" \
  --description "Knowledge base for my project" \
  --set-default
```

### Ingest Documents

#### Single File
```bash
venv/bin/python scripts/knowledge.py ingest document.txt -n myproject
```

#### Multiple Files with Glob Pattern
```bash
venv/bin/python scripts/knowledge.py ingest "*.md" -n docs
venv/bin/python scripts/knowledge.py ingest "**/*.txt" -n docs --recursive
```

#### Directory
```bash
venv/bin/python scripts/knowledge.py ingest /path/to/docs/ -n docs --recursive --pattern "*.md"
```

#### URLs
```bash
venv/bin/python scripts/knowledge.py ingest https://example.com/article1 https://example.com/article2 -n web
```

#### URLs from File
```bash
venv/bin/python scripts/knowledge.py ingest urls.txt --from -n web --parallel 5
```

### View Statistics
```bash
venv/bin/python scripts/knowledge.py stats myproject
```

### Configure CLI
```bash
# View current configuration
venv/bin/python scripts/knowledge.py config --list

# Set default namespace
venv/bin/python scripts/knowledge.py config --default-namespace myproject

# Set API base URL
venv/bin/python scripts/knowledge.py config --api-base http://localhost:8004

# Set parallel uploads
venv/bin/python scripts/knowledge.py config --parallel 5
```

## Options

### Ingest Command Options
- `-n, --namespace`: Target namespace (uses default if not specified)
- `-r, --recursive`: Process directories recursively
- `-p, --pattern`: File pattern for directory ingestion (e.g., "*.md")
- `--from`: Treat input as a file containing URLs
- `-m, --metadata`: Additional metadata as JSON string
- `--parallel`: Number of parallel uploads (default: 1)
- `--auto-create`: Create namespace if it doesn't exist

## Features

- **Progress Bars**: Visual feedback for batch operations
- **Colored Output**: Clear success/error/info messages
- **Parallel Uploads**: Speed up large ingestions
- **Configuration Persistence**: Settings saved in `~/.knowledge/config.json`
- **Auto-create Namespaces**: No need to manually create namespaces first
- **Glob Pattern Support**: Flexible file selection
- **URL Ingestion**: Direct web content ingestion
- **Comprehensive Error Handling**: Clear error messages and recovery

## Makefile Commands

For convenience, the Makefile provides these commands:

```bash
# Show help
make knowledge-help

# List namespaces
make knowledge-list

# Create namespace
make knowledge-create NAMESPACE=myproject

# Ingest files
make knowledge-ingest FILES="file1.txt file2.md" NAMESPACE=myproject
```

## Example Workflow

```bash
# 1. Create a namespace
venv/bin/python scripts/knowledge.py create product_docs --set-default

# 2. Ingest documentation
venv/bin/python scripts/knowledge.py ingest "docs/**/*.md" --recursive --parallel 5

# 3. Check statistics
venv/bin/python scripts/knowledge.py stats

# 4. Query via API (using the API directly)
curl -X POST "http://localhost:8004/api/product_docs/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I configure the system?", "mode": "hybrid"}'
```