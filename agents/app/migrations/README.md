# Database Migrations

## Setting Up User Identity Tables

### For Development

1. **Ensure you have the database URL configured:**
   ```bash
   # Check your .env file has:
   IDENTITY_DATABASE_URL=postgresql://postgres:password@db.supabase.co:5432/postgres
   ```

2. **Run the migration:**
   ```bash
   # From the project root
   psql $IDENTITY_DATABASE_URL -f agents/app/migrations/003_user_identity.sql
   ```

3. **Verify tables were created:**
   ```bash
   psql $IDENTITY_DATABASE_URL -c "\dt users; \dt conversations; \dt user_facts;"
   ```

### For Production

1. **Review the migration file first:**
   - Location: `agents/app/migrations/003_user_identity.sql`
   - Creates 3 tables: users, conversations, user_facts
   - Safe to run multiple times (uses IF NOT EXISTS)

2. **Run via your deployment process or manually:**
   ```sql
   -- Connect to your production database and run:
   \i agents/app/migrations/003_user_identity.sql
   ```

### What This Migration Does

- **users table**: Stores user identity from Shopify OAuth
  - `id`: Deterministic usr_xxx format
  - `shop_domain`: Unique Shopify domain
  - `email`: Optional email address
  - `created_at`: Timestamp

- **conversations table**: Archives conversation messages
  - `user_id`: Links to users table
  - `message`: JSONB message data
  - `created_at`: Timestamp

- **user_facts table**: Stores learned information
  - `user_id`: Links to users table  
  - `facts`: JSONB array of facts

### Troubleshooting

If you get connection errors:
1. Verify IDENTITY_DATABASE_URL is set correctly
2. Check you have network access to the database
3. Ensure your database user has CREATE TABLE permissions

If tables already exist:
- The migration is safe to re-run (uses IF NOT EXISTS)
- To start fresh: `DROP TABLE conversations, user_facts, users CASCADE;`