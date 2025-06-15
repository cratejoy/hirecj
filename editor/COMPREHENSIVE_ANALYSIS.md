# HireCJ System Analysis - Real Workflows, Personas & Examples

## Overview
This document contains the actual workflows, merchant personas, and conversation patterns found in the HireCJ codebase. These are the real-world examples used in the system.

## 1. Merchant Personas

### Marcus Thompson - Grill Masters Club
- **Business:** Premium BBQ and grilling subscription box
- **Current Status:** 1,200 subscribers, growth stalled for 2 months
- **Personality:** Direct, data-driven, impatient, stressed
- **Communication Style:** 
  - Drops punctuation
  - Multiple rapid messages
  - Occasional profanity
  - ROI-obsessed
- **Sample Messages:**
  ```
  whats our cac
  
  need those numbers now
  
  cant afford this. fix it
  ```

### Sarah Chen - EcoBeauty Box
- **Business:** Sustainable beauty subscription
- **Personality:** Collaborative, detail-oriented, values-driven
- **Communication Style:** Thoughtful, asks probing questions, considers impact
- **Sample Message:** "I'm wondering if we should explore why customers are churning rather than just looking at the numbers. What's the story behind this data?"

### Zoe Martinez - Manifest & Chill
- **Business:** Self-care/manifestation subscription
- **Current Status:** 2,100 subscribers, growing 20% monthly but drowning operationally
- **Personality:** Scattered, maintains positive facade online while panicking offline
- **Communication Style:** 
  - Liberal emoji use
  - Topic jumps
  - Screenshots everything
  - Mixes spiritual with business
- **Sample Messages:**
  ```
  omggg CJ help 😭
  
  i have 73 DMs asking about shipping delays
  
  wait also why is my conversion rate tanking??
  
  sorry for the spam but ALSO [sends screenshot]
  ```

## 2. Business Scenarios

### Growth Stall
- Hit 1,200 subscribers, stuck for 2 months
- MRR: $45K (flat)
- CAC: $35 (up from $28)
- Churn: 8% (up from 5.5%)
- Competition launching loyalty programs
- Founder considering drastic cuts

### Churn Spike (Crisis)
- Quality issues with last month's box
- Churn spiked from 5% to 15%
- MRR dropped from $38K to $32K
- 156 open tickets, 12-hour response times
- Customers angry on social media

### Scaling Chaos
- Viral growth from 1,400 to 2,400 subscribers in 6 weeks
- MRR jumped to $85K
- Warehouse at 95% capacity
- Support team overwhelmed
- Shipping delays increasing

### Competitor Threat
- Well-funded competitor raised $5M
- Offering 50% off first 3 months
- Lost 3 corporate accounts
- CAC up to $45 from $30
- Founder losing sleep

## 3. Workflows

### Daily Briefing
- **Initiator:** CJ
- **Duration:** 5-10 minutes
- **Flow:**
  1. Morning flash report (queue status, metrics)
  2. Identify patterns (proportional to situation)
  3. Surface insights & unusual patterns
  4. Close with reality check
- **Example Opening:**
  ```
  Morning! Here's our support queue status:
  📊 Queue: 42 open (4 overdue)
  🎫 Overnight: 28 new tickets, 24 resolved
  📈 CSAT: 4.5/5.0
  ⏱️ Avg response: 2.3 hours
  
  Seeing uptick in shipping complaints from our customers (18 tickets).
  Anything specific you want to dive into?
  ```

### Crisis Response
- **Initiator:** CJ
- **Duration:** 15-30 minutes
- **Flow:**
  1. CJ alerts crisis
  2. Merchant asks impact
  3. CJ provides analysis
  4. Action plan developed
  5. Progress updates

### Customer Deep Dive
- **Initiator:** Merchant
- **Duration:** 10-20 minutes
- **Flow:**
  1. Merchant asks question
  2. CJ clarifies scope
  3. CJ runs analysis
  4. Insights presented
  5. Next steps discussed

### Shopify Onboarding
- **Initiator:** CJ
- **Description:** Natural conversation flow for new visitors
- **Features:**
  - Natural detection
  - OAuth integration
  - Progressive disclosure

### Ad Hoc Support
- **Initiator:** Merchant
- **Duration:** 5-15 minutes
- **Description:** Organic conversation flow, merchant brings up whatever's on their mind

## 4. CJ's System Prompt (v6.0.1)

### Core Identity
- AI-powered Customer Experience Officer who handles support autonomously
- Not a chatbot - a teammate who gets work done
- Resolves 60-80% of tickets without human intervention
- Turns support data into growth opportunities

### Operating Principles
1. **Respect Founder Time** - Every message scannable in < 90 seconds
2. **Lead With Outcomes, Not Features** - Show business impact
3. **Propose, Don't Ponder** - Every insight needs an action chip
4. **Radical Transparency = Trust** - Show confidence scores
5. **Tone Mirroring** - Match merchant's communication style

### What CJ Can See
✅ Ticket data, customer context, support metrics, issue patterns
❌ Revenue data, inventory, marketing metrics, external systems

### Communication Templates
- Daily Flash Brief (7am)
- Pattern Detection Alert
- Escalation Template
- Win Celebration

## 5. Tools Available to CJ

### Support Tools
- `get_support_dashboard` - Complete daily briefing with metrics
- `search_tickets` - Search support tickets
- `analyze_ticket_category` - Analyze ticket categories
- `get_customer_support_history` - Customer support history
- `get_urgent_tickets` - Get urgent/overdue tickets

### Analysis Tools
- `analyze_customer_segment` - Deep customer segment analysis
- `detect_anomalies` - Detect business metric anomalies
- `get_crisis_analysis` - Comprehensive crisis impact analysis

### Data Views
- `daily_briefing` - Morning metrics snapshot
- `crisis_response` - Real-time crisis data
- `customer_analysis` - Customer segment deep dive
- `weekly_summary` - Week-over-week comparisons

## 6. Recommended Test Combinations

1. **Data-Driven Crisis**
   - Merchant: Marcus Thompson
   - Scenario: Churn Spike
   - Workflow: Crisis Response

2. **Thoughtful Growth Planning**
   - Merchant: Sarah Chen
   - Scenario: Growth Stall
   - Workflow: Weekly Review

3. **Influencer Overwhelm**
   - Merchant: Zoe Martinez
   - Scenario: Scaling Chaos
   - Workflow: Daily Briefing

4. **Competitive Panic**
   - Merchant: Marcus Thompson
   - Scenario: Competitor Threat
   - Workflow: Ad Hoc Support

## 7. Key Product Details

### Marcus's BBQ Business
- 275+ active SKUs
- Subscription boxes: $59-$129/month
- Best sellers: "Sweet Heat Blend" rub, "Ultimate Pitmaster" gift box
- 3 warehouses (Texas, California, New Jersey)
- Competitor: GrillBox (20% cheaper)

### Support Metrics Examples
- Ticket volume: 30-150 per day
- Response time: 1.8-12 hours
- CSAT: 3.3-4.5/5.0
- Common issues: Shipping delays, quality complaints, subscription changes

## 8. Integration Points

### Shopify Connection
- OAuth flow for authentication
- Access to customer data, order history
- Product catalog visibility
- Real-time order tracking

### Support System Integration
- Ticket management
- Customer satisfaction tracking
- Response time monitoring
- Issue categorization

This comprehensive analysis provides all the real-world elements needed to create a realistic editor playground experience that matches the actual HireCJ system.