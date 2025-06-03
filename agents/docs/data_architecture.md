# Data Architecture

## Overview

The HireCJ conversation generator uses a clean two-layer data architecture that separates data views from data generation. This allows workflows to declare their data needs while keeping the system flexible for both simulation and production use.

## Architecture Components

### 1. Data Views (`app/data_views.py`)

Strongly-typed data structures that define what information workflows need:

- **DailyBriefingView**: MRR trends, ticket volume, CSAT scores
- **CrisisMetricsView**: Real-time churn data, root cause analysis
- **WeeklyReviewView**: Comprehensive business metrics
- **CustomerSegmentView**: Detailed segment analysis

Each view includes formatting methods to present data naturally in conversations.

### 2. DataAgent (`app/agents/data_agent.py`)

During simulation, the DataAgent serves as our "database":

```python
# Creates consistent synthetic data based on merchant + scenario
data_agent = DataAgent(merchant_name="marcus_thompson", scenario_name="churn_spike")

# Get formatted views
daily_view = data_agent.get_daily_briefing()
crisis_view = data_agent.get_crisis_metrics()
```

Key features:
- Generates internally consistent data across a conversation
- Scenario-aware (churn_spike produces crisis metrics)
- Deterministic (same inputs = same outputs)

### 3. Workflow Data Requirements

Workflows declare their data needs in YAML:

```yaml
data_requirements:
  - view: "daily_briefing"
    refresh: "on_start"
  - view: "customer_segments"
    refresh: "on_demand"

available_tools:
  - get_daily_briefing
  - analyze_customer_segment
```

### 4. CJ Tools

CJ accesses data through CrewAI tools:

```python
def get_daily_briefing() -> str:
    """Get the daily flash report with key metrics."""
    view = data_agent.get_daily_briefing()
    return view.to_flash_report()
```

## Data Flow

1. **Workflow starts** → Declares needed data views
2. **DataAgent created** → Initialized with merchant + scenario context
3. **CJ agent created** → Receives tools connected to DataAgent
4. **During conversation** → CJ calls tools to get formatted data
5. **Data consistency** → All metrics remain consistent within conversation

## Production Migration

In production, replace DataAgent with ProductionDataProvider:

```python
# Simulation
data_agent = DataAgent(merchant_name, scenario_name)

# Production
data_provider = ProductionDataProvider(merchant_id, db_connection)
```

The interface remains identical:
- Same method names (get_daily_briefing, etc.)
- Same return types (data views)
- CJ tools unchanged
- Workflows continue working

## Example Usage

```python
# Create data layer
data_agent = DataAgent("sarah_chen", "scaling_chaos")

# CJ can now use tools
cj_agent = create_cj_agent(
    workflow_name="crisis_response",
    data_agent=data_agent
)

# In conversation, CJ might say:
# "Let me pull the latest metrics... *uses get_crisis_analysis tool*
#  I see we have 67 shipping delays affecting East Coast customers."
```

## Benefits

1. **Clean Separation**: Views separate from generation logic
2. **Type Safety**: Pydantic models ensure data structure
3. **Consistency**: All data coherent within a conversation
4. **Production Ready**: Simple migration path
5. **Workflow Flexibility**: Each workflow gets exactly the data it needs
