#!/bin/bash
# Migration Verification Checklist

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}HireCJ Monorepo Migration Checklist${NC}"
echo "===================================="
echo ""

# Function to check status
check_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
        return 0
    else
        echo -e "${RED}❌ $2${NC}"
        return 1
    fi
}

# Phase 1: Check current repos
echo -e "${YELLOW}Phase 1: Checking current sub-repos...${NC}"
for dir in hirecj-agents hirecj-auth hirecj-database hirecj-homepage hirecj-knowledge; do
    if [ -d "$dir" ]; then
        echo -e "\n${BLUE}=== $dir ===${NC}"
        
        # Check if it's a git repo
        if [ -d "$dir/.git" ]; then
            cd "$dir"
            
            # Check for uncommitted changes
            if git diff --quiet && git diff --staged --quiet; then
                echo -e "${GREEN}✅ No uncommitted changes${NC}"
            else
                echo -e "${RED}❌ Has uncommitted changes!${NC}"
                git status --short
            fi
            
            # Check if pushed
            if [ -z "$(git log origin/$(git branch --show-current)..HEAD 2>/dev/null)" ]; then
                echo -e "${GREEN}✅ All changes pushed${NC}"
            else
                echo -e "${RED}❌ Has unpushed commits!${NC}"
                git log origin/$(git branch --show-current)..HEAD --oneline
            fi
            
            # Show remotes
            echo "Remotes:"
            git remote -v | head -2
            
            cd ..
        else
            echo -e "${YELLOW}⚠️  Not a git repository (already migrated?)${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Directory $dir not found${NC}"
    fi
done

# Phase 2: Check new structure readiness
echo -e "\n${YELLOW}Phase 2: Checking new structure readiness...${NC}"

# Check for new directories
for dir in agents auth database homepage knowledge; do
    if [ -d "$dir" ]; then
        check_status 0 "Directory $dir exists"
        # Check if it's NOT a git repo (good)
        if [ ! -d "$dir/.git" ]; then
            check_status 0 "Directory $dir is not a git repo (integrated)"
        else
            check_status 1 "Directory $dir still has .git directory"
        fi
    else
        check_status 1 "Directory $dir does not exist"
    fi
done

# Check for required files
echo -e "\n${YELLOW}Checking required files...${NC}"
[ -f ".gitignore" ] && check_status 0 ".gitignore exists" || check_status 1 ".gitignore missing"
[ -f "Makefile" ] && check_status 0 "Makefile exists" || check_status 1 "Makefile missing"
[ -f "docker-compose.yml" ] && check_status 0 "docker-compose.yml exists" || check_status 1 "docker-compose.yml missing"

# Phase 3: Check Heroku remotes
echo -e "\n${YELLOW}Phase 3: Checking Heroku remotes...${NC}"
for remote in heroku-agents heroku-auth heroku-homepage heroku-database; do
    if git remote | grep -q "^${remote}$"; then
        check_status 0 "Remote $remote configured"
    else
        check_status 1 "Remote $remote not configured"
    fi
done

# Phase 4: Test services can start
echo -e "\n${YELLOW}Phase 4: Quick service checks...${NC}"

# Check Python venvs
for service in agents auth database; do
    if [ -d "$service/venv" ]; then
        check_status 0 "$service has virtual environment"
    else
        echo -e "${YELLOW}⚠️  $service missing venv (run: make install)${NC}"
    fi
done

# Check Node modules
if [ -d "homepage/node_modules" ]; then
    check_status 0 "homepage has node_modules"
else
    echo -e "${YELLOW}⚠️  homepage missing node_modules (run: make install)${NC}"
fi

# Check Docker
if command -v docker &> /dev/null && docker ps &> /dev/null; then
    check_status 0 "Docker is available"
else
    check_status 1 "Docker not available or not running"
fi

# Summary
echo -e "\n${BLUE}=== Summary ===${NC}"
echo "If all checks pass, you're ready to:"
echo "1. Run: make install"
echo "2. Run: make dev"
echo "3. Deploy with: make deploy-{service}"
echo ""
echo "For detailed migration steps, see MIGRATION_PLAN.md"