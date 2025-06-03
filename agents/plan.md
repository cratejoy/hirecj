# Real-Time Fact Extraction Implementation Plan

## Current State
- Fact extraction only runs when conversation ends (disconnect or explicit end)
- Facts learned during conversation aren't available until next conversation
- Using gpt-4o-mini for extraction (fast & cheap)

## Goal
Extract facts in real-time after EVERY merchant message, making them immediately available to CJ in the same conversation.

## Implementation Plan

### 1. Modify MessageProcessor
**File**: `app/services/message_processor.py`

Add fact extraction after every merchant message:
```python
async def process_message(self, session: Session, message: str, sender: str = "merchant") -> str:
    """Process a message and get response."""
    # Update session
    session.last_activity = datetime.utcnow()
    session.metrics["messages"] += 1
    
    # Add message to conversation
    msg = Message(
        timestamp=datetime.utcnow(),
        sender=sender,
        content=message
    )
    session.conversation.add_message(msg)
    
    # Extract facts immediately after merchant message (non-blocking)
    if sender == "merchant" and session.merchant_memory:
        asyncio.create_task(self._extract_facts_background(session))
    
    # Continue with normal processing...
```

### 2. Add Background Fact Extraction Method
**File**: `app/services/message_processor.py`

```python
async def _extract_facts_background(self, session: Session):
    """Extract facts in background without blocking conversation."""
    try:
        logger.info(f"[REAL_TIME_FACTS] Starting extraction for {session.conversation.merchant_name}")
        
        fact_extractor = FactExtractor()
        new_facts = await fact_extractor.extract_and_add_facts(
            session.conversation, 
            session.merchant_memory
        )
        
        if new_facts:
            logger.info(f"[REAL_TIME_FACTS] Extracted {len(new_facts)} new facts")
            # Save memory every 5 new facts to avoid too many disk writes
            total_facts = len(session.merchant_memory.facts)
            if total_facts % 5 == 0:
                memory_service = MerchantMemoryService()
                memory_service.save_memory(session.merchant_memory)
                logger.info(f"[REAL_TIME_FACTS] Saved memory with {total_facts} facts")
                
    except Exception as e:
        logger.error(f"[REAL_TIME_FACTS] Error extracting facts: {e}", exc_info=True)
```

### 3. Optimize Fact Extraction for Incremental Processing
**File**: `app/services/fact_extractor.py`

Add a parameter to only process recent messages:
```python
async def extract_and_add_facts(
    self, 
    conversation: Conversation, 
    memory: MerchantMemory,
    last_n_messages: Optional[int] = None
) -> List[str]:
    """Extract new facts from conversation and add to memory.
    
    Args:
        conversation: The conversation to analyze
        memory: The merchant's existing memory
        last_n_messages: Only analyze the last N messages (for incremental extraction)
        
    Returns:
        List of newly extracted facts
    """
    # If last_n_messages specified, only format recent messages
    if last_n_messages:
        messages_to_analyze = conversation.messages[-last_n_messages:]
    else:
        messages_to_analyze = conversation.messages
```

### 4. Update Background Extraction to Use Incremental Processing
```python
async def _extract_facts_background(self, session: Session):
    """Extract facts in background without blocking conversation."""
    try:
        # Only analyze last 4 messages (2 exchanges) for efficiency
        fact_extractor = FactExtractor()
        new_facts = await fact_extractor.extract_and_add_facts(
            session.conversation, 
            session.merchant_memory,
            last_n_messages=4
        )
        # ... rest of implementation
```

### 5. Clean Up Redundant End-of-Conversation Extraction
- Keep extraction in `finally` block for safety (in case any facts were missed)
- Remove from `end_conversation` handler (redundant now)

## Configuration

### Environment Variables
- **FACT_EXTRACTION_MODEL**: The model used for fact extraction
  - Default: `gpt-4o-mini`
  - Can be overridden by setting `FACT_EXTRACTION_MODEL=gpt-4o` or any other model

### Model Choice Rationale
- **gpt-4o-mini**: Fast, cheap, good enough for fact extraction
- Runs on every message, so speed/cost is critical
- Can upgrade to gpt-4o for better extraction quality if needed

## Benefits
1. **Immediate Learning**: Facts available in same conversation
2. **Better UX**: CJ adapts and learns as conversation progresses
3. **Resilient**: No data loss on disconnects
4. **Efficient**: Only processes new messages
5. **Cost-Effective**: Uses cheap/fast model

## Testing Strategy
1. Send message with new fact (e.g., "My name is Amir")
2. Verify fact is extracted in logs
3. Send follow-up message
4. Verify CJ uses the learned fact in response

## Rollback Plan
If real-time extraction causes issues:
1. Remove the `asyncio.create_task` line
2. Facts will still be extracted on disconnect
3. No data loss, just delayed learning