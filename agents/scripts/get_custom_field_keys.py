#!/usr/bin/env python3
"""Script to extract all unique custom field keys from Freshdesk tickets."""

import logging
from collections import Counter
from app.utils.supabase_util import get_db_session
from app.dbmodels.etl_tables import FreshdeskTicket
from sqlalchemy import func

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_all_custom_field_keys():
    """Extract all unique keys from custom_fields JSONB across all tickets."""
    
    with get_db_session() as session:
        # First, let's get a sample of tickets to understand the structure
        logger.info("Fetching sample tickets to analyze custom_fields structure...")
        sample_tickets = session.query(FreshdeskTicket).limit(10).all()
        
        print("\n=== Sample Custom Fields ===")
        for i, ticket in enumerate(sample_tickets[:3]):
            custom_fields = ticket.data.get('custom_fields', {})
            print(f"\nTicket {i+1} (ID: {ticket.freshdesk_ticket_id}):")
            print(f"Custom fields: {custom_fields}")
        
        # Now get all tickets and extract custom field keys
        logger.info("\nFetching all tickets to extract custom field keys...")
        all_tickets = session.query(FreshdeskTicket).all()
        
        # Track all unique keys and their occurrence count
        custom_field_keys = Counter()
        tickets_with_custom_fields = 0
        
        for ticket in all_tickets:
            custom_fields = ticket.data.get('custom_fields', {})
            if custom_fields:
                tickets_with_custom_fields += 1
                for key in custom_fields.keys():
                    custom_field_keys[key] += 1
        
        # Display results
        print(f"\n=== Custom Fields Analysis ===")
        print(f"Total tickets analyzed: {len(all_tickets)}")
        print(f"Tickets with custom fields: {tickets_with_custom_fields}")
        print(f"Unique custom field keys found: {len(custom_field_keys)}")
        
        print("\n=== All Unique Custom Field Keys ===")
        for key, count in sorted(custom_field_keys.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(all_tickets)) * 100
            print(f"{key}: {count} tickets ({percentage:.1f}%)")
        
        # Also check if there are any nested structures
        print("\n=== Checking for Nested Structures ===")
        nested_examples = []
        for ticket in all_tickets[:100]:  # Check first 100 tickets
            custom_fields = ticket.data.get('custom_fields', {})
            for key, value in custom_fields.items():
                if isinstance(value, dict):
                    nested_examples.append({
                        'ticket_id': ticket.freshdesk_ticket_id,
                        'key': key,
                        'value': value
                    })
                elif isinstance(value, list) and value:
                    nested_examples.append({
                        'ticket_id': ticket.freshdesk_ticket_id,
                        'key': key,
                        'value': value
                    })
        
        if nested_examples:
            print("Found nested structures:")
            for example in nested_examples[:5]:  # Show first 5 examples
                print(f"  Ticket {example['ticket_id']}, Key '{example['key']}': {example['value']}")
        else:
            print("No nested structures found in custom fields.")
        
        # Try using PostgreSQL's jsonb_object_keys function for verification
        print("\n=== Using PostgreSQL jsonb_object_keys ===")
        try:
            # This query extracts all keys from the custom_fields object
            query = session.query(
                func.jsonb_object_keys(FreshdeskTicket.data['custom_fields']).label('key')
            ).distinct()
            
            db_keys = [row.key for row in query.all()]
            print(f"Keys found via jsonb_object_keys: {len(db_keys)}")
            for key in sorted(db_keys):
                print(f"  - {key}")
                
            # Compare with our Python extraction
            python_keys = set(custom_field_keys.keys())
            db_keys_set = set(db_keys)
            
            if python_keys == db_keys_set:
                print("\n✓ Python extraction matches PostgreSQL extraction!")
            else:
                print("\n⚠ Mismatch between Python and PostgreSQL extraction:")
                if python_keys - db_keys_set:
                    print(f"  Keys only in Python: {python_keys - db_keys_set}")
                if db_keys_set - python_keys:
                    print(f"  Keys only in PostgreSQL: {db_keys_set - python_keys}")
                    
        except Exception as e:
            logger.error(f"Error using jsonb_object_keys: {e}")
        
        return custom_field_keys

if __name__ == "__main__":
    get_all_custom_field_keys()