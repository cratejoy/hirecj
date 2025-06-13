# Analytics Library Refactoring Guide

## Overview
This guide documents the refactoring of the Freshdesk Analytics Library to address three critical issues:

1. **Session Management**: Functions now accept sessions as parameters instead of creating their own
2. **Rating Consistency**: Fixed inconsistent rating comparisons 
3. **Conversation Access**: Added markdown-formatted conversation property to unified view

## Key Changes

### 1. Session Management Pattern

**Before (Anti-pattern):**
```python
def get_daily_snapshot(merchant_id: int, target_date: date):
    with get_db_session() as session:  # Creates session inside function
        # ... query logic
```

**After (Correct pattern):**
```python
def get_daily_snapshot(session: Session, merchant_id: int, target_date: date):
    # Uses passed session
    # ... query logic
```

### 2. Rating Constants and Consistency

**Issue Found**: 
- CSAT calculation only counted 103 (Extremely Happy) as satisfied
- But `get_tickets_by_rating()` counted both 102 and 103 as "happy"
- This created inconsistent metrics

**Solution**:
```python
class FreshdeskRatings:
    EXTREMELY_HAPPY = 103      # Only this counts for CSAT
    VERY_HAPPY = 102          
    HAPPY = 101
    NEUTRAL = 100
    UNHAPPY = -101
    VERY_UNHAPPY = -102
    EXTREMELY_UNHAPPY = -103
    
    SATISFIED_THRESHOLD = 103  # Only "Extremely Happy" counts for CSAT
    NEGATIVE_THRESHOLD = 102   # Below "Very Happy" is considered negative
```

### 3. Conversation Access Pattern

**New property on FreshdeskUnifiedTicketView:**
```python
ticket = session.query(FreshdeskUnifiedTicketView).first()
print(ticket.conversation)  # Returns formatted markdown of entire conversation
```

**Output format:**
```markdown
## Ticket #12345: Customer can't login

### Message 1 - 2024-01-01T10:00:00Z
**Customer** (customer@example.com)

> I can't log into my account. It says invalid password
> but I know it's correct.

### Message 2 - 2024-01-01T10:15:00Z  
**Agent** (support@company.com)

>> I'll help you reset your password. Please check your email
>> for a reset link.

---
**Customer Rating**: 😊 Extremely Happy
**Feedback**: Quick and helpful!
```

## Migration Steps

### Step 1: Update CrewAI Tools (database_tools.py)

```python
@tool
def get_daily_snapshot(date_str: Optional[str] = None) -> str:
    """Get comprehensive daily health metrics for support operations."""
    # ... argument parsing ...
    
    try:
        # Create session at tool level
        with get_db_session() as session:
            # Pass session to analytics function
            snapshot = FreshdeskAnalytics.get_daily_snapshot(
                session=session,
                merchant_id=merchant_id, 
                target_date=target_date
            )
            
        # Format output...
        return output
```

### Step 2: Update All Analytics Functions

Functions to update with session parameter:
- [x] get_daily_snapshot
- [ ] get_csat_detail_log  
- [ ] get_open_ticket_distribution
- [ ] get_response_time_metrics
- [ ] get_volume_trends
- [ ] get_root_cause_analysis
- [ ] calculate_csat
- [ ] get_recent_ticket
- [ ] get_support_dashboard
- [ ] search_tickets
- [ ] get_ticket_by_id
- [ ] get_tickets_by_email
- [ ] get_tickets_by_rating
- [ ] get_recent_bad_csat_tickets
- [ ] get_rating_statistics

### Step 3: Fix Rating Comparisons

Search and replace:
- `rating_score >= 102` → `rating_score == 103` (for "happy" filters)
- Document that only 103 counts as satisfied for CSAT

### Step 4: Test Conversation Property

```python
with get_db_session() as session:
    ticket = session.query(FreshdeskUnifiedTicketView).filter(
        FreshdeskUnifiedTicketView.has_rating == True
    ).first()
    
    # This now works!
    print(ticket.conversation)
```

## Key Implementation Details

### Conversation Access Without Session in Models

**Update**: As of migration 009, conversation_history is now embedded in the view!

The FreshdeskUnifiedTicketView now includes:
```python
# Column in the view
conversation_history = Column(JSONB)  # Full conversation data from etl_freshdesk_conversations

# Property that uses embedded data - no DB query needed!
@property
def conversation(self):
    """Get formatted conversation using embedded data."""
    if not self.conversation_history:
        return None  # Returns None instead of error message
    return self.format_conversation(self.conversation_history)
```

Benefits:
- **Zero additional queries** - conversation data is pre-loaded in the view
- **Better performance** - no N+1 query problems when accessing multiple tickets
- **Simpler code** - just use `ticket.conversation` anywhere

The conversation_formatter utility still exists for backward compatibility:
```python
def get_formatted_conversation(session: Session, ticket: FreshdeskUnifiedTicketView) -> str:
    """Uses embedded data when available, falls back to query if needed."""
    if ticket.conversation_history is not None:
        return ticket.format_conversation(ticket.conversation_history)
    # ... fallback query logic
```

### Enhanced CSAT Detail Log

The CSAT detail log now supports including full conversations for negative ratings:
```python
result = FreshdeskAnalytics.get_csat_detail_log(
    session=session,
    merchant_id=1, 
    target_date=date(2025, 5, 26),
    rating_threshold=102,
    include_conversations=True  # NEW: Include conversations for bad ratings
)
```

## Benefits

1. **Better Resource Management**: Sessions are managed at the appropriate level
2. **Consistent Metrics**: CSAT and happiness metrics now align
3. **Easier Debugging**: Conversation history readily accessible
4. **Performance**: Reuse sessions for multiple queries
5. **Testing**: Easier to mock sessions for unit tests
6. **Clean Architecture**: No session access in model files

## Next Steps

1. Complete refactoring of all analytics functions
2. Update all CrewAI tools to create sessions
3. Add unit tests with mocked sessions
4. Update documentation
5. Consider adding session pooling for performance