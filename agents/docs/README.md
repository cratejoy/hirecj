# CJ Testing Framework Documentation

Welcome to the comprehensive testing framework for CJ agent behavior validation. This documentation will help you understand, use, and extend the testing system.

## 🚀 Quick Start

### 1. Set Up Environment
```bash
# Install dependencies
make install

# Start test server (Terminal 1)
make test-server

# Run tests (Terminal 2)
make test-cj-mock  # Fast testing with mock evaluator
make test-cj       # Full testing with GPT-4 evaluator
```

### 2. View Results
```bash
# Generate reports
make test-report          # Markdown report
make test-report-json     # JSON for CI/CD
```

### 3. Create Your First Test
```bash
# Copy a template
cp docs/test_templates/boundary_test_template.yaml tests/my_new_test.yaml

# Edit the template
# Run your test
make test-cj-mock
```

## 📋 Documentation Index

### Essential Reading
- **[Test Authoring Guide](TEST_AUTHORING_GUIDE.md)** - How to write effective tests
- **[TEST_FORMAT.md](../TEST_FORMAT.md)** - Technical specification for YAML test format
- **[Troubleshooting Guide](TROUBLESHOOTING_GUIDE.md)** - Debug common issues

### Reference Materials
- **[Common Test Patterns](COMMON_TEST_PATTERNS.md)** - Proven patterns for different test scenarios
- **[Test Templates](test_templates/)** - Ready-to-use templates for new tests
- **[Testing Architecture](../TESTING_ARCHITECTURE.md)** - System design and rationale

### Advanced Topics
- **[Schema Validation](../tests/schema/test_schema.yaml)** - Test file validation rules
- **[CI/CD Integration](../.github/workflows/cj-tests.yml)** - GitHub Actions workflow

## 🎯 Framework Overview

### What This Framework Does
The CJ testing framework validates that CJ (Customer Experience Officer) maintains appropriate boundaries while being helpful. It tests:

- **Data Boundaries**: CJ doesn't access forbidden data (inventory, financial, analytics)
- **Workflow Integration**: Boundaries maintained during structured workflows
- **Pressure Handling**: Consistent behavior under merchant pressure
- **Edge Cases**: Complex scenarios with multiple constraints

### How It Works
1. **YAML Test Definitions**: Tests written in human-readable YAML
2. **HTTP API**: Flask server wraps CJ conversations for testing
3. **Model-Based Evaluation**: GPT-4 evaluates responses against natural language criteria
4. **Rich Reporting**: Multiple output formats with detailed analysis

### Key Benefits
- ✅ **Declarative**: Tests are data, not code
- ✅ **Model-Evaluated**: No brittle regex matching
- ✅ **Scalable**: Easy to add new tests
- ✅ **Maintainable**: Human-readable YAML format
- ✅ **Fast**: Parallel execution and mock evaluator for rapid iteration

## 🏗️ Architecture Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   YAML Tests    │────│  Test Runner     │────│  Test Server    │
│                 │    │                  │    │                 │
│ ├─ boundaries/  │    │ ├─ test_loader   │    │ ├─ Flask API    │
│ ├─ workflows/   │────│ ├─ evaluator     │────│ ├─ CrewAI       │
│ └─ edge_cases/  │    │ └─ reporter      │    │ └─ CJ Agent     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Test Runner (`run_cj_tests.py`)
- Discovers and loads YAML test files
- Executes tests via HTTP API calls
- Evaluates responses using GPT-4 or mock evaluator
- Generates comprehensive reports

### Test Server (`cj_test_server.py`)
- Flask HTTP API wrapping CrewAI conversations
- Provides `/chat` endpoint for test execution
- Handles different merchants, scenarios, and workflows

### Test Components (`app/testing/`)
- **TestLoader**: Loads and validates YAML test definitions
- **TestEvaluator**: GPT-4 and mock evaluation engines
- **TestReportGenerator**: Multi-format report generation

## 📁 Test Organization

### Directory Structure
```
tests/
├── cj_boundaries/          # Core data boundary tests
│   ├── inventory_boundaries.yaml
│   ├── financial_boundaries.yaml
│   ├── analytics_boundaries.yaml
│   └── vendor_boundaries.yaml
├── cj_workflows/           # Workflow integration tests
│   ├── daily_briefing_boundaries.yaml
│   └── crisis_response_boundaries.yaml
├── cj_edge_cases/          # Complex scenario tests
│   ├── persistent_requests.yaml
│   └── multiple_boundaries.yaml
└── schema/                 # Validation rules
    └── test_schema.yaml
```

### Test Categories

**Boundary Tests** - Core data access limitations
- Inventory access boundaries
- Financial data boundaries
- Analytics access boundaries
- Vendor information boundaries

**Workflow Tests** - Boundary maintenance in structured interactions
- Daily briefing integration
- Crisis response scenarios

**Edge Cases** - Complex and challenging scenarios
- Persistent merchant requests
- Multi-boundary violations
- Emotional pressure situations

## 🛠️ Available Commands

### Basic Testing
```bash
make test-cj                 # Run all tests with GPT-4
make test-cj-mock           # Run all tests with mock evaluator (fast)
make test-cj-verbose        # Show detailed test output
```

### Development & Debugging
```bash
make test-cj-watch          # Watch mode for test development
make test-cj-sequential     # Sequential execution for debugging
make test-cj-strict         # Enable strict validation
```

### Specific Test Categories
```bash
make test-boundaries        # Run only boundary tests
make test-workflows         # Run only workflow tests
make test-edge-cases        # Run only edge case tests
```

### Reports & CI/CD
```bash
make test-report            # Generate markdown report
make test-report-json       # Generate JSON report for CI/CD
```

### Server Management
```bash
make test-server            # Start CJ test server
```

## 📝 Writing Tests

### Basic Test Structure
```yaml
version: "1.0.0"
description: "Brief description of test suite purpose"

tests:
  - name: "test_name_in_snake_case"
    description: "What this test validates"
    setup:
      merchant_opens: "What the merchant says to CJ"
      merchant: "marcus_thompson"
      scenario: "growth_stall"
      cj_version: "v5.0.0"
      num_turns: 1
    evaluate_cj:
      - "Specific criterion CJ's response must meet"
      - "Another criterion for evaluation"
```

### Test Writing Process
1. **Choose Pattern**: Use templates from `docs/test_templates/`
2. **Define Setup**: Configure merchant, scenario, and conversation
3. **Write Criteria**: Specific, observable evaluation criteria
4. **Test Iteratively**: Use mock evaluator for rapid iteration
5. **Validate**: Run with GPT-4 evaluator for final validation

### Best Practices
- ✅ Keep tests focused (one primary behavior per test)
- ✅ Use specific, observable criteria
- ✅ Follow snake_case naming conventions
- ✅ Start simple and add complexity gradually
- ✅ Test both positive and negative behaviors

## 🔧 Development Workflow

### For New Features
1. **Write Tests First**: Define expected CJ behavior
2. **Implement Feature**: Update CJ prompts/logic
3. **Validate**: Run tests to verify behavior
4. **Document**: Update tests and documentation

### For Bug Fixes
1. **Reproduce**: Create test that demonstrates the bug
2. **Fix**: Update CJ implementation
3. **Verify**: Ensure test passes and no regressions
4. **Regression**: Add test to prevent future occurrences

### For Test Development
```bash
# Rapid iteration cycle
make test-cj-watch

# Or manual iteration
make test-cj-mock           # Fast development testing
make test-cj-verbose        # Debug failing tests
make test-cj                # Final validation
```

## 🚦 CI/CD Integration

### GitHub Actions
The framework includes comprehensive GitHub Actions integration:

- **Pull Requests**: Mock evaluator tests with results posted as comments
- **Main Branch**: Full GPT-4 evaluation with failure reporting
- **Scheduled**: Daily regression testing
- **Security**: Automated checks for secrets and permissions

### Local CI Testing
```bash
# Simulate CI environment
make test-cj-mock --output-format json
make test-report-json
```

## 📊 Evaluation Methods

### GPT-4 Evaluator (Production)
- Uses OpenAI GPT-4 for intelligent evaluation
- Understands natural language criteria
- Provides detailed explanations for pass/fail decisions
- Requires `OPENAI_API_KEY` environment variable

### Mock Evaluator (Development)
- Always returns pass/fail based on configuration
- Instant results for rapid development iteration
- No API costs or external dependencies
- Perfect for testing the framework itself

## 🎓 Learning Resources

### New to the Framework?
1. Start with **[Test Authoring Guide](TEST_AUTHORING_GUIDE.md)**
2. Copy a template from **[test_templates/](test_templates/)**
3. Run `make test-cj-mock` to see it work
4. Review **[Common Test Patterns](COMMON_TEST_PATTERNS.md)**

### Debugging Issues?
1. Check **[Troubleshooting Guide](TROUBLESHOOTING_GUIDE.md)**
2. Use `make test-cj-verbose` for detailed output
3. Start with simple tests and add complexity
4. Verify test server is running (`make test-server`)

### Advanced Usage?
1. Review **[Testing Architecture](../TESTING_ARCHITECTURE.md)**
2. Understand validation with **[test_schema.yaml](../tests/schema/test_schema.yaml)**
3. Customize evaluation in `app/testing/test_evaluator.py`
4. Extend reports in `app/testing/report_generator.py`

## 🤝 Contributing

### Adding New Tests
1. Use appropriate template from `docs/test_templates/`
2. Follow naming conventions and file organization
3. Test with mock evaluator first
4. Validate with GPT-4 evaluator
5. Update documentation if adding new patterns

### Improving the Framework
1. Check existing issues and documentation
2. Follow established patterns and conventions
3. Add tests for new framework features
4. Update documentation for changes
5. Ensure CI passes before submitting

## 📞 Getting Help

### Quick References
- **Makefile commands**: `make help`
- **CLI options**: `python run_cj_tests.py --help`
- **Test format**: [TEST_FORMAT.md](../TEST_FORMAT.md)

### Common Issues
- **Server not running**: `make test-server`
- **Tests failing**: Check [Troubleshooting Guide](TROUBLESHOOTING_GUIDE.md)
- **YAML errors**: Validate syntax and required fields
- **Evaluation issues**: Use `--verbose` to see CJ responses

### Support Channels
1. Check documentation in this directory
2. Review existing tests for examples
3. Use troubleshooting guide for common issues
4. Contact the development team for complex questions

---

**Happy Testing!** 🧪 The CJ testing framework is designed to make validating agent behavior simple, reliable, and maintainable. Start with the basics and gradually explore the advanced features as your testing needs grow.
