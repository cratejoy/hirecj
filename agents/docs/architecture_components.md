# HireCJ Data Architecture - Component Diagram

## System Components

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          USER INTERFACE                                 │
│                   make conversation WORKFLOW=daily_briefing             │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │
┌─────────────────────────────────────┴───────────────────────────────────┐
│                     CONVERSATION GENERATOR                              │
│                  scripts/generate_conversation.py                       │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────────┐   │
│  │ Workflow Loader │  │ Scenario Loader  │  │  Prompt Loader     │   │
│  │                 │  │                  │  │                    │   │
│  │ • daily_briefing│  │ • growth_stall   │  │ • CJ v4.0.0       │   │
│  │ • crisis_response│ │ • churn_spike    │  │ • marcus_thompson │   │
│  │ • weekly_review │  │ • scaling_chaos  │  │ • sarah_chen      │   │
│  └─────────────────┘  └──────────────────┘  └────────────────────┘   │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │
┌─────────────────────────────────────┴───────────────────────────────────┐
│                          AGENT LAYER                                    │
│  ┌─────────────────────────────┐  ┌─────────────────────────────────┐ │
│  │         CJ AGENT             │  │      MERCHANT AGENT             │ │
│  │                              │  │                                 │ │
│  │ • Workflow-aware prompt      │  │ • Persona prompt               │ │
│  │ • Has data tools             │  │ • Scenario context             │ │
│  │ • Conversation history       │  │ • Emotional state              │ │
│  │                              │  │                                 │ │
│  │ Tools:                       │  │ Behaviors:                     │ │
│  │ - get_daily_briefing        │  │ - React to metrics             │ │
│  │ - analyze_customer_segment  │  │ - Express stress/optimism      │ │
│  │ - get_crisis_analysis       │  │ - Ask pointed questions        │ │
│  └──────────────┬───────────────┘  └─────────────────────────────────┘ │
└─────────────────┼───────────────────────────────────────────────────────┘
                  │ Tool Calls
┌─────────────────┴───────────────────────────────────────────────────────┐
│                          DATA LAYER                                     │
│  ┌─────────────────────────────┐  ┌─────────────────────────────────┐ │
│  │      DATA AGENT              │  │      DATA VIEWS                 │ │
│  │   (Simulation Mode)          │  │                                 │ │
│  │                              │  │ • DailyBriefingView            │ │
│  │ • Scenario-aware generation  │  │ • CrisisMetricsView            │ │
│  │ • Consistent metrics         │  │ • CustomerSegmentView          │ │
│  │ • Deterministic output       │  │ • WeeklyReviewView             │ │
│  │                              │  │                                 │ │
│  │ Base Metrics:                │  │ Methods:                        │ │
│  │ - MRR, Subscribers           │  │ - to_flash_report()            │ │
│  │ - Churn rate, Tickets        │  │ - to_crisis_summary()          │ │
│  │ - CSAT, Growth rate          │  │ - format_for_display()         │ │
│  └─────────────────────────────┘  └─────────────────────────────────┘ │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                    PRODUCTION DATA PROVIDER                     │  │
│  │                        (Future State)                           │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐    │  │
│  │  │ PostgreSQL  │  │ Materialized │  │ Redis Cache      │    │  │
│  │  │             │  │ Views        │  │                  │    │  │
│  │  └─────────────┘  └──────────────┘  └───────────────────┘    │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Flow Example: Daily Briefing

```
1. CJ needs daily metrics
   │
   ├─> CJ.use_tool("get_daily_briefing")
   │
   ├─> DataAgent.get_daily_briefing()
   │   ├─> Calculate trends from base_metrics
   │   ├─> Generate ticket categories
   │   └─> Identify urgent issues
   │
   ├─> Returns: DailyBriefingView
   │   ├─> mrr: MetricTrend(current=$45k, change=+0.0%)
   │   ├─> churn_rate: MetricTrend(current=5.5%, change=+5.3%)
   │   └─> urgent_issues: ["CAC increased 25%", "Competitor launched"]
   │
   └─> CJ receives formatted: "📊 Daily Flash - May 24:..."
```

## Key Design Principles

### 1. Separation of Concerns
- **Workflows**: Define conversation patterns
- **Agents**: Handle conversation logic
- **Data Layer**: Manages all metrics and business data
- **Views**: Format data for presentation

### 2. Consistency
- All data within a conversation comes from same DataAgent instance
- Metrics are coherent (e.g., if churn is high, MRR growth is negative)
- Scenario context affects all generated data

### 3. Flexibility
- Workflows guide but don't constrain
- Agents can deviate based on conversation flow
- Data tools can be called as needed

### 4. Production Path
```
Current: CJ → Tools → DataAgent → Synthetic Data
Future:  CJ → Tools → ProductionDataProvider → Real Database
```

The interface remains identical, only the implementation changes.
