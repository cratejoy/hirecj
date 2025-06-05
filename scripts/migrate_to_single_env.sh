#!/bin/bash
# ================================================
# Migrate to Single .env Pattern - Phase 4.0
# ================================================
# This script helps migrate from multiple .env files
# to the new single .env pattern
# ================================================

echo "🔄 Migrating to Single .env Pattern..."
echo ""

# Check if .env.consolidated exists
if [ -f ".env.consolidated" ]; then
    echo "✅ Found .env.consolidated with your collected variables"
    
    if [ ! -f ".env" ]; then
        echo "📝 Creating .env from .env.consolidated..."
        cp .env.consolidated .env
        echo "✅ Created .env"
    else
        echo "⚠️  .env already exists. Your consolidated config is in .env.consolidated"
        echo "   Manually merge any missing values into .env"
    fi
else
    echo "⚠️  No .env.consolidated found"
    echo "   Copy .env.master.example to .env and configure manually"
    
    if [ ! -f ".env" ]; then
        cp .env.master.example .env
        echo "✅ Created .env from .env.master.example"
    fi
fi

echo ""
echo "🧹 Cleaning up old environment files..."
./scripts/cleanup_old_env.sh

echo ""
echo "📦 Distributing environment variables..."
python scripts/distribute_env.py

echo ""
echo "🔍 Verifying setup..."
python scripts/verify_single_env.py

echo ""
echo "✅ Migration complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Edit .env with any missing configuration"
echo "   2. Run 'make dev' to start development"
echo "   3. Never edit service .env files again!"
echo ""
echo "🎉 You now manage just ONE .env file!"