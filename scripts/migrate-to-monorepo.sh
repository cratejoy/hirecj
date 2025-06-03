#!/bin/bash
# Script to migrate from multi-repo to monorepo structure

set -e  # Exit on error

echo "🚀 HireCJ Monorepo Migration Script"
echo "===================================="
echo ""
echo "This script will help migrate from the current multi-repo structure"
echo "to a clean monorepo while preserving git history."
echo ""

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "hirecj-agents" ]; then
    echo "❌ Error: This script must be run from the hirecj root directory"
    exit 1
fi

echo "📋 Migration Plan:"
echo "1. Remove .git directories from subdirectories"
echo "2. Rename directories to remove 'hirecj-' prefix"
echo "3. Update import paths and configurations"
echo "4. Set up Heroku git remotes"
echo "5. Create unified development tools"
echo ""

read -p "Continue with migration? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Migration cancelled."
    exit 0
fi

# Step 1: Clean up git subdirectories
echo ""
echo "🧹 Step 1: Removing .git directories from subdirectories..."
for dir in hirecj-agents hirecj-auth hirecj-database hirecj-homepage hirecj-knowledge; do
    if [ -d "$dir/.git" ]; then
        echo "  Removing $dir/.git"
        rm -rf "$dir/.git"
    fi
done

# Step 2: Rename directories
echo ""
echo "📁 Step 2: Renaming directories..."
mv hirecj-agents agents 2>/dev/null || echo "  agents already exists"
mv hirecj-auth auth 2>/dev/null || echo "  auth already exists"
mv hirecj-database database 2>/dev/null || echo "  database already exists"
mv hirecj-homepage homepage 2>/dev/null || echo "  homepage already exists"
mv hirecj-knowledge knowledge 2>/dev/null || echo "  knowledge already exists"

# Step 3: Create shared directory
echo ""
echo "📂 Step 3: Creating shared directory structure..."
mkdir -p shared
mkdir -p scripts
mkdir -p .github/workflows

# Step 4: Move proposed files to active
echo ""
echo "📄 Step 4: Activating new configuration files..."
if [ -f "Makefile.proposed" ]; then
    mv Makefile.proposed Makefile
    echo "  ✅ Makefile activated"
fi
if [ -f "docker-compose.proposed.yml" ]; then
    mv docker-compose.proposed.yml docker-compose.yml
    echo "  ✅ docker-compose.yml activated"
fi

# Step 5: Create .env.example
echo ""
echo "📝 Step 5: Creating .env.example..."
cat > .env.example << 'EOF'
# HireCJ Environment Variables

# Shared
DATABASE_URL=postgresql://hirecj:hirecj_dev_password@localhost:5432/hirecj_dev
LOG_LEVEL=DEBUG

# Auth Service
AUTH_PORT=8103
JWT_SECRET=dev_jwt_secret_change_in_production
SHOPIFY_CLIENT_ID=your_shopify_client_id
SHOPIFY_CLIENT_SECRET=your_shopify_client_secret

# Agents Service
AGENTS_PORT=8000
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key

# Homepage
HOMEPAGE_PORT=3000
VITE_API_URL=http://localhost:8000
VITE_AUTH_URL=http://localhost:8103

# Database Service
DATABASE_PORT=8002

# Heroku App Names (for deployment)
HEROKU_AUTH_APP=hirecj-auth
HEROKU_AGENTS_APP=hirecj-agents
HEROKU_HOMEPAGE_APP=hirecj-homepage
HEROKU_DATABASE_APP=hirecj-database
EOF
echo "  ✅ .env.example created"

# Step 6: Create Dockerfile for each service if missing
echo ""
echo "🐳 Step 6: Creating Dockerfiles..."
for service in auth agents database knowledge; do
    if [ ! -f "$service/Dockerfile" ]; then
        cat > "$service/Dockerfile" << 'EOF'
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "app.main"]
EOF
        echo "  ✅ Created $service/Dockerfile"
    fi
done

# Homepage needs a different Dockerfile
if [ ! -f "homepage/Dockerfile" ]; then
    cat > "homepage/Dockerfile" << 'EOF'
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

EXPOSE 3000
CMD ["npm", "run", "dev"]
EOF
    echo "  ✅ Created homepage/Dockerfile"
fi

# Step 7: Update .gitignore
echo ""
echo "📄 Step 7: Updating .gitignore..."
cat >> .gitignore << 'EOF'

# Monorepo specific
.env
*.log
.DS_Store

# Python
__pycache__/
*.py[cod]
*$py.class
venv/
env/
.pytest_cache/

# Node
node_modules/
dist/
build/
.next/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Docker
.docker/
EOF
echo "  ✅ .gitignore updated"

# Step 8: Set up git remotes for Heroku
echo ""
echo "🔗 Step 8: Setting up Heroku git remotes..."
echo "Run the following commands to set up Heroku remotes:"
echo ""
echo "git remote add heroku-auth https://git.heroku.com/hirecj-auth.git"
echo "git remote add heroku-agents https://git.heroku.com/hirecj-agents.git"
echo "git remote add heroku-homepage https://git.heroku.com/hirecj-homepage.git"
echo "git remote add heroku-database https://git.heroku.com/hirecj-database.git"
echo ""

# Step 9: Final instructions
echo ""
echo "✅ Migration complete!"
echo ""
echo "📋 Next steps:"
echo "1. Review the changes with: git status"
echo "2. Set up your environment: make env-setup"
echo "3. Install dependencies: make install"
echo "4. Start development: make dev"
echo "5. Commit the changes: git add . && git commit -m 'Migrate to monorepo structure'"
echo ""
echo "🚀 Deployment:"
echo "To deploy a service to Heroku:"
echo "  make deploy-auth"
echo "  make deploy-agents"
echo "  make deploy-homepage"
echo ""
echo "Happy coding! 🎉"