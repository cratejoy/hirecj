#!/usr/bin/env python3
"""Check parsed_shopify_id values in the database."""

from app.utils.supabase_util import get_db_connection
from psycopg2.extras import RealDictCursor
import json

def check_shopify_ids():
    """Check the state of parsed_shopify_id values in tickets table."""
    
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Query 1: Check for any non-null parsed_shopify_id values
            print('=== Checking for non-null parsed_shopify_id values ===')
            cur.execute("""
                SELECT COUNT(*) as total_tickets,
                       COUNT(parsed_shopify_id) as tickets_with_shopify_id,
                       COUNT(CASE WHEN parsed_shopify_id IS NOT NULL AND parsed_shopify_id != '' THEN 1 END) as non_empty_shopify_ids
                FROM etl_freshdesk_tickets
            """)
            result = cur.fetchone()
            print(f'Total tickets: {result["total_tickets"]}')
            print(f'Tickets with parsed_shopify_id (not null): {result["tickets_with_shopify_id"]}')
            print(f'Tickets with non-empty parsed_shopify_id: {result["non_empty_shopify_ids"]}')
            
            # Query 2: Check custom_fields JSONB data
            print('\n=== Examining custom_fields JSONB data ===')
            cur.execute("""
                SELECT freshdesk_ticket_id, data->'custom_fields' as custom_fields, parsed_shopify_id
                FROM etl_freshdesk_tickets
                WHERE data->'custom_fields' IS NOT NULL
                LIMIT 10
            """)
            
            tickets_with_fields = cur.fetchall()
            print(f'Found {len(tickets_with_fields)} tickets with custom_fields')
            
            # Look for any field that might contain shopify ID
            shopify_field_names = set()
            for ticket in tickets_with_fields:
                if ticket['custom_fields']:
                    for key in ticket['custom_fields'].keys():
                        if 'shopify' in key.lower() or 'customer' in key.lower():
                            shopify_field_names.add(key)
            
            if shopify_field_names:
                print(f'\nFound potential Shopify-related fields: {shopify_field_names}')
            
            # Show sample of custom_fields data
            print('\nSample custom_fields data (first 3 tickets):')
            for i, ticket in enumerate(tickets_with_fields[:3]):
                print(f'\nTicket {ticket["freshdesk_ticket_id"]}:')
                print(f'  parsed_shopify_id: {ticket["parsed_shopify_id"]}')
                if ticket['custom_fields']:
                    print('  custom_fields:')
                    for key, value in ticket['custom_fields'].items():
                        if value is not None and value != '':
                            print(f'    {key}: {value}')
            
            # Query 3: Check if cf_shopify_customer_id field exists
            print('\n=== Checking for cf_shopify_customer_id field ===')
            cur.execute("""
                SELECT COUNT(*) as count
                FROM etl_freshdesk_tickets
                WHERE data->'custom_fields' ? 'cf_shopify_customer_id'
            """)
            result = cur.fetchone()
            print(f'Tickets with cf_shopify_customer_id field: {result["count"]}')
            
            # Check for any variations
            field_variations = ['cf_shopify_customer_id', 'shopify_customer_id', 'cf_shopify_id', 'shopify_id']
            for field in field_variations:
                cur.execute("""
                    SELECT COUNT(*) as count
                    FROM etl_freshdesk_tickets
                    WHERE data->'custom_fields' ? %s AND data->'custom_fields'->%s IS NOT NULL AND data->'custom_fields'->%s != ''
                """, (field, field, field))
                result = cur.fetchone()
                if result['count'] > 0:
                    print(f'  Found {result["count"]} tickets with non-empty {field}')

if __name__ == '__main__':
    check_shopify_ids()