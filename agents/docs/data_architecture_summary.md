# Data Architecture Summary

## Overview

This two-layer data architecture cleanly separates:
1. **What data workflows need** (Data Views)
2. **How data is provided** (DataAgent in simulation, ProductionDataProvider in production)

## Key Design Principles

### 1. Workflow-Driven Data Requirements
Each workflow explicitly declares what data it needs:
- Daily briefing needs ticket metrics, financials, and alerts
- Crisis response needs impact analysis and affected customers
- Customer analysis needs segment data and behavior patterns

### 2. Consistent Tool Interface
CJ always uses the same tools regardless of data source:
```python
# Same in simulation and production
cj.tools.get_daily_briefing()
cj.tools.analyze_customer_segment("at_risk")
```

### 3. Context-Aware Data Generation
DataAgent generates realistic data based on:
- Merchant context (business stage, stress level)
- Scenario modifiers (growth stall → declining MRR)
- Internal consistency (all metrics align)

### 4. Clean Separation of Concerns
- **Data Views**: Define structure and formatting
- **DataAgent**: Generates synthetic data during simulation
- **CJ Tools**: Standard interface for data access
- **ProductionDataProvider**: Future real database access

## Implementation Files

### Core Architecture
- `/app/data_views.py` - Data view definitions and interfaces
- `/app/agents/data_agent.py` - Simulation database implementation
- `/data/workflow_definitions.yaml` - Workflow data requirements

### Integration Points
- `/app/agents/cj_agent.py` - Updated with data tools
- `/app/agents/simple_conversation_manager.py` - Manages data context
- `/app/models.py` - Extended with workflow support

### Documentation
- `/docs/data_architecture.md` - Detailed architecture documentation
- `/examples/data_architecture_demo.py` - Working demonstration

## How It Works

### During Simulation (Current)
1. Conversation starts with merchant context + scenario
2. DataAgent initializes with base metrics
3. CJ makes tool calls during conversation
4. DataAgent generates consistent synthetic data
5. Data is formatted and returned to CJ
6. All metrics remain consistent throughout

### In Production (Future)
1. Same conversation flow
2. ProductionDataProvider replaces DataAgent
3. Tool calls hit real database
4. Pre-calculated views for performance
5. Caching layer for efficiency
6. Real-time data updates

## Benefits

### For Development
- No external dependencies needed
- Consistent, repeatable data
- Easy to test different scenarios
- Fast iteration on conversation quality

### For Production
- Same agent code works unchanged
- Optimized database queries
- Materialized views for performance
- Clean migration path

### For Maintenance
- Clear separation of concerns
- Easy to add new data views
- Easy to add new tools
- Testable at each layer

## Example Usage

```python
# 1. Create conversation with workflow
conversation = manager.create_conversation(
    scenario_name="growth_stall",
    merchant_name="Marcus Thompson",
    workflow="daily_briefing",
    merchant_context={
        "business_stage": "growth",
        "stress_level": "high"
    }
)

# 2. CJ automatically has appropriate tools
cj = create_cj_agent(
    workflow_name="daily_briefing",
    merchant_context=manager.get_data_context()["merchant_context"],
    scenario_name="growth_stall"
)

# 3. During conversation, CJ can:
# - Call get_daily_briefing() for formatted report
# - Call get_ticket_metrics() for support details
# - Call analyze_customer_segment() for deep dives

# 4. All data is consistent and scenario-appropriate
```

## Next Steps

### Immediate
- Test with various scenarios
- Refine data generation logic
- Add more sophisticated data views

### Future
- Design production database schema
- Implement materialized views
- Build caching layer
- Create data pipeline for real metrics
