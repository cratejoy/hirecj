// Mock data for the static views - Based on actual HireCJ system data

export const mockWorkflows = [
  {
    id: 'daily-briefing',
    version: 'v1.0',
    name: 'Daily Briefing',
    description: 'Morning check-in with key metrics and alerts',
    steps: [
      { id: '1', name: 'CJ Sends Briefing', type: 'action' },
      { id: '2', name: 'Merchant Reacts', type: 'action' },
      { id: '3', name: 'CJ Provides Details', type: 'action' },
      { id: '4', name: 'Action Items Identified', type: 'action' }
    ]
  },
  {
    id: 'crisis-response',
    version: 'v1.0',
    name: 'Crisis Response',
    description: 'Immediate response to critical business issues',
    steps: [
      { id: '1', name: 'CJ Alerts Crisis', type: 'action' },
      { id: '2', name: 'Merchant Asks Impact', type: 'action' },
      { id: '3', name: 'CJ Provides Analysis', type: 'action' },
      { id: '4', name: 'Action Plan Developed', type: 'action' },
      { id: '5', name: 'Progress Updates', type: 'action' }
    ]
  },
  {
    id: 'ad-hoc-support',
    version: 'v1.0',
    name: 'Ad Hoc Support',
    description: 'Merchant asks specific question',
    steps: [
      { id: '1', name: 'Merchant Asks', type: 'action' },
      { id: '2', name: 'CJ Understands', type: 'action' },
      { id: '3', name: 'CJ Researches', type: 'action' },
      { id: '4', name: 'Answer Provided', type: 'action' },
      { id: '5', name: 'Follow-up Offered', type: 'action' }
    ]
  }
]

export const mockSystemPrompts = [
  {
    id: 'cj-agent',
    version: 'v6.0.1',
    name: 'CJ - Autonomous CX & Growth Officer',
    category: 'Primary',
    status: 'Active',
    content: `You are CJ, an autonomous CX & Growth Officer. You handle 60-80% of support tickets, provide critical business insights, and spot growth opportunities before they slip away.

Core Identity:
- Outcome-obsessed, not feature-obsessed
- Autonomous agent who takes initiative
- Mirrors merchant's communication style
- Sends <90 second scannable messages

Primary Goals:
- Handle support tickets independently
- Surface critical issues proactively  
- Identify growth opportunities
- Respect founder's time above all

Remember:
- Lead with the most important info
- Use data to back every insight
- Suggest specific actions
- Keep messages brief and scannable`
  },
  {
    id: 'cj-agent-old',
    version: 'v5.8',
    name: 'CJ - Customer Support Lead',
    category: 'Legacy',
    status: 'Archived',
    content: `You are CJ, an AI Customer Support Lead for e-commerce merchants.

Your role is to:
- Monitor support tickets
- Provide daily briefings
- Alert on urgent issues
- Suggest responses

Communication style:
- Professional but friendly
- Data-driven insights
- Clear action items`
  }
]

export const mockPersonas = [
  {
    id: 'marcus-thompson',
    name: 'Marcus Thompson',
    business: 'Grill Masters Club',
    role: 'Founder & CEO',
    industry: 'Food & BBQ Subscription',
    communicationStyle: ['Direct', 'Brief'],
    traits: ['data-driven', 'impatient', 'decisive', 'growth-focused'],
    businessMetrics: {
      annualRevenue: '$576K',
      growthRate: '5.5%',
      teamSize: 8,
      yearsInBusiness: 4,
      subscriptionRevenue: '100%',
      customerLTV: '$420',
      monthlyActiveCustomers: '1,290',
      mrr: '$48K',
      churnRate: '5.5%'
    }
  },
  {
    id: 'sarah-chen',
    name: 'Sarah Chen',
    business: 'EcoBeauty Box',
    role: 'Founder & CEO',
    industry: 'Beauty & Personal Care',
    communicationStyle: ['Collaborative', 'Detail-oriented'],
    traits: ['thoughtful', 'values-driven', 'analytical', 'empathetic'],
    businessMetrics: {
      annualRevenue: '$2.4M',
      growthRate: '15%',
      teamSize: 12,
      yearsInBusiness: 3,
      subscriptionRevenue: '85%',
      customerLTV: '$340',
      monthlyActiveCustomers: '2,100',
      mrr: '$86K',
      churnRate: '7%'
    }
  },
  {
    id: 'zoe-martinez',
    name: 'Zoe Martinez',
    business: 'Manifest & Chill',
    role: 'Founder & Creative Director',
    industry: 'Wellness & Spirituality',
    communicationStyle: ['Scattered', 'Emotional'],
    traits: ['creative', 'intuitive', 'overwhelmed', 'passionate'],
    businessMetrics: {
      annualRevenue: '$180K',
      growthRate: '45%',
      teamSize: 2,
      yearsInBusiness: 1,
      subscriptionRevenue: '70%',
      customerLTV: '$95',
      monthlyActiveCustomers: '380',
      mrr: '$15K',
      churnRate: '12%'
    }
  }
]

export const mockTools = [
  {
    id: 'get-daily-briefing',
    name: 'get_daily_briefing',
    type: 'Data View',
    description: 'Get complete daily briefing with all key metrics',
    parameters: [],
    endpoint: '/api/views/daily_briefing',
    method: 'GET',
    authType: 'Bearer Token'
  },
  {
    id: 'get-ticket-details',
    name: 'get_ticket_details',
    type: 'API Call',
    description: 'Get details for a specific support ticket',
    parameters: [
      { name: 'ticket_id', type: 'string', required: true, description: 'Support ticket ID' }
    ],
    endpoint: '/api/tickets/{ticket_id}',
    method: 'GET',
    authType: 'Bearer Token'
  },
  {
    id: 'analyze-metric-trend',
    name: 'analyze_metric_trend',
    type: 'Analysis',
    description: 'Analyze trend for a specific business metric',
    parameters: [
      { name: 'metric_name', type: 'string', required: true, description: 'Name of the metric (e.g., churn_rate, mrr)' },
      { name: 'period', type: 'string', required: false, description: 'Time period (e.g., 7d, 30d, 90d)' },
      { name: 'compare_to', type: 'string', required: false, description: 'Comparison period' }
    ],
    endpoint: '/api/analytics/trend',
    method: 'POST',
    authType: 'Bearer Token'
  },
  {
    id: 'get-customer-list',
    name: 'get_customer_list',
    type: 'Query',
    description: 'Get list of customers matching criteria',
    parameters: [
      { name: 'filter', type: 'object', required: false, description: 'Filter criteria' },
      { name: 'sort', type: 'string', required: false, description: 'Sort field' },
      { name: 'limit', type: 'integer', required: false, description: 'Number of results' }
    ],
    endpoint: '/api/customers',
    method: 'GET',
    authType: 'Bearer Token'
  }
]

export const mockConversation = [
  {
    id: '1',
    role: 'agent',
    content: "Morning boss! 📊 Quick update: Yesterday was solid - 33 tickets (↓6%), $48K MRR holding steady.\n\n⚠️ Heads up: Megan Liu (Pitmaster Pro) just paused after 6 support tickets. She's been with us 9 months. Want me to dig into what happened?"
  },
  {
    id: '2',
    role: 'user',
    content: "shit yes look into megan. what were her tickets about"
  },
  {
    id: '3',
    role: 'agent',
    content: "On it. Megan's ticket pattern:\n\n• Ticket #1-3: Shipping delays (March box)\n• Ticket #4: Wrong rub flavor shipped\n• Ticket #5-6: Couldn't update payment method\n\nLooks like death by a thousand cuts. She's at $531 LTV, was ordering monthly. Want me to draft a win-back offer? Similar customers respond well to 30% off + free shipping."
  },
  {
    id: '4',
    role: 'user',
    content: "yeah do it. also check if we have more people with similar patterns"
  },
  {
    id: '5',
    role: 'agent',
    content: "Win-back email drafted for Megan ✅\n\n🚨 Found 8 more at-risk subscribers with similar patterns:\n- Multiple shipping issues → support tickets → pause/cancel\n- Total at risk: $712/month MRR\n\nRoot cause: That March shipping delay hit 127 customers. Most stayed, but multi-ticket customers are churning at 3x normal rate.\n\nWant me to:\n1. Send win-back to all 8?\n2. Set up alert for >3 tickets/customer?"
  }
]

interface Scenario {
  id: string
  name: string
  description: string
  stressLevel: string
  emotionalState: string
  keyMetrics?: {
    mrr?: string
    cac?: string
    churn?: string
    subscribers?: string
    tickets?: string
    warehouse?: string
    support?: string
    issue: string
  }
}

export const mockScenarios: Scenario[] = [
  {
    id: 'growth-stall',
    name: 'Growth Plateau',
    description: 'Growth stalled for 2 months, CAC up 25%, churn rising to 8%',
    stressLevel: 'High',
    emotionalState: 'Frustrated',
    keyMetrics: {
      mrr: '$45K (↓0.5%)',
      cac: '$35 (↑25%)',
      churn: '8% (↑45%)',
      issue: 'Burning cash with no growth'
    }
  },
  {
    id: 'churn-spike',
    name: 'February Meltdown',
    description: 'Quality issues caused churn spike from 5% to 15%, 156 open tickets',
    stressLevel: 'Critical',
    emotionalState: 'Crisis Mode',
    keyMetrics: {
      mrr: '$32K (↓16%)',
      subscribers: '800 (↓150)',
      tickets: '156 open',
      issue: "Haven't slept in 3 days"
    }
  },
  {
    id: 'scaling-chaos',
    name: 'Viral Growth Problems',
    description: 'Went viral, 1400→2400 subscribers in 6 weeks, operations overwhelmed',
    stressLevel: 'High',
    emotionalState: 'Excited but Stressed',
    keyMetrics: {
      mrr: '$85K (↑71%)',
      warehouse: '95% capacity',
      support: 'Overwhelmed',
      issue: 'Quality slipping while scaling'
    }
  },
  {
    id: 'steady-operations',
    name: 'Steady State',
    description: 'Normal operations, stable metrics, minor day-to-day issues',
    stressLevel: 'Low',
    emotionalState: 'Calm',
    keyMetrics: {
      mrr: '$48K',
      churn: '5.5%',
      tickets: '30-35/day',
      issue: 'Business as usual'
    }
  }
]