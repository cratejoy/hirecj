#!/usr/bin/env python
"""Investigate custom_fields structure for Shopify data in etl_freshdesk_tickets"""

import json
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.utils.supabase_util import execute_query

def investigate():
    print("=== 1. Looking for tickets with 'shopify' anywhere in JSONB data ===")
    results = execute_query("""
        SELECT freshdesk_ticket_id, data
        FROM etl_freshdesk_tickets
        WHERE data::text ILIKE '%shopify%'
        LIMIT 5
    """)
    
    if results:
        print(f"Found {len(results)} tickets with 'shopify' in data")
        for ticket_id, data in results:
            print(f"\n--- Ticket {ticket_id} ---")
            # Pretty print with truncation
            data_str = json.dumps(data, indent=2)
            if len(data_str) > 2000:
                print(data_str[:2000] + "\n... (truncated)")
            else:
                print(data_str)
    else:
        print("No tickets found with 'shopify' in data")
    
    print("\n=== 2. Looking for exact 'cf_shopify_customer_id' in data ===")
    results = execute_query("""
        SELECT freshdesk_ticket_id, 
               data->'custom_fields' as custom_fields,
               data::text as full_data
        FROM etl_freshdesk_tickets
        WHERE data::text LIKE '%cf_shopify_customer_id%'
        LIMIT 5
    """)
    
    if results:
        print(f"Found {len(results)} tickets with 'cf_shopify_customer_id'")
        for ticket_id, custom_fields, full_data in results:
            print(f"\n--- Ticket {ticket_id} ---")
            if custom_fields:
                print("custom_fields:", json.dumps(custom_fields, indent=2))
            else:
                # Search for cf_shopify_customer_id in the full data
                if 'cf_shopify_customer_id' in full_data:
                    print("Found cf_shopify_customer_id in data, searching for location...")
                    # Try to find where it appears
                    data_dict = json.loads(full_data)
                    for key, value in data_dict.items():
                        if isinstance(value, dict) and 'cf_shopify_customer_id' in str(value):
                            print(f"Found in '{key}':", json.dumps(value, indent=2)[:500])
                            break
    else:
        print("No tickets found with 'cf_shopify_customer_id'")
    
    print("\n=== 3. Examining custom_fields structure ===")
    results = execute_query("""
        SELECT freshdesk_ticket_id, 
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
    else:
        print("No tickets found with custom_fields")
    
    print("\n=== 4. Check all unique keys in custom_fields ===")
    results = execute_query("""
        SELECT DISTINCT jsonb_object_keys(data->'custom_fields') as key
        FROM etl_freshdesk_tickets
        WHERE data->'custom_fields' IS NOT NULL
        AND jsonb_typeof(data->'custom_fields') = 'object'
        ORDER BY key
    """)
    
    if results:
        keys = [row[0] for row in results]
        print(f"Found {len(keys)} unique custom_field keys:")
        shopify_keys = []
        for key in keys:
            if 'shopify' in key.lower():
                shopify_keys.append(key)
                print(f"  - {key} <-- SHOPIFY KEY FOUND!")
            else:
                print(f"  - {key}")
        
        if shopify_keys:
            print(f"\nShopify-related keys found: {shopify_keys}")
    else:
        print("No custom_fields keys found")
    
    print("\n=== 5. Check parsed_shopify_id column ===")
    results = execute_query("""
        SELECT COUNT(*) as total,
               COUNT(parsed_shopify_id) as with_shopify_id,
               COUNT(CASE WHEN parsed_shopify_id IS NOT NULL AND parsed_shopify_id != '' THEN 1 END) as non_empty_shopify_id
        FROM etl_freshdesk_tickets
    """)
    
    if results:
        total, with_id, non_empty = results[0]
        print(f"Total tickets: {total}")
        print(f"Tickets with parsed_shopify_id: {with_id}")
        print(f"Tickets with non-empty parsed_shopify_id: {non_empty}")
    
    print("\n=== 6. Sample tickets with parsed_shopify_id ===")
    results = execute_query("""
        SELECT freshdesk_ticket_id, parsed_shopify_id, data->'custom_fields'
        FROM etl_freshdesk_tickets
        WHERE parsed_shopify_id IS NOT NULL AND parsed_shopify_id != ''
        LIMIT 3
    """)
    
    if results:
        for ticket_id, shopify_id, custom_fields in results:
            print(f"\n--- Ticket {ticket_id} ---")
            print(f"parsed_shopify_id: {shopify_id}")
            print(f"custom_fields: {json.dumps(custom_fields, indent=2) if custom_fields else 'None'}")

if __name__ == "__main__":
    investigate()