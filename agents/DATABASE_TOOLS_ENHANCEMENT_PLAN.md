# Database Tools Enhancement Plan

## 1. Fix `analyze_systemic_issues` Tool with Pagination

### 1.1 Rename Tool
- **Current name**: `analyze_systemic_issues`
- **New name**: `get_recent_tickets_for_review`
- **Rationale**: Current name implies the tool performs analysis, but it only returns raw data

### 1.2 Pagination Architecture
**Approach**: Cursor-based pagination with flexible page sizes
- **Why cursor-based**: Prevents issues with records being added/updated during pagination
- **Cursor field**: Use `freshdesk_ticket_id` as it's immutable
- **Sort order**: Sort by `created_at DESC, freshdesk_ticket_id DESC` for stable ordering
- **Page size**: 20 tickets default, up to 100 tickets per call

**Implementation patterns**:
```python
# Get last 100 tickets in one call
get_recent_tickets_for_review(limit=100)
# Returns: 100 tickets + next_cursor (if more exist)

# Paginate through tickets 20 at a time
page1 = get_recent_tickets_for_review(limit=20)
# Returns: 20 tickets + next_cursor="345927"

page2 = get_recent_tickets_for_review(limit=20, cursor="345927")
# Returns: next 20 tickets + next_cursor="345899"
```

### 1.3 Update Tool Description
```python
@tool
def get_recent_tickets_for_review(
    limit: int = 20,
    cursor: Optional[str] = None,
    status_filter: Optional[List[str]] = None
) -> str:
    """Get recent support tickets with full conversations for manual review and pattern detection.
    
    Args:
        limit: Number of tickets to retrieve (default: 20, max: 100)
        cursor: Pagination cursor from previous call (ticket_id to continue after)
        status_filter: Optional list of statuses to include 
                      ['open', 'pending', 'waiting'] (default: all statuses)
    
    Returns raw ticket data including:
    - Ticket metadata, conversations, ratings, escalation status
    - Pagination info (has_more, next_cursor if applicable)
    
    NOTE: This tool returns RAW DATA ONLY. You must analyze the tickets yourself.
    
    Usage examples:
        # Get last 100 tickets in one call
        get_recent_tickets_for_review(limit=100)
        
        # Paginate through all tickets
        page1 = get_recent_tickets_for_review(limit=20)
        # If has_more=True and next_cursor="345927"
        page2 = get_recent_tickets_for_review(limit=20, cursor="345927")
    """
```

### 1.4 Implementation Details

**Query structure**:
```sql
-- First page (no cursor)
SELECT * FROM v_freshdesk_unified_tickets
WHERE merchant_id = 1
  AND (:status_filter IS NULL OR status = ANY(:status_filter))
ORDER BY created_at DESC, freshdesk_ticket_id DESC
LIMIT :limit + 1;  -- Fetch +1 to check if more exist

-- Subsequent pages (with cursor)
SELECT * FROM v_freshdesk_unified_tickets
WHERE merchant_id = 1
  AND (:status_filter IS NULL OR status = ANY(:status_filter))
  AND (created_at, freshdesk_ticket_id) < (
    SELECT created_at, freshdesk_ticket_id 
    FROM v_freshdesk_unified_tickets 
    WHERE freshdesk_ticket_id = :cursor
  )
ORDER BY created_at DESC, freshdesk_ticket_id DESC
LIMIT :limit + 1;  -- Fetch +1 to check if more exist
```

**Output format examples**:

```
# Single call for 100 tickets:
📋 RECENT TICKETS FOR REVIEW
Retrieved: 100 tickets
Date range: 2024-01-20 14:30 to 2024-01-15 09:15
Has more: No

TICKET DATA:
[... 100 tickets with conversations ...]

# Cursor pagination (page 1):
📋 RECENT TICKETS FOR REVIEW
Retrieved: 20 tickets
Date range: 2024-01-20 14:30 to 2024-01-19 11:45
Has more: Yes
Next cursor: "345927"

TICKET DATA:
[... 20 tickets with conversations ...]

To get next page, use cursor="345927"

# Cursor pagination (page 2):
📋 RECENT TICKETS FOR REVIEW (continuing from cursor)
Retrieved: 20 tickets
Date range: 2024-01-19 11:43 to 2024-01-18 16:22
Has more: Yes
Next cursor: "345811"

TICKET DATA:
[... 20 tickets with conversations ...]
```

### 1.5 Benefits of This Approach
1. **Simple common case**: Can get last 100 tickets in one call with `limit=100`
2. **Stable pagination**: Cursor approach prevents missing tickets or duplicates
3. **Consistent ordering**: Always uses (created_at, ticket_id) tuple 
4. **Efficient**: Can use compound index on (merchant_id, created_at DESC, freshdesk_ticket_id DESC)
5. **Flexible page sizes**: From 20 tickets (manageable) to 100 tickets (comprehensive scan)

## 2. Enhance Search Capabilities

### 2.1 Upgrade `search_tickets_in_db`
**Current limitations**:
- Only searches in subject and description fields
- No customer name search
- No date filtering
- No status filtering

**New implementation**:
```python
@tool
def search_tickets_in_db(
    query: str,
    search_fields: List[str] = None,
    status_filter: List[str] = None,
    date_range: Optional[Dict[str, str]] = None,
    limit: int = 20
) -> str:
    """Search support tickets across multiple fields with advanced filtering.
    
    Args:
        query: Search term (searches across subject, description, customer name, email, and tags)
        search_fields: Specific fields to search in (default: all fields)
            Options: ['subject', 'description', 'customer_name', 'customer_email', 'tags']
        status_filter: Filter by ticket status (default: all statuses)
            Options: ['open', 'pending', 'resolved', 'closed', 'waiting']
        date_range: Filter by date range (e.g. {'start': '2024-01-01', 'end': '2024-01-31'})
        limit: Maximum results to return (default: 20)
    
    Examples:
        - search_tickets_in_db("singlesswag") - finds tickets from SinglesSwag company
        - search_tickets_in_db("renewal", status_filter=["open"]) - finds open renewal tickets
        - search_tickets_in_db("payment", date_range={'start': '2024-01-15'}) - recent payment issues
    """
```

### 2.2 Add `search_by_customer` Tool
```python
@tool
def search_by_customer(
    customer_identifier: str,
    include_resolved: bool = True,
    limit: int = 50
) -> str:
    """Find all tickets from a specific customer by name, email, or company.
    
    Args:
        customer_identifier: Can be:
            - Full or partial customer name (e.g., "Mary Beskin", "Beskin") 
            - Email address (full or partial, e.g., "mary@singlesswag.com", "@singlesswag")
            - Company name (e.g., "SinglesSwag", "Reveal Book Box")
        include_resolved: Include resolved/closed tickets (default: True)
        limit: Maximum results (default: 50)
    
    Returns all tickets from matching customers with basic info.
    Use get_ticket_details() to see full conversations.
    
    Examples:
        - search_by_customer("singlesswag") - finds all SinglesSwag tickets
        - search_by_customer("Mary Beskin", include_resolved=False) - only open tickets from Mary
    """
```

### 2.3 Add `get_tickets_by_merchant` Tool
```python
@tool  
def get_tickets_by_merchant(
    merchant_name: str,
    days_back: int = 30,
    min_priority: Optional[int] = None
) -> str:
    """Get all support tickets from a specific merchant/seller.
    
    Args:
        merchant_name: The merchant/seller name to search for
        days_back: How many days of history to include (default: 30)
        min_priority: Minimum priority level (1=Low, 2=Medium, 3=High, 4=Urgent)
    
    Returns tickets grouped by status with key metrics.
    Useful for merchant-specific support reviews.
    """
```

## 3. Create True Analysis Tools

### 3.1 Add `detect_critical_patterns` Tool
```python
@tool
def detect_critical_patterns(days_back: int = 7) -> str:
    """Analyze recent tickets to detect critical patterns requiring immediate attention.
    
    Args:
        days_back: Number of days to analyze (default: 7)
    
    This tool ACTUALLY ANALYZES tickets and returns:
    - Payment/billing failures affecting multiple customers
    - Potential service outages (multiple similar errors)
    - Security or data concerns mentioned by customers
    - Escalation risks (very angry customers, legal threats)
    - Subscription/renewal processing issues
    
    Returns a prioritized list of detected issues with:
    - Issue type and severity
    - Number of affected customers
    - Example ticket IDs
    - Recommended actions
    """
```

**Implementation approach**:
- Use SQL queries to group tickets by patterns
- Look for keywords indicating critical issues
- Count occurrences and affected customers
- Return structured analysis, not raw data

### 3.2 Add `get_issue_summary` Tool
```python
@tool
def get_issue_summary(days_back: int = 7) -> str:
    """Get a categorized summary of recent support issues.
    
    Args:
        days_back: Number of days to analyze (default: 7)
    
    Returns:
    - Top 10 issue categories by volume
    - Comparison to previous period
    - Emerging issues (new patterns)
    - Resolution rates by category
    
    Useful for identifying what's driving support volume.
    """
```

## 4. Fix Existing Tool Descriptions

### 4.1 Tools to Update
1. **`analyze_bad_csat_tickets`** - Clarify it returns conversations for manual review
2. **`get_daily_snapshot`** - Emphasize it's metrics only, not analysis
3. **`get_root_cause_analysis`** - Clarify it identifies volume drivers, not deep analysis

### 4.2 Description Template
Each tool description should clearly state:
- What data it returns (raw vs. analyzed)
- What the user needs to do with the data
- Example use cases
- Limitations

## 5. Implementation Priority

### Phase 1 (Critical - Do First)
1. Rename and fix `analyze_systemic_issues` → `get_recent_tickets_for_review`
2. Update search to include customer names in `search_tickets_in_db`

### Phase 2 (High Priority)
3. Add `search_by_customer` tool
4. Add `detect_critical_patterns` tool
5. Update misleading tool descriptions

### Phase 3 (Nice to Have)
6. Add `get_tickets_by_merchant` tool
7. Add `get_issue_summary` tool
8. Add date range filtering to search

## 6. Testing Plan

### 6.1 Test Scenarios
1. **Search for SinglesSwag tickets** - Should find all variations:
   - By email: "@singlesswag.com"
   - By name: "Mary Beskin"
   - By company: "SinglesSwag"

2. **Critical pattern detection** - Should identify:
   - Multiple payment failures
   - Service outages
   - Angry customer clusters

3. **Raw data tools** - Should clearly indicate:
   - No analysis provided
   - User must review manually

### 6.2 Success Metrics
- CJ stops hallucinating analysis that wasn't performed
- CJ can find tickets by customer name/company
- CJ correctly identifies real systemic issues
- Reduced number of failed tool calls

## 7. Workflow Integration for Pagination

### 7.1 Update support_daily Workflow
The workflow should be updated to handle paginated results intelligently:

```yaml
# In support_daily.yaml workflow section:
When using get_recent_tickets_for_review:
1. Start with first page (no cursor)
2. Analyze the tickets for critical patterns
3. If critical issues found in first 20, stop and report
4. If no critical issues but has_more=true, optionally continue:
   - "No critical issues in first 20 tickets. Should I check more? (next_cursor available)"
5. Allow merchant to request deeper analysis with pagination
```

### 7.2 Agent Behavior Guidelines
```python
# The agent should:
1. Always start with the first page (20 tickets)
2. Look for patterns that appear multiple times
3. Prioritize recent and high-priority tickets
4. Only paginate if:
   - Merchant explicitly asks to see more
   - A pattern needs more data to confirm
   - Searching for a specific issue not found yet
5. Include pagination state in responses:
   - "Reviewed 20 most recent tickets (more available)"
   - "Found issue in 3 of 20 tickets checked so far"
```

## 8. Migration Notes

### 8.1 Backward Compatibility
- Keep old tool names as aliases temporarily
- Log deprecation warnings when old names used
- Remove aliases after 2 weeks

### 8.2 Update Dependencies
- Update `support_daily.yaml` workflow to use new tool names
- Update any other workflows using these tools
- Update tool documentation

### 8.3 Database Indexes
Ensure proper indexes exist for pagination performance:
```sql
CREATE INDEX idx_unified_tickets_pagination 
ON v_freshdesk_unified_tickets(merchant_id, created_at DESC, freshdesk_ticket_id DESC);
```

This plan addresses the core issues while maintaining system stability and improving the support daily workflow's effectiveness.