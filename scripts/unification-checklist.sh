#!/bin/bash
# Service Pattern Unification Checklist

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}HireCJ Service Unification Checklist${NC}"
echo "====================================="
echo ""

# Function to check if file exists
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✅ $2${NC}"
        return 0
    else
        echo -e "${RED}❌ $2 (missing: $1)${NC}"
        return 1
    fi
}

# Function to check if pattern exists in file
check_pattern() {
    if grep -q "$2" "$1" 2>/dev/null; then
        echo -e "${GREEN}✅ $3${NC}"
        return 0
    else
        echo -e "${RED}❌ $3${NC}"
        return 1
    fi
}

echo -e "${YELLOW}1. Checking unified port assignments...${NC}"
# Check that each service uses correct port
check_pattern "agents/app/config.py" "PORT.*8000" "Agents uses port 8000"
check_pattern "auth/app/config.py" "PORT.*8103" "Auth uses port 8103"
check_pattern "database/app/config.py" "PORT.*8002" "Database uses port 8002"
check_pattern "knowledge/app/config.py" "PORT.*8001" "Knowledge uses port 8001"

echo ""
echo -e "${YELLOW}2. Checking standardized startup patterns...${NC}"
for service in agents auth database; do
    check_file "$service/app/__main__.py" "$service has __main__.py"
done

echo ""
echo -e "${YELLOW}3. Checking environment configuration...${NC}"
for service in agents auth database homepage knowledge; do
    check_file "$service/.env.example" "$service has .env.example"
done

echo ""
echo -e "${YELLOW}4. Checking unified logging...${NC}"
# Check if services use consistent logging
for service in agents auth database; do
    if [ -f "$service/app/logging_config.py" ] || [ -L "$service/app/logging_config.py" ]; then
        echo -e "${GREEN}✅ $service has logging config${NC}"
    else
        echo -e "${YELLOW}⚠️  $service missing unified logging${NC}"
    fi
done

echo ""
echo -e "${YELLOW}5. Checking removed redundant files...${NC}"
# Check that old dev scripts are gone
if [ ! -f "dev.py" ]; then
    echo -e "${GREEN}✅ dev.py removed${NC}"
else
    echo -e "${RED}❌ dev.py still exists${NC}"
fi

if [ ! -f "dev-simple.py" ]; then
    echo -e "${GREEN}✅ dev-simple.py removed${NC}"
else
    echo -e "${RED}❌ dev-simple.py still exists${NC}"
fi

echo ""
echo -e "${YELLOW}6. Checking simplified Makefiles...${NC}"
for service in agents auth database; do
    if [ -f "$service/Makefile" ]; then
        lines=$(wc -l < "$service/Makefile")
        if [ $lines -gt 20 ]; then
            echo -e "${YELLOW}⚠️  $service/Makefile has $lines lines (should be minimal)${NC}"
        else
            echo -e "${GREEN}✅ $service/Makefile is minimal ($lines lines)${NC}"
        fi
    else
        echo -e "${GREEN}✅ $service has no Makefile (uses root)${NC}"
    fi
done

echo ""
echo -e "${YELLOW}7. Checking test configuration...${NC}"
for service in agents auth database; do
    check_file "$service/pytest.ini" "$service has pytest.ini"
done

echo ""
echo -e "${YELLOW}8. Checking Procfile consistency...${NC}"
for service in agents auth database homepage; do
    if [ -f "$service/Procfile" ]; then
        echo -e "${GREEN}✅ $service has Procfile${NC}"
    else
        echo -e "${RED}❌ $service missing Procfile${NC}"
    fi
done

echo ""
echo -e "${YELLOW}9. Checking shared utilities...${NC}"
check_file "shared/logging_config.py" "Shared logging config exists"
check_file "shared/__init__.py" "Shared package initialized"

echo ""
echo -e "${YELLOW}10. Checking root orchestration...${NC}"
check_file "Makefile" "Root Makefile exists"
check_file "docker-compose.yml" "Docker Compose exists"
check_file "scripts/dev.sh" "Dev helper script exists"

echo ""
echo -e "${BLUE}=== Summary ===${NC}"
echo "This checklist verifies that all services follow unified patterns."
echo "Fix any ❌ items before proceeding with the migration."