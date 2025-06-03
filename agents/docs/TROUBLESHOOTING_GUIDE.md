# CJ Testing Troubleshooting Guide

This guide helps you diagnose and fix common issues with the CJ testing framework.

## Quick Diagnosis

### Is the test server running?
```bash
curl http://localhost:5001/health
```
If this fails: `make test-server`

### Can you load test files?
```bash
make test-cj-mock --verbose
```
If this fails: Check YAML syntax and file structure

### Are evaluations working?
```bash
make test-cj-verbose
```
If unexpected results: Review evaluation criteria specificity

## Common Issues & Solutions

### 1. Test Server Issues

#### Problem: "CJ test server not running"
```
❌ CJ test server not running at http://localhost:5001
💡 Start it with: make test-server
```

**Solution:**
```bash
# Terminal 1 - Start server
make test-server

# Terminal 2 - Run tests
make test-cj-mock
```

**Root Causes:**
- Server not started
- Port 5001 in use by another process
- Virtual environment not activated

#### Problem: "API error 500" during tests
```
Test execution failed: API error 500: {"error":"..."}
```

**Diagnosis:**
```bash
# Check server logs in Terminal 1
# Look for Python tracebacks
```

**Common Causes:**
- Invalid scenario name in test setup
- Missing merchant persona
- Malformed test configuration
- CrewAI execution error

**Solutions:**
```yaml
# Verify scenario names
scenario: "growth_stall"  # Not "growth-stall" or "Growth Stall"

# Verify merchant names
merchant: "marcus_thompson"  # Not "Marcus Thompson"

# Check available scenarios
# See prompts/cj/versions/v5.0.0.yaml for valid values
```

### 2. Test File Issues

#### Problem: "No test files found"
```
❌ No test files found in: ['tests/cj_boundaries/']
```

**Diagnosis:**
```bash
ls tests/cj_boundaries/
# Check if .yaml files exist and are readable
```

**Solutions:**
- Ensure files end with `.yaml` or `.yml`
- Check file permissions
- Verify directory structure
- Use absolute paths if relative paths fail

#### Problem: "Invalid YAML" errors
```
ValueError: Invalid YAML in tests/my_test.yaml: ...
```

**Diagnosis:**
```bash
# Test YAML syntax
python -c "import yaml; yaml.safe_load(open('tests/my_test.yaml'))"
```

**Common YAML Issues:**
```yaml
# Bad - Inconsistent indentation
tests:
  - name: "test1"
    description: "..."
      setup:  # Wrong indentation
        merchant: "..."

# Good - Consistent indentation
tests:
  - name: "test1"
    description: "..."
    setup:
      merchant: "..."
```

```yaml
# Bad - Unquoted special characters
description: "Test CJ's response to: How much $$$?"

# Good - Properly quoted
description: "Test CJ's response to: How much money?"
```

#### Problem: "Missing required field" errors
```
ValueError: Test case missing 'evaluate_cj' field
```

**Solution:**
```yaml
# Ensure all required fields are present
tests:
  - name: "required"
    description: "required"
    setup:                   # required
      merchant_opens: "required"
    evaluate_cj:             # required
      - "At least one criterion required"
```

### 3. Evaluation Issues

#### Problem: Tests always pass (when they shouldn't)
```
✅ All tests passed!  # But you expected some to fail
```

**Diagnosis:**
```bash
# Check if using mock evaluator
make test-cj-mock  # This always passes
make test-cj       # This uses real GPT-4 evaluation
```

**Solutions:**
- Use `make test-cj` for real evaluation
- Check criteria specificity (too vague?)
- Test with obviously broken criteria to verify evaluator works

#### Problem: Tests always fail (when they shouldn't)
```
❌ Test consistently fails with good CJ responses
```

**Diagnosis:**
```bash
# Check actual CJ response
make test-cj-verbose

# Review the evaluation explanation
```

**Common Causes:**
- Criteria too strict or unrealistic
- CJ behavior changed (need criteria update)
- Misunderstanding of CJ's actual capabilities

**Solutions:**
```yaml
# Bad - Too strict
- "CJ should use exactly these words: 'I cannot access inventory'"

# Good - Flexible but specific
- "CJ should acknowledge she cannot access inventory data"
```

#### Problem: Inconsistent evaluation results
```
# Same test sometimes passes, sometimes fails
```

**Causes:**
- GPT-4 evaluation variance
- Ambiguous evaluation criteria
- Non-deterministic CJ responses

**Solutions:**
```yaml
# Make criteria more specific
# Bad - Ambiguous
- "CJ should respond appropriately"

# Good - Specific
- "CJ should acknowledge she cannot access inventory data"
- "CJ should NOT provide specific inventory numbers"
```

### 4. Performance Issues

#### Problem: Tests take too long
```
# Full test suite takes >5 minutes
```

**Solutions:**
```bash
# Use mock evaluator for development
make test-cj-mock

# Run specific test directories
make test-boundaries

# Use parallel execution (default)
make test-cj-parallel

# Reduce num_turns in development tests
num_turns: 1  # Instead of 3-4
```

#### Problem: API timeouts
```
requests.exceptions.Timeout: Request timed out
```

**Solutions:**
- Reduce num_turns for complex tests
- Check if server is overloaded
- Restart test server
- Use sequential execution if parallel causes issues

### 5. Validation Issues

#### Problem: Strict validation fails
```
ValueError: Test name 'My Test' must match pattern '^[a-z0-9_]+$'
```

**Solutions:**
```yaml
# Bad - Invalid name
name: "My Test"
name: "test-with-dashes"

# Good - Valid snake_case
name: "my_test"
name: "test_with_underscores"
```

#### Problem: "Invalid field type" errors
```
ValueError: Setup field 'num_turns' must be integer, got str
```

**Solutions:**
```yaml
# Bad - String instead of integer
num_turns: "2"

# Good - Proper integer
num_turns: 2
```

### 6. Development Workflow Issues

#### Problem: Can't iterate quickly
**Solution:**
```bash
# Use watch mode for rapid iteration
make test-cj-watch

# Or run specific files during development
python run_cj_tests.py tests/cj_boundaries/my_new_test.yaml --mock-evaluator --verbose
```

#### Problem: Hard to debug failing tests
**Solution:**
```bash
# Use verbose mode to see CJ responses
make test-cj-verbose

# Run single test file for focus
python run_cj_tests.py tests/cj_boundaries/inventory_boundaries.yaml --verbose

# Use mock evaluator to test framework without GPT-4 costs
make test-cj-mock
```

## Debugging Checklist

When tests aren't working, check these in order:

### 1. Environment Setup
- [ ] Virtual environment activated (`source venv/bin/activate`)
- [ ] Dependencies installed (`make install`)
- [ ] Test server running (`make test-server`)

### 2. Test File Structure
- [ ] Valid YAML syntax
- [ ] Required fields present (`name`, `description`, `setup`, `evaluate_cj`)
- [ ] Proper indentation and quoting
- [ ] File saved with `.yaml` extension

### 3. Test Configuration
- [ ] Valid scenario name (check `prompts/cj/versions/v5.0.0.yaml`)
- [ ] Valid merchant name (`marcus_thompson` or `sarah_chen`)
- [ ] Appropriate `num_turns` (start with 1)
- [ ] Clear merchant message

### 4. Evaluation Criteria
- [ ] Specific and observable criteria
- [ ] Realistic expectations for CJ's capabilities
- [ ] No vague language ("appropriate", "good", "helpful")
- [ ] Positive and negative assertions (what CJ should/shouldn't do)

### 5. Testing Process
- [ ] Using correct make command for your needs
- [ ] Checking actual CJ responses with `--verbose`
- [ ] Verifying with mock evaluator first
- [ ] Testing with minimal example before complex scenarios

## Getting Help

### 1. Check Existing Documentation
- `TEST_FORMAT.md` - Technical specification
- `TEST_AUTHORING_GUIDE.md` - Writing effective tests
- `COMMON_TEST_PATTERNS.md` - Proven patterns

### 2. Use Framework Tools
```bash
# Test framework itself
make test-cj-mock

# Validate test files
python run_cj_tests.py --strict-validation

# See detailed output
make test-cj-verbose
```

### 3. Debug Systematically
1. Start with simple test
2. Add complexity gradually
3. Use verbose output to understand behavior
4. Compare with working examples

### 4. Common Commands for Debugging

```bash
# Quick framework test
make test-cj-mock

# Full diagnostic
make test-cj-verbose

# Test specific file
python run_cj_tests.py tests/cj_boundaries/inventory_boundaries.yaml --verbose

# Validate test syntax
python run_cj_tests.py --strict-validation

# Check server health
curl http://localhost:5001/health

# Test single conversation
curl -X POST http://localhost:5001/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test", "merchant_name": "marcus_thompson", "scenario_name": "growth_stall"}'
```

## Prevention Tips

### Write Tests Incrementally
1. Start with basic boundary test
2. Verify it works with mock evaluator
3. Test with GPT-4 evaluator
4. Add complexity gradually

### Use Templates
- Copy from `docs/test_templates/`
- Modify template gradually
- Test each change

### Follow Naming Conventions
- Files: `category_type.yaml`
- Tests: `action_context_variation`
- Use snake_case everywhere

### Keep Criteria Focused
- Test one primary behavior per test
- Use 2-4 criteria maximum
- Make criteria specific and observable

### Test Your Tests
- Intentionally break CJ to verify tests catch issues
- Use both positive and negative test cases
- Validate with mock evaluator before GPT-4 evaluation

Remember: The testing framework is designed to be simple and robust. Most issues come from YAML syntax, configuration mismatches, or overly complex test scenarios. Start simple and build complexity gradually!
