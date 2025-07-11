.PHONY: help deploy dry-run check setup install clean dev-install test test-unit test-integration test-coverage test-verbose

# Default target
help:
	@echo "🚀 BigQuery View Manager - Available Commands"
	@echo "=============================================="
	@echo ""
	@echo "📦 Setup & Installation:"
	@echo "  make setup       Setup environment and install dependencies"
	@echo "  make install     Install the package"
	@echo "  make dev-install Install in development mode"
	@echo ""
	@echo "🔄 Deployment:"
	@echo "  make deploy      Deploy all views to BigQuery"
	@echo "  make dry-run     Show what would be deployed (no changes)"
	@echo "  make check       Validate SQL syntax without deploying"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  make test        Run all tests"
	@echo "  make test-unit   Run unit tests only"
	@echo "  make test-integration  Run integration tests only"
	@echo "  make test-template     Run template compiler tests"
	@echo "  make test-coverage     Run tests with coverage report"
	@echo "  make test-verbose      Run tests with verbose output"
	@echo ""
	@echo "🧹 Maintenance:"
	@echo "  make clean       Remove build artifacts and cache"
	@echo ""
	@echo "💡 Quick aliases you can add to your shell:"
	@echo "  alias bq-deploy='make deploy'"
	@echo "  alias bq-dry='make dry-run'"
	@echo "  alias bq-check='make check'"

# Setup environment and install dependencies
setup:
	@echo "🚀 Setting up BigQuery View Manager..."
	@./setup.sh

# Install the package
install:
	@echo "📦 Installing package..."
	@uv sync --frozen

# Install in development mode
dev-install:
	@echo "📦 Installing in development mode..."
	@uv sync

# Deploy all views
deploy:
	@echo "🚀 Deploying views to BigQuery..."
	@bq-view-deploy

# Dry run - show what would be deployed
dry-run:
	@echo "🔍 Dry run - showing what would be deployed..."
	@bq-view-deploy --dry-run

# Check/validate SQL files
check: dry-run

# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	@rm -rf build/
	@rm -rf dist/
	@rm -rf *.egg-info/
	@find . -type d -name __pycache__ -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@echo "✅ Cleaned successfully"

# Quick deploy with confirmation
deploy-confirm:
	@echo "⚠️  Are you sure you want to deploy to BigQuery? [y/N]"
	@read -r CONFIRM && [ "$$CONFIRM" = "y" ] || [ "$$CONFIRM" = "Y" ] && make deploy

# Deploy specific files (usage: make deploy-files FILES="file1.sql file2.sql")
deploy-files:
	@echo "🚀 Deploying specific files: $(FILES)"
	@bq-view-deploy --files $(FILES)

# Testing targets
test:
	@echo "🧪 Running all tests..."
	@uv run pytest

test-unit:
	@echo "🧪 Running unit tests..."
	@uv run pytest -m unit

test-integration:
	@echo "🧪 Running integration tests..."
	@uv run pytest -m integration

test-coverage:
	@echo "🧪 Running tests with coverage..."
	@uv run pytest --cov=bq_view_manager --cov-report=html --cov-report=term

test-verbose:
	@echo "🧪 Running tests with verbose output..."
	@uv run pytest -v

test-watch:
	@echo "🧪 Running tests in watch mode..."
	@uv run pytest --watch

test-template:
	@echo "🧪 Running template compiler tests..."
	@uv run pytest tests/test_template_compiler.py -v

# Test utilities
test-install:
	@echo "📦 Installing test dependencies..."
	@uv sync --extra test 