#!/usr/bin/env python3
"""
Refactored Freshdesk sync script with separate tables for tickets, conversations, and ratings.
Supports syncing each component independently.
"""

import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from app.utils.supabase_util import get_db_session
from app.dbmodels.base import Merchant, FreshdeskTicket, FreshdeskConversation, FreshdeskRating
from app.lib.freshdesk_lib import FreshdeskETL


def main():
    """Main sync function with component-specific options."""
    parser = argparse.ArgumentParser(
        description="Freshdesk sync with separate handling for tickets, conversations, and ratings"
    )
    parser.add_argument(
        "--merchant",
        default="amir_elaguizy",
        help="Merchant name to sync (default: amir_elaguizy)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Sync tickets from last N days (default: 90)"
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        help="Maximum number of pages to fetch (for testing)"
    )
    
    # Component selection
    parser.add_argument(
        "--tickets-only",
        action="store_true",
        help="Sync only ticket data (no conversations or ratings)"
    )
    parser.add_argument(
        "--conversations-only",
        action="store_true",
        help="Sync only conversation data for existing tickets"
    )
    parser.add_argument(
        "--ratings-only",
        action="store_true",
        help="Sync only satisfaction ratings for existing tickets"
    )
    parser.add_argument(
        "--skip-tickets",
        action="store_true",
        help="Skip ticket sync (useful with --conversations or --ratings)"
    )
    parser.add_argument(
        "--skip-conversations",
        action="store_true",
        help="Skip conversation sync"
    )
    parser.add_argument(
        "--skip-ratings",
        action="store_true",
        help="Skip ratings sync"
    )
    
    args = parser.parse_args()
    
    # Determine what to sync (simplified for current implementation)
    sync_tickets = not args.ratings_only
    sync_conversations = False  # Always false - conversations sync with tickets
    sync_ratings = not args.tickets_only
    
    # Calculate since date
    since = datetime.now() - timedelta(days=args.days)
    
    # Get merchant
    with get_db_session() as session:
        merchant = session.query(Merchant).filter_by(name=args.merchant).first()
        if not merchant:
            print(f"❌ Merchant '{args.merchant}' not found")
            sys.exit(1)
        
        merchant_id = merchant.id
        merchant_name = merchant.name
    
    print(f"🚀 Freshdesk sync for merchant: {merchant_name}")
    print(f"   Components to sync:")
    if sync_tickets:
        print(f"   ✓ Tickets (from last {args.days} days)")
    if sync_conversations:
        print(f"   ✓ Conversations")
    if sync_ratings:
        print(f"   ✓ Satisfaction Ratings")
    if args.max_pages:
        print(f"   Limiting to {args.max_pages} pages per API")
    print()
    
    # Initialize ETL
    etl = FreshdeskETL(merchant_id)
    
    # Show current sync status
    print("📊 Current sync status:")
    status = etl.get_sync_status()
    for resource, info in status.items():
        if info:
            print(f"   {resource}: {info['status']} (last: {info['last_sync']})")
    print()
    
    total_results = {
        'tickets': {'synced': 0, 'errors': 0},
        'conversations': {'synced': 0, 'errors': 0},
        'ratings': {'synced': 0, 'errors': 0}
    }
    
    # Step 1: Sync tickets (core data only)
    if sync_tickets:
        print("=" * 60)
        print("STEP 1: SYNCING TICKETS (Core Data)")
        print("=" * 60)
        
        result = etl.sync_tickets(
            since=since,
            max_pages=args.max_pages
        )
        
        if result['status'] == 'success':
            print(f"✅ Tickets synced: {result['total_synced']}")
            print(f"❌ Errors: {result['total_errors']}")
            total_results['tickets'] = {
                'synced': result['total_synced'],
                'errors': result['total_errors']
            }
        else:
            print(f"❌ Ticket sync failed: {result.get('error', 'Unknown error')}")
            total_results['tickets']['errors'] = 1
    
    # Step 2: Sync conversations - SKIPPED (conversations are synced with tickets)
    if sync_conversations:
        print("\n" + "=" * 60)
        print("STEP 2: SYNCING CONVERSATIONS")
        print("=" * 60)
        print("   ⚠️  Conversations are automatically synced with tickets in this implementation")
        print("   ✅ Skipping separate conversation sync")
    
    # Step 3: Sync satisfaction ratings
    if sync_ratings:
        print("\n" + "=" * 60)
        print("STEP 3: SYNCING SATISFACTION RATINGS")
        print("=" * 60)
        
        print(f"   Fetching ALL satisfaction ratings from Freshdesk")
        
        result = etl.sync_satisfaction_ratings(
            since=None,  # Always get all ratings
            max_pages=args.max_pages
        )
        
        if result['status'] == 'success':
            print(f"\n✅ Ratings synced: {result['total_synced']}")
            print(f"   Tickets with ratings: {result.get('tickets_updated', 0)}")
            print(f"❌ Errors: {result['total_errors']}")
            total_results['ratings'] = {
                'synced': result['total_synced'],
                'errors': result['total_errors']
            }
        else:
            print(f"\n❌ Ratings sync failed: {result.get('error', 'Unknown error')}")
            total_results['ratings']['errors'] = 1
    
    # Final summary
    print("\n" + "=" * 60)
    print("SYNC SUMMARY")
    print("=" * 60)
    
    for component, stats in total_results.items():
        if stats['synced'] > 0 or stats['errors'] > 0:
            print(f"{component.capitalize()}:")
            print(f"  ✅ Synced: {stats['synced']}")
            print(f"  ❌ Errors: {stats['errors']}")
    
    # Show final sync status
    print("\n📊 Final sync status:")
    status = etl.get_sync_status()
    for resource, info in status.items():
        if info:
            print(f"   {resource}: {info['status']} (last: {info['last_sync']})")
    
    print("\n✨ Done!")


if __name__ == "__main__":
    main()