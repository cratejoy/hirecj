#!/usr/bin/env python3
"""Freshdesk sync script with smart defaults for handling large datasets efficiently."""

import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from app.utils.supabase_util import get_db_session
from app.models.base import Merchant
from app.lib.freshdesk_lib import FreshdeskETL


def main():
    """Main sync function with smart defaults."""
    parser = argparse.ArgumentParser(
        description="Freshdesk sync with optimized handling for large datasets"
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
    parser.add_argument(
        "--ratings",
        action="store_true",
        help="Also sync ALL satisfaction ratings and attach to tickets"
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
    print(f"   Syncing tickets from last {args.days} days")
    print(f"   Fetching complete conversation history for every ticket")
    if args.max_pages:
        print(f"   Limiting to {args.max_pages} pages")
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
    
    # Sync tickets
    print("=" * 60)
    print("SYNCING TICKETS")
    print("=" * 60)
    
    result = etl.sync_tickets(
        since=since,
        max_pages=args.max_pages,
        conversation_days_limit=None  # ALWAYS fetch all conversations
    )
    
    # Summary
    print("\n" + "=" * 60)
    print("SYNC SUMMARY")
    print("=" * 60)
    
    if result['status'] == 'success':
        print(f"✅ Tickets synced: {result['total_synced']}")
        print(f"❌ Errors: {result['total_errors']}")
    else:
        print(f"❌ Sync failed: {result.get('error', 'Unknown error')}")
    
    # Sync satisfaction ratings if requested
    if args.ratings and result['status'] == 'success':
        print("\n" + "=" * 60)
        print("SYNCING SATISFACTION RATINGS")
        print("=" * 60)
        
        print(f"   Syncing ALL satisfaction ratings from Freshdesk")
        
        ratings_result = etl.sync_satisfaction_ratings(
            since=None,  # ALWAYS get all ratings
            max_pages=args.max_pages
        )
        
        if ratings_result['status'] == 'success':
            print(f"\n✅ Ratings synced: {ratings_result['total_synced']}")
            print(f"   Tickets updated: {ratings_result['tickets_updated']}")
            print(f"❌ Errors: {ratings_result['total_errors']}")
        else:
            print(f"\n❌ Ratings sync failed: {ratings_result.get('error', 'Unknown error')}")
    
    # Show final sync status
    print("\n📊 Final sync status:")
    status = etl.get_sync_status()
    for resource, info in status.items():
        if info:
            print(f"   {resource}: {info['status']} (last: {info['last_sync']})")
    
    print("\n✨ Done!")


if __name__ == "__main__":
    main()