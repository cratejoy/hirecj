# LightRAG Logging Configuration

## Overview

The knowledge service now supports detailed logging from LightRAG to help debug document processing issues and monitor the knowledge graph building process.

## Configuration

### Environment Variable

Set the `LIGHTRAG_LOG_LEVEL` environment variable to control LightRAG's logging verbosity:

```bash
# Default level (recommended for normal operation)
export LIGHTRAG_LOG_LEVEL=INFO

# Debug level (for troubleshooting)
export LIGHTRAG_LOG_LEVEL=DEBUG

# Warning level (less verbose)
export LIGHTRAG_LOG_LEVEL=WARNING
```

### What You'll See

With logging enabled, you'll see:

1. **Document Processing**:
   - Chunking operations
   - Entity extraction progress
   - Relationship identification
   - Graph building steps

2. **Storage Operations**:
   - Vector database updates
   - Graph storage operations
   - Document status changes

3. **Query Processing**:
   - Query parsing
   - Retrieval operations
   - Result generation

## Testing Logging

Run the test script to verify logging is working:

```bash
cd knowledge
# Set debug level for detailed output
LIGHTRAG_LOG_LEVEL=DEBUG python scripts/test_lightrag_logging.py
```

## Example Log Output

```
2025-06-16 10:30:45 - lightrag - INFO - Processing 1 document(s)
2025-06-16 10:30:45 - lightrag - DEBUG - Chunking document with 250 tokens
2025-06-16 10:30:45 - lightrag.operate - INFO - Extracting entities from chunk 1/3
2025-06-16 10:30:46 - lightrag.operate - DEBUG - Found entities: Python, LightRAG, logging
2025-06-16 10:30:46 - lightrag.kg.shared_storage - INFO - Updating vector storage with 3 entities
2025-06-16 10:30:47 - lightrag - INFO - Document processing completed successfully
```

## Troubleshooting Stuck Documents

With debug logging enabled, you can identify where documents get stuck:

1. Look for the last log entry for a document ID
2. Check if entity extraction is taking too long
3. Monitor storage operation timeouts
4. Identify LLM API failures

## Performance Considerations

- `INFO` level is recommended for production
- `DEBUG` level generates significant log output
- Consider log rotation for long-running services with debug logging