# HireCJ Evaluation System

## Overview

The HireCJ eval system tests CJ's responses against plain English requirements. It generates fresh responses using current prompts to ensure CJ behaves correctly NOW, not based on historical data.

## Quick Start

### 1. Create Test Cases from Playground

First, have a conversation with CJ in the playground that you want to turn into a test case:

1. Open the Playground view in the editor
2. Have a conversation with CJ
3. Click "Export for Eval" button
4. Note the exported file path (e.g., `/Users/you/workspace/hirecj/hirecj_evals/conversations/playground/2025-06-21/conv_1234567890_abc123.json`)

### 2. Add Test Requirements

Convert your conversation into a test case with requirements:

```bash
make add-test
```

This interactive command will:
- Show you recent playground conversations
- Let you select the conversation you just exported
- Extract the context (messages, workflow, persona)
- Ask you to describe requirements in plain English

Example requirements:
- "Must not say 'As CJ I'd say' or similar meta-commentary"
- "Must greet the user professionally"
- "Must identify as CJ"
- "Must provide specific help or ask clarifying questions"

### 3. Run Your Tests

Test CJ's current behavior against your requirements:

```bash
make test-reqs
```

This will:
- Load all test cases from `hirecj_evals/datasets/all_tests.jsonl`
- Generate fresh CJ responses using current prompts
- Evaluate each response against your requirements using GPT-4o-mini
- Show clear pass/fail results with explanations

## Example Workflow

### Step 1: Test a Greeting

In the playground:
```
User: sup guy
CJ: Hey there! CJ here – ready to help...
```

Export this conversation.

### Step 2: Add Requirements

```bash
$ make add-test

Recent conversations:
1. conv_1234567890_abc123.json - 2 messages
Select conversation [1]: 1

Requirements for this test (plain English):
1. Must not say 'As CJ I'd say'
2. Must greet professionally
3. Must identify as CJ
Done adding? [y/N]: y

✓ Test case added to all_tests.jsonl
```

### Step 3: Run the Test

```bash
$ make test-reqs

Running Requirements Tests (Live Generation)

Running 3 tests with fresh CJ responses...

Generated: Hey there! CJ here – ready to jump in and help...

Results by Requirement
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                                          Passed Failed Pass Rate
Must not say 'As CJ I'd say'               1      0     100%
Must greet professionally                   1      0     100%  
Must identify as CJ                         1      0     100%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ 3/3 tests passed (100%)
```

## Understanding Test Results

### When Tests Pass

A passing test shows CJ's current response meets your requirement:
```
Must identify as CJ
  ✓ greeting_test: The response includes "CJ here" which clearly identifies the speaker as CJ.
```

### When Tests Fail

A failing test shows exactly what went wrong:
```
Must not say 'As CJ I'd say' or similar meta-commentary
  • day_question_test: The response includes the phrase "as CJ I'd say," which is a form of meta-commentary that violates the requirement.
```

## Tips for Writing Good Requirements

1. **Be Specific**: "Must greet professionally" is better than "Must be nice"
2. **Test One Thing**: Each requirement should test a single behavior
3. **Use Clear Language**: Write requirements as if explaining to a human
4. **Think Edge Cases**: What could go wrong? Test for that

Example good requirements:
- "Must not reveal that it's an AI or chatbot"
- "Must provide actionable next steps, not just information"
- "Must use inclusive 'we/our' language when referring to the team"
- "Must surface confidence scores when making recommendations"

## Advanced Usage

### Viewing All Test Cases

Your test cases live in a single file:
```bash
cat hirecj_evals/datasets/all_tests.jsonl | jq .
```

### Manual Test Case Creation

You can also manually add test cases by editing `all_tests.jsonl`:

```json
{
  "sample_id": "unique_test_id",
  "context": {
    "messages": [
      {"role": "user", "content": "your test message"}
    ],
    "workflow": "ad_hoc_support",
    "persona": "jessica"
  },
  "requirements": [
    "Must do something specific",
    "Must not do something else"
  ]
}
```

### Running Specific Tests

Currently, all tests run together. To test specific scenarios, you can temporarily move other tests aside:

```bash
# Backup current tests
cp hirecj_evals/datasets/all_tests.jsonl hirecj_evals/datasets/all_tests.backup.jsonl

# Keep only specific test
jq 'select(.sample_id == "greeting_test")' hirecj_evals/datasets/all_tests.backup.jsonl > hirecj_evals/datasets/all_tests.jsonl

# Run test
make test-reqs

# Restore all tests
mv hirecj_evals/datasets/all_tests.backup.jsonl hirecj_evals/datasets/all_tests.jsonl
```

## How It Works

1. **Context Only**: Test cases store only the conversation context (messages, workflow, persona), never CJ's historical responses
2. **Live Generation**: Each test run calls the eval endpoint to generate fresh CJ responses with current prompts
3. **LLM Evaluation**: GPT-4o-mini evaluates if responses meet your plain English requirements
4. **Clear Feedback**: Results show exactly why tests passed or failed

## Troubleshooting

### "No test file found"
Run `make add-test` to create your first test case.

### "Error calling CJ API"
Make sure the agents service is running:
```bash
make dev-agents
```

### "OPENAI_API_KEY not set"
The eval system needs OpenAI API access:
```bash
export OPENAI_API_KEY=your-key-here
```

## Best Practices

1. **Test Regularly**: Run tests after every prompt change
2. **Start Small**: A few high-quality tests are better than many poor ones
3. **Iterate**: When tests fail, update prompts and re-run immediately
4. **Document Failures**: Save interesting failures as new test cases
5. **Test Real Scenarios**: Use actual customer interactions, not synthetic examples

## Next Steps

- Run `make add-test` to create your first test
- Run `make test-reqs` to see CJ's current behavior
- Iterate on prompts until all tests pass
- Add more tests as you discover new requirements