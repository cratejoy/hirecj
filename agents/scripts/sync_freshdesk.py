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
from app.dbmodels.base import Merchant
from app.dbmodels.etl_tables import FreshdeskTicket, FreshdeskConversation, FreshdeskRating
from app.lib.freshdesk_sync_lib import FreshdeskETL


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
        default=180,
        help="Sync tickets from last N days (default: 180)"
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        help="Maximum number of pages to fetch (for testing)"
    )
    parser.add_argument(
        "--force-reparse",
        action="store_true",
        help="Force re-parsing of all parsed fields"
    )
    parser.add_argument(
        "--tickets-only",
        action="store_true",
        help="Only sync ticket data without conversations"
    )
    parser.add_argument(
        "--conversations-for",
        nargs="+",
        help="Sync conversations for specific ticket IDs"
    )
    
    args = parser.parse_args()
    
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
    if args.max_pages:
        print(f"   Limiting to {args.max_pages} pages per API")
    if args.force_reparse:
        print(f"   🔄 Force re-parsing enabled - will update all parsed fields")
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
    
    # Check if we're only syncing specific conversations
    if args.conversations_for:
        print("=" * 60)
        print("SYNCING CONVERSATIONS FOR SPECIFIC TICKETS")
        print("=" * 60)
        print(f"   Ticket IDs: {', '.join(args.conversations_for)}")
        
        result = etl.sync_conversations_for_tickets(
            ticket_ids=args.conversations_for,
            force_reparse=args.force_reparse
        )
        
        if result['status'] == 'success':
            print(f"\n✅ Conversations synced: {result['total_synced']}")
            print(f"❌ Errors: {result['total_errors']}")
            total_results['conversations'] = {
                'synced': result['total_synced'],
                'errors': result['total_errors']
            }
        else:
            print(f"❌ Conversation sync failed: {result.get('error', 'Unknown error')}")
            total_results['conversations']['errors'] = 1
        
        # Skip other syncs
        print("\n✨ Done!")
        return
    
    # Step 1: Sync tickets (and optionally conversations)
    print("=" * 60)
    if args.tickets_only:
        print("STEP 1: SYNCING TICKETS ONLY (NO CONVERSATIONS)")
        method = etl.sync_ticket_data
    else:
        print("STEP 1: SYNCING TICKETS AND CONVERSATIONS")
        method = etl.sync_tickets
    print("=" * 60)
    
    result = method(
        since=since,
        max_pages=args.max_pages,
        force_reparse=args.force_reparse
    )
    
    if result['status'] in ['success', 'partial']:
        print(f"\n📊 Sync Results:")
        print(f"✅ Tickets synced: {result['total_synced']}")
        if 'tickets_updated' in result:
            print(f"✅ Tickets updated: {result['tickets_updated']}")
        if 'conversations_synced' in result:
            print(f"✅ Conversations synced: {result['conversations_synced']}")
        print(f"❌ Errors: {result['total_errors']}")
        
        total_results['tickets'] = {
            'synced': result['total_synced'],
            'errors': result.get('total_errors', 0)
        }
        if 'conversations_synced' in result:
            total_results['conversations'] = {
                'synced': result.get('conversations_synced', 0),
                'errors': 0
            }
    else:
        print(f"❌ Ticket sync failed: {result.get('error', 'Unknown error')}")
        total_results['tickets']['errors'] = 1
    
    # Step 2: Sync satisfaction ratings
    print("\n" + "=" * 60)
    print("STEP 2: SYNCING SATISFACTION RATINGS")
    print("=" * 60)
    
    print(f"   Fetching ALL satisfaction ratings from Freshdesk")
    
    result = etl.sync_satisfaction_ratings(
        since=None,  # Always get all ratings
        max_pages=args.max_pages,
        force_reparse=args.force_reparse
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