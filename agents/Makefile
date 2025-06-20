.PHONY: install test conversation clean clean-memories clean-memory lint format help dev stop dev-run dev-shell dev-build dev-stop dev-clean dev-setup-venv dev-test-conversation dev-health-check

# Python environment management
install:
	venv/bin/python -m pip install --upgrade pip
	venv/bin/pip install -r requirements-dev.txt

# Testing - run both Python framework tests and YAML behavioral tests
test:
	@echo "Running Python framework tests..."
	venv/bin/pytest tests/ -v
	@echo "\nRunning YAML behavioral tests (with mock evaluator for speed)..."
	venv/bin/python tests/scripts/run_cj_tests.py --mock-evaluator --max-workers 6
	@echo "\n✅ All tests completed! Use 'make test-cj' for full GPT-4 evaluation."

# API tests (using FastAPI TestClient - no server needed)
test-api:
	venv/bin/pytest tests/test_api.py tests/test_api_websocket.py tests/test_api_annotations.py -v --tb=short

# Test ConversationAPI client (requires running server)
test-conversation-api:
	@venv/bin/python tests/scripts/test_all_conversation_api.py

# Test API adapter (requires running server)
test-api-adapter:
	@echo "Testing API adapter (requires server running on port 8100)"
	venv/bin/python tests/scripts/test_api_adapter.py

# Run CJ behavior tests
test-cj:
	venv/bin/python tests/scripts/run_cj_tests.py --max-workers 6

# Run CJ behavior tests with detailed output
test-cj-verbose:
	venv/bin/python tests/scripts/run_cj_tests.py --verbose --max-workers 6

# Run CJ behavior tests with mock evaluator (for testing the framework)
test-cj-mock:
	venv/bin/python tests/scripts/run_cj_tests.py --mock-evaluator --max-workers 6

# Run YAML tests with server running
test-yaml:
	@echo "⚠️  This requires the API server to be running on port 8100"
	@echo "   Run 'make dev' in another terminal first"
	@echo ""
	venv/bin/python tests/scripts/run_cj_tests.py --mock-evaluator --max-workers 6

# Run CJ tests sequentially for debugging
test-cj-sequential:
	venv/bin/python tests/scripts/run_cj_tests.py --sequential

# Run CJ tests with strict validation
test-cj-strict:
	venv/bin/python tests/scripts/run_cj_tests.py --strict-validation --max-workers 6

# Generate markdown test report
test-report:
	venv/bin/python tests/scripts/run_cj_tests.py --output-format markdown --output-file test_report.md --max-workers 6
	@echo "Test report saved to test_report.md"

# Generate JSON test report for CI/CD
test-report-json:
	venv/bin/python tests/scripts/run_cj_tests.py --output-format json --output-file test_results.json --max-workers 6
	@echo "Test results saved to test_results.json"

# Run specific test directory
test-boundaries:
	venv/bin/python tests/scripts/run_cj_tests.py tests/cj_boundaries/ --max-workers 6

test-workflows:
	venv/bin/python tests/scripts/run_cj_tests.py tests/cj_workflows/ --max-workers 6

test-edge-cases:
	venv/bin/python tests/scripts/run_cj_tests.py tests/cj_edge_cases/ --max-workers 6

test-universe-data:
	venv/bin/python tests/scripts/run_cj_tests.py tests/universe_data/ --max-workers 6

# Run a single test with full output
# Usage: make test-one TEST=tests/cj_boundaries/vendor_boundaries.yaml
test-one:
	@if [ -z "$(TEST)" ]; then \
		echo "❌ Please specify a test file:"; \
		echo "   make test-one TEST=tests/cj_boundaries/vendor_boundaries.yaml"; \
		exit 1; \
	fi
	@echo "🧪 Running single test with full output: $(TEST)"
	@venv/bin/python tests/scripts/run_cj_tests.py --verbose --sequential "$(TEST)"

# Run tests by name pattern (sequential for readability)
# Usage: make test-name NAME=daily_briefing
test-name:
	@if [ -z "$(NAME)" ]; then \
		echo "❌ Please specify a test name:"; \
		echo "   make test-name NAME=supplier_pricing_request"; \
		exit 1; \
	fi
	@echo "🔍 Running tests matching: $(NAME)"
	@venv/bin/python tests/scripts/run_cj_tests.py $(if $(VERBOSE),--verbose) --test-name "$(NAME)" --sequential --no-interactive tests/

# Run single test by exact name (always sequential)
# Usage: make test-exact NAME=daily_briefing_normal_summer_lull
test-exact:
	@if [ -z "$(NAME)" ]; then \
		echo "❌ Please specify an exact test name:"; \
		echo "   make test-exact NAME=daily_briefing_normal_summer_lull"; \
		exit 1; \
	fi
	@echo "🔍 Running test with exact name: $(NAME)"
	@venv/bin/python tests/scripts/run_cj_tests.py $(if $(VERBOSE),--verbose) --test-name "$(NAME)" --exact-match --sequential --no-interactive tests/

# Generate a conversation
conversation:
	venv/bin/python scripts/tools/generate_conversation.py \
		--merchant $(or $(MERCHANT),marcus_thompson) \
		--scenario $(or $(SCENARIO),growth_stall) \
		--turns $(or $(TURNS),3) \
		$(if $(WORKFLOW),--workflow $(WORKFLOW)) \
		$(if $(OPENS),--merchant-opens "$(OPENS)") \
		$(if $(QUIET),--quiet) \
		$(if $(DEBUG),--debug) \
		$(if $(MARKDOWN),--markdown)

# Code quality
lint:
	venv/bin/ruff check app/ tests/ scripts/
	venv/bin/black --check app/ tests/ scripts/

format:
	venv/bin/black app/ tests/ scripts/
	venv/bin/ruff check --fix app/ tests/ scripts/

# Cleanup
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/

# Clear merchant memories
clean-memories:
	@echo "🧹 Clearing all merchant memories..."
	@if [ -d "data/merchant_memory" ]; then \
		rm -rf data/merchant_memory/*.yaml; \
		echo "✅ Cleared all merchant memory files"; \
	else \
		echo "📁 No merchant memory directory found"; \
	fi

# Clear specific merchant's memory
# Usage: make clean-memory MERCHANT=marcus_thompson
clean-memory:
	@if [ -z "$(MERCHANT)" ]; then \
		echo "❌ Please specify a merchant:"; \
		echo "   make clean-memory MERCHANT=marcus_thompson"; \
		exit 1; \
	fi
	@if [ -f "data/merchant_memory/$(MERCHANT)_memory.yaml" ]; then \
		rm -f "data/merchant_memory/$(MERCHANT)_memory.yaml"; \
		echo "✅ Cleared memory for merchant: $(MERCHANT)"; \
	else \
		echo "❌ No memory file found for merchant: $(MERCHANT)"; \
	fi

# Main development server (API for web frontend) with hot reload
dev:
	@echo "Starting HireCJ API Server on http://localhost:8100 (DEBUG mode with hot reload)"
	@echo "Press Ctrl+C to stop"
	LOG_LEVEL=DEBUG venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8100 --reload --log-level debug

# Development server without hot reload (if reload causes issues)
dev-noreload:
	@echo "Starting HireCJ API Server on http://localhost:8100 (DEBUG mode, no hot reload)"
	@echo "Press Ctrl+C to stop"
	LOG_LEVEL=DEBUG venv/bin/python -m app.main

# Stop all running server instances
stop:
	@echo "Stopping all HireCJ server instances..."
	@pkill -f "python.*app.main" || true
	@pkill -f "uvicorn.*app.main" || true
	@echo "All server instances stopped."

# Annotation commands
annotate:
	@if [ -z "$(CONVERSATION)" ]; then \
		venv/bin/python scripts/analysis/annotate.py --latest; \
	else \
		venv/bin/python scripts/analysis/annotate.py $(CONVERSATION); \
	fi

annotate-latest:
	venv/bin/python scripts/analysis/annotate.py --latest

conversation-annotate:
	@echo "Generating conversation..."
	@venv/bin/python scripts/tools/generate_conversation.py \
		--merchant $(or $(MERCHANT),marcus_thompson) \
		--scenario $(or $(SCENARIO),growth_stall) \
		--turns $(or $(TURNS),3) \
		$(if $(WORKFLOW),--workflow $(WORKFLOW)) \
		$(if $(QUIET),--quiet)
	@echo "\nStarting annotation..."
	@venv/bin/python scripts/analysis/annotate.py --latest

review-annotations:
	venv/bin/python scripts/analysis/review_annotations.py \
		$(if $(FILTER),--filter "$(FILTER)") \
		$(if $(TYPE),--type "$(TYPE)") \
		$(if $(SCENARIO),--scenario "$(SCENARIO)") \
		$(if $(SUMMARY),--summary-only)

# Play merchant role
conversation-play:
	@set -a && [ -f .env ] && . ./.env && set +a; \
	venv/bin/python scripts/demos/play_conversation_simple.py \
		--merchant $(or $(MERCHANT),marcus_thompson) \
		--scenario $(or $(SCENARIO),steady_operations) \
		--turns $(or $(TURNS),10) \
		$(if $(WORKFLOW),--workflow $(WORKFLOW)) \
		$(if $(CJ_VERSION),--cj-version $(CJ_VERSION)) \
		$(if $(FACT_CHECK),--fact-check) \
		$(if $(FACT_CHECK_VERBOSE),--fact-check-verbose)

# Play with verbose fact-checking (fact-check is now on by default)
conversation-play-factcheck:
	@set -a && [ -f .env ] && . ./.env && set +a; \
	venv/bin/python scripts/demos/play_conversation_simple.py \
		--merchant $(or $(MERCHANT),marcus_thompson) \
		--scenario $(or $(SCENARIO),steady_operations) \
		--turns $(or $(TURNS),10) \
		$(if $(WORKFLOW),--workflow $(WORKFLOW)) \
		$(if $(CJ_VERSION),--cj-version $(CJ_VERSION)) \
		--fact-check \
		$(if $(VERBOSE),--fact-check-verbose)

# Interactive conversation launcher
play:
	@set -a && [ -f .env ] && . ./.env && set +a; \
	venv/bin/python scripts/demos/conversation_launcher.py

# Universe generation
generate-universe:
	@set -a && [ -f .env ] && . ./.env && set +a; \
	venv/bin/python scripts/tools/generate_universe.py \
		--merchant $(or $(MERCHANT),marcus_thompson) \
		--scenario $(or $(SCENARIO),steady_operations) \
		$(if $(VALIDATE),--validate)

list-universes:
	@echo "🌌 Available Universes:"
	@if ls data/universes/*.yaml >/dev/null 2>&1; then \
		for file in data/universes/*.yaml; do \
			basename="$$(basename $$file .yaml)"; \
			echo "  • $$basename"; \
		done; \
	else \
		echo "  No universes found"; \
	fi

generate-all-universes:
	@set -a && [ -f .env ] && . ./.env && set +a; \
	venv/bin/python scripts/tools/generate_universe.py --all

validate-universe:
	@if [ -z "$(UNIVERSE)" ]; then \
		echo "❌ Please specify a universe:"; \
		echo "   make validate-universe UNIVERSE=marcus_thompson_steady_operations_v1"; \
		exit 1; \
	fi
	venv/bin/python scripts/tools/validate_universe.py $(UNIVERSE)

# Help
# Docker Development Environment Commands
dev-run:
	@echo "Starting HireCJ Docker development environment..."
	cd local && make run

dev-shell:
	@echo "Attaching to HireCJ Docker container..."
	cd local && make shell

dev-build:
	@echo "Building HireCJ Docker image..."
	cd local && make build

dev-stop:
	@echo "Stopping HireCJ Docker container..."
	cd local && make stop

dev-clean:
	@echo "Cleaning up HireCJ Docker containers and images..."
	cd local && make clean

dev-setup-venv:
	@echo "Setting up Python virtual environment in Docker..."
	cd local && make setup-venv

dev-test-conversation:
	@echo "Testing conversation generation in Docker..."
	cd local && make test-conversation

dev-health-check:
	@echo "Running health check in Docker..."
	cd local && make health-check

help:
	@echo "Available commands:"
	@echo ""
	@echo "🔧 Setup & Maintenance:"
	@echo "  install          - Install dependencies"
	@echo "  lint             - Run code linting"
	@echo "  format           - Format code"
	@echo "  clean            - Clean up temporary files"
	@echo ""
	@echo "🖥️  Server Commands:"
	@echo "  dev              - Run API server with hot reload (port 8100)"
	@echo "  dev-noreload     - Run API server without hot reload"
	@echo "  stop             - Stop all running server instances"
	@echo ""
	@echo "🧪 Testing Commands:"
	@echo "  test             - Run Python unit tests only"
	@echo "  test-yaml        - Run YAML behavioral tests (requires dev server)"
	@echo "  test-api         - Run API tests (REST endpoints and WebSocket)"
	@echo "  test-conversation-api - Test ConversationAPI client (requires dev server)"
	@echo "  test-api-adapter - Test API adapter (requires dev server)"
	@echo ""
	@echo "🤖 CJ Behavior Testing:"
	@echo "  test-cj          - Run all CJ behavior tests"
	@echo "  test-cj-verbose  - Run tests with detailed output"
	@echo "  test-cj-mock     - Run tests with mock evaluator (fast)"
	@echo "  test-cj-strict   - Run tests with strict validation"
	@echo "  test-report      - Generate markdown test report"
	@echo "  test-report-json - Generate JSON report for CI/CD"
	@echo "  test-boundaries  - Run only boundary tests"
	@echo "  test-workflows   - Run only workflow tests"
	@echo "  test-edge-cases  - Run only edge case tests"
	@echo "  test-universe-data - Run only universe data tests"
	@echo ""
	@echo "🎯 Single Test Commands:"
	@echo "  test-one TEST=<file>     - Run single test file"
	@echo "  test-name NAME=<pattern> - Run all tests matching pattern"
	@echo "  test-exact NAME=<name>   - Run single test by exact name"
	@echo ""
	@echo "💬 Conversation Generation:"
	@echo "  conversation     - Generate a test conversation"
	@echo "    Options: MERCHANT=name SCENARIO=name WORKFLOW=name TURNS=n"
	@echo "    Flags: OPENS='message' QUIET=1 DEBUG=1 MARKDOWN=1"
	@echo ""
	@echo "📝 Annotation Commands:"
	@echo "  annotate CONVERSATION=<file>  - Annotate specific conversation"
	@echo "  annotate-latest              - Annotate most recent conversation"
	@echo "  conversation-annotate        - Generate and immediately annotate"
	@echo "  review-annotations           - Review all annotations"
	@echo "    Options: FILTER=text TYPE=like/dislike SCENARIO=name SUMMARY=1"
	@echo ""
	@echo "🎮 Interactive Commands:"
	@echo "  play                         - Interactive conversation launcher"
	@echo "  conversation-play            - Play merchant role (fact-check on by default)"
	@echo "    Options: MERCHANT=name SCENARIO=name WORKFLOW=name TURNS=n"
	@echo "    Fact-check: FACT_CHECK_VERBOSE=1 (or use --no-fact-check to disable)"
	@echo "  conversation-play-factcheck  - Play with verbose fact-checking"
	@echo ""
	@echo "🌌 Universe Generation:"
	@echo "  generate-universe    - Generate a universe file"
	@echo "    Options: MERCHANT=name SCENARIO=name VALIDATE=1"
	@echo "  list-universes       - List all available universes"
	@echo "  generate-all-universes - Generate all universes"
	@echo "  validate-universe UNIVERSE=<name> - Validate a universe file"
	@echo ""
	@echo "🐳 Docker Development Environment:"
	@echo "  dev-run              - Start Docker development container"
	@echo "  dev-shell            - Attach to running Docker container"
	@echo "  dev-build            - Build Docker image"
	@echo "  dev-stop             - Stop Docker container"
	@echo "  dev-clean            - Clean up Docker containers/images"
	@echo "  dev-setup-venv       - Set up Python venv in Docker"
	@echo "  dev-test-conversation - Test conversation generation in Docker"
	@echo "  dev-health-check     - Check Docker environment health"
	@echo ""
	@echo "📚 Examples:"
	@echo "  make test-name NAME=daily_briefing     # Run all daily_briefing tests"
	@echo "  make test-exact NAME=daily_briefing_normal_summer_lull"
	@echo "  make conversation WORKFLOW=daily_briefing TURNS=5"
	@echo "  make play                              # Interactive launcher"
	@echo "  make generate-universe MERCHANT=zoe_martinez SCENARIO=memorial_day_weekend"
