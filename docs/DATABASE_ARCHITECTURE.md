# Database Architecture

## Single Shared Database

HireCJ uses a **single PostgreSQL database** shared by all services. This follows our North Star principle of "Single Source of Truth".

### Connection

All services connect using the same connection string:
- **Environment Variable**: `SUPABASE_CONNECTION_STRING`
- **Database**: Single PostgreSQL instance (Supabase in production)

### Services

1. **Auth Service**
   - Uses: `supabase_connection_string`
   - Tables: `users`, `web_sessions`, `oauth_csrf_state`
   - Note: The `AUTH_DATABASE_URL` in config was legacy and has been removed

2. **Agents Service**
   - Uses: `supabase_connection_string`
   - Tables: All business tables, shared auth tables
   - Migrations: All database migrations run from here

### Tables Overview

```
📊 Shared Database Tables:
├── Authentication & Sessions
│   ├── users                    # User accounts
│   ├── web_sessions            # HTTP session storage
│   └── oauth_csrf_state        # OAuth CSRF protection
│
├── Business Data
│   ├── merchants               # Merchant accounts
│   ├── merchant_integrations   # OAuth tokens & integration data
│   ├── conversations          # Chat conversations
│   └── user_facts             # Extracted user facts
│
├── ETL & Sync
│   ├── etl_freshdesk_*        # Freshdesk data
│   ├── etl_shopify_*          # Shopify data
│   ├── sync_metadata          # Sync tracking
│   └── daily_ticket_summaries # Aggregated data
│
└── Legacy (to be removed)
    └── oauth_completion_state  # Old OAuth handoff mechanism
```

### Migrations

All database migrations are managed from the agents service:
- Location: `agents/app/migrations/`
- Run: `cd agents && python scripts/run_migration.py app/migrations/XXX_name.sql`

### Important Notes

1. **No Separate Auth Database**: Despite old configs, auth service uses the same database
2. **Single Migration Point**: All schema changes go through agents service
3. **Shared Models**: Database models in `shared/db_models.py` are used by all services

### Environment Configuration

In your `.env` file, you only need:
```env
# Single database connection for all services
SUPABASE_CONNECTION_STRING=postgresql://user:pass@host:port/database
```

Do NOT use:
- ❌ `AUTH_DATABASE_URL` (removed - was never actually used)
- ❌ Multiple database connections
- ❌ Service-specific databases

This architecture ensures data consistency, simplifies operations, and maintains a true single source of truth.