#!/bin/bash
#
# Setup script for BigQuery View Manager
#

set -e  # Exit on error

echo "🚀 Setting up BigQuery View Manager"
echo "=================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Check Python version
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Found Python $python_version"

if [ "$(printf '%s\n' "3.11" "$python_version" | sort -V | head -n1)" != "3.11" ]; then
    echo "⚠️  Warning: Python 3.11+ is recommended. Current version: $python_version"
fi

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "⚠️  uv not found. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source ~/.cargo/env 2>/dev/null || true
    
    if ! command -v uv &> /dev/null; then
        echo "❌ Failed to install uv. Please install manually: https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    fi
    echo "✅ uv installed successfully"
else
    echo "✅ Found uv"
fi

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "⚠️  Warning: gcloud CLI not found. Install it from https://cloud.google.com/sdk/docs/install"
else
    echo "✅ Found gcloud CLI"
fi

# Create virtual environment with uv
echo ""
echo "📦 Creating virtual environment with uv..."
if [ ! -d ".venv" ]; then
    uv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Install dependencies with uv
echo ""
echo "📦 Installing dependencies with uv..."
uv pip install -e .
echo "✅ Dependencies installed"

# Create config file if it doesn't exist
echo ""
echo "⚙️  Setting up configuration..."
if [ ! -f "config.yaml" ]; then
    cp config.yaml.template config.yaml
    echo "✅ Created config.yaml from template"
    echo "📝 Please edit config.yaml with your BigQuery project details"
else
    echo "✅ config.yaml already exists"
fi

# Initialize git repository if not exists
echo ""
echo "🔄 Setting up Git repository..."
if [ ! -d ".git" ]; then
    git init
    echo "✅ Git repository initialized"
else
    echo "✅ Git repository already exists"
fi

# Make sure git hook is executable
if [ -f ".git/hooks/post-commit" ]; then
    chmod +x .git/hooks/post-commit
    echo "✅ Git post-commit hook is executable"
fi

# Test authentication (if gcloud is available)
echo ""
echo "🔐 Checking authentication..."
if command -v gcloud &> /dev/null; then
    if gcloud auth application-default print-access-token &> /dev/null; then
        echo "✅ Application Default Credentials are configured"
    else
        echo "⚠️  Application Default Credentials not found"
        echo "📝 Run: gcloud auth application-default login"
    fi
fi

echo ""
echo "🎉 Setup completed!"
echo ""
echo "Next steps:"
echo "1. Edit config.yaml with your BigQuery project details"
echo "2. Authenticate with Google Cloud:"
echo "   gcloud auth application-default login"
echo "3. Add your SQL view files (using CREATE OR REPLACE VIEW syntax) to sql/views/"
echo "4. Commit changes to auto-deploy views:"
echo "   git add ."
echo "   git commit -m 'Initial SQL views'"
echo ""
echo "For manual deployment, run:"
echo "   uv run python -m bq_view_manager.main"
echo ""
echo "For testing (dry run):"
echo "   uv run python -m bq_view_manager.main --dry-run"
echo ""
echo "Happy coding! 🚀" 