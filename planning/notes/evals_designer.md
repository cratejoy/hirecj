===========================================================================================
                          PROMPT EVALUATION SYSTEM - EXECUTIVE SUMMARY
===========================================================================================

PURPOSE:
A unified interface for systematically evaluating and comparing different prompt versions 
across various use cases in the HireCJ system. This enables data-driven prompt improvement
by running automated tests against real scenarios and measuring performance metrics.

KEY CONCEPTS:

• PROMPT CATALOG: All prompt types discovered from the filesystem
  - Fact extraction (v1, v2_dedup, latest)
  - Workflows (conversation flows, agent behaviors)
  - Scenarios (business contexts, merchant interactions)
  - Universe generation (data creation prompts)
  - CJ agent prompts (personality, responses)
  - Data provider prompts
  - Fact checking prompts

• EVALUATION DATASETS: Test cases for each prompt type
  - Golden datasets with expected outputs
  - Real conversation transcripts
  - Synthetic test scenarios
  - Edge cases and failure modes

• METRICS & SCORING: Automated quality measurements
  - Accuracy (matches expected output)
  - Consistency (stable across runs)
  - Latency (response time)
  - Token usage (cost efficiency)
  - Custom metrics per prompt type

• VERSION COMPARISON: Side-by-side performance analysis
  - Compare v1 vs v2 vs latest
  - Track improvements/regressions
  - Statistical significance testing
  - Visual diff highlighting


===========================================================================================
                      EVALUATION DASHBOARD - MAIN INTERFACE
===========================================================================================

+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                              PROMPT EVALUATION CENTER                                               |
|  HEADER          +-----------------------------------------------------------------------------------------------------+
|                  | Active Evaluations: 3    Completed Today: 47    Success Rate: 94.2%           [📊 Analytics] [⚙️] |
+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                                                                                                     |
| ┌──────────────┐ | PROMPT SELECTION                                                               [🔄 Refresh Prompts] |
| │              │ | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
| │ ▶ Evaluation │ | │ Select prompts to evaluate:                                                  [Select All ☐]  │   |
| │   Dashboard  │ | │                                                                                              │   |
| │   (current)  │ | │ 📝 Fact Extraction                           🔄 Workflows                                   │   |
| │              │ | │ ┌────────────────────────────┐              ┌────────────────────────────┐                │   |
| ├──────────────┤ | │ │ ☑ fact_extraction.yaml     │              │ ☐ conversation_flow.yaml   │                │   |
| │              │ | │ │   Latest (8.1KB)           │              │   v1.2 (4.3KB)             │                │   |
| │   Test       │ | │ │   Last tested: 2h ago      │              │   Last tested: 1d ago      │                │   |
| │   Datasets   │ | │ │   Success: 96.5%           │              │   Success: 92.1%           │                │   |
| │              │ | │ │                             │              │                              │                │   |
| ├──────────────┤ | │ │ ☑ fact_extraction_v1.yaml  │              │ ☐ agent_behavior.yaml      │                │   |
| │              │ | │ │   v1 (6.6KB)               │              │   v2.1 (5.2KB)             │                │   |
| │   Results    │ | │ │   Last tested: 2h ago      │              │   Last tested: 3d ago      │                │   |
| │   History    │ | │ │   Success: 89.2%           │              │   Success: 94.7%           │                │   |
| │              │ | │ │                             │              │                              │                │   |
| ├──────────────┤ | │ │ ☐ fact_extraction_v2_dedup │              │ ☐ escalation_flow.yaml    │                │   |
| │              │ | │ │   v2 (6.0KB)               │              │   v1.0 (3.8KB)             │                │   |
| │   Compare    │ | │ │   Last tested: 5h ago      │              │   Never tested             │                │   |
| │   Prompts    │ | │ │   Success: 93.8%           │              │   Success: --              │                │   |
| │              │ | │ └────────────────────────────┘              └────────────────────────────┘                │   |
| ├──────────────┤ | │                                                                                              │   |
| │              │ | │ 🎭 Scenarios                                 🌍 Universe Generation                          │   |
| │   Settings   │ | │ ┌────────────────────────────┐              ┌────────────────────────────┐                │   |
| │              │ | │ │ ☐ growth_scenarios.yaml    │              │ ☐ merchant_universe.yaml   │                │   |
| └──────────────┘ | │ │   v1.1 (7.2KB)             │              │   v3.0 (9.1KB)             │                │   |
|                  | │ │   Last tested: 12h ago     │              │   Last tested: 6h ago      │                │   |
|                  | │ │   Success: 91.3%           │              │   Success: 88.9%           │                │   |
|                  | │ └────────────────────────────┘              └────────────────────────────┘                │   |
|                  | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
|                  |                                                                                                     |
|                  | TEST CONFIGURATION                                                                                  |
|                  | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
|                  | │ Dataset: [Production Samples (1,247 items) ▼]      Model: [claude-3-opus ▼]                │   |
|                  | │                                                                                              │   |
|                  | │ Test Parameters:                                                                             │   |
|                  | │ ├─ Sample Size: [100 ▼] items      ├─ Runs per prompt: [3 ▼]                              │   |
|                  | │ ├─ Temperature: [0.7        ]      ├─ Timeout: [30s ▼]                                     │   |
|                  | │ ├─ Max tokens: [2048       ]      ├─ Parallel workers: [5 ▼]                              │   |
|                  | │                                                                                              │   |
|                  | │ Evaluation Metrics:                                                                          │   |
|                  | │ [✓] Accuracy vs Golden Set    [✓] Latency (p50/p95/p99)    [✓] Token Usage               │   |
|                  | │ [✓] Semantic Similarity       [✓] Format Compliance         [ ] Custom Rubric             │   |
|                  | │ [✓] Consistency Score         [ ] Human Preference          [ ] Error Rate                │   |
|                  | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
|                  |                                                                                                     |
|                  | [▶️ Run Evaluation]  [📋 Save Config]  [🔄 Load Previous]          Estimated time: ~5 minutes      |
+------------------+-----------------------------------------------------------------------------------------------------+


===========================================================================================
                    EVALUATION RESULTS - LIVE PROGRESS VIEW
===========================================================================================

+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                              EVALUATION IN PROGRESS                                                 |
|  HEADER          +-----------------------------------------------------------------------------------------------------+
|                  | Started: 14:32:15    Elapsed: 02:47    ETA: 02:13                             [⏸️ Pause] [❌ Stop] |
+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                                                                                                     |
| ┌──────────────┐ | OVERALL PROGRESS                                                                                    |
| │              │ | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
| │ ▶ Evaluation │ | │ Total Progress: ████████████████░░░░░░░░░░ 58% (174/300 tests)                            │   |
| │   Dashboard  │ | │                                                                                              │   |
| │   (current)  │ | │ fact_extraction.yaml:      ██████████████████████ 100% (100/100) ✅                       │   |
| │              │ | │ fact_extraction_v1.yaml:   ████████████░░░░░░░░░░  74% (74/100)  🔄                       │   |
| ├──────────────┤ | │ fact_extraction_v2_dedup:  ░░░░░░░░░░░░░░░░░░░░░░   0% (0/100)   ⏳                       │   |
| │              │ | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
| │   Test       │ |                                                                                                     |
| │   Datasets   │ | LIVE METRICS                                                                                        |
| │              │ | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
| ├──────────────┤ | │                    fact_extraction.yaml            fact_extraction_v1.yaml                   │   |
| │              │ | │ ┌─────────────────────────────────┐              ┌─────────────────────────────────┐       │   |
| │   Results    │ | │ │ Accuracy                        │              │ Accuracy                        │       │   |
| │   History    │ | │ │ ████████████████████ 96.5%     │              │ ██████████████████   89.2%     │       │   |
| │              │ | │ │                                 │              │                                 │       │   |
| ├──────────────┤ | │ │ Avg Latency: 847ms             │              │ Avg Latency: 923ms             │       │   |
| │              │ | │ │ p95 Latency: 1,203ms           │              │ p95 Latency: 1,456ms           │       │   |
| │   Compare    │ | │ │                                 │              │                                 │       │   |
| │   Prompts    │ | │ │ Tokens Used: 145,234           │              │ Tokens Used: 167,891           │       │   |
| │              │ | │ │ Cost: $2.18                     │              │ Cost: $2.52                     │       │   |
| ├──────────────┤ | │ └─────────────────────────────────┘              └─────────────────────────────────┘       │   |
| │              │ | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
| │   Settings   │ |                                                                                                     |
| │              │ | LIVE TEST LOG                                                                   [Auto-scroll ✓]   |
| └──────────────┘ | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
|                  | │ [14:34:52] ✅ fact_extraction.yaml - Test 100/100: merchant_story_47.txt                    │   |
|                  | │            Accuracy: 97.2% | Latency: 756ms | Tokens: 1,432                                 │   |
|                  | │                                                                                              │   |
|                  | │ [14:34:53] 🔄 fact_extraction_v1.yaml - Test 74/100: product_launch_23.txt                 │   |
|                  | │            Processing... (1.2s)                                                              │   |
|                  | │                                                                                              │   |
|                  | │ [14:34:51] ✅ fact_extraction_v1.yaml - Test 73/100: customer_feedback_92.txt              │   |
|                  | │            Accuracy: 91.5% | Latency: 892ms | Tokens: 1,687                                 │   |
|                  | │                                                                                              │   |
|                  | │ [14:34:49] ⚠️  fact_extraction_v1.yaml - Test 72/100: edge_case_null_values.json           │   |
|                  | │            Partial match: 76.3% | Missing: revenue_data, team_size                          │   |
|                  | │                                                                                              │   |
|                  | │ [14:34:47] ❌ fact_extraction_v1.yaml - Test 71/100: complex_narrative_18.txt              │   |
|                  | │            Failed: Timeout after 30s                                                         │   |
|                  | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
|                  |                                                                                                     |
|                  | [📊 View Partial Results]  [💾 Export Progress]  [🔄 Retry Failed]                                 |
+------------------+-----------------------------------------------------------------------------------------------------+


===========================================================================================
                    EVALUATION RESULTS - COMPLETED VIEW
===========================================================================================

+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                          EVALUATION COMPLETE - FACT EXTRACTION COMPARISON                           |
|  HEADER          +-----------------------------------------------------------------------------------------------------+
|                  | Completed: 14:37:02    Duration: 04:47    Total Tests: 300                    [💾 Export] [🔄 Re-run] |
+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                                                                                                     |
| ┌──────────────┐ | SUMMARY COMPARISON                                                                                  |
| │              │ | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
| │   Evaluation │ | │         Prompt Version        Success Rate    Avg Accuracy    Avg Latency    Total Cost     │   |
| │   Dashboard  │ | │ ─────────────────────────────────────────────────────────────────────────────────────────── │   |
| │              │ | │ 🥇 fact_extraction.yaml           96.5%          94.8%          847ms         $2.18        │   |
| ├──────────────┤ | │ 🥈 fact_extraction_v2_dedup      93.8%          92.3%          901ms         $2.09        │   |
| │              │ | │ 🥉 fact_extraction_v1.yaml        89.2%          87.6%          923ms         $2.52        │   |
| │   Test       │ | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
| │   Datasets   │ |                                                                                                     |
| │              │ | DETAILED METRICS                                                              [📈 View Charts]    |
| ├──────────────┤ | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
| │              │ | │ Metric                  fact_extraction.yaml    fact_extraction_v1    fact_extraction_v2   │   |
| │ ▶ Results    │ | │ ─────────────────────────────────────────────────────────────────────────────────────────── │   |
| │   History    │ | │ Accuracy Score                94.8% ↑              87.6%                  92.3% ↑          │   |
| │   (current)  │ | │ Format Compliance             98.2% ✓              91.3%                  96.7% ✓          │   |
| │              │ | │ Semantic Similarity           0.912                0.847                  0.891            │   |
| ├──────────────┤ | │                                                                                              │   |
| │              │ | │ Latency p50                   823ms               897ms                  878ms            │   |
| │   Compare    │ | │ Latency p95                   1,203ms             1,456ms                1,298ms          │   |
| │   Prompts    │ | │ Latency p99                   1,567ms             2,134ms                1,789ms          │   |
| │              │ | │                                                                                              │   |
| ├──────────────┤ | │ Tokens per Request            1,452               1,679                  1,523            │   |
| │              │ | │ Cost per 1K Requests          $21.80              $25.20                 $20.90           │   |
| │   Settings   │ | │                                                                                              │   |
| │              │ | │ Consistency (3 runs)          97.3%               89.1%                  94.6%            │   |
| └──────────────┘ | │ Error Rate                    3.5%                10.8%                   6.2%             │   |
|                  | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
|                  |                                                                                                     |
|                  | FAILURE ANALYSIS                                                              [View All Failures] |
|                  | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
|                  | │ Common Failure Patterns:                                                                     │   |
|                  | │                                                                                              │   |
|                  | │ fact_extraction_v1.yaml (11 failures):                                                      │   |
|                  | │ • 5x Timeout on complex narratives (>2000 tokens)                                           │   |
|                  | │ • 3x Missing nested data extraction                                                          │   |
|                  | │ • 3x Format mismatch (returned list instead of dict)                                        │   |
|                  | │                                                                                              │   |
|                  | │ fact_extraction_v2_dedup (6 failures):                                                      │   |
|                  | │ • 4x Incomplete deduplication (left duplicate facts)                                        │   |
|                  | │ • 2x Lost facts during deduplication                                                        │   |
|                  | │                                                                                              │   |
|                  | │ fact_extraction.yaml (3 failures):                                                          │   |
|                  | │ • 2x Edge case: null/empty input handling                                                   │   |
|                  | │ • 1x Timeout on extremely long document                                                     │   |
|                  | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
|                  |                                                                                                     |
|                  | SAMPLE OUTPUTS                                                                [🔍 Inspect Mode]    |
|                  | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
|                  | │ Test Case: merchant_story_15.txt                                          [< Prev] [Next >]  │   |
|                  | │ ┌─────────────────────────────────┐  ┌─────────────────────────────────┐                   │   |
|                  | │ │ Expected Output                 │  │ fact_extraction.yaml Output     │                   │   |
|                  | │ │ {                               │  │ {                               │  [✅ 97% match] │   |
|                  | │ │   "business_name": "EcoBeauty", │  │   "business_name": "EcoBeauty", │                   │   |
|                  | │ │   "revenue": "$2.4M",           │  │   "revenue": "$2.4M",           │                   │   |
|                  | │ │   "team_size": 12,              │  │   "team_size": 12,              │                   │   |
|                  | │ │   "key_metrics": {              │  │   "key_metrics": {              │                   │   |
|                  | │ │     "subscription": "45%",      │  │     "subscription": "45%",      │                   │   |
|                  | │ │     "ltv": "$185"               │  │     "ltv": "$185",              │                   │   |
|                  | │ │   }                             │  │     "monthly_active": "8500" ←  │  [+ Extra field] │   |
|                  | │ │ }                               │  │   }                             │                   │   |
|                  | │ │                                 │  │ }                               │                   │   |
|                  | │ └─────────────────────────────────┘  └─────────────────────────────────┘                   │   |
|                  | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
|                  |                                                                                                     |
|                  | [📊 Generate Report]  [🔄 Run Regression Test]  [💬 Share Results]  [🏷️ Tag for Baseline]        |
+------------------+-----------------------------------------------------------------------------------------------------+
