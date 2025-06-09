#!/usr/bin/env python
"""Deep search for cf_shopify_customer_id in all JSONB paths"""

import json
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.utils.supabase_util import execute_query

def search_jsonb_paths():
    print("=== 1. Search for cf_shopify_customer_id anywhere in JSONB ===")
    
    # First, let's see if cf_shopify_customer_id exists anywhere
    results = execute_query("""
        SELECT freshdesk_ticket_id,
               data
        FROM etl_freshdesk_tickets
        WHERE data::text LIKE '%cf_shopify_customer_id%'
        LIMIT 5
    """)
    
    if results:
        print(f"Found {len(results)} tickets with cf_shopify_customer_id")
        for ticket_id, data in results:
            print(f"\n--- Analyzing ticket {ticket_id} ---")
            
            # Search through all keys recursively
            def find_key(obj, target_key, path=""):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        new_path = f"{path}.{key}" if path else key
                        if key == target_key:
                            print(f"Found '{target_key}' at path: {new_path}")
                            print(f"Value: {value}")
                        find_key(value, target_key, new_path)
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        find_key(item, target_key, f"{path}[{i}]")
            
            find_key(data, "cf_shopify_customer_id")
    else:
        print("No tickets found with cf_shopify_customer_id")
    
    print("\n=== 2. Check if it might be in _raw_data ===")
    results = execute_query("""
        SELECT freshdesk_ticket_id,
               jsonb_path_query_first(data, '$._raw_data.custom_fields.cf_shopify_customer_id') as shopify_id_raw,
               jsonb_path_query_first(data, '$.custom_fields.cf_shopify_customer_id') as shopify_id_direct
        FROM etl_freshdesk_tickets
        WHERE jsonb_path_exists(data, '$._raw_data.custom_fields.cf_shopify_customer_id')
           OR jsonb_path_exists(data, '$.custom_fields.cf_shopify_customer_id')
        LIMIT 5
    """)
    
    if results:
        print(f"Found {len(results)} tickets with cf_shopify_customer_id in paths")
        for ticket_id, shopify_id_raw, shopify_id_direct in results:
            print(f"\nTicket {ticket_id}:")
            print(f"  - In _raw_data.custom_fields: {shopify_id_raw}")
            print(f"  - In custom_fields: {shopify_id_direct}")
    
    print("\n=== 3. Check all possible JSONB paths containing 'custom' ===")
    results = execute_query("""
        SELECT DISTINCT jsonb_object_keys(data) as top_key
        FROM etl_freshdesk_tickets
        WHERE data IS NOT NULL
        ORDER BY top_key
    """)
    
    if results:
        print("Top-level keys in data:")
        for row in results:
            print(f"  - {row[0]}")
    
    print("\n=== 4. Sample a ticket that likely has Shopify data ===")
    results = execute_query("""
        SELECT freshdesk_ticket_id, data
        FROM etl_freshdesk_tickets
        WHERE (data->>'subject' ILIKE '%order%' 
            OR data->>'subject' ILIKE '%subscription%'
            OR data->>'subject' ILIKE '%payment%')
        AND data->'requester'->>'email' IS NOT NULL
        LIMIT 1
    """)
    
    if results:
        ticket_id, data = results[0]
        print(f"\nExamining ticket {ticket_id} with potential order data:")
        
        # Pretty print the entire structure
        print("\nFull ticket structure:")
        print(json.dumps(data, indent=2))

if __name__ == "__main__":
    search_jsonb_paths()