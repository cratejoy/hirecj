# Example CSAT Detail Log Output

## 1. Direct Function Call Output

When calling `FreshdeskAnalytics.get_csat_detail_log()` directly, you get a structured dictionary:

```python
{
    "surveys": [
        {
            "ticket_id": 234,
            "rating": -101,  # Freshdesk scale
            "rating_label": "Very Unhappy",
            "feedback": "Agent was rude and didn't solve my problem",
            "agent": "support@example.com",
            "customer_email": "angry.customer@gmail.com",
            "tags": ["shipping", "damaged"],
            "created_at": "2024-01-10T15:30:00Z",
            "first_response_min": 145.2,  # 2h 25m
            "resolution_min": None,  # Still open
            "conversation_count": 5
        },
        {
            "ticket_id": 567,
            "rating": 101,
            "rating_label": "Happy",
            "feedback": "",
            "agent": "agent2@example.com",
            "customer_email": "satisfied@customer.com",
            "tags": ["refund"],
            "created_at": "2024-01-10T12:15:00Z",
            "first_response_min": 8.5,
            "resolution_min": 45.3,
            "conversation_count": 3
        },
        {
            "ticket_id": 890,
            "rating": 103,
            "rating_label": "Extremely Happy",
            "feedback": "Amazing service! So quick and helpful!",
            "agent": "star.agent@example.com",
            "customer_email": "happy@customer.com",
            "tags": ["product-question"],
            "created_at": "2024-01-10T09:00:00Z",
            "first_response_min": 2.1,
            "resolution_min": 12.7,
            "conversation_count": 2
        }
    ],
    "total_count": 15,
    "below_threshold_count": 3,  # Ratings below 102
    "avg_rating": 95.4
}
```

## 2. CrewAI Tool Output

When called as a CrewAI tool, the output is formatted for the agent:

```
📊 Detailed CSAT Log for 2024-01-10:
            
**Summary:**
• Total Surveys: 15
• Average Rating: 95.4 
• Below Threshold (<102): 3 (20.0%)

**Individual Survey Details:**

❌ **Negative Ratings:**

Ticket #234 - Very Unhappy (-101)
• Customer: angry.customer@gmail.com
• Agent: support@example.com
• Response Time: 2h 25m
• Resolution Time: N/A
• Conversations: 5
• Tags: shipping, damaged
• Feedback: "Agent was rude and didn't solve my problem"

Ticket #456 - Unhappy (-100)
• Customer: frustrated@customer.com
• Agent: unassigned
• Response Time: 3h 45m
• Resolution Time: 8h 30m
• Conversations: 8
• Tags: None
• Feedback: "No feedback provided"

✅ **Positive Ratings:**

Ticket #890 - Extremely Happy (103)
• Customer: happy@customer.com
• Response: 2 min | Resolution: 12 min

Ticket #123 - Very Happy (102)
• Customer: content@customer.com
• Response: 5 min | Resolution: 30 min

... and 10 more positive ratings

Data Source: Live database analytics
```

## 3. Usage in Support Daily Workflow

In the context of the support_daily workflow, CJ might analyze the data like this:

```
Based on today's CSAT analysis, I've identified some concerning patterns:

📉 **Key Issues:**
- 20% of ratings were negative (below "Very Happy")
- Average response time for negative ratings: 2.5 hours
- Main complaint themes: shipping delays and product damage

🎯 **Action Items:**
1. **Shipping Issues** - 2 tickets mentioned damaged products in transit
   - Consider reviewing packaging procedures
   - May need to escalate to shipping partner

2. **Response Time Correlation** - All negative ratings had >2 hour first response
   - Current SLA may need adjustment
   - Consider prioritizing based on ticket urgency

3. **Agent Performance** - One agent (support@example.com) received multiple negative ratings
   - May benefit from additional training
   - Review conversation for coaching opportunities

💡 **Positive Highlights:**
- Star performer: star.agent@example.com with 100% perfect scores
- Quick resolutions (<15 min) consistently receive "Extremely Happy" ratings
```

## 4. Common Use Cases

### A. Daily Manager Brief
```python
# Get yesterday's CSAT details for morning standup
yesterday = date.today() - timedelta(days=1)
csat_data = get_csat_detail_log(date_str=yesterday.isoformat())
```

### B. Weekly Trend Analysis
```python
# Analyze CSAT with stricter threshold for weekly review
# Only count "Extremely Happy" as positive
csat_data = get_csat_detail_log(
    date_str="2024-01-10",
    rating_threshold=103  # Only perfect scores
)
```

### C. Investigation Mode
```python
# When spike in complaints detected, get full details
# Default threshold (102) to see all non-perfect scores
csat_data = get_csat_detail_log(date_str="2024-01-10")
# Then drill into specific feedback and response times
```

## 5. Integration with Other Tools

The CSAT detail log works well with other analytics tools:

1. **With `get_daily_snapshot`**: Compare CSAT count with overall metrics
2. **With `get_volume_trends`**: Correlate satisfaction with ticket volume
3. **With `get_response_time_metrics`**: Analyze impact of speed on satisfaction
4. **With `get_root_cause_analysis`**: Identify patterns in negative feedback