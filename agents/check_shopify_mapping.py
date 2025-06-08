#!/usr/bin/env python3
"""Check how Shopify customers are mapped to Freshdesk tickets."""

from app.utils.supabase_util import get_db_connection
from psycopg2.extras import RealDictCursor

def check_shopify_mapping():
    """Check if Shopify customers can be linked to tickets via email."""
    
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Check if we have Shopify customers
            print('=== Checking Shopify customers table ===')
            cur.execute("""
                SELECT COUNT(*) as total_customers,
                       COUNT(DISTINCT merchant_id) as merchants_with_customers
                FROM etl_shopify_customers
            """)
            result = cur.fetchone()
            print(f"Total Shopify customers: {result['total_customers']}")
            print(f"Merchants with customers: {result['merchants_with_customers']}")
            
            # Sample Shopify customer data
            cur.execute("""
                SELECT 
                    shopify_customer_id,
                    merchant_id,
                    data->>'email' as email,
                    data->>'first_name' as first_name,
                    data->>'last_name' as last_name
                FROM etl_shopify_customers
                LIMIT 5
            """)
            print('\nSample Shopify customers:')
            for row in cur.fetchall():
                print(f"  Customer {row['shopify_customer_id']}: {row['email']} ({row['first_name']} {row['last_name']})")
            
            # Check if any ticket emails match Shopify customer emails
            print('\n=== Checking for email matches between tickets and Shopify customers ===')
            cur.execute("""
                WITH ticket_emails AS (
                    SELECT DISTINCT 
                        t.merchant_id,
                        t.freshdesk_ticket_id,
                        t.parsed_email,
                        t.data->'requester'->>'email' as requester_email
                    FROM etl_freshdesk_tickets t
                    WHERE t.parsed_email IS NOT NULL OR t.data->'requester'->>'email' IS NOT NULL
                ),
                shopify_emails AS (
                    SELECT DISTINCT
                        s.merchant_id,
                        s.shopify_customer_id,
                        s.data->>'email' as email
                    FROM etl_shopify_customers s
                    WHERE s.data->>'email' IS NOT NULL
                )
                SELECT 
                    te.merchant_id,
                    COUNT(DISTINCT te.freshdesk_ticket_id) as matched_tickets,
                    COUNT(DISTINCT se.shopify_customer_id) as matched_customers
                FROM ticket_emails te
                INNER JOIN shopify_emails se 
                    ON te.merchant_id = se.merchant_id 
                    AND (te.parsed_email = se.email OR te.requester_email = se.email)
                GROUP BY te.merchant_id
            """)
            
            matches = cur.fetchall()
            if matches:
                print('Found email matches:')
                for match in matches:
                    print(f"  Merchant {match['merchant_id']}: {match['matched_tickets']} tickets match {match['matched_customers']} Shopify customers")
            else:
                print('No email matches found between tickets and Shopify customers')
            
            # Show a few example matches
            print('\n=== Example email matches ===')
            cur.execute("""
                WITH ticket_emails AS (
                    SELECT 
                        t.merchant_id,
                        t.freshdesk_ticket_id,
                        COALESCE(t.parsed_email, t.data->'requester'->>'email') as email
                    FROM etl_freshdesk_tickets t
                    WHERE t.parsed_email IS NOT NULL OR t.data->'requester'->>'email' IS NOT NULL
                )
                SELECT 
                    te.freshdesk_ticket_id,
                    te.email,
                    s.shopify_customer_id,
                    s.data->>'first_name' as first_name,
                    s.data->>'last_name' as last_name
                FROM ticket_emails te
                INNER JOIN etl_shopify_customers s 
                    ON te.merchant_id = s.merchant_id 
                    AND te.email = s.data->>'email'
                LIMIT 5
            """)
            
            examples = cur.fetchall()
            if examples:
                print('Example matches:')
                for ex in examples:
                    print(f"  Ticket {ex['freshdesk_ticket_id']} ({ex['email']}) -> Shopify Customer {ex['shopify_customer_id']} ({ex['first_name']} {ex['last_name']})")
            else:
                print('No example matches to show')
            
            # Check merchant configuration
            print('\n=== Checking merchant configuration ===')
            cur.execute("""
                SELECT 
                    m.id,
                    m.name,
                    mi.platform,
                    mi.is_active
                FROM merchants m
                LEFT JOIN merchant_integrations mi ON m.id = mi.merchant_id
                ORDER BY m.id, mi.platform
            """)
            
            print('Merchant integrations:')
            for row in cur.fetchall():
                print(f"  Merchant {row['id']} ({row['name']}): {row['platform']} - Active: {row['is_active']}")

if __name__ == '__main__':
    check_shopify_mapping()