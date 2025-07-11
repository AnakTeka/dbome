#!/bin/bash
# dbome (dbt at home) - One-line installer 🏠
# Usage: curl -sSL https://raw.githubusercontent.com/your-repo/dbome/main/install.sh | bash

set -e  # Exit on error

# Colors for output - check if terminal supports colors
if [ -t 1 ] && [ -n "$TERM" ] && [ "$TERM" != "dumb" ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    BOLD='\033[1m'
    NC='\033[0m' # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    BOLD=''
    NC=''
fi

# Configuration
PACKAGE_NAME="dbome"

# Helper functions
log() {
    printf "${BLUE}[dbome]${NC} %s\n" "$1"
}

success() {
    printf "${GREEN}✅ %s${NC}\n" "$1"
}

warning() {
    printf "${YELLOW}⚠️  %s${NC}\n" "$1"
}

error() {
    printf "${RED}❌ %s${NC}\n" "$1"
    exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --help)
            cat << EOF
dbome (dbt at home) - One-line installer 🏠

Usage: curl -sSL https://raw.githubusercontent.com/your-repo/dbome/main/install.sh | bash

This installer will set up dbome in your current directory.

What it does:
  • Installs uv (if not already installed)
  • Creates a Python project with dbome as dependency
  • Initializes dbome project with templates
  • Sets up git repository with auto-deployment hooks

Example:
  curl -sSL https://raw.githubusercontent.com/your-repo/dbome/main/install.sh | bash
EOF
            exit 0
            ;;
        *)
            error "Unknown option: $1. Use --help for usage information."
            ;;
    esac
done

# Banner
cat << 'EOF'
🏠 dbome (dbt at home) - One-line installer
==========================================

    "Mom, can we have dbt?"
    "We have dbt at home."
    dbt at home: 🏠

EOF

# Install in current directory
INSTALL_DIR="$(pwd)"
PROJECT_NAME=$(basename "$INSTALL_DIR")
log "Installing in current directory: $INSTALL_DIR"

# Check if directory already has a Python project
if [ -f "pyproject.toml" ] || [ -f "config.yaml" ] || [ -f "config.yaml.template" ]; then
    warning "Directory appears to already have a Python project or dbome installation."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log "Installation cancelled."
        exit 0
    fi
fi

# Check if uv is installed
log "Checking for uv..."
if ! command -v uv &> /dev/null; then
    warning "uv not found. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Source the environment
    export PATH="$HOME/.cargo/bin:$PATH"
    source ~/.cargo/env 2>/dev/null || true
    
    # Verify uv installation
    if ! command -v uv &> /dev/null; then
        error "Failed to install uv. Please install uv manually: https://docs.astral.sh/uv/getting-started/installation/"
    fi
    success "uv installed successfully"
else
    success "Found uv"
fi

# Initialize Python project with uv
log "Initializing Python project..."
if [ ! -f "pyproject.toml" ]; then
    # Create a minimal pyproject.toml for the project
    cat > pyproject.toml << EOF
[project]
name = "${PROJECT_NAME:-dbome-project}"
version = "0.1.0"
description = "BigQuery view management with dbome (dbt at home)"
dependencies = [
    "dbome>=0.1.0",
]
requires-python = ">=3.8"

[tool.uv.sources]
dbome = { path = "/home/yoga/tmp/people/andre" }

EOF
    success "Created pyproject.toml"
fi

# Install dbome
log "Installing dbome package..."
uv sync
success "dbome installed successfully"

# Run dbome init
log "Initializing dbome project..."
uv run dbome init
success "dbome project initialized"

# Final instructions
echo
printf "${BOLD}🎉 Installation completed successfully!${NC}\n"
echo
printf "${BOLD}📋 Next steps:${NC}\n"
echo "1. Edit config.yaml with your BigQuery project details"
echo "2. Authenticate with Google Cloud:"
printf "   ${BLUE}gcloud auth application-default login${NC}\n"
echo "3. Test your setup:"
printf "   ${BLUE}uv run dbome --dry-run${NC}\n"
echo "4. Deploy your views:"
printf "   ${BLUE}uv run dbome${NC}\n"
echo
printf "${BOLD}💡 Useful aliases to add to your shell profile:${NC}\n"
printf "   ${BLUE}alias dbome='uv run dbome'${NC}\n"
printf "   ${BLUE}alias bq-deploy='uv run dbome'${NC}\n"
printf "   ${BLUE}alias bq-dry='uv run dbome --dry-run'${NC}\n"
echo
printf "${BOLD}📚 Documentation:${NC}\n"
echo "   • Project README: ./README.md"
echo "   • Example SQL files: ./sql/views/"
echo "   • Configuration: ./config.yaml"
echo
printf "${BOLD}🚀 Welcome to dbome - dbt at home!${NC}\n"

# Show project structure
if command -v tree &> /dev/null; then
    echo
    printf "${BOLD}📁 Project structure:${NC}\n"
    tree -a -I '.git|__pycache__|*.pyc|.uv|.venv' -L 3
fi 