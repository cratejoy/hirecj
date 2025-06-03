# HireCJ Database Service

A clean, extensible REST API for managing external service connections with OAuth authentication.

## Overview

This service provides a unified interface for checking and managing connections to external services like Freshdesk, Google Analytics, and more. Built with simplicity and extensibility in mind.

## Features

- 🔌 **Pluggable Architecture** - Easy to add new service connectors
- 🔐 **OAuth Support** - Built-in OAuth credential management
- 🚀 **Fast & Simple** - Built with FastAPI for performance
- 📊 **Status Monitoring** - Real-time connection status for all services
- 🎯 **Single Tenant** - Designed for single organization use

## Quick Start

```bash
# Install dependencies
make install

# Run development server
make dev

# Server will be available at http://localhost:8002
# API documentation at http://localhost:8002/docs
```

## API Endpoints

### Connection Management

- `GET /api/v1/connections` - Get status of all service connections
- `GET /api/v1/connections/{service_type}` - Get status of specific service
- `POST /api/v1/connections/{service_type}/connect` - Connect to a service
- `POST /api/v1/connections/{service_type}/disconnect` - Disconnect from a service
- `POST /api/v1/connections/{service_type}/refresh` - Refresh OAuth token

### Health Check

- `GET /health` - Service health check
- `GET /` - API information

## Supported Services

- **Freshdesk** - Customer support platform
- **Google Analytics** - Web analytics service

## Adding New Services

1. Create a new connector in `app/connectors/`
2. Inherit from `ServiceConnector` base class
3. Implement required methods (connect, check_connection, disconnect, refresh_token)
4. Register in `ConnectionManager`

Example:
```python
from app.connectors.base import ServiceConnector
from app.models.connection import ServiceType

class MyServiceConnector(ServiceConnector):
    def __init__(self):
        super().__init__(ServiceType.MY_SERVICE)
    
    async def connect(self, credentials):
        # Implementation
        pass
```

## Database Setup

1. **Start PostgreSQL with Docker:**
   ```bash
   make db-up
   ```
   This starts PostgreSQL on port 5435 (non-default to avoid conflicts)

2. **Run migrations:**
   ```bash
   make db-upgrade
   ```

3. **Initialize development data (optional):**
   ```bash
   python scripts/init_dev_data.py
   ```

## Configuration

Environment variables:
- `APP_HOST` - Server host (default: 0.0.0.0)
- `APP_PORT` - Server port (default: 8002)
- `DATABASE_URL` - PostgreSQL connection string (default: postgresql://hirecj:hirecj_dev_password@localhost:5435/hirecj_connections)
- `LOG_LEVEL` - Logging level (default: INFO)
- `DEBUG` - Debug mode (default: False)

## Multi-Tenancy

This service is built with multi-tenancy in mind. Each account has isolated data:

- **Accounts**: Top-level tenant container
- **Users**: Belong to an account
- **Connections**: Service connections belong to an account
- **Credentials**: OAuth credentials belong to an account

The database schema uses JSONB columns for flexible, schemaless data storage while maintaining relational integrity for tenant isolation.

## Development

```bash
# Run tests
make test

# Clean build files
make clean
```
