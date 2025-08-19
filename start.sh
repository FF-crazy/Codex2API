#!/bin/bash

# Codex2API Quick Start Script

set -e

echo "🚀 Codex2API Quick Start"
echo "========================"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
    echo "✅ uv installed successfully"
fi

# Check if dependencies are installed
if [ ! -d ".venv" ]; then
    echo "📦 Installing dependencies..."
    uv sync
    echo "✅ Dependencies installed"
fi

# Check if auth.json exists
if [ ! -f "auth.json" ]; then
    echo "🔐 Authentication setup required"
    echo "Please run the authentication script first:"
    echo "  uv run get_token.py"
    echo ""
    echo "After authentication, run this script again."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created"
fi

echo "🎯 Starting Codex2API server..."
echo "🔧 Health check available at http://localhost:{PORT}/health"
echo ""

# Start the server
uv run main.py
