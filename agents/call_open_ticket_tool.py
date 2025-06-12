#!/usr/bin/env python3
"""Call the open ticket distribution tool directly"""

import sys
import os

# Add the agents directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # Import and create the tools
    from app.agents.database_tools import create_database_tools
    
    print("🔧 Calling get_open_ticket_distribution tool...")
    print("=" * 80)
    
    # Create all tools
    tools = create_database_tools()
    
    # Find the open ticket distribution tool
    open_ticket_tool = None
    for tool in tools:
        if tool.name == "get_open_ticket_distribution":
            open_ticket_tool = tool
            break
    
    if open_ticket_tool:
        # Call the tool and print the exact output
        result = open_ticket_tool.func()
        print(result)
    else:
        print("❌ Tool not found!")

except ImportError as e:
    # If CrewAI import fails, call the function directly
    print("CrewAI import failed, calling analytics function directly...")
    print("=" * 80)
    
    from app.lib.freshdesk_analytics_lib import FreshdeskAnalytics
    
    # Call the raw function
    raw_result = FreshdeskAnalytics.get_open_ticket_distribution(merchant_id=1)
    
    # Format it manually to show what the tool would output
    output = f"""📊 Open Ticket Distribution Analysis:

**Backlog Overview:**
• Total Open Tickets: {raw_result['total_open']}

**Age Distribution:**
"""
    
    bucket_order = ["0-4h", "4-24h", "1-2d", "3-7d", ">7d"]
    for bucket in bucket_order:
        data = raw_result['age_buckets'][bucket]
        bar_length = int(data['percentage'] / 5) if data['percentage'] > 0 else 0
        bar = "█" * bar_length if bar_length > 0 else ""
        output += f"• {bucket:>6}: {data['count']:3d} tickets ({data['percentage']:5.1f}%) {bar}\n"
    
    old_tickets = raw_result['age_buckets']['>7d']['count']
    if old_tickets > 0:
        output += f"\n⚠️ **Alert**: {old_tickets} ticket(s) older than 7 days!\n"
    
    if raw_result['oldest_tickets']:
        output += "\n**10 Oldest Open Tickets:**\n"
        for i, ticket in enumerate(raw_result['oldest_tickets'], 1):
            priority_emoji = {1: "🟢", 2: "🟡", 3: "🟠", 4: "🔴"}.get(ticket['priority'], "⚪")
            
            output += f"""
{i}. {priority_emoji} Ticket #{ticket['ticket_id']} - {ticket['age_display']} old
   Subject: {ticket['subject']}
   Status: {ticket['status']}
   Customer: {ticket['customer_email']}
   Tags: {', '.join(ticket['tags']) if ticket['tags'] else 'None'}
   Last Updated: {ticket['last_updated']}
"""
    
    if raw_result['total_open'] > 0:
        fresh_pct = raw_result['age_buckets']['0-4h']['percentage']
        aging_pct = raw_result['age_buckets']['3-7d']['percentage'] + raw_result['age_buckets']['>7d']['percentage']
        
        output += "\n**Insights:**\n"
        if fresh_pct > 50:
            output += f"• {fresh_pct:.1f}% of tickets are fresh (<4h) - good responsiveness\n"
        if aging_pct > 20:
            output += f"• {aging_pct:.1f}% of tickets are aging (>3d) - consider prioritizing these\n"
        
        waiting_count = sum(1 for t in raw_result['oldest_tickets'] 
                          if 'Waiting' in t['status'])
        if waiting_count > 0:
            output += f"• {waiting_count} oldest tickets are waiting on customer/third party\n"
    
    output += "\nData Source: Live database analytics"
    
    print(output)

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()