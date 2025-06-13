# Analytics Quick Start Guide

## Getting Started with Support Analytics

The support_daily workflow provides powerful analytics capabilities. Here's how to use them effectively.

## Quick Examples

### 1. Daily Health Check
```
You: "Give me yesterday's support metrics"

CJ will use: get_daily_snapshot
Returns: Volume metrics, response times, CSAT scores, SLA breaches
```

### 2. Find Problem Tickets
```
You: "Show me bad CSAT ratings with full conversations"

CJ will use: get_csat_detail_log with include_conversations=True
Returns: Negative ratings with complete interaction history
```

### 3. Monitor Backlog
```
You: "How old are our open tickets?"

CJ will use: get_open_ticket_distribution
Returns: Age distribution and details of oldest tickets
```

### 4. Detect Anomalies
```
You: "Have we had any ticket spikes recently?"

CJ will use: get_volume_trends
Returns: Daily volumes with spike detection
```

### 5. Check SLA Compliance
```
You: "Which tickets are breaching our SLAs?"

CJ will use: get_sla_exceptions
Returns: Tickets exceeding response/resolution thresholds
```

## Common Workflows

### Morning Standup
1. "Give me a complete support overview for yesterday"
2. Review metrics, identify issues
3. "Show me the oldest open tickets"
4. Prioritize team's work for the day

### Weekly Review
1. "Analyze our performance for the past week"
2. "Show me CSAT trends"
3. "Have we had any spikes?"
4. "What are our common SLA breaches?"

### Issue Investigation
1. "What caused the spike on [date]?"
2. "Show me bad ratings from that day with conversations"
3. Review patterns and root causes
4. Create action items

## Tips

- **Be specific with dates**: "January 10th" not "recently"
- **Ask for conversations**: Add "with full conversations" for CSAT analysis
- **Set custom SLAs**: "tickets exceeding 2-hour response time"
- **Combine insights**: "Give me a full health check"

## All Available Tools

1. **get_daily_snapshot** - Daily metrics overview
2. **get_csat_detail_log** - CSAT analysis with conversations
3. **get_open_ticket_distribution** - Backlog age analysis
4. **get_response_time_metrics** - Performance statistics
5. **get_volume_trends** - Spike detection
6. **get_sla_exceptions** - SLA breach monitoring
7. **get_root_cause_analysis** - Spike investigation