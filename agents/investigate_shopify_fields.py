#!/usr/bin/env python
"""Investigate custom_fields structure in freshdesk_tickets"""

import json
import sys
import os
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.utils.supabase_util import execute_query

def investigate():
    print("=== 1. Looking for tickets with 'shopify' anywhere in data ===")
    results = execute_query("""
        SELECT id, data
        FROM etl_freshdesk_tickets
        WHERE data::text ILIKE '%shopify%'
        LIMIT 3
    """)
    
    if results:
        print(f"Found {len(results)} tickets with 'shopify' in data")
        for ticket_id, data in results:
            print(f"\n--- Ticket {ticket_id} ---")
            print(json.dumps(data, indent=2)[:2000] + "..." if len(json.dumps(data)) > 2000 else json.dumps(data, indent=2))
    
    print("\n=== 2. Looking for exact 'cf_shopify_customer_id' ===")
    results = execute_query("""
        SELECT id, data->'custom_fields' as custom_fields
        FROM etl_freshdesk_tickets
        WHERE data::text LIKE '%cf_shopify_customer_id%'
        LIMIT 3
    """)
    
    if results:
        print(f"Found {len(results)} tickets with 'cf_shopify_customer_id'")
        for ticket_id, custom_fields in results:
            print(f"\n--- Ticket {ticket_id} ---")
            print("custom_fields:", json.dumps(custom_fields, indent=2))
    
    print("\n=== 3. Examining custom_fields structure (first 5 tickets) ===")
    results = execute_query("""
        SELECT id, 
               jsonb_typeof(data->'custom_fields') as cf_type,
               data->'custom_fields' as custom_fields
        FROM etl_freshdesk_tickets
        WHERE data->'custom_fields' IS NOT NULL
        LIMIT 5
    """)
    
    if results:
        for ticket_id, cf_type, custom_fields in results:
            print(f"\n--- Ticket {ticket_id} ---")
            print(f"Type: {cf_type}")
            print(f"Content: {json.dumps(custom_fields, indent=2)[:1000]}")
    
    print("\n=== 4. Check if custom_fields keys are prefixed ===")
    results = execute_query("""
        SELECT DISTINCT jsonb_object_keys(data->'custom_fields') as key
        FROM etl_freshdesk_tickets
        WHERE data->'custom_fields' IS NOT NULL
        AND jsonb_typeof(data->'custom_fields') = 'object'
        ORDER BY key
        LIMIT 50
    """)
    
    if results:
        keys = [row[0] for row in results]
        print(f"Found {len(keys)} unique custom_field keys:")
        for key in keys:
            if 'shopify' in key.lower():
                print(f"  - {key} <-- SHOPIFY KEY FOUND!")
            else:
                print(f"  - {key}")
    
    print("\n=== 5. Let's check the raw JSONB structure of a ticket ===")
    results = execute_query("""
        SELECT id, data::text
        FROM etl_freshdesk_tickets
        WHERE data IS NOT NULL
        LIMIT 1
    """)
    
    if results:
        ticket_id, raw_data = results[0]
        print(f"\nRaw ticket {ticket_id} structure preview:")
        print(raw_data[:3000] + "..." if len(raw_data) > 3000 else raw_data)

if __name__ == "__main__":
    investigate()