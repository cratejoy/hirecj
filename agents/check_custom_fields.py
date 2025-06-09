#!/usr/bin/env python3
"""Check all custom fields in Freshdesk tickets."""

from app.utils.supabase_util import get_db_connection
from psycopg2.extras import RealDictCursor
import json
from collections import Counter

def check_custom_fields():
    """Analyze all custom fields in tickets to find the right field for Shopify IDs."""
    
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get all unique custom field names
            print('=== Analyzing all custom fields ===')
            cur.execute("""
                SELECT jsonb_object_keys(data->'custom_fields') as field_name
                FROM etl_freshdesk_tickets
                WHERE data->'custom_fields' IS NOT NULL
                GROUP BY field_name
                ORDER BY field_name
            """)
            
            all_fields = [row['field_name'] for row in cur.fetchall()]
            print(f'Found {len(all_fields)} unique custom fields:')
            for field in all_fields:
                print(f'  - {field}')
            
            # Look for fields that might contain Shopify data
            print('\n=== Searching for potential Shopify-related fields ===')
            shopify_candidates = []
            for field in all_fields:
                if any(keyword in field.lower() for keyword in ['shopify', 'customer', 'id', 'identifier']):
                    shopify_candidates.append(field)
            
            if shopify_candidates:
                print(f'Found {len(shopify_candidates)} potential Shopify-related fields:')
                for field in shopify_candidates:
                    # Count how many tickets have non-empty values for this field
                    cur.execute("""
                        SELECT COUNT(*) as count
                        FROM etl_freshdesk_tickets
                        WHERE data->'custom_fields'->%s IS NOT NULL 
                        AND data->'custom_fields'->%s != 'null'::jsonb
                        AND data->'custom_fields'->%s != '""'::jsonb
                    """, (field, field, field))
                    count = cur.fetchone()['count']
                    
                    # Get sample values
                    cur.execute("""
                        SELECT data->'custom_fields'->%s as value
                        FROM etl_freshdesk_tickets
                        WHERE data->'custom_fields'->%s IS NOT NULL 
                        AND data->'custom_fields'->%s != 'null'::jsonb
                        AND data->'custom_fields'->%s != '""'::jsonb
                        LIMIT 5
                    """, (field, field, field, field))
                    samples = [row['value'] for row in cur.fetchall()]
                    
                    print(f'\n  Field: {field}')
                    print(f'    Non-empty values: {count}')
                    if samples:
                        print(f'    Sample values: {samples[:3]}')
            else:
                print('No obvious Shopify-related custom fields found.')
            
            # Check if there's a pattern in ticket data that indicates Shopify customer
            print('\n=== Checking for Shopify references in other ticket fields ===')
            
            # Check requester data
            cur.execute("""
                SELECT COUNT(*) as count
                FROM etl_freshdesk_tickets
                WHERE data->'requester' IS NOT NULL
            """)
            requester_count = cur.fetchone()['count']
            print(f'Tickets with requester data: {requester_count}')
            
            # Sample requester data
            cur.execute("""
                SELECT 
                    freshdesk_ticket_id,
                    data->'requester' as requester,
                    data->'requester'->'email' as email
                FROM etl_freshdesk_tickets
                WHERE data->'requester' IS NOT NULL
                LIMIT 5
            """)
            print('\nSample requester data:')
            for row in cur.fetchall():
                print(f"  Ticket {row['freshdesk_ticket_id']}: email = {row['email']}")
            
            # Check tags for Shopify references
            cur.execute("""
                SELECT data->'tags' as tags
                FROM etl_freshdesk_tickets
                WHERE data->'tags' IS NOT NULL AND data->'tags' != '[]'::jsonb
                LIMIT 10
            """)
            print('\nSample tags:')
            for row in cur.fetchall():
                print(f"  {row['tags']}")

if __name__ == '__main__':
    check_custom_fields()