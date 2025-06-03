import React, { useState } from 'react';

interface QuickReplyChip {
  id: string;
  text: string;
}

interface ScriptStep {
  id: string;
  message: string;
  isHtml?: boolean;
  chips: QuickReplyChip[];
}

// Script flow data for the entire conversation
const scriptData: Record<string, ScriptStep> = {
  'welcome': {
    id: 'welcome',
    message: `Morning, boss! 👋 Hope you had a good night. Would you like to see your daily flash brief?`,
    chips: [
      { id: 'show_brief', text: 'Yes, show me the brief' },
      { id: 'skip_brief', text: 'Not now, thanks' }
    ]
  },
  'show_brief': {
    id: 'show_brief',
    message: `📊 **Daily Flash Report: May 21, 2025**

**Ticket Stats (Last 24h)**
• 220 tickets received → Auto-resolved 160 (73%)
• Founder hours saved: 8h 6m ≈ $203 labor
• Carts recovered in DM: 17 → $812 GMV
• Avg CSAT: 4.79★ (bot) vs 4.63★ (human)

**Alert Signals**
🔥 SKU-218 "glass jar" breakages +37% WoW
💎 VIP customer (LTV $842) delayed 5 days; suggest $20 credit

What would you like to focus on first?`,
    chips: [
      { id: 'jar_breakage', text: '① Fix Jar Breakage' },
      { id: 'save_vip', text: '② Save the VIP' },
      { id: 'roi_math', text: '③ Show Me the ROI Math' },
      { id: 'main_menu', text: '④ Main Menu' },
      { id: 'waitlist', text: '→ Join Waitlist' }
    ]
  },
  'skip_brief': {
    id: 'skip_brief',
    message: `No problem! I'm here whenever you need me. What can I help you with today?`,
    chips: [
      { id: 'jar_breakage', text: 'Product Issue (Jar Breakage)' },
      { id: 'save_vip', text: 'Customer Service' },
      { id: 'roi_math', text: 'ROI & Performance' },
      { id: 'main_menu', text: 'Main Menu' },
      { id: 'show_brief', text: 'Actually, show me the brief' }
    ]
  },
  'jar_breakage': {
    id: 'jar_breakage',
    message: `Diagnostics done: 12 tickets + 3 reviews flag lot B0425 from Supplier #2, FedEx Zone 5 heavy.

Proposed Moves
• Slack #ops with photo collage + QC request
• Auto-tag new B0425 claims for tracking
• Temporarily switch West-coast orders to UPS

Shall I fire those off?`,
    chips: [
      { id: 'approve_notify', text: 'Approve & Notify Ops' },
      { id: 'skip_now', text: 'Skip for Now' },
      { id: 'main_menu', text: 'Main Menu' },
      { id: 'waitlist', text: '→ Join Waitlist' }
    ]
  },
  'approve_notify': {
    id: 'approve_notify',
    message: "📣 Done. I'll surface QC findings in tomorrow's brief.",
    chips: [
      { id: 'main_menu', text: 'Main Menu' },
      { id: 'waitlist', text: '→ Join Waitlist' }
    ]
  },
  'save_vip': {
    id: 'save_vip',
    message: `Delay 5 days via Memphis hub. Sent apology already; sentiment neutral. Data: $20 credit flips 84% of VIPs and pays back in 1.3 orders.

Queued actions:
✓ Issue $20 gift card (<$25 guard-rail)
✓ Upgrade next box to priority ship
✓ Invite honest review post-delivery

Green-light?`,
    chips: [
      { id: 'send_credit', text: 'Send $20 Credit' },
      { id: 'offer_something', text: 'Offer Something Else' },
      { id: 'skip', text: 'Skip' },
      { id: 'main_menu', text: 'Main Menu' },
      { id: 'waitlist', text: '→ Join Waitlist' }
    ]
  },
  'send_credit': {
    id: 'send_credit',
    message: "Credit sent and customer notified. I'll track their next purchase for ROI calculation.",
    chips: [
      { id: 'main_menu', text: 'Main Menu' },
      { id: 'waitlist', text: '→ Join Waitlist' }
    ]
  },
  'offer_something': {
    id: 'offer_something',
    message: "What would you like to offer instead? (For demo purposes, let's stick with simple options)",
    chips: [
      { id: 'offer_25', text: '$25 Credit' },
      { id: 'offer_free', text: 'Free Next Box' },
      { id: 'main_menu', text: 'Main Menu' },
      { id: 'waitlist', text: '→ Join Waitlist' }
    ]
  },
  'offer_25': {
    id: 'offer_25',
    message: "$25 credit applied. This exceeds your typical threshold but has been processed for your VIP customer.",
    chips: [
      { id: 'main_menu', text: 'Main Menu' },
      { id: 'waitlist', text: '→ Join Waitlist' }
    ]
  },
  'offer_free': {
    id: 'offer_free',
    message: "Free next box has been set up. Value: $45. Note: This exceeds your typical compensation guidelines but has been processed.",
    chips: [
      { id: 'main_menu', text: 'Main Menu' },
      { id: 'waitlist', text: '→ Join Waitlist' }
    ]
  },
  'roi_math': {
    id: 'roi_math',
    message: `Yesterday's hard dollars:

• Old agent cost/ticket (Gorgias data) … $1.68
• Tickets I closed … 160 ⟹ $268 labor avoided
• My usage fee … $56
Net daily savings … $212

Year-to-date: $14,480 net + $42,310 recovered carts.

What else should I crunch?`,
    chips: [
      { id: 'cost_trend', text: 'Cost-per-Ticket Trend' },
      { id: 'labor_saved', text: 'Labor Hours Saved YTD' },
      { id: 'main_menu', text: 'Main Menu' },
      { id: 'waitlist', text: '→ Join Waitlist' }
    ]
  },
  'cost_trend': {
    id: 'cost_trend',
    message: `Cost-per-Ticket Trend (Last 6 months):

Jan: $2.17
Feb: $1.93
Mar: $1.84
Apr: $1.75
May: $1.68
Jun (MTD): $1.52

43% savings trend at current pace, now delivering substantial reduction versus industry benchmarks.`,
    chips: [
      { id: 'labor_saved', text: 'Labor Hours Saved YTD' },
      { id: 'main_menu', text: 'Main Menu' },
      { id: 'waitlist', text: '→ Join Waitlist' }
    ]
  },
  'labor_saved': {
    id: 'labor_saved',
    message: `Labor Hours Saved YTD:

Total tickets auto-resolved: 18,340
Avg handling time (human): 8.2 min
Total hours avoided: 2,504 hours
Equivalent FTE savings: 1.2 full-time agents

Would you like to see the breakdown by department?`,
    chips: [
      { id: 'main_menu', text: 'Main Menu' },
      { id: 'waitlist', text: '→ Join Waitlist' }
    ]
  },
  'main_menu': {
    id: 'main_menu',
    message: "What can I show next?",
    chips: [
      { id: 'cx_report', text: 'A Weekly CX Report Preview' },
      { id: 'product_insights', text: 'B Hidden Product Insights' },
      { id: 'brand_voice', text: 'C Brand-Voice Test' },
      { id: 'integration', text: 'D Integration Checklist' },
      { id: 'pricing', text: 'E Pricing Snapshot' },
      { id: 'waitlist', text: "F I'm Done — Join Waitlist" }
    ]
  },
  'cx_report': {
    id: 'cx_report',
    message: `Sneak peek (full deck hits your inbox Monday):

• Auto-resolve rate trend … 73% → 78%
• Hours saved this week … 46.9
• Labor $ replaced … $1,177
• Net incremental GMV … $4,917
• Emerging theme … "Sizing runs small" tickets +18% → PDP update flagged.

Next?`,
    chips: [
      { id: 'upsell_wins', text: 'Show Upsell Wins' },
      { id: 'main_menu', text: 'Main Menu' },
      { id: 'waitlist', text: '→ Join Waitlist' }
    ]
  },
  'upsell_wins': {
    id: 'upsell_wins',
    message: `Top 3 Upsell Wins This Week:

1. Order #8294 - Added premium subscription +$145 LTV
2. Order #8317 - Added 2 complementary products +$37
3. Order #8429 - Upgraded to annual plan +$249

Total AOV lift from upsells: +$18.72 average per engaged cart
Conversion on upsell suggestions: 22%`,
    chips: [
      { id: 'main_menu', text: 'Main Menu' },
      { id: 'waitlist', text: '→ Join Waitlist' }
    ]
  },
  'product_insights': {
    id: 'product_insights',
    message: `Top insights I surfaced from last 7 days of conversations:

17% of cancel requests cite "too many repeats" → rotate 3 SKUs next month.
42 customers asked "vegan option?"—no SKU yet.
FedEx Memphis hub delays triggered 4× CSAT drops—pre-emptive emails suggested.
Want these piped into Slack automatically?`,
    chips: [
      { id: 'to_slack', text: 'Yes, Ship to Slack' },
      { id: 'maybe_later', text: 'Maybe Later' },
      { id: 'main_menu', text: 'Main Menu' },
      { id: 'waitlist', text: '→ Join Waitlist' }
    ]
  },
  'to_slack': {
    id: 'to_slack',
    message: "Great! I've set up a weekly insights digest to post to your #product-feedback channel every Friday at 9am.",
    chips: [
      { id: 'main_menu', text: 'Main Menu' },
      { id: 'waitlist', text: '→ Join Waitlist' }
    ]
  },
  'brand_voice': {
    id: 'brand_voice',
    message: `Type a quick reply you'd send to a frustrated customer. I'll mirror the tone back.

(For demo purposes, let's assume you typed a friendly, understanding response)`,
    chips: [
      { id: 'voice_result', text: 'See Results' },
      { id: 'main_menu', text: 'Main Menu' },
      { id: 'waitlist', text: '→ Join Waitlist' }
    ]
  },
  'voice_result': {
    id: 'voice_result',
    message: `Your tone: Friendly, reassuring with empathetic problem-solving focus.

My mirrored response:
"I completely understand your frustration with the delayed shipment—that's definitely not the experience we want for you! I've gone ahead and rushed a replacement that will arrive in 2 days, and added a complimentary sample of our new formula. Please let me know when it arrives, and thank you for your patience with us!"

Tone-match: 96%`,
    chips: [
      { id: 'main_menu', text: 'Main Menu' },
      { id: 'waitlist', text: '→ Join Waitlist' }
    ]
  },
  'integration': {
    id: 'integration',
    message: `Current demo stack: Shopify, ReCharge, Gorgias, Slack. I plug into:

• Shopify & Shopify Plus (OAuth)
• Cratejoy, WooCommerce (API key)
• Helpdesks: Gorgias, Zendesk, HelpScout
• DMs: IG, FB, TikTok, Twitter
• Review apps: Yotpo, Stamped
Total setup time founders report: 27 min average.

Need more tech details or good to go?`,
    chips: [
      { id: 'more_details', text: 'Need More Details' },
      { id: 'main_menu', text: 'Main Menu' },
      { id: 'waitlist', text: '→ Join Waitlist' }
    ]
  },
  'more_details': {
    id: 'more_details',
    message: `Tech Integration Details:

• Webhooks: Real-time events for orders, customers, tickets
• Data scope: Read-only for customer/order history, write for pre-approved actions
• Sandbox mode: Test with real data, no customer impact
• GDPR/CCPA compliant: All PII properly managed
• API rate limits: Never exceeds platform thresholds
• Single sign-on: Manage from your existing admin`,
    chips: [
      { id: 'main_menu', text: 'Main Menu' },
      { id: 'waitlist', text: '→ Join Waitlist' }
    ]
  },
  'pricing': {
    id: 'pricing',
    message: `Founder-beta pricing: pay only for tickets I fully resolve.

• $0.35 per email/chat solved
• $0.15 per social DM solved
• First 30 days: 100 free resolutions
• No seat fees, no annual lock-in.

Ready to lock-in beta rates?`,
    chips: [
      { id: 'waitlist', text: 'Join Waitlist' },
      { id: 'main_menu', text: 'Main Menu' }
    ]
  },
  'waitlist': {
    id: 'waitlist',
    message: `Inbox quiet, coffee hot—let's give your real store the same treatment. Drop your email, I'll hold a slot and send the onboarding link.

(For this demo, we'll just show the form would appear here)`,
    chips: [
      { id: 'welcome', text: 'Restart Demo' },
      { id: 'leave_demo', text: 'Leave Demo' }
    ]
  },
  'leave_demo': {
    id: 'leave_demo',
    message: "Thanks for visiting! You can restart anytime.",
    chips: [
      { id: 'welcome', text: 'Restart Demo' }
    ]
  }
};

interface DemoScriptFlowProps {
  className?: string;
  onComplete?: () => void;
}

const DemoScriptFlow: React.FC<DemoScriptFlowProps> = ({ className = '', onComplete }) => {
  const [currentStepId, setCurrentStepId] = useState('welcome');
  const [conversationHistory, setConversationHistory] = useState<{
    message: string;
    isUser: boolean;
    stepId: string;
  }[]>([
    { message: scriptData['welcome'].message, isUser: false, stepId: 'welcome' }
  ]);

  const handleChipClick = (chipId: string) => {
    const selectedChip = scriptData[currentStepId].chips.find(c => c.id === chipId);
    if (!selectedChip) return;

    // Add user's selection to history
    setConversationHistory(prev => [
      ...prev,
      { message: selectedChip.text, isUser: true, stepId: currentStepId }
    ]);

    // Check if we have a response for this chip
    if (scriptData[chipId]) {
      setCurrentStepId(chipId);
      
      // Add CJ's response
      setConversationHistory(prev => [
        ...prev,
        { message: scriptData[chipId].message, isUser: false, stepId: chipId }
      ]);
    }

    if (chipId === 'waitlist' && onComplete) {
      // In a real app, we would first show the email form
      setTimeout(() => {
        onComplete();
      }, 500);
    }
  };

  const currentStep = scriptData[currentStepId];

  return (
    <div className={`w-full h-full flex flex-col ${className}`}>
      <div className="flex-1 overflow-y-auto p-4 space-y-4 pb-0">
        {conversationHistory.map((item, index) => (
          <div key={index} className="flex items-start">
            {item.isUser ? (
              // User message
              <div className="flex items-start ml-auto">
                <div className="bg-gray-700 rounded-lg p-3 max-w-md">
                  <p className="text-white">{item.message}</p>
                </div>
                <div className="flex-shrink-0 ml-3">
                  <div className="bg-linkedin-blue w-10 h-10 rounded flex items-center justify-center text-white">
                    <span className="font-semibold">You</span>
                  </div>
                </div>
              </div>
            ) : (
              // CJ message
              <div className="flex items-start">
                <div className="flex-shrink-0 mr-3">
                  <div className="bg-cratejoy-teal w-10 h-10 rounded flex items-center justify-center text-white">
                    <span className="font-semibold">CJ</span>
                  </div>
                </div>
                <div className="bg-gray-800 rounded-lg p-3 max-w-2xl">
                  <p className="text-white whitespace-pre-line">{item.message}</p>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Quick reply chips */}
      <div className="p-4 border-t border-gray-700">
        <div className="flex flex-wrap gap-2">
          {currentStep.chips.map((chip) => (
            <button
              key={chip.id}
              onClick={() => handleChipClick(chip.id)}
              className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-full text-sm transition-colors"
            >
              {chip.text}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default DemoScriptFlow;