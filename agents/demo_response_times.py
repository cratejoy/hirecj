#!/usr/bin/env python3
"""Demo of the response time metrics tool"""

import sys
import os
from datetime import date, timedelta

# Add the agents directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app.lib.freshdesk_analytics_lib import FreshdeskAnalytics
    
    print("⏱️ Response Time Metrics Demo")
    print("=" * 60)
    
    # Define date range (last 7 days)
    end_date = date.today()
    start_date = end_date - timedelta(days=7)
    date_range = {
        'start_date': start_date,
        'end_date': end_date
    }
    
    print(f"\nAnalyzing tickets from {start_date} to {end_date}")
    print("-" * 60)
    
    # Get the metrics
    result = FreshdeskAnalytics.get_response_time_metrics(merchant_id=1, date_range=date_range)
    
    # Display first response statistics
    print("\n📊 First Response Time Statistics:")
    if result['first_response']:
        fr = result['first_response']
        print(f"  Median: {fr['median_min']:.1f} minutes")
        print(f"  Average: {fr['mean_min']:.1f} minutes")
        print(f"  25th percentile: {fr['p25_min']:.1f} min (75% respond slower)")
        print(f"  75th percentile: {fr['p75_min']:.1f} min (25% respond slower)")
        print(f"  95th percentile: {fr['p95_min']:.1f} min (5% respond slower)")
        
        if fr['outliers']:
            print(f"\n  ⚠️ Found {len(fr['outliers'])} outliers (>2σ from mean):")
            for outlier in fr['outliers'][:3]:
                print(f"    - Ticket #{outlier['ticket_id']}: {outlier['response_min']:.1f} minutes")
    else:
        print("  No response time data available")
    
    # Display resolution statistics
    print("\n⏰ Resolution Time Statistics:")
    if result['resolution']:
        res = result['resolution']
        print(f"  Median: {res['median_min']:.1f} minutes")
        print(f"  Average: {res['mean_min']:.1f} minutes")
        print(f"  25th percentile: {res['p25_min']:.1f} min")
        print(f"  75th percentile: {res['p75_min']:.1f} min")
        print(f"  95th percentile: {res['p95_min']:.1f} min")
        
        if res['outliers']:
            print(f"\n  ⚠️ Found {len(res['outliers'])} outliers:")
            for outlier in res['outliers'][:3]:
                print(f"    - Ticket #{outlier['ticket_id']}: {outlier['resolution_min']:.1f} minutes")
    else:
        print("  No resolution time data available")
    
    # Display quick resolution breakdown
    print(f"\n🚀 Quick Resolution Performance (Total: {result['total_resolved']} tickets):")
    for bucket, data in result['quick_resolutions'].items():
        bar_length = int(data['percentage'] / 5) if data['percentage'] > 0 else 0
        bar = "█" * bar_length if bar_length > 0 else ""
        csat_str = f" (CSAT: {data['avg_csat']}/5)" if data['avg_csat'] > 0 else ""
        print(f"  {bucket:>6}: {data['count']:3d} tickets ({data['percentage']:5.1f}%) {bar}{csat_str}")
    
    # Display CSAT correlation
    print("\n😊 CSAT vs Response Speed:")
    for category, data in result['csat_by_speed'].items():
        if data['count'] > 0:
            # Convert rating to emoji
            if data['avg_rating'] >= 102:
                emoji = "😊"
            elif data['avg_rating'] >= 100:
                emoji = "😐"
            else:
                emoji = "😞"
            
            # Format category name
            category_display = category.replace('_', ' ').title()
            print(f"  {category_display}: {data['count']} tickets, avg rating: {emoji} {data['avg_rating']}")
    
    # Analysis insights
    print("\n💡 Key Insights:")
    
    # Response time insights
    if result['first_response']:
        median_response = result['first_response']['median_min']
        if median_response < 60:
            print(f"  ✅ Excellent median first response time: {median_response:.1f} minutes")
        elif median_response > 240:
            print(f"  ⚠️ Slow median first response time: {median_response:.1f} minutes")
        else:
            print(f"  ⏱️ Moderate median first response time: {median_response:.1f} minutes")
    
    # Quick resolution insights
    if result['quick_resolutions'] and result['quick_resolutions']['<30min']['percentage'] > 50:
        print(f"  ✅ {result['quick_resolutions']['<30min']['percentage']:.1f}% of tickets resolved within 30 minutes")
    
    # CSAT correlation insights
    if result['csat_by_speed']:
        ultra_fast = result['csat_by_speed'].get('ultra_fast_<5min', {})
        slow = result['csat_by_speed'].get('slow_>180min', {})
        if ultra_fast.get('avg_rating', 0) > slow.get('avg_rating', 0):
            print("  ✅ Faster resolutions correlate with higher satisfaction")
        elif slow.get('avg_rating', 0) > ultra_fast.get('avg_rating', 0):
            print("  ⚠️ Slower resolutions have higher satisfaction (quality over speed?)")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    print("\nNote: Make sure your database is configured and contains data.")