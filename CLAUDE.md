# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

dbome is a dbt-like tool for BigQuery that simplifies SQL view management through template compilation, automatic dependency resolution, and git-based workflows. The project is written in Python and uses Jinja2 for SQL templating with a `{{ ref() }}` syntax similar to dbt.

## Common Development Commands

### Building and Running
```bash
# Install dependencies and set up development environment
uv sync

# Run the CLI
uv run dbome run                  # Deploy all views to BigQuery
uv run dbome run --dry            # Preview what would be deployed
uv run dbome run view_name        # Deploy specific view
uv run dbome validate             # Check all references are valid
uv run dbome deps                 # Show dependency graph
uv run dbome compile              # Generate compiled SQL files
```

### Testing
```bash
# Run all tests
uv run pytest

# Run specific test types
uv run pytest -m unit             # Unit tests only
uv run pytest -m integration      # Integration tests only
uv run pytest tests/test_template_compiler.py -v  # Template compiler tests
uv run pytest --cov=dbome --cov-report=html --cov-report=term  # Generate coverage report
uv run pytest -v                  # Verbose output

# Run a single test file
uv run pytest tests/test_template_compiler.py -v
```

### Version Management

The project uses a single source of truth for versioning:
- Version is defined in `pyproject.toml`
- `dbome/__init__.py` reads the version from package metadata when installed
- Use `bump_version.py` to update versions:
  ```bash
  python bump_version.py         # Bump patch (0.3.0 -> 0.3.1)
  python bump_version.py minor   # Bump minor (0.3.0 -> 0.4.0)
  python bump_version.py major   # Bump major (0.3.0 -> 1.0.0)
  ```

### Development Workflow
```bash
# Validate changes before committing
uv run dbome validate             # Check all references are valid
uv run dbome run --dry            # Preview what would be deployed
uv run pytest                     # Run test suite

# Clean build artifacts
rm -rf build/ dist/ *.egg-info/ htmlcov/ .coverage
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

## Architecture and Code Structure

### Core Components

1. **CLI Entry Point** (`dbome/main.py`): 
   - Implements the command-line interface using argparse
   - Commands: `init`, `run`, `compile`, `validate`, `deps`
   - Handles configuration loading and authentication setup

2. **Template Compiler** (`dbome/template_compiler.py`):
   - Processes SQL files with Jinja2 templates
   - Implements the `ref()` function for view references
   - Resolves dependencies using topological sorting
   - Validates SQL syntax using sqlglot

3. **Authentication Flow**:
   - Supports three authentication methods:
     - Default Google Cloud credentials (`gcloud auth`)
     - Service account JSON file
     - AWS SSM Parameter Store (for SageMaker environments)
   - Credentials are loaded based on `config.yaml` settings

### Key Design Patterns

1. **Template Processing**:
   - SQL files in `sql/views/` use Jinja2 syntax
   - `{{ ref('view_name') }}` resolves to fully qualified BigQuery table names
   - Dependencies are automatically extracted and ordered

2. **Dependency Resolution**:
   - Uses networkx-style topological sorting
   - Circular dependencies are detected and reported
   - Views are deployed in dependency order

3. **Configuration Management**:
   - YAML-based configuration in `config.yaml`
   - Template provided as `config.yaml.template`
   - Supports environment-specific settings

### Testing Strategy

- **Fixtures** (`tests/conftest.py`): Shared test utilities and mock objects
- **Unit Tests**: Test individual functions in isolation
- **Integration Tests**: Test end-to-end workflows with mocked BigQuery
- **Template Tests**: Verify SQL compilation and dependency resolution

### Important Implementation Details

1. **SQL Compilation**: 
   - Templates are compiled to `compiled/views/` directory
   - Original formatting and comments are preserved
   - Only `{{ ref() }}` blocks are replaced

2. **BigQuery Integration**:
   - Uses google-cloud-bigquery client
   - Creates dataset if it doesn't exist
   - Handles view creation/replacement atomically

3. **Error Handling**:
   - Rich library provides formatted error messages
   - SQL validation catches syntax errors before deployment
   - Dependency cycles are detected early

4. **Git Integration**:
   - Post-commit hook can auto-deploy on commits
   - Supports CI/CD workflows through CLI commands