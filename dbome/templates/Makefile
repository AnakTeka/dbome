# dbome (dbt at home) - BigQuery View Manager
# Makefile for common project tasks

# Variables
PYTHON = python
UV = uv
PROJECT_NAME = dbome
VIEWS_DIR = sql/views
COMPILED_DIR = compiled/views
CONFIG_FILE = config.yaml

# Colors for output
RED = \033[0;31m
GREEN = \033[0;32m
YELLOW = \033[1;33m
BLUE = \033[0;34m
BOLD = \033[1m
NC = \033[0m # No Color

# Default target
.PHONY: all
all: check deploy

# Display help
.PHONY: help
help:
	@echo "$(BOLD)dbome (dbt at home) - BigQuery View Manager$(NC)"
	@echo ""
	@echo "$(BOLD)Available targets:$(NC)"
	@echo "  $(BLUE)setup$(NC)          - Run setup script"
	@echo "  $(BLUE)deploy$(NC)         - Deploy all views to BigQuery"
	@echo "  $(BLUE)dry-run$(NC)        - Preview deployment without executing"
	@echo "  $(BLUE)check$(NC)          - Validate SQL syntax and references"
	@echo "  $(BLUE)compile$(NC)        - Compile SQL templates to compiled/ directory"
	@echo "  $(BLUE)deps$(NC)           - Show dependency graph and deployment order"
	@echo "  $(BLUE)validate$(NC)       - Validate all ref() references"
	@echo "  $(BLUE)clean$(NC)          - Clean build artifacts"
	@echo "  $(BLUE)install$(NC)        - Install dependencies"
	@echo "  $(BLUE)test$(NC)           - Run tests"
	@echo "  $(BLUE)test-coverage$(NC)  - Run tests with coverage"
	@echo "  $(BLUE)lint$(NC)           - Run linting"
	@echo "  $(BLUE)format$(NC)         - Format code"
	@echo "  $(BLUE)init-git$(NC)       - Initialize git hooks"
	@echo "  $(BLUE)help$(NC)           - Show this help message"

# Setup
.PHONY: setup
setup:
	@echo "$(YELLOW)🚀 Setting up dbome project...$(NC)"
	@chmod +x setup.sh
	@./setup.sh

# Deploy views
.PHONY: deploy
deploy:
	@echo "$(YELLOW)🚀 Deploying views to BigQuery...$(NC)"
	@$(UV) run dbome --config $(CONFIG_FILE)

# Dry run
.PHONY: dry-run
dry-run:
	@echo "$(YELLOW)🔍 Preview deployment (dry run)...$(NC)"
	@$(UV) run dbome --config $(CONFIG_FILE) --dry-run

# Check SQL syntax and references
.PHONY: check
check: validate
	@echo "$(GREEN)✅ SQL validation completed$(NC)"

# Validate references
.PHONY: validate
validate:
	@echo "$(YELLOW)🔍 Validating SQL references...$(NC)"
	@$(UV) run dbome --config $(CONFIG_FILE) --validate-refs

# Compile templates
.PHONY: compile
compile:
	@echo "$(YELLOW)🔧 Compiling SQL templates...$(NC)"
	@$(UV) run dbome --config $(CONFIG_FILE) --compile-only

# Show dependencies
.PHONY: deps
deps:
	@echo "$(YELLOW)📊 Showing dependency graph...$(NC)"
	@$(UV) run dbome --config $(CONFIG_FILE) --show-deps

# Clean build artifacts
.PHONY: clean
clean:
	@echo "$(YELLOW)🧹 Cleaning build artifacts...$(NC)"
	@rm -rf $(COMPILED_DIR)
	@rm -rf __pycache__
	@rm -rf .pytest_cache
	@rm -rf htmlcov
	@rm -rf .coverage
	@rm -rf dist
	@rm -rf build
	@rm -rf *.egg-info
	@echo "$(GREEN)✅ Clean completed$(NC)"

# Install dependencies
.PHONY: install
install:
	@echo "$(YELLOW)📦 Installing dependencies...$(NC)"
	@$(UV) sync

# Run tests
.PHONY: test
test:
	@echo "$(YELLOW)🧪 Running tests...$(NC)"
	@$(UV) run pytest

# Run tests with coverage
.PHONY: test-coverage
test-coverage:
	@echo "$(YELLOW)🧪 Running tests with coverage...$(NC)"
	@$(UV) run pytest --cov=dbome --cov-report=html --cov-report=term

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
	@uv run pytest --cov=dbome --cov-report=html --cov-report=term

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