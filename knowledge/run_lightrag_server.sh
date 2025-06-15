#!/bin/bash

# Script to run LightRAG server with existing database

echo "Starting LightRAG Web UI Server..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Set environment variables for LightRAG configuration
export WORKING_DIR="./lightrag_transcripts_db"
export INPUT_DIR="./transcripts"

# OpenAI configuration to match existing embeddings
export LLM_BINDING="openai"
export LLM_MODEL="gpt-4o-mini"
export EMBEDDING_BINDING="openai"
export EMBEDDING_MODEL="text-embedding-3-small"
export EMBEDDING_DIMENSION="1536"

# Check if lightrag-server is available
if ! command -v lightrag-server &> /dev/null; then
    echo "Error: lightrag-server not found. Installing..."
    pip install -e "./LightRAG[api]"
fi

echo "Configuration:"
echo "- Working directory: ${WORKING_DIR}"
echo "- Input directory: ${INPUT_DIR}"
echo "- LLM: ${LLM_BINDING} (${LLM_MODEL})"
echo "- Embeddings: ${EMBEDDING_BINDING} (${EMBEDDING_MODEL})"
echo "- Server URL: http://localhost:9621"
echo ""
echo "Starting server..."

# Run the server
lightrag-server \
    --host 0.0.0.0 \
    --port 9621 \
    --input-dir "${INPUT_DIR}" \
    --working-dir "${WORKING_DIR}" \
    --llm-binding openai \
    --embedding-binding openai