#!/usr/bin/env python3
"""Sync Shopify data to database."""

import sys
import argparse
from datetime import datetime
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from app.utils.supabase_util import get_db_session
from app.models.base import Merchant
from app.lib.shopify_lib import ShopifyETL


def main():
    """Main sync function."""
    parser = argparse.ArgumentParser(description="Sync Shopify data to database")
    parser.add_argument(
        "--merchant",
        default="amir_elaguizy",
        help="Merchant name to sync (default: amir_elaguizy)"
    )
    parser.add_argument(
        "--since",
        type=str,
        help="Sync data updated since this date (ISO format: 2024-01-01T00:00:00Z)"
    )
    parser.add_argument(
        "--customers",
        action="store_true",
        help="Sync customers"
    )
    parser.add_argument(
        "--orders",
        action="store_true", 
        help="Sync orders"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Sync all resources (customers and orders)"
    )
    
    args = parser.parse_args()
    
    # Default to syncing all if no specific resources selected
    if not args.customers and not args.orders and not args.all:
        args.all = True
    
    if args.all:
        args.customers = True
        args.orders = True
    
    # Parse since date if provided
    since = None
    if args.since:
        try:
            since = datetime.fromisoformat(args.since.replace('Z', '+00:00'))
        except ValueError:
            print(f"❌ Invalid date format: {args.since}")
            print("   Use ISO format: 2024-01-01T00:00:00Z")
            sys.exit(1)
    
    # Get merchant
    with get_db_session() as session:
        merchant = session.query(Merchant).filter_by(name=args.merchant).first()
        if not merchant:
            print(f"❌ Merchant '{args.merchant}' not found")
            sys.exit(1)
        
        merchant_id = merchant.id
        merchant_name = merchant.name
    
    print(f"🚀 Starting Shopify sync for merchant: {merchant_name}")
    if since:
        print(f"   Syncing data updated since: {since}")
    else:
        print(f"   Syncing all data (or since last sync)")
    print()
    
    # Initialize ETL
    etl = ShopifyETL(merchant_id)
    
    # Show current sync status
    print("📊 Current sync status:")
    status = etl.get_sync_status()
    for resource, info in status.items():
        print(f"   {resource}: {info['status']} (last: {info['last_sync']})")
    print()
    
    results = {}
    
    # Sync customers
    if args.customers:
        print("=" * 60)
        print("SYNCING CUSTOMERS")
        print("=" * 60)
        results['customers'] = etl.sync_customers(since=since)
        print()
    
    # Sync orders
    if args.orders:
        print("=" * 60)
        print("SYNCING ORDERS")
        print("=" * 60)
        results['orders'] = etl.sync_orders(since=since)
        print()
    
    # Summary
    print("=" * 60)
    print("SYNC SUMMARY")
    print("=" * 60)
    
    total_synced = 0
    total_errors = 0
    
    for resource, result in results.items():
        if result['status'] == 'success':
            print(f"✅ {resource}: {result['total_synced']} synced, {result['total_errors']} errors")
            total_synced += result['total_synced']
            total_errors += result['total_errors']
        else:
            print(f"❌ {resource}: FAILED - {result.get('error', 'Unknown error')}")
    
    print(f"\nTotal records synced: {total_synced}")
    print(f"Total errors: {total_errors}")
    
    # Show final sync status
    print("\n📊 Final sync status:")
    status = etl.get_sync_status()
    for resource, info in status.items():
        print(f"   {resource}: {info['status']} (last: {info['last_sync']})")
    
    print("\n✨ Shopify sync completed!")


if __name__ == "__main__":
    main()