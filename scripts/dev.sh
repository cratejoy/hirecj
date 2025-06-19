#!/bin/bash
# HireCJ Development Helper Script
# ================================
# This script follows the Single .env Pattern
# All configuration comes from root .env file
# ================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default action
ACTION=${1:-help}

# Move to project root
cd "$(dirname "$0")/.."

# Functions
print_header() {
    echo -e "${BLUE}🚀 HireCJ Development Environment${NC}"
    echo "=================================="
}

check_dependencies() {
    echo -e "${YELLOW}Checking dependencies...${NC}"
    
    # Check for Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker is not installed${NC}"
        echo "   Install from: https://www.docker.com/get-started"
        exit 1
    fi
    
    # Check for Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python 3 is not installed${NC}"
        exit 1
    fi
    
    # Check for Node
    if ! command -v node &> /dev/null; then
        echo -e "${RED}❌ Node.js is not installed${NC}"
        echo "   Install from: https://nodejs.org/"
        exit 1
    fi
    
    echo -e "${GREEN}✅ All dependencies found${NC}"
}

start_infrastructure() {
    echo -e "${YELLOW}Starting infrastructure (PostgreSQL & Redis)...${NC}"
    docker-compose up -d
    
    # Wait for services to be ready
    echo -n "Waiting for PostgreSQL..."
    until docker-compose exec -T postgres pg_isready -U hirecj > /dev/null 2>&1; do
        echo -n "."
        sleep 1
    done
    echo -e " ${GREEN}Ready!${NC}"
    
    echo -n "Waiting for Redis..."
    until docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; do
        echo -n "."
        sleep 1
    done
    echo -e " ${GREEN}Ready!${NC}"
    
    echo -e "${GREEN}✅ Infrastructure is ready${NC}"
    echo ""
    echo "PostgreSQL: localhost:5432"
    echo "Redis:      localhost:6379"
}

stop_infrastructure() {
    echo -e "${YELLOW}Stopping infrastructure...${NC}"
    docker-compose down
    echo -e "${GREEN}✅ Infrastructure stopped${NC}"
}

case $ACTION in
    start|up)
        print_header
        check_dependencies
        start_infrastructure
        echo ""
        echo -e "${YELLOW}Next steps:${NC}"
        echo "1. In terminal 1: make dev-agents"
        echo "2. In terminal 2: make dev-homepage"
        echo "3. In terminal 3: make dev-auth (if needed)"
        echo ""
        echo "Or use: make dev-all (requires tmux)"
        ;;
    
    stop|down)
        print_header
        stop_infrastructure
        ;;
    
    agents)
        print_header
        echo -e "${YELLOW}Starting Agents service...${NC}"
        echo -e "${BLUE}Using single .env pattern - env vars will be distributed automatically${NC}"
        make dev-agents
        ;;
    
    homepage)
        print_header
        echo -e "${YELLOW}Starting Homepage...${NC}"
        echo -e "${BLUE}Using single .env pattern - env vars will be distributed automatically${NC}"
        make dev-homepage
        ;;
    
    auth)
        print_header
        echo -e "${YELLOW}Starting Auth service...${NC}"
        echo -e "${BLUE}Using single .env pattern - env vars will be distributed automatically${NC}"
        make dev-auth
        ;;
    
    database)
        print_header
        echo -e "${YELLOW}Starting Database service...${NC}"
        echo -e "${BLUE}Using single .env pattern - env vars will be distributed automatically${NC}"
        make dev-database
        ;;
    
    status)
        print_header
        echo -e "${YELLOW}Checking service status...${NC}"
        echo ""
        
        # Check infrastructure
        if docker-compose ps | grep -q "Up"; then
            echo -e "Infrastructure: ${GREEN}Running${NC}"
            docker-compose ps
        else
            echo -e "Infrastructure: ${RED}Stopped${NC}"
        fi
        echo ""
        
        # Check services
        for port in 8100 8103 8002 3000; do
            if lsof -i :$port > /dev/null 2>&1; then
                case $port in
                    8100) echo -e "Agents (8100):   ${GREEN}Running${NC}" ;;
                    8103) echo -e "Auth (8103):     ${GREEN}Running${NC}" ;;
                    8002) echo -e "Database (8002): ${GREEN}Running${NC}" ;;
                    3000) echo -e "Homepage (3000): ${GREEN}Running${NC}" ;;
                esac
            else
                case $port in
                    8100) echo -e "Agents (8100):   ${RED}Stopped${NC}" ;;
                    8103) echo -e "Auth (8103):     ${RED}Stopped${NC}" ;;
                    8002) echo -e "Database (8002): ${RED}Stopped${NC}" ;;
                    3000) echo -e "Homepage (3000): ${RED}Stopped${NC}" ;;
                esac
            fi
        done
        ;;
    
    logs)
        SERVICE=${2:-all}
        if [ "$SERVICE" = "all" ]; then
            docker-compose logs -f
        else
            docker-compose logs -f $SERVICE
        fi
        ;;
    
    help|*)
        print_header
        echo ""
        echo "Usage: ./scripts/dev.sh [command]"
        echo ""
        echo "Commands:"
        echo "  start|up      Start infrastructure (PostgreSQL & Redis)"
        echo "  stop|down     Stop infrastructure"
        echo "  agents        Start Agents service"
        echo "  homepage      Start Homepage"
        echo "  auth          Start Auth service"
        echo "  database      Start Database service"
        echo "  status        Check status of all services"
        echo "  logs [service] View logs (default: all)"
        echo "  help          Show this help"
        echo ""
        echo "Example workflow:"
        echo "  1. make env-setup            # Set up .env file (first time only)"
        echo "  2. ./scripts/dev.sh start    # Start infrastructure"
        echo "  3. make dev-agents           # In terminal 1"
        echo "  4. make dev-homepage         # In terminal 2"
        echo ""
        echo "Or simply use: make dev-all (tmux) or make dev-tunnels-tmux (with ngrok)"
        ;;
esac