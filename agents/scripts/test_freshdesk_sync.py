#!/usr/bin/env python3
"""Test script for the refactored Freshdesk sync functionality."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from app.utils.supabase_util import get_db_session
from app.dbmodels.base import Merchant
from app.dbmodels.etl_tables import FreshdeskTicket, FreshdeskConversation, FreshdeskRating
import subprocess


def run_sync_test(args):
    """Run sync command and capture output."""
    cmd = [sys.executable, "scripts/sync_freshdesk_refactored.py"] + args
    print(f"\n🚀 Running: {' '.join(cmd)}")
    print("-" * 60)
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    return result.returncode == 0


def check_data_counts():
    """Check record counts in all tables."""
    with get_db_session() as session:
        tickets = session.query(FreshdeskTicket).count()
        conversations = session.query(FreshdeskConversation).count()
        ratings = session.query(FreshdeskRating).count()
        
        print(f"\n📊 Current data counts:")
        print(f"   Tickets: {tickets}")
        print(f"   Conversations: {conversations}")
        print(f"   Ratings: {ratings}")


def main():
    """Run comprehensive tests of the sync functionality."""
    print("🧪 Testing Freshdesk Sync Refactored Implementation")
    print("=" * 60)
    
    # Check initial state
    print("\n1️⃣ Initial state:")
    check_data_counts()
    
    # Test 1: Sync tickets only
    print("\n2️⃣ Test: Sync tickets only (last 7 days, max 2 pages)")
    success = run_sync_test([
        "--tickets-only",
        "--days", "7",
        "--max-pages", "2"
    ])
    if success:
        check_data_counts()
    else:
        print("❌ Tickets sync failed!")
        return
    
    # Test 2: Sync conversations only
    print("\n3️⃣ Test: Sync conversations only")
    success = run_sync_test([
        "--conversations-only",
        "--max-pages", "1"  # Limit for testing
    ])
    if success:
        check_data_counts()
    else:
        print("❌ Conversations sync failed!")
    
    # Test 3: Sync ratings only
    print("\n4️⃣ Test: Sync ratings only")
    success = run_sync_test([
        "--ratings-only",
        "--max-pages", "2"
    ])
    if success:
        check_data_counts()
    else:
        print("❌ Ratings sync failed!")
    
    # Test 4: Full sync with skip options
    print("\n5️⃣ Test: Full sync but skip conversations")
    success = run_sync_test([
        "--skip-conversations",
        "--days", "3",
        "--max-pages", "1"
    ])
    if success:
        check_data_counts()
    
    # Final summary
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    check_data_counts()
    
    # Show sample data
    with get_db_session() as session:
        sample_ticket = session.query(FreshdeskTicket).first()
        if sample_ticket:
            print(f"\n📋 Sample ticket data:")
            print(f"   ID: {sample_ticket.freshdesk_ticket_id}")
            print(f"   Subject: {sample_ticket.data.get('subject', 'N/A')}")
            
            # Check if it has conversations
            if sample_ticket.conversations:
                conv_count = len(sample_ticket.conversations.data.get('conversations', []))
                print(f"   Conversations: {conv_count}")
            
            # Check if it has rating
            if sample_ticket.rating:
                rating = sample_ticket.rating.data.get('rating', 'N/A')
                print(f"   Rating: {rating}")


if __name__ == "__main__":
    main()