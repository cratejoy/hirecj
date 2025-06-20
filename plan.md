# HireCJ Evals Implementation Plan

## North Stars & Principles

### ⚠️ CRITICAL: Definition of Success

Success is **not** simply building something that captures conversations and runs tests.
Only elegant, complete solutions that fully embody our principles count as success.

* ❌ Shortcuts = **FAILURE**
* ❌ Half‑measures = **FAILURE**
* ❌ Compatibility shims = **FAILURE**
* ❌ "Good enough" = **FAILURE**

### 🌟 Guiding Principles

1. **Long‑Term Elegance Over Short‑Term Hacks** – Build a proper eval framework that prevents prompt regressions
2. **Break It & Fix It Right** – No backwards compatibility with old conversation formats
3. **Simplicity, Simplify, Simplify** – Basic evals should require no code, just YAML + JSONL
4. **Single Source of Truth** – One eval runner, one registry, one format
5. **No Cruft** – Clean, minimal eval definitions without redundancy
6. **Thoughtful Logging & Instrumentation** – Track eval performance and failures with proper visibility
7. **Infrastructure as Code** – Eval infrastructure deployed via Terraform
8. **Answer Before You Code** – Design the eval framework properly before implementation

---

## Do's ✅ and Do Not's ❌

### Do's

* Capture complete conversation context including thinking, tool calls, and grounding
* Build on OpenAI's eval patterns but tailored for CrewAI architecture
* Support parallel execution for fast regression testing
* Make evals accessible to non-technical team members
* Track metrics on latency, tokens, and accuracy
* Export conversations in multiple formats (JSON, JSONL, reports)
* Store conversations in a structured file system for version control and easy access

### Do Not's

* 🚫 Create multiple eval frameworks or runners
* 🚫 Build backwards compatibility for old conversation formats
* 🚫 Over-engineer with features we don't need yet
* 🚫 Create complex eval DSLs when YAML suffices
* 🚫 Mix eval code with production agent code
* 🚫 Store sensitive customer data in eval datasets
* 🚫 Use browser local storage for conversation persistence

---

## 🚧 Implementation Status Banner

> **🚀 CURRENT PHASE:** *Planning* 🔵 Complete
> **🔜 NEXT STEPS:** *Milestone 1 – Conversation Capture Infrastructure*

## Executive Summary

Build an elegant evaluation system for HireCJ that captures agent conversations from the editor and uses them to systematically test and improve prompts. The system will catch prompt regressions, ensure consistent agent behavior across workflows, and enable rapid iteration on agent capabilities. Inspired by OpenAI's evals framework but tailored to CrewAI's multi-agent architecture, with a file-based storage system modeled after third_party/evals.

---

## Architecture Snapshot – Before vs. After

### On‑Disk Layout

|                 | **Before**        | **After**           |                   |
| --------------- | ----------------- | ------------------- | ----------------- |
| `editor/src/`   | Basic playground  | `editor/src/evals/` | Eval framework, capture, runner |
| `backend/app/`  | Agent endpoints   | `backend/app/api/v1/evals/` | Eval execution API |
| N/A             | No eval data      | `hirecj_evals/` | Structured eval data directory |
| N/A             | No conversations  | `hirecj_evals/conversations/` | Date-organized JSON captures |
| N/A             | No test datasets  | `hirecj_evals/datasets/` | JSONL test cases |
| N/A             | No eval configs   | `hirecj_evals/registry/` | YAML eval definitions |

### Conceptual / Object Hierarchies

|                | **Before** | **After**      |       |
| -------------- | ---------- | -------------- | ----- |
| Message Storage | In-memory only | File-based `ConversationCapture` | Persistent JSON files |
| Testing | Manual playground | `EvalRunner` with file datasets | Automated regression testing |
| Prompts | Static files | Version-tracked with evals | A/B testing capability |
| Data Organization | None | Date/source-based directories | Easy batch processing |

---

## Overview
An elegant evaluation system for HireCJ that captures conversations from the editor and uses them to systematically test and improve prompts. Inspired by OpenAI's evals framework, but tailored to our CrewAI agent architecture and multi-step reasoning patterns.

## File System Structure

Following the pattern established by `third_party/evals`, we'll create a structured directory system:

```
hirecj_evals/
├── conversations/           # Raw captured conversations (JSON)
│   ├── playground/         # From playground testing
│   │   └── 2024-06-20/    # Date-based organization
│   │       ├── conv_abc123.json
│   │       └── conv_def456.json
│   ├── production/         # From production use (sanitized)
│   │   └── 2024-06-20/
│   └── synthetic/          # Generated test conversations
│       └── edge_cases/
├── datasets/               # JSONL eval datasets
│   ├── golden/            # Manually curated test cases
│   │   ├── tool_selection.jsonl
│   │   ├── grounding_accuracy.jsonl
│   │   └── workflow_compliance.jsonl
│   ├── generated/         # Auto-generated from conversations
│   │   └── 2024-06-20/
│   └── regression/        # Specific regression tests
│       └── issue_123_tool_fix.jsonl
├── registry/              # YAML eval definitions
│   ├── base.yaml         # Base eval configurations
│   ├── cj_responses.yaml
│   ├── tool_usage.yaml
│   └── workflows/
│       ├── ad_hoc_support.yaml
│       └── conversation_flow.yaml
├── results/               # Eval run results
│   ├── runs/             # Individual run data
│   │   └── 2024-06-20/
│   │       └── run_xyz789/
│   └── reports/          # Aggregated reports
│       └── weekly/
└── README.md             # Documentation
```

## Core Architecture

### 1. Conversation Capture Layer
**Purpose**: Capture complete conversation context for reproducible evaluation

```typescript
interface ConversationCapture {
  // Unique identifier
  id: string;
  timestamp: string;
  
  // Full execution context
  context: {
    workflow: WorkflowConfig;
    persona: Persona;
    scenario: Scenario;
    trustLevel: number;
    model: string;
    temperature: number;
  };
  
  // System prompts at time of execution
  prompts: {
    cj_prompt: string;
    workflow_prompt: string;
    tool_definitions: ToolDefinition[];
  };
  
  // Complete conversation history
  messages: Array<{
    turn: number;
    user_input: string;
    
    // Full agent processing chain
    agent_processing: {
      thinking: string;
      intermediate_responses: string[];
      tool_calls: ToolCall[];
      grounding_queries: GroundingQuery[];
      final_response: string;
    };
    
    // Performance metrics
    metrics: {
      latency_ms: number;
      tokens: {
        prompt: number;
        completion: number;
        thinking: number;
      };
    };
  }>;
}
```

### 2. Eval Registry System
**Pattern**: YAML-based registry for discovering and configuring evaluations

```yaml
# editor/evals/registry/cj_responses.yaml
cj_response_quality:
  id: cj_response_quality.v1
  description: "Evaluates CJ's response quality and tool usage"
  
  # Eval class to use
  class: evals.cj.ResponseQuality
  
  # Default arguments
  args:
    metrics:
      - response_helpfulness
      - tool_selection_accuracy
      - grounding_relevance
    threshold: 0.85

cj_response_quality.conversation_flow:
  parent: cj_response_quality
  args:
    workflow_filter: "conversation_flow"
    additional_metrics:
      - conversation_coherence
      - context_retention
```

### 3. Eval Data Format
**Pattern**: JSONL format compatible with OpenAI evals, extended for CrewAI

```jsonl
{
  "eval_id": "tool_selection_accuracy",
  "sample_id": "conv_abc123_turn_2",
  
  // Input context
  "input": {
    "messages": [
      {"role": "system", "content": "..."},
      {"role": "user", "content": "test a tool"},
      {"role": "assistant", "content": "I'll help you test..."},
      {"role": "user", "content": "yeah try a diff tool"}
    ],
    "context": {
      "workflow": "ad_hoc_support",
      "available_tools": ["get_shopify_store_counts", "get_orders", ...]
    }
  },
  
  // Expected behavior
  "ideal": {
    "tool_selection": {
      "should_use_tool": true,
      "acceptable_tools": ["get_shopify_store_counts", "get_store_analytics"],
      "unacceptable_tools": ["get_orders"]
    },
    "response_criteria": {
      "must_include": ["different tool", "Shopify"],
      "tone": "helpful",
      "explains_choice": true
    }
  },
  
  // Actual output from conversation
  "actual": {
    "thinking": "The user asked for a different tool...",
    "tool_calls": ["get_shopify_store_counts"],
    "response": "I'll use the Shopify store counts tool..."
  },
  
  // Metadata for analysis
  "metadata": {
    "source_conversation": "playground_abc123",
    "turn": 2,
    "timestamp": "2024-06-19T22:35:00Z"
  }
}
```

### 4. Eval Types Hierarchy

```python
# Base eval types (inspired by OpenAI)
class CJEval(ABC):
    """Base class for all HireCJ evaluations"""
    
    @abstractmethod
    def eval_sample(self, sample: EvalSample) -> EvalResult:
        pass

class MatchEval(CJEval):
    """Exact or fuzzy matching of responses"""
    
class IncludesEval(CJEval):
    """Checks if response includes required elements"""
    
class ModelGradedEval(CJEval):
    """Uses another model to grade the response"""

# HireCJ-specific eval types
class ToolSelectionEval(CJEval):
    """Evaluates if correct tools were selected"""
    
class GroundingAccuracyEval(CJEval):
    """Evaluates grounding query relevance and usage"""
    
class ConversationFlowEval(CJEval):
    """Evaluates multi-turn conversation coherence"""
    
class WorkflowComplianceEval(CJEval):
    """Ensures responses follow workflow rules"""
```

## Progress Summary

### Completed ✅
- **Phase 1: Conversation Capture Infrastructure** ✅ COMPLETED
  - ✅ Created TypeScript types for conversation capture
  - ✅ Implemented useConversationCapture React hook  
  - ✅ Built conversation capture endpoint in agents service
  - ✅ Implemented file-based storage with date organization
  - ✅ Created proxy endpoint in editor-backend for complete integration
  
- **Phase 2: Eval Framework Core**
  - ✅ Built base evaluation classes (ExactMatch, FuzzyMatch, Includes, ModelGraded)
  - ✅ Created YAML-based registry system with inheritance
  - ✅ Implemented parallel eval runner
  - ✅ Built HireCJ-specific evaluators (ToolSelectionAccuracy, ResponseQuality, etc.)
  - ✅ Created CLI tool for running evaluations
  - ✅ Added colorful number-driven CLI interface
  - ✅ Implemented conversion tool for captured conversations to JSONL format
  - ✅ Created comprehensive test datasets
  - ✅ Added privacy scrubbing utility
  - ✅ Fixed conversation capture to include full agent processing details (thinking, intermediate responses, tool calls, grounding queries)

### In Progress 🚧
- Phase 3: Editor Integration - Eval Designer View

### Next Steps 📋
- Phase 3: Editor Integration (Eval Designer View, Batch Testing, Results Dashboard)
- Phase 4: Advanced Features (Continuous Evaluation, Smart Test Generation)
- Production model-graded evaluations with GPT-4

## Implementation Phases

### Phase 1: Conversation Capture Infrastructure ✅ COMPLETED
**Goal**: Reliably capture all conversation data to structured file system

1. **Enhanced Message Recording** ✅
   - Implemented `useConversationCapture` hook in editor frontend
   - Tracks full conversation context including thinking states
   - Captures tool calls and grounding queries
   - "Export for Eval" button added to PlaygroundView

2. **Backend Storage API** ✅ COMPLETED
   
   **Current Architecture:**
   ```
   Editor Frontend → Editor-Backend (proxy) → Agents Service (storage)
         ↓                    ↓                        ↓
   /api/v1/conversations → Forward request → /api/v1/conversations/capture
                                                      ↓
                                            hirecj_evals/conversations/
                                                  playground/
                                                    2024-06-20/
                                                      conv_abc123.json
   ```
   
   **Implementation Status:**
   - ✅ Capture endpoint exists in agents service at `/api/v1/conversations/capture`
   - ✅ File-based storage with date organization implemented
   - ✅ All models and validation in place
   - ✅ Proxy endpoint in editor-backend implemented and connected
   
   **Implementation Details:**
   ```python
   # agents/app/api/routes/conversations.py - IMPLEMENTED
   @router.post("/capture")
   async def capture_conversation(request: CaptureRequest):
       """Capture a conversation for evaluation purposes."""
       # Creates: hirecj_evals/conversations/{source}/{date}/{id}.json
   ```
   
   ```python
   # editor-backend/app/api/routes/conversations.py - IMPLEMENTED
   @router.post("/capture") 
   async def proxy_capture(request: Request):
       """Forward capture requests to agents service."""
       # Proxies to agents service with error handling and logging
   ```

3. **Export & Conversion Tools** ✅
   - ✅ CLI tool to convert conversations to JSONL eval format (`scripts/convert_conversations.py`)
   - ✅ Batch processing for date ranges
   - ✅ Privacy scrubbing for production data (`scripts/scrub_conversations.py`)
   - ✅ Git integration (.gitignore for sensitive paths)

### Phase 2: Eval Framework Core ✅ COMPLETED
**Goal**: Build the evaluation engine

1. **Registry System**
   ```typescript
   // Eval registry loader
   class EvalRegistry {
     loadEvals(pattern: string = "evals/**/*.yaml") {
       // Discover and parse eval definitions
     }
     
     getEval(evalId: string): EvalConfig {
       // Resolve eval with inheritance
     }
   }
   ```

2. **Eval Runner**
   ```typescript
   class EvalRunner {
     async run(evalId: string, options: RunOptions) {
       const eval = registry.getEval(evalId);
       const samples = await loadSamples(eval.dataset);
       
       // Parallel execution with progress tracking
       const results = await pmap(samples, 
         sample => this.evalSample(eval, sample),
         { concurrency: options.workers }
       );
       
       return this.aggregateResults(results);
     }
   }
   ```

3. **Recording System**
   ```typescript
   // Event-based recording (like OpenAI)
   class EvalRecorder {
     record(event: EvalEvent) {
       // Record to multiple backends
       this.backends.forEach(b => b.record(event));
     }
   }
   ```

### Phase 3: Editor Integration
**Goal**: Seamless eval workflow in the editor

1. **Eval Designer View**
   - Visual interface for creating eval cases
   - Convert conversations to test cases
   - Edit expected outputs
   - Preview eval execution

2. **Batch Testing Interface**
   ```typescript
   // Run evals against multiple prompt versions
   const comparePrompts = async (evalId: string, prompts: PromptVersion[]) => {
     const results = await Promise.all(
       prompts.map(p => runEval(evalId, { promptOverride: p }))
     );
     return generateComparisonReport(results);
   };
   ```

3. **Results Dashboard**
   - Real-time eval progress
   - Detailed failure analysis
   - Prompt version comparison
   - Export results for further analysis

### Phase 4: Advanced Features
**Goal**: Production-ready evaluation system

1. **Continuous Evaluation**
   - Webhook triggers on prompt changes
   - Automated regression detection
   - Performance benchmarking

2. **Smart Test Generation**
   ```python
   class TestGenerator:
       def generate_edge_cases(self, conversation: Conversation):
           # Analyze conversation for patterns
           # Generate variations and edge cases
           # Suggest missing test coverage
   ```

3. **Model-Graded Evals**
   - Use GPT-4 to evaluate response quality
   - Custom rubrics for different workflows
   - Human-in-the-loop validation

## File Structure

```
# Root-level eval data directory (following third_party/evals pattern)
hirecj_evals/
├── conversations/             # Raw captured conversations
│   ├── playground/           # Playground testing
│   ├── production/           # Production (sanitized)
│   └── synthetic/            # Generated conversations
├── datasets/                 # JSONL eval datasets  
│   ├── golden/              # Manually curated
│   ├── generated/           # Auto-generated
│   └── regression/          # Regression tests
├── registry/                # YAML eval definitions
│   ├── base.yaml
│   ├── cj_responses.yaml
│   ├── tool_usage.yaml
│   └── workflows/
├── results/                 # Eval run results
│   ├── runs/               # Individual runs
│   └── reports/            # Aggregated reports
└── README.md

# Application code
editor/
├── src/
│   ├── evals/
│   │   ├── core/              # Eval framework
│   │   │   ├── registry.ts
│   │   │   ├── runner.ts
│   │   │   ├── recorder.ts
│   │   │   └── types.ts
│   │   └── evaluators/        # Eval implementations
│   │       ├── base.ts
│   │       ├── toolSelection.ts
│   │       ├── grounding.ts
│   │       └── workflow.ts
│   ├── components/
│   │   └── evals/
│   │       ├── EvalDesigner.tsx
│   │       ├── EvalRunner.tsx
│   │       └── ResultsViewer.tsx
│   └── hooks/
│       ├── useEvals.ts
│       └── useConversationCapture.ts

backend/
├── app/
│   └── api/
│       └── v1/
│           ├── conversations/  # Conversation capture
│           │   ├── __init__.py
│           │   ├── capture.py
│           │   └── converter.py
│           └── evals/         # Eval execution API
│               ├── __init__.py
│               ├── runner.py
│               └── storage.py

# CLI tools
scripts/
├── convert_conversations.py   # Convert JSON to JSONL
├── run_evals.py              # CLI eval runner
└── generate_report.py        # Create eval reports
```

## Key Design Principles

1. **Simplicity First**: Basic evals should require no code, just YAML + JSONL
2. **Extensibility**: Easy to add custom eval types for HireCJ-specific needs
3. **Reproducibility**: Every eval run is deterministic and traceable
4. **Performance**: Parallel execution, caching, and incremental evaluation
5. **Integration**: Works seamlessly with existing editor and backend

## Success Metrics

1. **Coverage**: 80%+ of production conversations can be converted to eval cases
2. **Speed**: Eval suite runs in <5 minutes for regression testing
3. **Accuracy**: Catch 95%+ of prompt regressions before deployment
4. **Usability**: Non-technical team members can create and run evals

## Next Steps

1. Start with Phase 1: Implement robust conversation capture
2. Build minimal eval runner for tool selection accuracy
3. Create first batch of golden test cases from real conversations
4. Iterate based on team feedback

This implementation plan provides a solid foundation that captures the elegance of OpenAI's eval framework while being specifically tailored to HireCJ's unique architecture and needs.