# Migration 004: Add Source Type and Merchant Integrations

## Overview
This migration adds source tracking for support tickets and creates a table for storing merchant integration configurations.

## Changes

### 1. Source Type Enum
- Created `source_type` enum with values: `'freshdesk'`, `'shopify'`
- Added `source_type` column to `support_tickets` table
- Made the column NOT NULL after migrating existing data

### 2. External ID Cleanup
- Removed the `freshdesk_` prefix from existing ticket external_ids
- External IDs now store the raw ID from the source system
- Source type is tracked separately in the `source_type` column

### 3. Updated Unique Constraint
- Changed from `(merchant_id, external_id)` to `(merchant_id, source_type, external_id)`
- This allows the same external_id from different sources

### 4. Merchant Integrations Table
- Created `merchant_integrations` table to store API keys and configuration
- Uses the same `source_type` enum
- Stores encrypted API keys and integration-specific config in JSONB

## Running the Migration

```bash
# Apply the migration
python scripts/apply_migration.py

# Or manually with
python scripts/run_migration.py scripts/004_add_source_type_and_integrations.sql
```

## Code Updates Required

### 1. SQLAlchemy Models (✅ Done)
- Added `SourceType` enum to models
- Updated `SupportTicket` model with `source_type` field
- Added `MerchantIntegration` model
- Updated unique constraints

### 2. ETL Libraries (✅ Done)
- **freshdesk_lib.py**: Removed `freshdesk_` prefix, added `source_type=SourceType.FRESHDESK`
- **shopify_lib.py**: Removed `shopify_order_` prefix, added `source_type=SourceType.SHOPIFY`
- Updated conflict resolution to use new unique constraint

### 3. Deprecated Scripts
The following scripts reference the old schema and should be updated or removed:
- `scripts/check_customer_data.py` - References removed `customer_id` column
- `scripts/cleanup_freshdesk_customers.py` - References removed `customer_id` column

## Benefits

1. **Cleaner External IDs**: No more prefixes cluttering the IDs
2. **Better Source Tracking**: Explicit source_type field makes filtering easier
3. **Integration Management**: Central place to store API keys and config
4. **Future Proof**: Easy to add new source types (e.g., 'zendesk', 'intercom')

## Example Queries

```sql
-- Get all Freshdesk tickets
SELECT * FROM support_tickets WHERE source_type = 'freshdesk';

-- Get all Shopify orders
SELECT * FROM support_tickets WHERE source_type = 'shopify';

-- Check merchant integrations
SELECT * FROM merchant_integrations WHERE merchant_id = 1;
```