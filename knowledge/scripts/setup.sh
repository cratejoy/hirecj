#!/bin/bash
# Knowledge API Setup Script - Phase 0.3
echo "🔧 Setting up Knowledge API with Dynamic Namespaces..."
echo ""

# Check if we're in the knowledge directory
if [[ ! -f "requirements.txt" ]] || [[ ! -d "gateway" ]]; then
    echo "❌ Error: Please run this script from the knowledge/ directory"
    exit 1
fi

# Create directory structure
echo "📁 Creating directory structure..."
mkdir -p knowledge_base
mkdir -p gateway logs scripts data/personalities
touch gateway/__init__.py

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is required but not installed"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [[ ! -d "venv" ]]; then
    echo "🐍 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Install dependencies
echo "📦 Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the API server:"
echo "  make dev"
echo ""
echo "Or manually:"
echo "  source venv/bin/activate"
echo "  python -m uvicorn gateway.main:app --reload --port 8004"
echo ""
echo "To run the example:"
echo "  make example"
echo ""
echo "The system starts with no namespaces. Create them dynamically via API!"
echo "Check the API docs at: http://localhost:8004/docs"