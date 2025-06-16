# LightRAG Technical Guide

## Overview

LightRAG is a Retrieval-Augmented Generation (RAG) system that combines multiple retrieval strategies for optimal performance.

## Architecture Components

### 1. Document Processing Pipeline
- **Chunking**: Splits documents into manageable segments
- **Embedding Generation**: Creates vector representations using OpenAI embeddings
- **Storage**: Persists data in both vector and graph databases

### 2. Query Modes

#### Naive Mode
Simple keyword-based search without advanced processing.

#### Local Mode
Focuses on dense semantic search within local context windows.

#### Global Mode
Leverages the knowledge graph for relationship-based queries.

#### Hybrid Mode
Combines local and global strategies for comprehensive results.

## Integration with HireCJ

The system is designed to support multiple isolated namespaces, allowing different teams or projects to maintain separate knowledge bases while sharing the same infrastructure.

### API Endpoints
- Document ingestion: `/api/{namespace}/documents`
- File upload: `/api/{namespace}/documents/upload`
- Batch upload: `/api/{namespace}/documents/batch-upload`
- Query: `/api/{namespace}/query`

## Best Practices

1. Use appropriate query modes based on your use case
2. Provide meaningful metadata for better document organization
3. Regular maintenance of the knowledge graph for optimal performance