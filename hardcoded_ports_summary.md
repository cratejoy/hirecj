# Hardcoded Port Numbers in Service Configuration

## Service Startup Scripts and Main Files

### 1. Agents Service (Port 8000)
- **Config**: `agents/app/config.py`
  - Line 48: `app_port: int = Field(8000, env="AGENTS_SERVICE_PORT")`
  - Line 102: `api_port: int = Field(8000, env="API_PORT")`
- **Dev Script**: `agents/scripts/dev_watcher.py`
  - Line 47: `'--host', '0.0.0.0', '--port', '8000'`
  - Line 175: `logger.info("🌐 Server: http://localhost:8000")`

### 2. Editor Backend Service (Port 8001)
- **Config**: `editor-backend/app/config.py`
  - Line 33-34: `def api_port(self) -> int: return int(os.getenv("EDITOR_BACKEND_PORT", "8001"))`
- **Test Files**: Multiple test files hardcode `ws://localhost:8001/ws/playground`

### 3. Database Service (Port 8002)
- **Config**: `database/app/config.py`
  - Line 23: `app_port: int = Field(8002, env="DATABASE_SERVICE_PORT")`
  - Line 91: `return f"http://localhost:8002"`

### 4. Auth Service (Port 8103)
- **Config**: `auth/app/config.py`
  - Line 29: `app_port: int = Field(8103, env="PORT")`

### 5. Knowledge Service (Port 8004)
- **Main**: `knowledge/gateway/main.py`
  - Line 75: `PORT = int(os.getenv("KNOWLEDGE_SERVICE_PORT", "8004"))`
- **Scripts**: Multiple scripts hardcode `http://localhost:8004`
- **Setup**: `knowledge/scripts/setup.sh`
  - Line 44: `python -m uvicorn gateway.main:app --reload --port 8004`

### 6. Homepage Frontend (Port 3456)
- **Server**: `homepage/server/index.ts`
  - Line 32: `const port = process.env.PORT || 3456;`
- **Vite Config**: Multiple references to `http://localhost:3456`

### 7. Editor Frontend (Port 3458)
- **Vite Config**: `editor/vite.config.ts`
  - Line 81: `port: 3458,`

### 8. LightRAG Server (Port 9621)
- **Script**: `knowledge/run_lightrag_server.sh`
  - Line 41: `--port 9621`

### 9. Database Connection (Port 5435)
- **Alembic**: `database/alembic.ini`
  - Line 52: `postgresql://hirecj:hirecj_dev_password@localhost:5435/hirecj_connections`
- **Config**: `database/app/config.py`
  - Line 40: `postgresql://hirecj:hirecj_dev_password@localhost:5435/hirecj_connections`

## Cross-Service References
Multiple services have hardcoded references to other services' URLs:
- `database/app/config.py`: References all service URLs
- `auth/app/config.py`: References multiple service URLs
- `agents/app/config.py`: References multiple service URLs
- CORS configurations in multiple `main.py` files

## Test Files
Numerous test files contain hardcoded URLs and ports for testing purposes.