# HireCJ Monorepo Restructuring Plan

## Implementation Checklist - Natural Order

### ✅ Phase 1: Backup & Audit (20 min) - COMPLETE
**Safety first - preserve everything before changes**
- ✅ Run audit script to check current state: `./scripts/migration-checklist.sh`
- ✅ Push all changes to individual repos
  - ✅ hirecj-database: Committed credential manager and connectors
  - ✅ hirecj-homepage: Committed chat integration and vite config
  - ✅ hirecj-knowledge: Committed scripts and demos (on ecommerce-fuel branch)
  - ✅ hirecj-agents: Already clean
- ✅ Create backup branches in each repo: `git checkout -b pre-monorepo-backup && git push origin pre-monorepo-backup`
  - ✅ hirecj-agents/pre-monorepo-backup
  - ✅ hirecj-database/pre-monorepo-backup
  - ✅ hirecj-homepage/pre-monorepo-backup (GitHub repo: hirecj-website)
  - ✅ hirecj-knowledge/pre-monorepo-backup (from ecommerce-fuel branch)
- ✅ Document current working state

**Completed**: 2025-06-03 08:41 AM (Duration: 6 minutes)

### ✅ Phase 2: Foundation Setup (30 min) - COMPLETE
**Prepare everything in root BEFORE touching sub-repos**
- ✅ Create comprehensive root `.gitignore` (updated earlier)
- ✅ Add `Makefile.proposed`, `docker-compose.proposed.yml`
- ✅ Create all helper scripts:
  - ✅ `scripts/dev.sh`
  - ✅ `scripts/migration-checklist.sh`
  - ✅ `scripts/unification-checklist.sh`
- ✅ Create `shared/` directory structure with:
  - ✅ `shared/logging_config.py` - Unified logging
  - ✅ `shared/config_base.py` - Base Pydantic config
  - ✅ `shared/README.md` - Usage documentation
- ✅ Create `.env.example` with all service configurations
- ✅ Create `.github/workflows/` for future CI/CD
- ✅ Commit foundation: `git commit -m "Prepare monorepo migration infrastructure"`

**Completed**: 2025-06-03 09:01 AM (Duration: 3 minutes)

### ☐ Phase 3: Pattern Unification IN PLACE (45 min)
**Fix inconsistencies BEFORE migration - repos improve even if migration fails**
- ☐ In each sub-repo, standardize patterns:
  - ☐ Add `app/__main__.py` files for consistent startup
  - ☐ Standardize config to use Pydantic settings
  - ☐ Fix port conflicts (Knowledge: 8001, not 8000)
  - ☐ Create proper `.env.example` files
  - ☐ Simplify Makefiles to minimal versions
- ☐ Push improvements to each repo: `git commit -am "Standardize patterns for monorepo migration"`
- ☐ Verify each service still works independently

### ☐ Phase 4: The Big Move (45 min)
**Now do the actual migration**
- ☐ Final safety check: all repos pushed and backed up
- ☐ Remove `.git` directories: `rm -rf hirecj-*/.git`
- ☐ Rename directories: `mv hirecj-agents agents` (etc.)
- ☐ Stage and commit each service:
  ```bash
  git add agents/ && git commit -m "Add agents service to monorepo"
  git add auth/ && git commit -m "Add auth service to monorepo"
  # ... repeat for each
  ```
- ☐ Run `./scripts/migration-checklist.sh` after each service

### ☐ Phase 5: Activate & Test Locally (30 min)
**Make it work locally before deploying**
- ☐ Activate new configs: `mv Makefile.proposed Makefile && mv docker-compose.proposed.yml docker-compose.yml`
- ☐ Create any missing directories: `mkdir -p shared .github/workflows`
- ☐ Run `make install` to set up all dependencies
- ☐ Start infrastructure: `make dev-infra`
- ☐ Test each service: `make dev-agents`, `make dev-auth`, etc.
- ☐ Fix any import or path issues that arise
- ☐ Verify hot reload works for each service

### ☐ Phase 6: Heroku Setup & Deploy (45 min)
**Deploy only after local works perfectly**
- ☐ Add Heroku git remotes:
  ```bash
  git remote add heroku-agents https://git.heroku.com/hirecj-agents.git
  git remote add heroku-auth https://git.heroku.com/hirecj-auth.git
  git remote add heroku-homepage https://git.heroku.com/hirecj-homepage.git
  git remote add heroku-database https://git.heroku.com/hirecj-database.git
  ```
- ☐ Configure buildpacks if needed
- ☐ Test deploy ONE service first (recommend homepage): `make deploy-homepage`
- ☐ Verify it works in production
- ☐ Deploy remaining services one by one
- ☐ Monitor logs during deployment: `make logs-{service}`

### ☐ Phase 7: Cleanup & Polish (30 min)
**Final touches for a clean end state**
- ☐ Remove old dev scripts: `rm dev.py dev-simple.py dev.sh`
- ☐ Update main README.md with new workflow
- ☐ Archive old GitHub repos (Settings → Archive repository)
- ☐ Create announcement for team with:
  - ☐ New workflow instructions
  - ☐ Benefits achieved
  - ☐ Any breaking changes
- ☐ Run final verification: `./scripts/unification-checklist.sh`
- ☐ Celebrate! 🎉

## Why This Order Works Better

1. **Safety First**: Complete backup before any destructive changes
2. **Prepare Infrastructure**: All tools ready before migration starts
3. **Improve in Place**: Services get better even if migration fails
4. **Test Locally First**: Ensure everything works before touching production
5. **Progressive Deployment**: Deploy one service first as canary
6. **Clean End State**: Everything tidy and documented when done

## Checkpoint Strategy

After each phase, you can:
- ✅ **Continue** if everything looks good
- ⏸️ **Pause** if you need to handle other priorities
- ↩️ **Rollback** if issues arise (original repos remain intact)

## Implementation Progress & Notes

### Current Status: Phase 1 Complete, Ready for Phase 2

### Important Findings from Phase 1:
1. **hirecj-auth**: Already not a git repository (appears to have been migrated previously)
2. **hirecj-knowledge**: Currently on `ecommerce-fuel` branch, not `main`
3. **hirecj-homepage**: GitHub repo is actually named `hirecj-website`
4. **Security**: 23 vulnerabilities detected in hirecj-knowledge (1 critical, 5 high)

### Repository Status Summary:
- **hirecj-agents**: Clean, backed up ✅
- **hirecj-auth**: Already migrated (no .git directory) ⚠️
- **hirecj-database**: Changes committed, backed up ✅
- **hirecj-homepage**: Changes committed, backed up ✅ (as hirecj-website)
- **hirecj-knowledge**: Changes committed, backed up ✅ (from ecommerce-fuel branch)

## Goal
Transform the current multi-repo structure into a clean monorepo while maintaining separate Heroku deployments for each service.

## Benefits
- ✅ Single GitHub repository = Simple PRs and reviews
- ✅ Unified patterns = No more "which command for which service?"
- ✅ Consistent configuration = Same patterns everywhere
- ✅ Easy local development = One set of commands to learn
- ✅ Each service still deploys independently to Heroku
- ✅ Cleaner project management = Less cognitive load

## New Structure

```
hirecj/
├── .github/              # GitHub Actions for CI/CD
├── auth/                 # Auth service (was hirecj-auth)
│   ├── app/
│   ├── Procfile         # For Heroku deployment
│   └── requirements.txt
├── agents/              # Agents service (was hirecj-agents)
│   ├── app/
│   ├── Procfile
│   └── requirements.txt
├── homepage/            # Homepage service (was hirecj-homepage)
│   ├── src/
│   ├── Procfile
│   └── package.json
├── database/            # Database service (was hirecj-database)
│   ├── app/
│   ├── Procfile
│   └── requirements.txt
├── knowledge/           # Knowledge service (was hirecj-knowledge)
│   ├── src/
│   └── requirements.txt
├── shared/              # Shared code/utilities
├── scripts/             # Development and deployment scripts
├── docker-compose.yml   # Local development orchestration
├── Makefile            # Root-level commands
├── .env.example        # Example environment variables
└── README.md           # Project overview
```

## Heroku Deployment Strategy

Each service will have:
1. Its own Heroku app
2. Buildpacks configured per service type
3. Procfile in each service directory
4. Deploy from subdirectories using Heroku's subtree push

Example deployment commands:
```bash
# Deploy auth service
git subtree push --prefix auth heroku-auth main

# Or use our Makefile
make deploy-auth
make deploy-agents
make deploy-homepage
```

## Root-Level Orchestration

### Makefile Commands
```makefile
# Development
make dev              # Start all services locally
make dev-auth         # Start only auth service
make dev-agents       # Start only agents service
make install          # Install all dependencies
make test             # Run all tests

# Deployment
make deploy-all       # Deploy all services
make deploy-auth      # Deploy auth to Heroku
make deploy-agents    # Deploy agents to Heroku

# Utilities
make logs-auth        # View auth service logs
make logs-agents      # View agents service logs
make db-migrate       # Run database migrations
```

### Docker Compose for Infrastructure Only
Docker is used ONLY for stateful services (PostgreSQL, Redis). Apps run locally for better DX:

```yaml
version: '3.8'
services:
  # Infrastructure only - apps run locally
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: hirecj
      POSTGRES_PASSWORD: hirecj_dev_password
      POSTGRES_DB: hirecj_dev
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

### Local Development Philosophy
- **Apps run locally**: Hot reload, easy debugging, fast iteration
- **Infrastructure in Docker**: Consistent PostgreSQL/Redis for everyone
- **Simple commands**: `make dev` starts infra, then tells you what to run
- **tmux option**: `make dev-all` opens all services in tmux windows

## Phased Migration Implementation

### Phase 1: Backup & Preserve Current State (30 min)
**Goal**: Ensure all work is safely pushed to individual repos before restructuring.

1. **Audit each sub-project**:
   ```bash
   for dir in hirecj-agents hirecj-auth hirecj-database hirecj-homepage hirecj-knowledge; do
     echo "=== Checking $dir ==="
     cd $dir && git status && git log --oneline -5 && cd ..
   done
   ```

2. **Push all changes** to individual repos
3. **Create backup branches**:
   ```bash
   git checkout -b pre-monorepo-backup && git push origin pre-monorepo-backup
   ```

### Phase 2: Prepare Root Repository (15 min)
**Goal**: Set up the main hirecj repo structure.

1. **Create root .gitignore** (see below for complete file)
2. **Commit foundation files**:
   ```bash
   git add .gitignore plan.md Makefile.proposed docker-compose.proposed.yml scripts/
   git commit -m "Prepare monorepo structure"
   ```

### Phase 3: Convert Sub-Repos to Directories (1 hour)
**Goal**: Safely integrate each service into the monorepo.

1. **Remove .git directories** (after verifying everything is pushed):
   ```bash
   rm -rf hirecj-agents/.git
   rm -rf hirecj-auth/.git
   # ... repeat for each
   ```

2. **Rename directories**:
   ```bash
   mv hirecj-agents agents
   mv hirecj-auth auth
   mv hirecj-database database
   mv hirecj-homepage homepage
   mv hirecj-knowledge knowledge
   ```

3. **Commit each service**:
   ```bash
   git add agents/ && git commit -m "Add agents service to monorepo"
   git add auth/ && git commit -m "Add auth service to monorepo"
   # ... repeat for each
   ```

### Phase 4: Activate New Structure (15 min)
**Goal**: Switch to the new development workflow.

1. **Activate configuration**:
   ```bash
   mv Makefile.proposed Makefile
   mv docker-compose.proposed.yml docker-compose.yml
   git add Makefile docker-compose.yml
   git commit -m "Activate monorepo configuration"
   ```

2. **Create shared directories**:
   ```bash
   mkdir -p shared .github/workflows
   ```

### Phase 4.5: Unify Service Patterns (45 min)
**Goal**: Clean up per-service inconsistencies for elegant, unified patterns.

1. **Standardize startup commands**:
   ```python
   # Each service gets a simple __main__.py pattern:
   # agents/app/__main__.py
   if __name__ == "__main__":
       import uvicorn
       uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
   ```

2. **Remove/simplify per-service Makefiles**:
   ```makefile
   # Keep only minimal service-specific Makefile if needed
   # agents/Makefile (example)
   .PHONY: run
   run:
   	cd .. && make dev-agents
   ```

3. **Unify environment handling**:
   ```bash
   # Standard .env.example in each service
   SERVICE_NAME=agents
   PORT=8000
   LOG_LEVEL=DEBUG
   DATABASE_URL=postgresql://localhost:5432/hirecj
   ```

4. **Fix port assignments**:
   - Agents: 8000
   - Auth: 8103  
   - Database: 8002
   - Homepage: 3000
   - Knowledge: 8001 (fix conflict!)

5. **Clean up redundant dev scripts**:
   ```bash
   # Remove old scripts
   rm dev.py dev-simple.py  # Keep only scripts/dev.sh
   git add -u
   git commit -m "Remove redundant dev scripts"
   ```

6. **Standardize Python app structure**:
   ```python
   # Each service follows same pattern:
   # app/main.py
   from fastapi import FastAPI
   from app.config import settings  # Pydantic settings
   
   app = FastAPI(title=f"HireCJ {settings.SERVICE_NAME}")
   ```

7. **Unify logging configuration**:
   ```python
   # shared/logging_config.py (symlink to each service)
   import logging
   
   def setup_logging(service_name: str, level: str = "INFO"):
       # Consistent format across all services
       logging.basicConfig(
           format=f"[{service_name}] %(asctime)s - %(name)s - %(levelname)s - %(message)s",
           level=level
       )
   ```

8. **Create unified test pattern**:
   ```bash
   # Root Makefile handles all, services just have:
   # agents/pytest.ini
   [pytest]
   testpaths = tests
   python_files = test_*.py
   ```

9. **Specific service updates**:
   ```bash
   # agents: Remove complex Makefile, use root commands
   # auth: Remove tunnel complexity from Makefile (keep as separate command)
   # database: Add missing lint/format commands to root
   # homepage: Create minimal package.json scripts that defer to root
   # all: Remove venv activation differences, use consistent pattern
   ```

10. **Create service config template**:
    ```python
    # shared/config_base.py
    from pydantic_settings import BaseSettings
    
    class ServiceConfig(BaseSettings):
        service_name: str
        port: int
        host: str = "0.0.0.0"
        log_level: str = "INFO"
        database_url: str
        
        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"
    ```

**Verification**: Run `./scripts/unification-checklist.sh` to ensure patterns are unified.

### Phase 5: Configure Heroku Deployments (30 min)
**Goal**: Set up subdirectory deployments.

1. **Add Heroku remotes**:
   ```bash
   git remote add heroku-agents https://git.heroku.com/hirecj-agents.git
   git remote add heroku-auth https://git.heroku.com/hirecj-auth.git
   git remote add heroku-homepage https://git.heroku.com/hirecj-homepage.git
   git remote add heroku-database https://git.heroku.com/hirecj-database.git
   ```

2. **Deploy each service**:
   ```bash
   git subtree push --prefix agents heroku-agents main
   git subtree push --prefix auth heroku-auth main
   # ... repeat for each
   ```

### Phase 6: Cleanup & Documentation (30 min)
1. Update main README.md
2. Archive old repos in GitHub (Settings → Archive)
3. Test everything works

### Rollback Plan
If issues arise:
- Original repos still exist with full history
- Each has a `pre-monorepo-backup` branch
- Can clone and continue as before

### Migration Timeline
- **Total time**: ~3.25 hours
  - Phase 1: 30 min (backup)
  - Phase 2: 15 min (prep)
  - Phase 3: 60 min (convert)
  - Phase 4: 15 min (activate)
  - Phase 4.5: 45 min (unify patterns)
  - Phase 5: 30 min (Heroku)
  - Phase 6: 30 min (cleanup)
- **Best time**: Low-activity period
- **Verification**: Run `./scripts/migration-checklist.sh` after each phase

### Root .gitignore
```gitignore
# Environment
.env
.env.local
*.env

# Python
__pycache__/
*.py[cod]
venv/
.pytest_cache/
.coverage

# Node.js
node_modules/
dist/
build/
.next/

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store

# Logs
*.log
logs/

# Local data
data/conversations/*.json
data/merchant_memory/*.yaml
!data/**/.gitkeep

# Old structure
hirecj-*/
```

## Development Workflow

### Starting Fresh
```bash
git clone https://github.com/cratejoy/hirecj.git
cd hirecj
make install      # Install all dependencies
make dev          # Start PostgreSQL & Redis

# Then in separate terminals:
make dev-agents   # Terminal 1: Start agents (port 8000)
make dev-homepage # Terminal 2: Start homepage (port 3000)

# Or use tmux for everything at once:
make dev-all     # Opens all services in tmux windows
```

### Working on a Service
```bash
# Start infrastructure
make dev-infra    # Just PostgreSQL & Redis

# Work on specific service
cd agents
make dev-agents   # Hot reload enabled!
# Make changes - they auto-reload
make test-agents  # Run tests
make deploy-agents # Deploy when ready
```

### Why This Approach?
- ✅ **Hot reload works**: Changes reflect instantly
- ✅ **Easy debugging**: Attach debuggers, see logs clearly
- ✅ **Fast startup**: No Docker build times for apps
- ✅ **IDE friendly**: Your IDE sees the actual running process
- ✅ **Realistic**: Matches how you'll run in production (Heroku)

### Creating PRs
```bash
# All changes in one repo!
git checkout -b feature/my-feature
# Make changes to any service
git add .
git commit -m "Update auth and agents services"
git push origin feature/my-feature
# One PR for all changes!
```

## Environment Management

### .env.example (root level)
```
# Shared
DATABASE_URL=postgresql://localhost:5432/hirecj

# Auth Service
AUTH_PORT=8103
JWT_SECRET=dev_secret

# Agents Service  
AGENTS_PORT=8000
OPENAI_API_KEY=your_key

# Homepage
HOMEPAGE_PORT=3000
API_URL=http://localhost:8000
```

### Service-specific .env files
Each service can have its own .env for specific needs

## Benefits Over Current Structure

1. **Simpler PRs**: No more cross-repo PRs
2. **Unified Testing**: Run all tests with one command
3. **Shared Dependencies**: Common utilities in /shared
4. **Easy Onboarding**: Clone one repo, run one command
5. **Better Visibility**: See all changes in one place
6. **Simpler CI/CD**: One set of GitHub Actions

## Key Unifications

After migration, all services will share:
- **Same startup pattern**: `make dev-{service}` or `python -m app.main`
- **Same config pattern**: Pydantic settings with `.env` files
- **Same test pattern**: `pytest` with consistent configuration
- **Same logging format**: `[service] timestamp - module - level - message`
- **Same port strategy**: No conflicts, clearly assigned
- **Same deployment**: `git subtree push --prefix {service} heroku-{service} main`

## North Star Alignment

✅ **Simplify**: One repo, one truth, one way to do things
✅ **No Cruft**: Remove git submodule complexity and redundant scripts
✅ **Elegant**: Clean structure, unified patterns
✅ **Long-term**: Scales with the team, easy to onboard
✅ **Backend-Driven**: Services clearly separated but consistently managed

## Next Steps

1. Get approval on this plan
2. Create feature branch for restructuring
3. Migrate services one by one
4. Test local development flow
5. Update Heroku deployments
6. Merge and celebrate! 🎉