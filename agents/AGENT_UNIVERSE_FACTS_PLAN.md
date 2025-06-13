# Agent Universe Facts Planning Document

## Overview
This document outlines the plan to build a comprehensive data agent that can perform daily support team analytics and insights. The agent will operate within the `support_daily` workflow to provide managers with automated daily health snapshots, CSAT analysis, ticket metrics, issue investigation, systemic issue detection, spike detection, etc.

## Current State Analysis
- **Existing Infrastructure**: Unified ticket view with comprehensive ticket, conversation, and rating data
- **Available Data**: Full Freshdesk ticket lifecycle, CSAT ratings, conversation history, timestamps
- **Integration Points**: CrewAI tools via database_tools.py, support_daily workflow
- **Missing Components**: Time-series analytics, spike detection, SLA tracking, root cause analysis

## Stage 1: Foundation Reset and Function Planning

### Stage 1.1: Clean Slate ✅ COMPLETE
**Objective**: Remove existing implementation to start fresh with focused functionality
- ✅ Renamed files to freshdesk_analytics_lib.py
- ✅ Cleared content from both library and test files
- ✅ Deleted old insight lib after migration

### Stage 1.2: Function Identification
**Objective**: Define all functions needed for the 7 daily artifacts

**CRITICAL REQUIREMENT**: All agent-facing functions MUST take merchant_id as the first parameter. NEVER look up merchants by name - always use the merchant_id for all queries. This ensures data isolation and prevents cross-merchant data leakage.

**Workflow**: UPDATE THIS DOCUMENT AS YOU GO

#### Core Analytics Functions
1. **get_daily_snapshot(merchant_id, date)**
   - Returns: new_tickets, closed_tickets, open_eod, median_first_response_min, median_resolution_min, quick_close_count, new_csat_count, avg_csat, bad_csat_count, sla_breaches
   - Requires: Ticket creation/close timestamps, status tracking, response time calculations
   - Output Schema:
     ```python
     {
         "date": "2024-01-10",
         "new_tickets": 45,
         "closed_tickets": 42,
         "open_eod": 23,  # Open at end of day
         "median_first_response_min": 8.5,
         "median_resolution_min": 185.0,
         "quick_close_count": 12,  # Closed <10min
         "new_csat_count": 15,
         "avg_csat": 4.2,  # 1-5 scale
         "bad_csat_count": 2,  # ≤3 rating
         "sla_breaches": 1
     }
     ```

2. **get_csat_detail_log(merchant_id, date, rating_threshold=102, include_conversations=False)**
   - Returns: List of CSAT surveys with ticket_id, rating, agent, response_times
   - NEW: Optional full conversation history for bad ratings
   - Requires: Rating data, ticket metadata, conversation timestamps, conversation bodies
   - Output Schema:
     ```python
     {
         "surveys": [
             {
                 "ticket_id": 123,
                 "rating": 101,  # Freshdesk scale: -103 to 103
                 "rating_label": "Happy",
                 "feedback": "Quick response but didn't fully solve my issue",
                 "agent": "support@example.com",
                 "customer_email": "customer@example.com",
                 "tags": ["shipping", "damaged"],
                 "created_at": "2024-01-10T14:30:00Z",
                 "first_response_min": 5.2,
                 "resolution_min": 45.8,
                 "conversation_count": 3,
                 "conversations": [  # Only included if include_conversations=True AND rating < threshold
                     {
                         "from": "customer@example.com",
                         "to": "support@example.com",
                         "timestamp": "2024-01-10T14:00:00Z",
                         "body": "My package arrived damaged...",
                         "type": "customer"  # or "agent", "note"
                     },
                     {
                         "from": "support@example.com",
                         "to": "customer@example.com", 
                         "timestamp": "2024-01-10T14:05:12Z",
                         "body": "I'm sorry to hear that. Let me help...",
                         "type": "agent"
                     }
                 ]
             }
         ],
         "total_count": 15,
         "below_threshold_count": 3,
         "avg_rating": 102.1
     }
     ```

3. **get_open_ticket_distribution(merchant_id)**
   - Returns: Tickets grouped by age buckets (0-4h, 4-24h, 1-2d, 3-7d, >7d)
   - Returns: Top 10 oldest tickets with details
   - Requires: Current timestamp comparison, status filtering
   - Output Schema:
     ```python
     {
         "age_buckets": {
             "0-4h": {"count": 8, "percentage": 34.8},
             "4-24h": {"count": 10, "percentage": 43.5},
             "1-2d": {"count": 3, "percentage": 13.0},
             "3-7d": {"count": 1, "percentage": 4.3},
             ">7d": {"count": 1, "percentage": 4.3}
         },
         "total_open": 23,
         "oldest_tickets": [
             {
                 "ticket_id": 456,
                 "subject": "Order never arrived",
                 "age_hours": 168.5,
                 "age_display": "7d 1h",
                 "status": "Open",
                 "priority": 3,
                 "tags": ["shipping", "missing"],
                 "customer_email": "upset@customer.com",
                 "last_updated": "2024-01-03T12:30:00Z"
             }
         ]
     }
     ```

4. **get_response_time_metrics(merchant_id, date_range)**
   - Returns: Distribution of first response and resolution times with percentiles
   - Returns: Quick resolution benchmarks (<5min, <10min, <30min, <60min)
   - Returns: Median values, outliers (>2σ), and CSAT correlation
   - Requires: Conversation timestamp analysis, statistical calculations
   - Output Schema:
     ```python
     {
         "first_response": {
             "median_min": 8.5,
             "mean_min": 12.3,
             "p25_min": 3.2,
             "p75_min": 18.7,
             "p95_min": 45.2,
             "outliers": [  # >2σ from mean
                 {"ticket_id": 789, "response_min": 180.5}
             ]
         },
         "resolution": {
             "median_min": 185.0,
             "mean_min": 245.8,
             "p25_min": 45.0,
             "p75_min": 380.0,
             "p95_min": 720.0,
             "outliers": [
                 {"ticket_id": 101, "resolution_min": 2880.0}
             ]
         },
         "quick_resolutions": {
             "<5min": {"count": 18, "percentage": 15.0, "avg_csat": 4.8},
             "<10min": {"count": 32, "percentage": 26.7, "avg_csat": 4.6},
             "<30min": {"count": 65, "percentage": 54.2, "avg_csat": 4.3},
             "<60min": {"count": 78, "percentage": 65.0, "avg_csat": 4.1}
         },
         "total_resolved": 120,
         "csat_by_speed": {
             "ultra_fast_<5min": {"count": 18, "avg_rating": 102.8},
             "fast_5-30min": {"count": 47, "avg_rating": 102.1},
             "normal_30-180min": {"count": 35, "avg_rating": 101.5},
             "slow_>180min": {"count": 20, "avg_rating": 100.2}
         }
     }
     ```

5. **get_volume_trends(merchant_id, days=60)**
   - Returns: Daily ticket counts, 7-day rolling average, spike detection (>2σ)
   - Requires: Time series analysis, standard deviation calculations
   - Output Schema:
     ```python
     {
         "daily_volumes": [
             {
                 "date": "2024-01-10",
                 "new_tickets": 45,
                 "is_spike": True,  # >2σ from 7-day avg
                 "deviation": 2.3  # Standard deviations from mean
             },
             # ... more days
         ],
         "summary": {
             "avg_daily_volume": 28.5,
             "std_dev": 7.2,
             "spike_threshold": 42.9,  # avg + 2σ
             "spike_days": [
                 {"date": "2024-01-10", "volume": 45, "deviation": 2.3}
             ],
             "trend": "increasing",  # or "stable", "decreasing"
             "trend_percentage": 15.2  # % change over period
         },
         "rolling_7d_avg": [
             {"date": "2024-01-10", "avg": 32.1},
             # ... more days
         ]
     }
     ```

6. **get_root_cause_analysis(merchant_id, date, spike_threshold=2)**
   - Returns: Tag/product breakdown when spike detected
   - Returns: Delta from average, example tickets
   - Requires: Tag extraction, comparative analysis
   - Output Schema:
     ```python
     {
         "spike_detected": True,
         "date": "2024-01-10",
         "total_tickets": 45,
         "normal_range": [20, 35],  # Based on historical avg ± 2σ
         "deviation": 2.3,  # Standard deviations above mean
         "tag_analysis": [
             {
                 "tag": "shipping",
                 "today_count": 25,
                 "avg_count": 8.2,
                 "delta": 16.8,
                 "percentage_increase": 204.9,
                 "example_tickets": [
                     {
                         "ticket_id": 234,
                         "subject": "Package stuck in transit for 2 weeks",
                         "created_at": "2024-01-10T09:15:00Z"
                     }
                 ]
             },
             {
                 "tag": "damaged",
                 "today_count": 12,
                 "avg_count": 3.1,
                 "delta": 8.9,
                 "percentage_increase": 287.1,
                 "example_tickets": []
             }
         ],
         "untagged_count": 8,
         "insights": "Major spike driven by shipping issues (+205%), possibly weather-related delays"
     }
     ```

7. **get_sla_exceptions(merchant_id, sla_config)**
   - Returns: Tickets breaching response/resolution SLAs
   - Returns: Patterns in breaches
   - Requires: SLA threshold configuration, time calculations
   - Output Schema:
     ```python
     {
         "sla_config": {
             "first_response_min": 60,  # 1 hour SLA
             "resolution_min": 1440,  # 24 hour SLA
             "business_hours_only": True
         },
         "breaches": {
             "first_response": [
                 {
                     "ticket_id": 567,
                     "subject": "Urgent: Product defect causing injury",
                     "created_at": "2024-01-10T08:00:00Z",
                     "first_response_at": "2024-01-10T10:45:00Z",
                     "response_time_min": 165,
                     "breach_by_min": 105,  # 105 min over SLA
                     "status": "Open",
                     "priority": 4,
                     "tags": ["urgent", "safety"]
                 }
             ],
             "resolution": [
                 {
                     "ticket_id": 890,
                     "subject": "Missing parts in shipment",
                     "created_at": "2024-01-08T14:00:00Z",
                     "resolution_time_min": 2880,
                     "breach_by_min": 1440,  # 24 hours over SLA
                     "status": "Pending",
                     "assigned_agent": "support@example.com"
                 }
             ]
         },
         "summary": {
             "total_breaches": 12,
             "response_breaches": 3,
             "resolution_breaches": 9,
             "breach_rate": 10.0,  # % of total tickets
             "common_tags": ["shipping", "damaged"],
             "worst_breach_min": 2880
         }
     }
     ```

#### Supporting Functions
8. **calculate_business_hours(start_time, end_time)**
   - Handles business hours calculations for accurate SLA tracking

9. **extract_product_from_ticket(ticket)**
   - Parses ticket content/tags for product identification

10. **aggregate_by_time_bucket(tickets, bucket_size)**
    - Generic time-based aggregation for various metrics

11. **get_bad_csat_analysis(merchant_id, date_range, auto_fetch_conversations=True)**
    - Specialized function for deep-diving into negative CSAT ratings
    - Automatically fetches full conversation history for bad ratings
    - Groups issues by common themes in feedback
    - Identifies problematic agent interactions
    - Output includes conversation snippets showing where things went wrong

### Stage 1.3: Daily Snapshot Implementation ✅ COMPLETE
**Objective**: Build the core daily health metrics function
- ✅ Implemented `get_daily_snapshot()` with proper merchant_id filtering
- ✅ Fixed CSAT calculation to be % of perfect scores (103 rating only)
- ✅ Added time formatting (9h 59m instead of 599.3 min)
- ✅ Confirmed first_responded_at is already "first agent response"
- ✅ Written comprehensive tests covering edge cases
- ✅ Updated database_tools.py to expose as CrewAI tool
- ✅ Made it the default tool in support_daily workflow
- ✅ Migrated all functions from insight_lib to analytics_lib

### Stage 1.4: CSAT Analysis Implementation ✅ COMPLETE → NEEDS ENHANCEMENT
**Objective**: Deep dive into customer satisfaction
- ✅ Implemented `get_csat_detail_log()` with detailed survey data
- ✅ Included feedback, response times, and conversation counts
- ✅ Written tests for various rating scenarios including edge cases
- ✅ Exposed as CrewAI tool in database_tools.py
- ✅ Fixed conversation count query to work with JSONB data structure
- 🔄 **ENHANCEMENT NEEDED**: Add `include_conversations` parameter
  - When True, include full conversation history for tickets below threshold
  - Helps identify what went wrong in bad interactions
  - Essential for root cause analysis and agent coaching

### Stage 1.5: Open Ticket Tracking ✅ COMPLETE
**Objective**: Monitor backlog health
- ✅ Implemented `get_open_ticket_distribution()` with age buckets
- ✅ Created age bucket calculations (0-4h, 4-24h, 1-2d, 3-7d, >7d)
- ✅ Identifies 10 oldest tickets with full details
- ✅ Written tests for various backlog states
- ✅ Exposed as CrewAI tool with formatted output
- ✅ Includes visual indicators (priority emojis, bar charts)
- 📊 **Real data shows**: 95.9% of tickets are >7 days old!

### Stage 1.6: Response Time Analytics ✅ COMPLETE
**Objective**: Track team performance metrics
- ✅ Implemented `get_response_time_metrics()` with full statistical analysis
- ✅ Calculates percentiles (p25, p50, p75, p95) and outlier detection (>2σ)
- ✅ Quick resolution buckets with CSAT correlation
- ✅ Speed categories showing impact on customer satisfaction
- ✅ Written comprehensive tests covering all edge cases
- ✅ Added numpy to requirements.txt for statistical calculations
- ✅ Exposed as CrewAI tool with formatted output
- 📊 **Real data insights**: 0.4 min median response, 599 min median resolution, 38.5% <5min

### Stage 1.7: Volume Trend Analysis ✅ COMPLETE
**Objective**: Detect unusual patterns
- ✅ Implemented `get_volume_trends()` with 60-day default analysis
- ✅ Statistical spike detection using 2σ threshold
- ✅ 7-day rolling averages for trend smoothing
- ✅ Week-over-week trend comparison
- ✅ Exposed as CrewAI tool with visual formatting
- ✅ Identifies highest/lowest volume days and zero-ticket days
- 📊 **Real data insights**: Memorial Day spike (304 tickets), current avg 35.6/day, high variability

### Stage 1.8: Root Cause Intelligence  # SKIP THIS STEP, WE DONT HAVE PRODUCT ATTRIBUTION YET
**Objective**: Understand spike drivers
- Implement `get_root_cause_analysis()`
- Tag and product attribution logic
- Example ticket selection
- Test with various spike scenarios

### Stage 1.9: SLA Monitoring ✅
**Objective**: Ensure service level compliance
- ✅ Implement `get_sla_exceptions()` with session parameter
- ✅ Configurable SLA thresholds (first_response_min, resolution_min, include_pending)
- ✅ Pattern detection in breaches (by priority, by tags)
- ✅ Test with various SLA configurations (default, strict, relaxed)
- ✅ CrewAI tool wrapper with formatted output

**Key Features Implemented**:
- Tracks both first response and resolution SLA breaches
- Identifies tickets with no response at all
- Shows patterns by priority level and common tags
- Handles still-open tickets that are breaching SLA
- Provides insights on urgent tickets and escalations

### Stage 1.10: Workflow Integration ✅ COMPLETE
**Objective**: Make sure everything is connected to the agent
- ✅ Audited database_tools.py - all analytics functions properly exposed
- ✅ Enhanced support_daily workflow prompts with new analytics capabilities
- ✅ Added CSAT conversation analysis to workflow
- ✅ Tested end-to-end workflow execution
- ✅ Updated all analytics functions to accept session parameter (no more internal session creation)
- ✅ Fixed all indentation issues in freshdesk_analytics_lib.py
- ✅ Updated all tool wrappers in database_tools.py to pass session parameter

**Key Improvements**:
- All analytics functions now follow consistent session management pattern
- Workflow can request full conversation history for bad CSAT ratings
- Agent has access to comprehensive analytics toolkit for daily support operations
- Proper data isolation maintained with merchant_id filtering

### Stage 1.11 Update the documentation
**Objective**: Make it so it's easy to understand the AI agent's current list of capabilties
- Write example user stories / scenarios that show what kinds of questions to ask the support_daily agent to yield corresponding tool calls
- Do this by generating a script to test inputs and outputs with the agent, get the actual example text, and put them in the correct places. They should at least be referenced in the README.md or QUICKSTART.md if not fully documented in one of those locations.

## Stage 1b
- Document best practices for sqlalchemy model code (keep it slim, never import from libs, it's ok to import from utils but models should be really thin and contain almost no business logic). Also cover other sqla usage best practices. Make sure those are included in the README. Show me what changes you made there.

## Stage 2: Advanced Analytics (Future)

### Stage 2.1: Predictive Metrics
- Ticket volume forecasting
- CSAT trend prediction
- Resource planning recommendations

### Stage 2.2: Comparative Analysis
- Week-over-week comparisons
- Seasonal pattern detection
- Benchmark tracking

### Stage 2.3: Agent Performance
- Individual agent metrics
- Team efficiency analysis
- Training need identification

## Stage 3: Shopify Integration (Future)

### Stage 3.1: Order Context
- Link tickets to order data
- Product performance correlation
- Customer lifetime value impact

### Stage 3.2: Revenue Impact
- Support cost per order
- CSAT to retention correlation
- High-value customer identification

## Implementation Guidelines

### Data Isolation Requirements
- **CRITICAL**: Every function MUST filter by merchant_id as the first operation
- **NEVER** accept merchant names as input - only merchant_id
- **NEVER** perform merchant lookups by name within these functions
- All SQL queries must include `WHERE merchant_id = ?` clause
- No function should ever return data from multiple merchants
- If a merchant_id is invalid or has no data, return empty results, not an error

### Data Considerations
- All timestamps should handle timezone conversions properly
- Business hours calculations must account for weekends/holidays
- Metrics should be cacheable for performance
- Results should be formatted for easy agent consumption

### Testing Requirements
- Each function needs unit tests with mock data
- Integration tests with actual database queries
- Edge case coverage (empty results, null values, etc.)
- Performance tests for large datasets

### Tool Integration
- Each function exposed via @tool decorator
- Clear descriptions for agent understanding
- Proper error handling and messaging
- Formatted output suitable for workflow context

## Success Metrics
- Agent can generate daily brief in <30 seconds
- All 7 artifacts accurately reproduced
- Spike detection catches 95%+ of anomalies
- Zero false positives in SLA breach detection
- Manager approval of automated insights

## Next Steps
1. Review and approve this plan
2. Begin Stage 1.1 implementation
3. Iterate on each stage with testing
4. Deploy to support_daily workflow
5. Gather feedback and refine