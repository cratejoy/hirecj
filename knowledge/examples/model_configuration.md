# LightRAG Model Configuration Guide

## Overview

The LightRAG integration in the Knowledge Service now supports flexible model configuration through environment variables. This allows you to easily switch between different OpenAI models without changing code.

## Configuration Variables

The following environment variables control LightRAG's behavior:

### Model Configuration
- `LIGHTRAG_LLM_MODEL` - The OpenAI model to use (default: gpt-4o-mini)
- `LIGHTRAG_EMBEDDING_MODEL` - The embedding model (default: text-embedding-3-small)
- `LIGHTRAG_MAX_TOKENS` - Maximum tokens per response (default: 32768)
- `LIGHTRAG_MAX_ASYNC` - Maximum concurrent LLM calls (default: 4)

### Chunking Configuration
- `LIGHTRAG_CHUNK_SIZE` - Token size for text chunks (default: 1200)
- `LIGHTRAG_CHUNK_OVERLAP_SIZE` - Overlap between chunks (default: 100)

### Embedding Configuration
- `LIGHTRAG_EMBEDDING_BATCH_NUM` - Batch size for embeddings (default: 32)
- `LIGHTRAG_EMBEDDING_FUNC_MAX_ASYNC` - Max concurrent embedding calls (default: 16)

### Processing Configuration
- `LIGHTRAG_MAX_TOKEN_SUMMARY` - Max tokens for entity summaries (default: 1000)
- `LIGHTRAG_FORCE_LLM_SUMMARY_ON_MERGE` - Force LLM summary on merge (default: 1)

## Supported Models

### Models with Specific Functions
- `gpt-4o-mini` - Optimized for speed and cost
- `gpt-4o` - Higher quality responses

### Models Using Generic OpenAI Function
Any other OpenAI model can be used, including:
- `o1-mini` - Reasoning model (when available)
- `o1-preview` - Preview reasoning model (when available)
- `o3-mini` - Advanced reasoning model (when available)
- Any future OpenAI models

## Example Configurations

### Using GPT-4o for Higher Quality
```env
LIGHTRAG_LLM_MODEL=gpt-4o
LIGHTRAG_MAX_TOKENS=32768
```

### Using O3-mini for Advanced Reasoning
```env
LIGHTRAG_LLM_MODEL=o3-mini
LIGHTRAG_MAX_TOKENS=32768
```

### Using Larger Embeddings
```env
LIGHTRAG_EMBEDDING_MODEL=text-embedding-3-large
LIGHTRAG_EMBEDDING_BATCH_NUM=16
```

## Implementation Details

The Knowledge Service automatically selects the appropriate function based on the model name:

1. Known models (gpt-4o-mini, gpt-4o) use optimized specific functions
2. All other models use the generic `openai_complete` function which supports any OpenAI model

This design ensures forward compatibility with new models as they become available.

## Testing Configuration

To verify your configuration is loaded correctly:

1. Check the service logs on startup - it will show which model is being used
2. The logs will indicate whether a specific or generic function is being used
3. Environment variables are loaded from the root `.env` file and distributed to services

## Notes

- The `OPENAI_API_KEY` must be set for any model to work
- Optional: Set `OPENAI_API_BASE` to use a custom API endpoint or proxy
- All configuration changes require a service restart to take effect