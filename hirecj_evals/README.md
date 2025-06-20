# HireCJ Evaluation System

This directory contains the evaluation (evals) system for HireCJ, inspired by OpenAI's evals framework but tailored for our CrewAI agent architecture.

## Directory Structure

```
hirecj_evals/
├── conversations/           # Raw captured conversations (JSON)
│   ├── playground/         # From playground testing
│   │   └── 2024-06-20/    # Date-based organization
│   ├── production/         # From production use (sanitized)
│   └── synthetic/          # Generated test conversations
├── datasets/               # JSONL eval datasets
│   ├── golden/            # Manually curated test cases
│   ├── generated/         # Auto-generated from conversations
│   └── regression/        # Specific regression tests
├── registry/              # YAML eval definitions
│   └── (eval configs)
├── results/               # Eval run results
│   ├── runs/             # Individual run data
│   └── reports/          # Aggregated reports
└── README.md             # This file
```

## Conversation Capture Format

Conversations are captured as JSON files with the following structure:

```json
{
  "id": "conv_1234567890_abc123",
  "timestamp": "2024-06-20T10:30:00Z",
  "context": {
    "workflow": { /* workflow config */ },
    "persona": { /* persona details */ },
    "scenario": { /* scenario config */ },
    "trustLevel": 5,
    "model": "gpt-4-turbo",
    "temperature": 0.7
  },
  "prompts": {
    "cj_prompt": "You are CJ...",
    "workflow_prompt": "...",
    "tool_definitions": [/* tool defs */]
  },
  "messages": [
    {
      "turn": 1,
      "user_input": "User message",
      "agent_processing": {
        "thinking": "Agent's thinking process...",
        "intermediate_responses": [],
        "tool_calls": [],
        "grounding_queries": [],
        "final_response": "CJ's response"
      },
      "metrics": {
        "latency_ms": 1250,
        "tokens": {
          "prompt": 450,
          "completion": 125,
          "thinking": 85
        }
      }
    }
  ]
}
```

## Usage

### Capturing Conversations

Conversations are automatically captured from the playground via the `/api/v1/conversations/capture` endpoint.

### Converting to Eval Format

Use the conversion scripts (coming soon) to transform captured conversations into JSONL eval cases.

### Running Evals

Use the eval runner (coming soon) to execute evaluations against captured datasets.

## Privacy & Security

- Production conversations are stored in `conversations/production/` which is gitignored
- Always sanitize production data before committing to version control
- Use the privacy scrubbing tools before sharing eval datasets