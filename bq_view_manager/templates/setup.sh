#!/bin/bash
#
# Setup script for BigQuery View Manager
#

set -e  # Exit on error

echo "🚀 Setting up BigQuery View Manager"
echo "=================================="


# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "⚠️  uv not found. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source ~/.cargo/env 2>/dev/null || true
    
    # Verify uv installation was successful
    if ! command -v uv &> /dev/null; then
        echo "❌ Failed to install uv. This project requires uv to work properly."
        echo ""
        echo "Please install uv manually:"
        echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
        echo ""
        echo "Or visit: https://docs.astral.sh/uv/getting-started/installation/"
        echo ""
        echo "Setup cannot continue without uv. Exiting..."
        exit 1
    fi
    echo "✅ uv installed successfully"
else
    echo "✅ Found uv"
fi


# Sync dependencies with uv
echo ""
echo "📦 Syncing dependencies with uv..."
uv sync
echo "✅ Dependencies synced"

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

# Make sure git hook is executable
if [ -f ".git/hooks/post-commit" ]; then
    chmod +x .git/hooks/post-commit
    echo "✅ Git post-commit hook is executable"
fi


echo ""
echo "🎉 Setup completed!"
echo ""
echo "Next steps:"
echo "1. Edit config.yaml with your BigQuery project details"
echo "2. Add your SQL view files (using CREATE OR REPLACE VIEW syntax) to sql/views/"
echo "3. Commit changes to auto-deploy views:"
echo "   git add ."
echo "   git commit -m 'Initial SQL views'"
echo ""
echo "For manual deployment, run:"
echo "   bq-view-deploy"
echo ""
echo "For testing (dry run):"
echo "   bq-view-deploy --dry-run"
echo ""
echo "💡 Pro tip: Create aliases for even faster access:"
echo "   alias bq-deploy='bq-view-deploy'"
echo "   alias bq-dry='bq-view-deploy --dry-run'"
echo ""
echo "Happy coding! 🚀" 