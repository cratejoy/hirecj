#!/usr/bin/env python3
"""Demo of the open ticket distribution tool"""

import sys
import os
from datetime import datetime

# Add the agents directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app.lib.freshdesk_analytics_lib import FreshdeskAnalytics
    
    print("🎫 Open Ticket Distribution Demo")
    print("=" * 60)
    
    # Get the distribution
    result = FreshdeskAnalytics.get_open_ticket_distribution(merchant_id=1)
    
    # Display raw data
    print("\n📊 Raw Data Structure:")
    print(f"Total open tickets: {result['total_open']}")
    print("\nAge buckets:")
    for bucket, data in result['age_buckets'].items():
        print(f"  {bucket}: {data['count']} tickets ({data['percentage']}%)")
    
    print(f"\nOldest {len(result['oldest_tickets'])} tickets:")
    for i, ticket in enumerate(result['oldest_tickets'][:5], 1):
        print(f"\n  {i}. Ticket #{ticket['ticket_id']} - {ticket['age_display']} old")
        print(f"     Subject: {ticket['subject']}")
        print(f"     Status: {ticket['status']}")
        print(f"     Priority: {ticket['priority']} {'🔴' if ticket['priority'] == 4 else '🟡' if ticket['priority'] == 3 else '🟢'}")
        print(f"     Customer: {ticket['customer_email']}")
        print(f"     Tags: {', '.join(ticket['tags']) if ticket['tags'] else 'None'}")
    
    # Analysis
    print("\n" + "=" * 60)
    print("📈 Analysis:")
    
    if result['total_open'] == 0:
        print("✅ No open tickets - backlog is clear!")
    else:
        # Age distribution insights
        fresh = result['age_buckets']['0-4h']['percentage']
        old = result['age_buckets']['>7d']['percentage']
        
        print(f"• {fresh:.1f}% of tickets are fresh (<4 hours old)")
        print(f"• {old:.1f}% of tickets are over 7 days old")
        
        # Status breakdown
        waiting_tickets = [t for t in result['oldest_tickets'] if 'Waiting' in t['status']]
        if waiting_tickets:
            print(f"• {len(waiting_tickets)} tickets are waiting on customer/third party")
        
        # Priority concerns
        urgent_tickets = [t for t in result['oldest_tickets'] if t['priority'] >= 3]
        if urgent_tickets:
            print(f"• ⚠️ {len(urgent_tickets)} high/urgent priority tickets in oldest 10")
        
        # Oldest ticket warning
        if result['oldest_tickets']:
            oldest = result['oldest_tickets'][0]
            if oldest['age_hours'] > 168:  # Over a week
                print(f"\n🚨 ALERT: Oldest ticket is {oldest['age_display']} old!")
                print(f"   Subject: {oldest['subject']}")
                print(f"   Customer: {oldest['customer_email']}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    print("\nNote: Make sure your database is configured and contains data.")