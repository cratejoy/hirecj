#!/usr/bin/env python
"""Investigate custom_fields structure in freshdesk_tickets"""

import json
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import get_config

config = get_config()

# Create engine
engine = create_engine(config.DATABASE_URL)
Session = sessionmaker(bind=engine)

def investigate_custom_fields():
    with Session() as session:
        print("=== 1. Looking for tickets with 'shopify' anywhere in JSONB data ===")
        result = session.execute(text("""
            SELECT id, data
            FROM freshdesk_tickets
            WHERE data::text ILIKE '%shopify%'
            LIMIT 5
        """))
        
        shopify_tickets = result.fetchall()
        print(f"Found {len(shopify_tickets)} tickets with 'shopify' in data")
        
        for ticket_id, data in shopify_tickets:
            print(f"\n--- Ticket {ticket_id} ---")
            print(json.dumps(data, indent=2)[:1000] + "..." if len(json.dumps(data)) > 1000 else json.dumps(data, indent=2))
        
        print("\n=== 2. Examining custom_fields structure ===")
        result = session.execute(text("""
            SELECT id, 
                   data->'custom_fields' as custom_fields,
                   jsonb_typeof(data->'custom_fields') as cf_type
            FROM freshdesk_tickets
            WHERE data->'custom_fields' IS NOT NULL
            LIMIT 5
        """))
        
        for ticket_id, custom_fields, cf_type in result:
            print(f"\n--- Ticket {ticket_id} ---")
            print(f"custom_fields type: {cf_type}")
            print(f"custom_fields content: {json.dumps(custom_fields, indent=2)[:500]}")
        
        print("\n=== 3. Looking for exact string 'cf_shopify_customer_id' ===")
        result = session.execute(text("""
            SELECT id, data
            FROM freshdesk_tickets
            WHERE data::text LIKE '%cf_shopify_customer_id%'
            LIMIT 5
        """))
        
        cf_tickets = result.fetchall()
        print(f"Found {len(cf_tickets)} tickets with 'cf_shopify_customer_id'")
        
        for ticket_id, data in cf_tickets:
            print(f"\n--- Ticket {ticket_id} ---")
            # Extract the custom_fields part specifically
            if 'custom_fields' in data:
                print("custom_fields:", json.dumps(data['custom_fields'], indent=2))
            else:
                print("Full data preview:", json.dumps(data, indent=2)[:1000])
        
        print("\n=== 4. Checking if custom_fields might be nested differently ===")
        result = session.execute(text("""
            SELECT DISTINCT jsonb_object_keys(data->'custom_fields')
            FROM freshdesk_tickets
            WHERE data->'custom_fields' IS NOT NULL
            AND jsonb_typeof(data->'custom_fields') = 'object'
            LIMIT 20
        """))
        
        keys = [row[0] for row in result]
        print(f"Found custom_fields keys: {keys}")
        
        print("\n=== 5. Looking for any field containing 'shopify' in custom_fields ===")
        result = session.execute(text("""
            SELECT id, data->'custom_fields'
            FROM freshdesk_tickets
            WHERE EXISTS (
                SELECT 1 
                FROM jsonb_each_text(data->'custom_fields') 
                WHERE key ILIKE '%shopify%' OR value ILIKE '%shopify%'
            )
            LIMIT 5
        """))
        
        shopify_cf_tickets = result.fetchall()
        print(f"Found {len(shopify_cf_tickets)} tickets with 'shopify' in custom_fields")
        
        for ticket_id, custom_fields in shopify_cf_tickets:
            print(f"\n--- Ticket {ticket_id} ---")
            print(json.dumps(custom_fields, indent=2))

if __name__ == "__main__":
    investigate_custom_fields()