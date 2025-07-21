#!/bin/bash
# dbome (dbt at home) - One-line installer 🏠
# Usage: curl -sSL https://raw.githubusercontent.com/AnakTeka/dbome/main/install.sh | bash

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

Usage: curl -sSL https://raw.githubusercontent.com/AnakTeka/dbome/main/install.sh | bash

This installer will set up dbome in your current directory.

What it does:
  • Installs uv (if not already installed)
  • Creates a Python project with dbome as dependency
  • Initializes dbome project with templates
  • Sets up git repository with auto-deployment hooks

Example:
  curl -sSL https://raw.githubusercontent.com/AnakTeka/dbome/main/install.sh | bash
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
    
    # Update PATH to include both possible uv installation locations
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    
    # Source environment files if they exist
    source ~/.cargo/env 2>/dev/null || true
    source "$HOME/.local/bin/env" 2>/dev/null || true
    
    # Verify uv installation
    if ! command -v uv &> /dev/null; then
        # Try to find uv in common locations
        if [ -f "$HOME/.local/bin/uv" ]; then
            export PATH="$HOME/.local/bin:$PATH"
            success "Found uv in $HOME/.local/bin"
        elif [ -f "$HOME/.cargo/bin/uv" ]; then
            export PATH="$HOME/.cargo/bin:$PATH"
            success "Found uv in $HOME/.cargo/bin"
        else
            error "Failed to install uv. Please install uv manually: https://docs.astral.sh/uv/getting-started/installation/"
        fi
    else
        success "uv installed successfully"
    fi
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
    "dbome @ git+https://github.com/AnakTeka/dbome.git",
]
requires-python = ">=3.8"


EOF
    success "Created pyproject.toml"
fi

# Set Python version for uv
if [ ! -f ".python-version" ]; then
    echo "3.11" > .python-version
    success "Set Python version to 3.11"
fi

# Install dbome
log "Installing dbome package..."
uv sync
success "dbome installed successfully"

# Run dbome init
log "Initializing dbome project..."
uv run dbome init --quiet
success "dbome project initialized"

# Final instructions
echo
printf "${BOLD}🎉 Installation completed successfully!${NC}\n"
printf "${BOLD}🚀 Welcome to dbome - dbt at home!${NC}\n"

# Show project structure
if command -v tree &> /dev/null; then
    echo
    printf "${BOLD}📁 Project structure:${NC}\n"
    tree -a -I '.git|__pycache__|*.pyc|.uv|.venv' -L 3
fi

echo
printf "${BOLD}⚡ IMPORTANT: Auto-Deployment Feature Enabled!${NC}\n"
echo "────────────────────────────────────────────────────────"
printf "${YELLOW}🔗 Git Hook Installed:${NC} ${BOLD}.git/hooks/post-commit${NC}\n"
echo
printf "${GREEN}✅ WHAT THIS MEANS:${NC}\n"
printf "   • When you commit SQL files, they will be ${BOLD}automatically deployed${NC} to BigQuery\n"
printf "   • This happens ${BOLD}immediately after each commit${NC} - no manual deployment needed!\n"
printf "   • Only changed SQL files in sql/views/ are deployed\n"
echo
printf "${RED}⚠️  SAFETY REMINDER:${NC}\n"
printf "   • Always test with ${BOLD}dry run${NC} before committing: ${BLUE}uv run dbome run --dry${NC}\n"
printf "   • Configure your BigQuery credentials in ${BOLD}config.yaml${NC} first\n"
printf "   • The hook respects your ${BOLD}dry_run${NC} config setting\n"
echo
printf "${BOLD}🚀 Next Steps:${NC}\n"
printf "   1. ${BLUE}cp config.yaml.template config.yaml${NC}\n"
printf "   2. Edit config.yaml with your BigQuery project details\n"
printf "   3. Set up authentication (see README.md for options)\n"
printf "   4. ${BLUE}uv run dbome run --dry${NC} to test your setup\n"
printf "   5. Write SQL views in sql/views/ and commit to auto-deploy!\n"
echo 