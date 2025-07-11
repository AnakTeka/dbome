#!/bin/bash
# dbome (dbt at home) - One-line installer 🏠
# Usage: curl -sSL https://raw.githubusercontent.com/your-repo/dbome/main/install.sh | bash

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuration
PACKAGE_NAME="dbome"
PROJECT_NAME=""
INSTALL_DIR=""

# Helper functions
log() {
    echo -e "${BLUE}[dbome]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --project-name)
            PROJECT_NAME="$2"
            shift 2
            ;;
        --dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        --help)
            cat << EOF
dbome (dbt at home) - One-line installer 🏠

Usage: curl -sSL https://raw.githubusercontent.com/your-repo/dbome/main/install.sh | bash

Options:
  --project-name NAME    Create a new project directory with NAME
  --dir PATH            Install in specific directory (default: current directory)
  --help                Show this help message

Examples:
  # Install in current directory
  curl -sSL https://raw.githubusercontent.com/your-repo/dbome/main/install.sh | bash

  # Create new project directory
  curl -sSL https://raw.githubusercontent.com/your-repo/dbome/main/install.sh | bash -s -- --project-name my-analytics

  # Install in specific directory
  curl -sSL https://raw.githubusercontent.com/your-repo/dbome/main/install.sh | bash -s -- --dir /path/to/project
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

# Determine installation directory
if [ -n "$INSTALL_DIR" ]; then
    INSTALL_DIR=$(realpath "$INSTALL_DIR")
    log "Installing in specified directory: $INSTALL_DIR"
elif [ -n "$PROJECT_NAME" ]; then
    INSTALL_DIR="$(pwd)/$PROJECT_NAME"
    log "Creating new project: $PROJECT_NAME"
else
    INSTALL_DIR="$(pwd)"
    log "Installing in current directory: $INSTALL_DIR"
fi

# Create project directory if needed
if [ -n "$PROJECT_NAME" ]; then
    if [ -d "$PROJECT_NAME" ]; then
        error "Directory '$PROJECT_NAME' already exists! Please choose a different name or remove the existing directory."
    fi
    mkdir -p "$PROJECT_NAME"
    cd "$PROJECT_NAME"
    success "Created project directory: $PROJECT_NAME"
fi

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

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
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
echo -e "${BOLD}🎉 Installation completed successfully!${NC}"
echo
echo -e "${BOLD}📋 Next steps:${NC}"
echo "1. Edit config.yaml with your BigQuery project details"
echo "2. Authenticate with Google Cloud:"
echo "   ${BLUE}gcloud auth application-default login${NC}"
echo "3. Test your setup:"
echo "   ${BLUE}uv run dbome --dry-run${NC}"
echo "4. Deploy your views:"
echo "   ${BLUE}uv run dbome${NC}"
echo
echo -e "${BOLD}💡 Useful aliases to add to your shell profile:${NC}"
echo "   ${BLUE}alias dbome='uv run dbome'${NC}"
echo "   ${BLUE}alias bq-deploy='uv run dbome'${NC}"
echo "   ${BLUE}alias bq-dry='uv run dbome --dry-run'${NC}"
echo
echo -e "${BOLD}📚 Documentation:${NC}"
echo "   • Project README: ./README.md"
echo "   • Example SQL files: ./sql/views/"
echo "   • Configuration: ./config.yaml"
echo
echo -e "${BOLD}🚀 Welcome to dbome - dbt at home!${NC}"

# Show project structure
if command -v tree &> /dev/null; then
    echo
    echo -e "${BOLD}📁 Project structure:${NC}"
    tree -a -I '.git|__pycache__|*.pyc|.uv' -L 3
fi 