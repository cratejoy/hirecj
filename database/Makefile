.PHONY: help install dev stop test clean run db-up db-down db-migrate db-upgrade db-downgrade db-reset

help:
	@echo "HireCJ Database Service Commands:"
	@echo "  make install      - Install dependencies"
	@echo "  make dev          - Run development server with auto-reload"
	@echo "  make stop         - Stop development server"
	@echo "  make test         - Run tests"
	@echo "  make clean        - Clean cache and build files"
	@echo "  make run          - Run production server"
	@echo ""
	@echo "Database Commands:"
	@echo "  make db-up        - Start PostgreSQL with Docker Compose"
	@echo "  make db-down      - Stop PostgreSQL"
	@echo "  make db-migrate   - Create a new migration"
	@echo "  make db-upgrade   - Apply migrations"
	@echo "  make db-downgrade - Rollback last migration"
	@echo "  make db-reset     - Reset database (WARNING: destroys data)"

install:
	@echo "Installing dependencies..."
	@pip install -r requirements.txt
	@echo "✅ Dependencies installed!"

dev:
	@echo "Starting development server..."
	@python -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload

stop:
	@echo "Stopping development server..."
	@pkill -f "uvicorn app.main:app" || echo "Server not running"

run:
	@echo "Starting production server..."
	@python -m uvicorn app.main:app --host 0.0.0.0 --port 8002

test:
	@echo "Running tests..."
	@python -m pytest tests/ -v

clean:
	@echo "Cleaning cache and build files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@echo "✅ Cleaned!"

# Database commands
db-up:
	@echo "Starting PostgreSQL..."
	@docker-compose up -d
	@echo "✅ PostgreSQL running on port 5435"

db-down:
	@echo "Stopping PostgreSQL..."
	@docker-compose down
	@echo "✅ PostgreSQL stopped"

db-migrate:
	@echo "Creating new migration..."
	@read -p "Enter migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

db-upgrade:
	@echo "Applying migrations..."
	@alembic upgrade head
	@echo "✅ Migrations applied"

db-downgrade:
	@echo "Rolling back last migration..."
	@alembic downgrade -1
	@echo "✅ Rolled back"

db-reset:
	@echo "⚠️  WARNING: This will destroy all data!"
	@read -p "Are you sure? (y/N) " confirm; \
	if [ "$$confirm" = "y" ]; then \
		docker-compose down -v; \
		docker-compose up -d; \
		sleep 5; \
		alembic upgrade head; \
		echo "✅ Database reset complete"; \
	else \
		echo "❌ Cancelled"; \
	fi