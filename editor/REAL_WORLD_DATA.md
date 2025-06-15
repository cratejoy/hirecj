# Real-World Data Integration

The Agent Editor playground now uses actual data from the HireCJ system.

## Updated Elements

### Workflows
- **Daily Briefing** - Morning metrics and alerts from CJ
- **Crisis Response** - Handling urgent business issues
- **Ad Hoc Support** - Natural conversation flow

### System Prompts
- **CJ v6.0.1** - Current production prompt emphasizing autonomy and brevity
- Shows CJ as "Autonomous CX & Growth Officer" not just support

### Merchant Personas
1. **Marcus Thompson** (Grill Masters Club)
   - BBQ subscription, $48K MRR
   - Direct communication style
   - Data-driven, impatient

2. **Sarah Chen** (EcoBeauty Box)
   - Sustainable beauty, $86K MRR
   - Collaborative, values-driven
   - Thoughtful communication

3. **Zoe Martinez** (Manifest & Chill)
   - Wellness subscription, $15K MRR
   - Scattered, overwhelmed
   - Creative but needs help

### Business Scenarios
- **Growth Plateau** - CAC rising, growth stalled
- **February Meltdown** - Quality crisis, churn spike
- **Viral Growth Problems** - Scaling too fast
- **Steady State** - Normal operations

### Example Conversation
Real daily briefing conversation showing:
- CJ's proactive morning update
- Churn alert about Megan Liu
- Root cause analysis of shipping issues
- Actionable win-back suggestions
- Pattern detection across customers

### Tools
- `get_daily_briefing` - Metrics view
- `get_ticket_details` - Support data
- `analyze_metric_trend` - Business analytics
- `get_customer_list` - Customer queries

## Key Differences from Generic Example
1. **Business-focused** - MRR, churn, LTV metrics instead of generic products
2. **Proactive CJ** - Initiates conversations with insights
3. **Real merchant language** - "shit yes" instead of formal speech
4. **Actionable insights** - Specific recommendations with data
5. **Pattern recognition** - Finding at-risk customers
6. **Brief messages** - <90 second scannable format