# Support Analytics Agent - Usage Scenarios & Examples

This document provides real-world scenarios and example questions that demonstrate the analytics capabilities of the support_daily workflow agent.

## Overview

The support analytics agent provides comprehensive insights into your support operations through natural language queries. It can analyze ticket volumes, response times, customer satisfaction, SLA compliance, and detect unusual patterns.

## Available Analytics Tools

### 1. Daily Snapshot (`get_daily_snapshot`)
**Purpose**: Get a comprehensive overview of support metrics for any specific day.

**Example Questions**:
- "What were our support metrics yesterday?"
- "Show me the daily snapshot for January 10th"
- "How many tickets did we handle on Monday?"

**Example Output**:
```
📊 Daily Support Snapshot for 2024-01-10:

📥 Volume Metrics:
• New Tickets: 45
• Closed Tickets: 42
• Open at EOD: 23

⏱️ Response Times:
• Median First Agent Response: 8 min
• Median Resolution: 3h 5m
• Quick Closes (<10min): 12

😊 Customer Satisfaction:
• New Ratings: 15
• CSAT Score: 86.7% (perfect scores)
• Bad Ratings (<Very Happy): 2

🚨 SLA Performance:
• Breaches: 1
```

### 2. CSAT Detail Analysis (`get_csat_detail_log`)
**Purpose**: Deep dive into customer satisfaction ratings with optional full conversation history.

**Example Questions**:
- "Show me all CSAT ratings from yesterday with conversations for the bad ones"
- "What feedback did unhappy customers give today?"
- "Analyze negative CSAT ratings from the past week including full conversations"

**Example Output**:
```
📊 Detailed CSAT Log for 2024-01-10:

Summary:
• Total Surveys: 15
• Average Rating: 102.1 
• Below Threshold (<102): 3 (20.0%)

❌ Negative Ratings:

Ticket #123 - Happy (101)
• Customer: john@example.com
• Agent: support@company.com
• Response Time: 5 min
• Resolution Time: 45 min
• Conversations: 3
• Tags: shipping, damaged
• Feedback: "Quick response but didn't fully solve my issue"

📧 Full Conversation:
- From: john@example.com at 2024-01-10T14:00:00Z
  "My package arrived damaged..."
  
- From: support@company.com at 2024-01-10T14:05:12Z
  "I'm sorry to hear that. Let me help..."
```

### 3. Open Ticket Distribution (`get_open_ticket_distribution`)
**Purpose**: Monitor backlog health and identify aging tickets.

**Example Questions**:
- "Show me the age distribution of open tickets"
- "What are our oldest unresolved tickets?"
- "How's our ticket backlog looking?"

**Example Output**:
```
📊 Open Ticket Distribution Analysis:

Backlog Overview:
• Total Open Tickets: 523

Age Distribution:
• 0-4h:   8 tickets ( 1.5%) █
• 4-24h: 10 tickets ( 1.9%) █
• 1-2d:   3 tickets ( 0.6%) 
• 3-7d:   1 tickets ( 0.2%) 
• >7d:  501 tickets (95.8%) ████████████████████

⚠️ Alert: 501 ticket(s) older than 7 days!

10 Oldest Open Tickets:
1. 🔴 Ticket #1234 - 45d 3h old
   Subject: Order never arrived
   Status: Waiting on Customer
   Customer: upset@customer.com
   Tags: shipping, missing
```

### 4. Response Time Metrics (`get_response_time_metrics`)
**Purpose**: Analyze team performance with statistical insights.

**Example Questions**:
- "Analyze our response times for the past week"
- "Show me resolution time statistics"
- "How fast are we resolving tickets?"

**Example Output**:
```
📊 Response Time Performance Analysis (7 days):

⏱️ First Response Times:
• Median: 8m
• Average: 12m
• 25th percentile: 3m (25% respond faster)
• 75th percentile: 18m (75% respond faster)
• 95th percentile: 45m (95% respond faster)

⚠️ Outliers (>2σ from mean): 3 tickets
   - Ticket #789: 3h 1m

🚀 Quick Resolution Performance:
Total Resolved: 120 tickets

• <5min:  18 (15.0%) ███ (CSAT: 4.8/5)
• <10min: 32 (26.7%) █████ (CSAT: 4.6/5)
• <30min: 65 (54.2%) ██████████ (CSAT: 4.3/5)
• <60min: 78 (65.0%) █████████████ (CSAT: 4.1/5)

😊 CSAT vs Response Speed:
• ultra_fast_<5min: 18 tickets, avg rating: 😊 102.8
• fast_5-30min: 47 tickets, avg rating: 😊 102.1
• normal_30-180min: 35 tickets, avg rating: 😊 101.5
• slow_>180min: 20 tickets, avg rating: 😐 100.2

💡 Key Insights:
✅ Excellent median first response time: 8m
✅ 54.2% of tickets resolved within 30 minutes
✅ Faster resolutions correlate with higher satisfaction
```

### 5. Volume Trend Analysis (`get_volume_trends`)
**Purpose**: Detect spikes, patterns, and trends in ticket volume.

**Example Questions**:
- "Show me ticket volume trends for the past 60 days"
- "Have we had any ticket spikes recently?"
- "Is our support volume increasing or decreasing?"

**Example Output**:
```
📊 Ticket Volume Trend Analysis (60 days):

Summary Statistics:
• Average Daily Volume: 35.6 tickets
• Standard Deviation: ±12.3 tickets
• Spike Threshold: 60.2 tickets (>2σ)
• Total Tickets: 2,136 over 60 days

Trend Analysis:
• Overall Trend: INCREASING 📈 15.2%
• Highest Volume: 304 tickets on 2024-05-26
• Lowest Volume: 8 tickets on 2024-04-15

🚨 Spike Days Detected (5 total):
• 2024-05-26: 304 tickets (8.5σ above average)
• 2024-11-29: 89 tickets (2.8σ above average)

📅 Last 7 Days:
• 2024-01-10: 45 tickets ████████
• 2024-01-09: 38 tickets ███████
• 2024-01-08: 41 tickets ████████
• 2024-01-07: 35 tickets ███████
• 2024-01-06: 32 tickets ██████
• 2024-01-05: 48 tickets █████████ 🚨 SPIKE
• 2024-01-04: 31 tickets ██████

💡 Key Insights:
📈 Volume is trending UP by 15.2%
⚠️ High variability in daily volumes - consider staffing flexibility
```

### 6. SLA Exception Monitoring (`get_sla_exceptions`)
**Purpose**: Track SLA compliance and identify breach patterns.

**Example Questions**:
- "Show me all SLA breaches"
- "Which tickets are exceeding our 1-hour response time?"
- "Find tickets that haven't been resolved within 24 hours"

**Example Output**:
```
🚨 SLA Exception Report:

Current SLA Thresholds:
• First Response: 60 minutes (1.0 hours)
• Resolution: 1440 minutes (24.0 hours)
• Including Pending Tickets: Yes

Summary:
• Total SLA Breaches: 127
• Response Breaches: 15 (avg overage: 89 min)
• Resolution Breaches: 112 (avg overage: 1,523 min)
• Tickets with No Response: 3

❌ First Response SLA Breaches (worst first):
1. #567 - NO RESPONSE YET
   Subject: Urgent: Product defect causing injury
   Created: 2024-01-10T08:00:00Z
   Overdue by: 245 min (4.1 hours)
   Priority: 4 | Status: Open

⏰ Resolution SLA Breaches (worst first):
1. #890 - 2880 min (2.0 days)
   Subject: Missing parts in shipment
   Overdue by: 1440 min (1.0 days)
   Status: STILL OPEN | Priority: 3

📊 Breach Patterns:
By Priority Level:
• Urgent: 5 breaches (avg 156 min over SLA)
• High: 23 breaches (avg 98 min over SLA)

Most Common Tags in Breaches:
• shipping: 45 breaches
• damaged: 28 breaches

💡 Key Insights:
⚠️ 3 tickets have received no response at all
🔴 5 urgent priority tickets breached response SLA
⏳ 89 tickets are still open and breaching resolution SLA
```

### 7. Root Cause Analysis (`get_root_cause_analysis`)
**Purpose**: Understand what's driving ticket spikes on specific dates.

**Example Questions**:
- "What caused the spike in tickets on May 26th?"
- "Analyze root causes for today's high ticket volume"
- "Why did we get so many tickets yesterday?"

**Example Output**:
```
🔍 Root Cause Analysis for 2024-05-26:

Volume Overview:
• Total Tickets: 304
• Historical Average: 35.6 (±12.3)
• Normal Range: 11 - 60 tickets
• Deviation: 8.5σ from mean
• Spike Detected: 🚨 YES

📊 Tag Analysis (Top Issues):

1. #MARK_AS_SPAM_AND_CLOSE - 112 tickets (+999.9%)
   Normal: 2.1 | Increase: +109.9 tickets
   Example tickets:
   • #12345: Spam - weight loss pills...
   • #12346: Spam - crypto investment...

2. shipping - 89 tickets (+387%)
   Normal: 18.3 | Increase: +70.7 tickets
   Example tickets:
   • #12347: Package stuck in transit for 2 weeks...

3. memorial-day-sale - 45 tickets (NEW)
   Normal: 0.0 | Increase: +45.0 tickets

💡 Insights:
• Major spike driven by '#MARK_AS_SPAM_AND_CLOSE' issues (+999.9%)
• Memorial Day period - expect shipping delays and order issues
• Multiple shipping-related tags suggest delivery system issues

📌 Recommended Actions:
• Check with shipping partners for delays or system issues
• Alert support team about increased volume
• Review example tickets to understand customer pain points
• Update knowledge base for trending issues
```

## Common Workflow Scenarios

### Scenario 1: Daily Morning Briefing
**User**: "Give me a complete support overview for yesterday"

**Agent Actions**:
1. Calls `get_daily_snapshot` for yesterday's metrics
2. Calls `get_open_ticket_distribution` to check backlog health
3. Calls `get_csat_detail_log` if there were bad ratings
4. Summarizes key insights and areas of concern

### Scenario 2: Spike Investigation
**User**: "We're getting a lot of tickets today, what's happening?"

**Agent Actions**:
1. Calls `get_volume_trends` to confirm if today is a spike
2. Calls `get_root_cause_analysis` for today's date
3. Identifies top tags and provides example tickets
4. Suggests potential causes and remediation

### Scenario 3: Performance Review
**User**: "How's our support team performing this week?"

**Agent Actions**:
1. Calls `get_response_time_metrics` for 7-day analysis
2. Calls `get_sla_exceptions` to check compliance
3. Calls `calculate_csat_score` for satisfaction trends
4. Provides balanced assessment with specific metrics

### Scenario 4: Customer Experience Deep Dive
**User**: "Why are customers unhappy with our support?"

**Agent Actions**:
1. Calls `get_csat_detail_log` with `include_conversations=True`
2. Analyzes conversation patterns in negative ratings
3. Identifies common failure points
4. Suggests specific improvements based on actual interactions

### Scenario 5: Backlog Management
**User**: "Which tickets should we prioritize today?"

**Agent Actions**:
1. Calls `get_open_ticket_distribution` for aging analysis
2. Calls `get_sla_exceptions` for breach identification
3. Highlights oldest tickets and urgent breaches
4. Provides actionable prioritization list

## Tips for Effective Use

1. **Be Specific with Dates**: "Show me metrics for January 10th" works better than "recent metrics"

2. **Combine Multiple Insights**: Ask for comprehensive views like "Give me a full support health check for this week"

3. **Investigate Anomalies**: When you see spikes or unusual patterns, follow up with "What caused the spike on [date]?"

4. **Include Context**: For CSAT analysis, specify "include full conversations" to get detailed interaction history

5. **Set Custom Thresholds**: For SLA monitoring, you can specify custom thresholds like "Show me tickets exceeding 2-hour response time"

## Integration with Daily Workflow

The support_daily workflow automatically runs these analytics to generate:
- Daily performance summary
- Backlog health status
- CSAT trends and concerns
- SLA compliance report
- Spike detection and root cause analysis
- Prioritized action items
- Team performance insights

This enables proactive support management without manual analysis.