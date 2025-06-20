===========================================================================================
                              AGENT EDITOR - EXECUTIVE SUMMARY
===========================================================================================

PURPOSE:
This is a visual interface for building, testing, and refining AI agents against various 
scenarios. It provides a unified environment to design agent behaviors, test conversations,
and iteratively improve agent responses.

KEY CONCEPTS:

• SOURCE OF TRUTH: All configurations live as files on disk
  - System prompts, workflows, tools, and user personas are stored as YAML/JSON files
  - The UI reads from and writes to these files directly
  - No separate database - the filesystem IS the database

• VERSION CONTROL: Every edit creates a new file version
  - Files use incremented version numbers (e.g., prompt_v1.yaml → prompt_v2.yaml)
  - All versions are committed to the repository
  - Git provides history and collaboration, but not the primary versioning mechanism
  - Easy rollback by selecting previous file versions

• DIRECTORY STRUCTURE: Organized hierarchy on disk
  /prompts
    /system           → System prompts for agents
    /workflows        → Conversation flow definitions
  /personas           → User persona definitions
  /scenarios          → Business scenarios for testing
  /tools              → Tool/function definitions

• DESIGN PHILOSOPHY:
  - Single interface for all agent design tasks
  - Visual editing with immediate file persistence
  - Test agents against realistic merchant personas and scenarios
  - Iterate quickly with version tracking
  - Collaborate through standard git workflows
  - AI-DRIVEN EDITING: While manual tweaks are possible, the primary workflow is to provide
    feedback and let AI suggest improvements. Each edit location becomes a conversation where
    you describe what you want changed, and the AI proposes specific adjustments to prompts,
    workflows, or configurations.


===========================================================================================
                            PLAYGROUND VIEW - MAIN CONVERSATION INTERFACE
===========================================================================================

+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                                    WORKFLOW SELECTOR                                                |
|  NAVIGATION      +-----------------------------------------------------------------------------------------------------+
|                  | Workflow: [v1.2 - Customer Support Flow ▼] [✏ Edit]                                               |
|                  | ▼ Workflow Editor (click to expand)                                                                |
|                  | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
|                  | │ 1. Greet customer → 2. Identify needs → 3. Provide recommendations... [collapsed]           │   |
|                  | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
+------------------+-----------------------------------------------------+-----------------------------------------------------+
|                  |                AGENT PERSPECTIVE (LEFT)             |                USER PERSPECTIVE (RIGHT)             |
|  NAVIGATION      +-----------------------------------------------------+-----------------------------------------------------+
|                  | ┌─────────────────────────────────────────────┐   | ┌─────────────────────────────────────────────┐   |
| ┌──────────────┐ | │                                             │   | │                                             │   |
| │              │ | │              SCROLLABLE AREA                │   | │              SCROLLABLE AREA                │   |
| │ ▶ Playground │ | │                                             │   | │ USER                                        │   |
| │   (current)  │ | │                                             │   | │ ┌─────────────────────────────────────┐   │   |
| ├──────────────┤ | │                                             │   | │ │ Hey, I'm looking for a new laptop   │   │   |
| │              │ | │                                             │   | │ │ for work. What do you recommend?    │   │   |
| │   User       │ | │                                             │   | │ └─────────────────────────────────────┘   │   |
| │   Personas   │ | │ AGENT                                       │   | │                                             │   |
| │              │ | │ ┌─────────────────────────────────────┐   │   | │                                             │   |
| ├──────────────┤ | │ │ I'd be happy to help you find a     │   │   | │                                             │   |
| │              │ | │ │ laptop! What's your budget and      │   │   | │                                             │   |
| │   System     │ | │ │ main use cases?                      │   │   | │                                             │   |
| │   Prompts    │ | │ └─────────────────────────────────────┘   │   | │                                             │   |
| │              │ | │  [💭 Prompt] [🔄 Workflow] [📋 Details]      │   | │                                             │   |
| ├──────────────┤ | │                                             │   | │ USER                                        │   |
| │              │ | │                                             │   | │ ┌─────────────────────────────────────┐   │   |
| │   Workflow   │ | │                                             │   | │ │ Budget is around $1500. I need it   │   │   |
| │   Editor     │ | │                                             │   | │ │ for coding and video editing.       │   │   |
| │              │ | │                                             │   | │ └─────────────────────────────────────┘   │   |
| ├──────────────┤ | │ AGENT                                       │   | │                                             │   |
| │              │ | │ ┌─────────────────────────────────────┐   │   | │                                             │   |
| │   Tool       │ | │ │ For that budget, I'd suggest the    │   │   | │                                             │   |
| │   Editor     │ | │ │ MacBook Pro 14" or Dell XPS 15...   │   │   | │                                             │   |
| │   Editor     │ | │ └─────────────────────────────────────┘   │   | │                                             │   |
| │              │ | │  [💭 Prompt] [🔄 Workflow] [📋 Details] ◀─ Hover for feedback │ │                                    │   |
| │              │ | │                                             │   | │                                             │   |
| │   Settings   │ | │              (more messages...)              │   | │              (more messages...)              │   |
| │              │ | │                                             │   | │                                             │   |
| └──────────────┘ | └─────────────────────────────────────────────┘   | └─────────────────────────────────────────────┘   |
|                  |----------------------------------------------------|----------------------------------------------|
|                  | System Prompt: [v2.1 - Customer Service ▼] [✏ Edit]| Merchant Persona: [Sarah Chen - EcoBeauty ▼]|
|                  |----------------------------------------------------|----------------------------------------------|
|                  | ▼ System Prompt Editor (click to expand)          | Business Context:                            |
|                  | ┌─────────────────────────────────────────────┐   | • Scenario: [Growth Stall ▼]                |
|                  | │ You are a helpful customer service agent... │   | • Stress Level: Moderate                     |
|                  | │ [collapsed - click ✏ to expand]             │   | • Emotional State: Focused                   |
|                  | └─────────────────────────────────────────────┘   |                                              |
|                  |                                                    | Communication Style:                         |
|                  |                                                    | • Collaborative, detail-oriented             |
|                  |                                                    | • Asks thoughtful questions                  |
|                  |                                                    | • Values > Numbers focus                     |
|                  |                                                    |                                              |
|                  |                                                    | Business Details:                            |
|                  |                                                    | • 45% subscription revenue                   |
|                  |                                                    | • B-Corp certified (score: 82)              |
|                  |                                                    | • 350+ SKUs, 45+ brand partners             |
|                  |                                                    |                                              |
|                  |                                                    | [✏ Edit Persona] [📊 View Universe Data]    |
+------------------+-----------------------------------------------------+-----------------------------------------------------+


===========================================================================================
                          PLAYGROUND BLANK STATE - INITIAL SCREEN
===========================================================================================

VARIANT A: CJ-INITIATED WORKFLOW
+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                                    WORKFLOW SELECTOR                                                |
|  NAVIGATION      +-----------------------------------------------------------------------------------------------------+
|                  | Workflow: [v1.2 - Proactive Outreach ▼] [✏ Edit]        Agent: CJ       Merchant: Sarah Chen       |
+------------------+-----------------------------------------------------+-----------------------------------------------------+
|                  |                AGENT PERSPECTIVE (LEFT)             |                USER PERSPECTIVE (RIGHT)             |
|  NAVIGATION      +-----------------------------------------------------+-----------------------------------------------------+
|                  | ┌─────────────────────────────────────────────┐   | ┌─────────────────────────────────────────────┐   |
| ┌──────────────┐ | │                                             │   | │                                             │   |
| │              │ | │                                             │   | │                                             │   |
| │ ▶ Playground │ | │                                             │   | │                                             │   |
| │   (current)  │ | │                                             │   | │                                             │   |
| │              │ | │                                             │   | │                                             │   |
| ├──────────────┤ | │                                             │   | │                                             │   |
| │              │ | │                                             │   | │                                             │   |
| │   User       │ | │              ┌─────────────┐               │   | │                                             │   |
| │   Personas   │ | │              │             │               │   | │                                             │   |
| │              │ | │              │    ▶ PLAY   │               │   | │         Waiting for CJ to begin...          │   |
| ├──────────────┤ | │              │             │               │   | │                                             │   |
| │              │ | │              └─────────────┘               │   | │                                             │   |
| │   System     │ | │                                             │   | │         ┌───────────────────────┐          │   |
| │   Prompts    │ | │         Click to start CJ outreach          │   | │         │  Sarah Chen           │          │   |
| │              │ | │                                             │   | │         │  EcoBeauty Founder    │          │   |
| ├──────────────┤ | │                                             │   | │         │                       │          │   |
| │              │ | │          Scenario: Growth Stall             │   | │         │  Current Scenario:    │          │   |
| │   Workflow   │ | │          Trust Level: 3                     │   | │         │  Growth Stall         │          │   |
| │   Editor     │ | │                                             │   | │         └───────────────────────┘          │   |
| │              │ | │                                             │   | │                                             │   |
| ├──────────────┤ | │                                             │   | │                                             │   |
| │              │ | │                                             │   | │                                             │   |
| │   Tool       │ | │                                             │   | │                                             │   |
| │   Editor     │ | │                                             │   | │                                             │   |
| │              │ | │                                             │   | │                                             │   |
| ├──────────────┤ | │                                             │   | │                                             │   |
| │              │ | │                                             │   | │                                             │   |
| │   Settings   │ | └─────────────────────────────────────────────┘   | └─────────────────────────────────────────────┘   |
| │              │ +=====================================================+==============================================+
| └──────────────┘ | AGENT CONTROLS                                     | USER CONTROLS                                |
|                  |----------------------------------------------------|----------------------------------------------|
|                  | System Prompt: [v2.1 - Proactive CJ ▼] [✏ Edit]   | Merchant Persona: [Sarah Chen - EcoBeauty ▼]|
|                  | Trust Level: [Level 3 - Trusted Support ▼]        | Scenario: [Growth Stall ▼]                  |
|                  | Opening Strategy: [Check recent metrics ▼]        | Stress Level: [High ▼]                      |
+------------------+-----------------------------------------------------+-----------------------------------------------------+


VARIANT B: MERCHANT-INITIATED WORKFLOW
+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                                    WORKFLOW SELECTOR                                                |
|  NAVIGATION      +-----------------------------------------------------------------------------------------------------+
|                  | Workflow: [v1.1 - Merchant Support ▼] [✏ Edit]          Agent: CJ       Merchant: Sarah Chen       |
+------------------+-----------------------------------------------------+-----------------------------------------------------+
|                  |                AGENT PERSPECTIVE (LEFT)             |                USER PERSPECTIVE (RIGHT)             |
|  NAVIGATION      +-----------------------------------------------------+-----------------------------------------------------+
|                  | ┌─────────────────────────────────────────────┐   | ┌─────────────────────────────────────────────┐   |
| ┌──────────────┐ | │                                             │   | │                                             │   |
| │              │ | │                                             │   | │                                             │   |
| │ ▶ Playground │ | │                                             │   | │                                             │   |
| │   (current)  │ | │                                             │   | │         ┌───────────────────────┐          │   |
| │              │ | │                                             │   | │         │  Sarah Chen           │          │   |
| ├──────────────┤ | │                                             │   | │         │  EcoBeauty Founder    │          │   |
| │              │ | │         Waiting for merchant...             │   | │         │                       │          │   |
| │   User       │ | │                                             │   | │         │  Ready to chat with   │          │   |
| │   Personas   │ | │              ┌─────────┐                   │   | │         │  your CJ assistant    │          │   |
| │              │ | │              │   CJ    │                   │   | │         └───────────────────────┘          │   |
| ├──────────────┤ | │              │ 👋 Ready │                   │   | │                                             │   |
| │              │ | │              └─────────┘                   │   | │                                             │   |
| │   System     │ | │                                             │   | │                                             │   |
| │   Prompts    │ | │         Trust Level: 3                     │   | │                                             │   |
| │              │ | │         Available Actions:                  │   | │                                             │   |
| ├──────────────┤ | │         • Answer questions                  │   | │                                             │   |
| │              │ | │         • Look up metrics                   │   | │                                             │   |
| │   Workflow   │ | │         • Provide recommendations           │   | │                                             │   |
| │   Editor     │ | │         • Issue credits (up to $100)        │   | │                                             │   |
| │              │ | │                                             │   | │                                             │   |
| ├──────────────┤ | │                                             │   | │                                             │   |
| │              │ | │                                             │   | │                                             │   |
| │   Tool       │ | │                                             │   | │                                             │   |
| │   Editor     │ | │                                             │   | │  ┌─────────────────────────────────────┐   │   |
| │              │ | │                                             │   | │  │ Type a message...                   │   │   |
| ├──────────────┤ | │                                             │   | │  │                                     │   │   |
| │              │ | │                                             │   | │  └─────────────────────────────────┘   │   |
| │   Settings   │ | │                                             │   | │         [Presets ▼]        [Send →]        │   |
| │              │ | └─────────────────────────────────────────────┘   | └─────────────────────────────────────────────┘   |
| │              │ +=====================================================+==============================================+
| └──────────────┘ | AGENT CONTROLS                                     | USER CONTROLS                                |
|                  |----------------------------------------------------|----------------------------------------------|
|                  | System Prompt: [v1.3 - Support Agent ▼] [✏ Edit]  | Merchant Persona: [Sarah Chen - EcoBeauty ▼]|
|                  | Trust Level: [Level 3 - Trusted Support ▼]        | Scenario: [Daily Operations ▼]              |
|                  | Response Style: [Friendly & Professional ▼]       | Mood: [Neutral ▼]                           |
+------------------+-----------------------------------------------------+-----------------------------------------------------+


PRESET MESSAGES (Dropdown when "Presets ▼" is clicked in Merchant-Initiated)
┌─────────────────────────────────────────────────────────┐
│ Quick Start Messages:                                   │
├─────────────────────────────────────────────────────────┤
│ 📊 "Hey CJ, how are my sales looking this week?"       │
│ 🚚 "I have a customer asking about shipping delays"    │
│ 💡 "What marketing strategies should I try?"            │
│ 🛍️  "Can you help me plan a promotion?"                │
│ ❓ "I need help with..." (custom)                      │
└─────────────────────────────────────────────────────────┘


===========================================================================================
                                    USER EDITOR SCREEN
===========================================================================================

+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                                    USER PERSONA EDITOR                                              |
|  NAVIGATION      +-----------------------------------------------------------------------------------------------------+
|                  | Current Persona: Sarah Chen - EcoBeauty Founder                                [💾 Save] [❌ Cancel] |
+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                                                                                                     |
| ┌──────────────┐ | BASIC INFORMATION                                                                                   |
| │              │ | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
| │   Playground │ | │ Name: [Sarah Chen                                    ]                                       │   |
| │              │ | │ Business: [EcoBeauty                                 ]                                       │   |
| ├──────────────┤ | │ Role: [Founder & CEO                                 ]                                       │   |
| │              │ | │ Industry: [Beauty & Personal Care ▼]                                                        │   |
| │ ▶ User       │ | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
| │   Personas   │ |                                                                                                     |
| │   (current)  │ | PERSONALITY & COMMUNICATION                                                                         |
| │              │ | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
| ├──────────────┤ | │ Communication Style:                                                                         │   |
| │              │ | │ [✓] Collaborative    [ ] Direct    [✓] Detail-oriented    [ ] Brief                        │   |
| │   System     │ | │                                                                                              │   |
| │   Prompts    │ | │ Key Traits (comma-separated):                                                               │   |
| │              │ | │ [thoughtful, values-driven, analytical, empathetic                                    ]     │   |
| ├──────────────┤ | │                                                                                              │   |
| │              │ | │ Speaking Patterns:                                                                           │   |
| │   Workflow   │ | │ [Uses sustainability jargon, asks clarifying questions, references metrics       ]          │   |
| │   Editor     │ | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
| │              │ |                                                                                                     |
| ├──────────────┤ | BUSINESS CONTEXT                                                                                    |
| │              │ | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
| │   Tool       │ | │ Annual Revenue: [$2.4M                    ]  Growth Rate: [15% ▼]                           │   |
| │   Editor     │ | │ Team Size: [12                            ]  Years in Business: [3                   ]      │   |
| │              │ | │                                                                                              │   |
| ├──────────────┤ | │ Key Metrics:                                                                                 │   |
| │              │ | │ • Subscription Revenue: [45%              ]                                                 │   |
| │   Settings   │ | │ • Customer LTV: [$185                     ]                                                 │   |
| │              │ | │ • Monthly Active Customers: [8,500        ]                                                 │   |
| └──────────────┘ | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
+------------------+-----------------------------------------------------------------------------------------------------+


===========================================================================================
                                 SYSTEM PROMPT EDITOR SCREEN
===========================================================================================

+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                                SYSTEM PROMPT EDITOR                                                 |
|  NAVIGATION      +-----------------------------------------------------------------------------------------------------+
|                  | Version: v2.1 - Customer Service Agent                                         [💾 Save] [❌ Cancel] |
+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                                                                                                     |
| ┌──────────────┐ | PROMPT CONFIGURATION                                                                                |
| │              │ | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
| │   Playground │ | │ Name: [Customer Service Agent v2.1                                          ]               │   |
| │              │ | │ Category: [Support ▼]    Status: [Active ▼]    Version: [2.1              ]               │   |
| ├──────────────┤ | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
| │              │ |                                                                                                     |
| │   User       │ | SYSTEM PROMPT                                                                                       |
| │   Personas   │ | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
| │              │ | │ You are a helpful and knowledgeable customer service agent for an e-commerce platform.      │   |
| ├──────────────┤ | │                                                                                              │   |
| │              │ | │ Your primary goals are to:                                                                  │   |
| │ ▶ System     │ | │ - Assist customers with product inquiries                                                   │   |
| │   Prompts    │ | │ - Help resolve order issues                                                                 │   |
| │   (current)  │ | │ - Provide personalized recommendations                                                      │   |
| │              │ | │ - Maintain a friendly and professional tone                                                 │   |
| ├──────────────┤ | │                                                                                              │   |
| │              │ | │ Always remember to:                                                                         │   |
| │   Workflow   │ | │ - Ask clarifying questions when needed                                                      │   |
| │   Editor     │ | │ - Reference customer history when available                                                 │   |
| │              │ | │ - Escalate complex issues appropriately                                                     │   |
| ├──────────────┤ | │                                                                                              │   |
| │              │ | │ [Type your system prompt here...]                                                           │   |
| │   Tool       │ | │                                                                                              │   |
| │   Editor     │ | │                                                                                              │   |
| │              │ | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
| ├──────────────┤ |                                                                                                     |
| │              │ | VARIABLES & PLACEHOLDERS                                                                            |
| │   Settings   │ | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
| │              │ | │ Available: {{customer_name}}, {{order_id}}, {{product_category}}              [+ Add]      │   |
| └──────────────┘ | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
+------------------+-----------------------------------------------------------------------------------------------------+


===========================================================================================
                                   WORKFLOW EDITOR SCREEN
===========================================================================================

+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                                    WORKFLOW EDITOR                                                  |
|  NAVIGATION      +-----------------------------------------------------------------------------------------------------+
|                  | Workflow: Customer Support Flow v1.2                                           [💾 Save] [❌ Cancel] |
+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                                                                                                     |
| ┌──────────────┐ | WORKFLOW STEPS                                                              [+ Add Step] [🔄 Reorder]|
| │              │ | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
| │   Playground │ | │                                                                                              │   |
| │              │ | │  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐      ┌─────────────┐          │   |
| ├──────────────┤ | │  │    START    │ ───→ │   STEP 1    │ ───→ │   STEP 2    │ ───→ │   STEP 3    │          │   |
| │              │ | │  │   Greeting  │      │  Identify   │      │   Gather    │      │  Provide    │          │   |
| │   User       │ | │  └─────────────┘      │    Need     │      │    Info     │      │  Solution   │          │   |
| │   Personas   │ | │                       └─────────────┘      └─────────────┘      └─────────────┘          │   |
| │              │ | │                                                     │                                       │   |
| ├──────────────┤ | │                                                     ↓                                       │   |
| │              │ | │                       ┌─────────────┐      ┌─────────────┐      ┌─────────────┐          │   |
| │   System     │ | │                       │   STEP 4    │ ←─── │  DECISION   │      │     END     │          │   |
| │   Prompts    │ | │                       │  Follow-up  │      │  Resolved?  │ ───→ │   Complete  │          │   |
| │              │ | │                       └─────────────┘      └─────────────┘      └─────────────┘          │   |
| ├──────────────┤ | │                                                                                              │   |
| │              │ | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
| │ ▶ Workflow   │ |                                                                                                     |
| │   Editor     │ | SELECTED STEP: Step 2 - Gather Info                                                                |
| │   (current)  │ | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
| │              │ | │ Step Name: [Gather Information                                              ]               │   |
| ├──────────────┤ | │                                                                                              │   |
| │              │ | │ Description:                                                                                 │   |
| │   Tool       │ | │ [Collect necessary details about the customer's issue or request            ]               │   |
| │   Editor     │ | │                                                                                              │   |
| │              │ | │ Actions:                                                                                     │   |
| ├──────────────┤ | │ [✓] Ask clarifying questions                                                                │   |
| │              │ | │ [✓] Check order history                                                                     │   |
| │   Settings   │ | │ [ ] Verify customer identity                                                                │   |
| │              │ | │                                                                                              │   |
| └──────────────┘ | │ Next Steps: [Step 3 - Provide Solution ▼]  If Failed: [Step 1 - Identify Need ▼]          │   |
|                  | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
+------------------+-----------------------------------------------------------------------------------------------------+


===========================================================================================
                                    TOOL EDITOR SCREEN
===========================================================================================

+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                                      TOOL EDITOR                                                    |
|  NAVIGATION      +-----------------------------------------------------------------------------------------------------+
|                  | Tool: check_inventory                                                          [💾 Save] [❌ Cancel] |
+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                                                                                                     |
| ┌──────────────┐ | TOOL CONFIGURATION                                                                                  |
| │              │ | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
| │   Playground │ | │ Name: [check_inventory                               ]  Type: [API Call ▼]                  │   |
| │              │ | │ Description: [Check product availability in inventory                                ]      │   |
| ├──────────────┤ | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
| │              │ |                                                                                                     |
| │   User       │ | PARAMETERS                                                                                          |
| │   Personas   │ | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
| │              │ | │ Parameter      Type        Required    Description                              [+ Add]     │   |
| ├──────────────┤ | │ ─────────────────────────────────────────────────────────────────────────────────────────── │   |
| │              │ | │ product_id     string      [✓]         Product SKU or ID                        [✏] [🗑]   │   |
| │   System     │ | │ location       string      [ ]         Warehouse location (optional)            [✏] [🗑]   │   |
| │   Prompts    │ | │ quantity       integer     [ ]         Minimum quantity needed                  [✏] [🗑]   │   |
| │              │ | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
| ├──────────────┤ |                                                                                                     |
| │              │ | API CONFIGURATION                                                                                   |
| │   Workflow   │ | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
| │   Editor     │ | │ Endpoint: [https://api.store.com/v1/inventory/check                        ]               │   |
| │              │ | │ Method: [GET ▼]    Authentication: [Bearer Token ▼]                                        │   |
| ├──────────────┤ | │                                                                                              │   |
| │              │ | │ Headers:                                                                                     │   |
| │ ▶ Tool       │ | │ [Content-Type: application/json                                                      ]      │   |
| │   Editor     │ | │ [Authorization: Bearer {{api_key}}                                                   ]      │   |
| │   (current)  │ | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
| │              │ |                                                                                                     |
| ├──────────────┤ | RESPONSE HANDLING                                                                                   |
| │              │ | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
| │   Settings   │ | │ Success Response:                                 Error Response:                           │   |
| │              │ | │ [{ "available": true,                   ]        [{ "error": "Product not found" }  ]     │   |
| └──────────────┘ | │ [  "quantity": 150,                     ]        [                                     ]     │   |
|                  | │ [  "locations": ["NYC", "LA"] }         ]        [                                     ]     │   |
|                  | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
+------------------+-----------------------------------------------------------------------------------------------------+


===========================================================================================
                                    GROUNDING VIEW - MAIN SCREEN
===========================================================================================

+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                                    KNOWLEDGE GRAPHS                                                 |
|  NAVIGATION      +-----------------------------------------------------------------------------------------------------+
|                  | Manage your RAG knowledge bases for enhanced agent capabilities                                     |
+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                                                                                                     |
| ┌──────────────┐ | AVAILABLE KNOWLEDGE GRAPHS                                                          [+ New Graph] |
| │              │ | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
| │   Playground │ | │                                                                                              │   |
| │              │ | │ ┌────────────────────────────┐  ┌────────────────────────────┐  ┌──────────────────────┐   │   |
| ├──────────────┤ | │ │    Product Knowledge         │  │    Customer Support          │  │   Tech Docs        │   │   |
| │              │ | │ │                              │  │                              │  │                    │   │   |
| │   User       │ | │ │ 📚 2,847 documents          │  │ 💬 5,432 conversations       │  │ 🔧 892 articles    │   │   |
| │   Personas   │ | │ │ 📊 Last updated: 2h ago     │  │ 📊 Last updated: 15m ago    │  │ 📊 Updated: 1d ago │   │   |
| │              │ | │ │                              │  │                              │  │                    │   │   |
| ├──────────────┤ | │ │ Sources:                     │  │ Sources:                     │  │ Sources:           │   │   |
| │              │ | │ │ • Product catalogs           │  │ • Support tickets            │  │ • API docs         │   │   |
| │   System     │ | │ │ • Feature docs               │  │ • Chat transcripts           │  │ • GitHub wikis     │   │   |
| │   Prompts    │ | │ │ • Release notes              │  │ • FAQ database               │  │ • Blog posts       │   │   |
| │              │ | │ │                              │  │                              │  │                    │   │   |
| ├──────────────┤ | │ │ Status: ✅ Active            │  │ Status: ✅ Active            │  │ Status: 🔄 Syncing │   │   |
| │              │ | │ │                              │  │                              │  │                    │   │   |
| │   Workflow   │ | │ │ [View Details →]            │  │ [View Details →]            │  │ [View Details →]  │   │   |
| │   Editor     │ | │ └────────────────────────────┘  └────────────────────────────┘  └──────────────────────┘   │   |
| │              │ | │                                                                                              │   |
| ├──────────────┤ | │ ┌────────────────────────────┐  ┌────────────────────────────┐                            │   |
| │              │ | │ │    Industry Research         │  │    Competitor Analysis       │                            │   |
| │   Tool       │ | │ │                              │  │                              │                            │   |
| │   Editor     │ | │ │ 🔬 1,203 sources             │  │ 📈 756 documents             │                            │   |
| │              │ | │ │ 📊 Last updated: 3d ago     │  │ 📊 Last updated: 1w ago     │                            │   |
| ├──────────────┤ | │ │                              │  │                              │                            │   |
| │              │ | │ │ Sources:                     │  │ Sources:                     │                            │   |
| │ ▶ Grounding   │ | │ │ • Industry reports           │  │ • Competitor sites           │                            │   |
| │   (current)   │ | │ │ • Market research            │  │ • Product comparisons        │                            │   |
| │              │ | │ │ • Trend analyses             │  │ • Feature matrices           │                            │   |
| ├──────────────┤ | │ │                              │  │                              │                            │   |
| │              │ | │ │ Status: ⏸️ Paused            │  │ Status: ✅ Active            │                            │   |
| │   Settings   │ | │ │                              │  │                              │                            │   |
| │              │ | │ │ [View Details →]            │  │ [View Details →]            │                            │   |
| └──────────────┘ | │ └────────────────────────────┘  └────────────────────────────┘                            │   |
|                  | │                                                                                              │   |
|                  | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
+------------------+-----------------------------------------------------------------------------------------------------+


===========================================================================================
                         GROUNDING VIEW - KNOWLEDGE GRAPH DETAIL
===========================================================================================

+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                              KNOWLEDGE GRAPH: Product Knowledge                                     |
|  NAVIGATION      +-----------------------------------------------------------------------------------------------------+
|                  | [← Back to Graphs]                                                            [⚙️ Settings] [🗑️ Delete] |
+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                                                                                                     |
| ┌──────────────┐ | OVERVIEW                                                                                            |
| │              │ | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
| │   Playground │ | │ Total Documents: 2,847          Last Updated: 2 hours ago         Status: ✅ Active         │   |
| │              │ | │ Vector Store: Pinecone          Embedding Model: text-embedding-3-small                     │   |
| ├──────────────┤ | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
| │              │ |                                                                                                     |
| │   User       │ | DATA SOURCES                                                                      [+ Add Source] |
| │   Personas   │ | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
| │              │ | │ Source                     Type        Documents    Last Sync    Status         Actions     │   |
| ├──────────────┤ | │ ─────────────────────────────────────────────────────────────────────────────────────────── │   |
| │              │ | │ products.cratejoy.com      Website     1,245        2h ago       ✅             [🔄] [✏️]  │   |
| │   System     │ | │ /docs/product-catalog      Files       892         1d ago       ✅             [🔄] [✏️]  │   |
| │   Prompts    │ | │ Release Notes RSS          RSS Feed    387         2h ago       ✅             [🔄] [✏️]  │   |
| │              │ | │ Feature Videos             YouTube     223         3h ago       🔄 Processing  [⏸️] [✏️]  │   |
| ├──────────────┤ | │ competitor-features.txt    URL List    100         1w ago       ⚠️ Partial     [🔄] [✏️]  │   |
| │              │ | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
| │   Workflow   │ |                                                                                                     |
| │   Editor     │ | UPLOAD NEW CONTENT                                                                                  |
| │              │ | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
| ├──────────────┤ | │ Add content to this knowledge graph:                                                         │   |
| │              │ | │                                                                                              │   |
| │   Tool       │ | │ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐     │   |
| │   Editor     │ | │ │   📁 Upload      │ │   🔗 Add URL     │ │   📰 RSS Feed    │ │   🎥 YouTube     │     │   |
| │              │ | │ │   Files          │ │                  │ │                  │ │   Video/Playlist │     │   |
| ├──────────────┤ | │ └──────────────────┘ └──────────────────┘ └──────────────────┘ └──────────────────┘     │   |
| │              │ | │                                                                                              │   |
| │ ▶ Grounding   │ | │ ┌─────────────────────────────────────────────────────────────────────────────────────┐   │   |
| │   (current)   │ | │ │ 📋 Paste content or drop files here...                                             │   │   |
| │              │ | │ │                                                                                     │   │   |
| ├──────────────┤ | │ │                                                                                     │   │   |
| │              │ | │ │ Or enter URLs (one per line):                                                      │   │   |
| │   Settings   │ | │ │ [                                                                             ]     │   │   |
| │              │ | │ │ [                                                                             ]     │   │   |
| └──────────────┘ | │ │                                                                                     │   │   |
|                  | │ │ Supported: .txt, .pdf, .md, .json, .csv, YouTube links, RSS feeds           │     │   │   |
|                  | │ └─────────────────────────────────────────────────────────────────────────────────────┘   │   |
|                  | │                                                                                              │   |
|                  | │ [🚀 Start Processing]  [📝 Paste URLs from File]                                           │   |
|                  | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
+------------------+-----------------------------------------------------------------------------------------------------+


===========================================================================================
                         GROUNDING VIEW - PROCESSING STATUS
===========================================================================================

+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                              KNOWLEDGE GRAPH: Product Knowledge                                     |
|  NAVIGATION      +-----------------------------------------------------------------------------------------------------+
|                  | Processing content...                                                         [⏸️ Pause] [❌ Cancel] |
+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                                                                                                     |
| ┌──────────────┐ | PROCESSING QUEUE                                                                                    |
| │              │ | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
| │   Playground │ | │ Overall Progress: ████████████░░░░░░░░░░ 62% (186/300 items)                              │   |
| │              │ | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
| ├──────────────┤ |                                                                                                     |
| │              │ | ACTIVE PROCESSING                                                                                   |
| │   User       │ | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
| │   Personas   │ | │ Source                          Status                 Progress        ETA                  │   |
| │              │ | │ ─────────────────────────────────────────────────────────────────────────────────────────── │   |
| ├──────────────┤ | │ 🎥 YouTube: Product Demo 2024   Transcribing          ████████░░ 82%  ~2 min              │   |
| │              │ | │ 📄 feature-guide-v3.pdf         Extracting text       ███████░░░ 71%  ~1 min              │   |
| │   System     │ | │ 🌐 docs.example.com/api         Crawling pages        ████░░░░░░ 43%  ~5 min              │   |
| │   Prompts    │ | │ 📰 Product Updates RSS          Fetching entries      ██████████ 100% Processing...       │   |
| │              │ | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
| ├──────────────┤ |                                                                                                     |
| │              │ | QUEUED                                                                                              |
| │   Workflow   │ | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
| │   Editor     │ | │ • podcast-episode-042.mp3                                            Waiting...             │   |
| │              │ | │ • competitor-analysis-2024.pdf                                       Waiting...             │   |
| ├──────────────┤ | │ • https://blog.example.com/product-updates/*                        Waiting...             │   |
| │              │ | │ • feature-requests.csv                                               Waiting...             │   |
| │   Tool       │ | │ • ... 108 more items                                                                         │   |
| │   Editor     │ | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
| │              │ |                                                                                                     |
| ├──────────────┤ | COMPLETED (Last 5)                                                                [View All →]    |
| │              │ | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
| │ ▶ Grounding   │ | │ ✅ roadmap-q4-2024.md           23 chunks created      Added 2 min ago                      │   |
| │   (current)   │ | │ ✅ YouTube: Feature Walkthrough  45 chunks created      Added 5 min ago                      │   |
| │              │ | │ ✅ pricing-tiers.json           12 chunks created      Added 7 min ago                      │   |
| ├──────────────┤ | │ ✅ https://example.com/features 38 chunks created      Added 10 min ago                     │   |
| │              │ | │ ✅ customer-feedback.txt        67 chunks created      Added 12 min ago                     │   |
| │   Settings   │ | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
| │              │ |                                                                                                     |
| └──────────────┘ | ERRORS & WARNINGS                                                                 [Clear]        |
|                  | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
|                  | │ ⚠️ broken-link.html: 404 Not Found - Skipping                                                │   |
|                  | │ ⚠️ large-video.mp4: File too large (>500MB) - Consider splitting                             │   |
|                  | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
+------------------+-----------------------------------------------------------------------------------------------------+


===========================================================================================
                      FEEDBACK & DIFF VIEW - APPEARS WHEN CLICKING FEEDBACK BUTTON
===========================================================================================

+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                              AI-SUGGESTED EDIT FOR: [💭 System Prompt]                              |
|  NAVIGATION      +-----------------------------------------------------------------------------------------------------+
|                  | Context: User asked about laptops, agent response was generic                  [✅ Accept] [❌ Cancel] |
+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                                                                                                     |
|   [Same as       | YOUR FEEDBACK                                                                                       |
|    before]       | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
|                  | │ The agent should ask about specific software they use for video editing before              │   |
|                  | │ recommending. Also should mention GPU requirements for video work.                           │   |
|                  | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
|                  |                                                                                                     |
|                  | AI THINKING...                                                                                      |
|                  | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
|                  | │ Based on the feedback, I should update the prompt to ensure the agent asks about specific   │   |
|                  | │ software requirements before making recommendations, especially for specialized use cases... │   |
|                  | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
|                  |                                                                                                     |
|                  | PROPOSED CHANGES TO: system_prompt_v2.1.yaml → system_prompt_v2.2.yaml                             |
|                  | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
|                  | │   Your primary goals are to:                                                                 │   |
|                  | │   - Assist customers with product inquiries                                                  │   |
|                  | │ - - Help resolve order issues                                                                │   |
|                  | │ + - Understand specific software and use case requirements before recommending              │   |
|                  | │ + - Help resolve order issues and technical requirements                                     │   |
|                  | │   - Provide personalized recommendations                                                     │   |
|                  | │   - Maintain a friendly and professional tone                                                │   |
|                  | │                                                                                               │   |
|                  | │   Always remember to:                                                                        │   |
|                  | │   - Ask clarifying questions when needed                                                     │   |
|                  | │ + - For technical purchases (laptops, workstations), always ask about:                      │   |
|                  | │ +   • Specific software they plan to use                                                    │   |
|                  | │ +   • Performance requirements (GPU for video editing, RAM for development)                 │   |
|                  | │ +   • Portability vs performance priorities                                                 │   |
|                  | │   - Reference customer history when available                                                │   |
|                  | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
|                  |                                                                                                     |
|                  | [✅ Accept & Re-run Conversation]  [✏️ Edit Manually]  [🔄 Try Different Suggestion]               |
+------------------+-----------------------------------------------------------------------------------------------------+


===========================================================================================
                    DETAILED VIEW: SYSTEM PROMPT FEEDBACK (Clicked 💭 on Agent Response)
===========================================================================================

+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                        SYSTEM PROMPT FEEDBACK - Improving Agent Behavior                            |
|  NAVIGATION      +-----------------------------------------------------------------------------------------------------+
|                  | Responding to: "For that budget, I'd suggest the MacBook Pro 14"..."           [✅ Accept] [❌ Cancel] |
+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                                                                                                     |
|   [Same as       | CONVERSATION CONTEXT (Up to this point)                                                            |
|    before]       | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
|                  | │ USER: Hey, I'm looking for a new laptop for work. What do you recommend?                    │   |
|                  | │ AGENT: I'd be happy to help you find a laptop! What's your budget and main use cases?      │   |
|                  | │ USER: Budget is around $1500. I need it for coding and video editing.                       │   |
|                  | │ AGENT: For that budget, I'd suggest the MacBook Pro 14" or Dell XPS 15...  ← FEEDBACK HERE │   |
|                  | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
|                  |                                                                                                     |
|                  | YOUR FEEDBACK                                                                                       |
|                  | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
|                  | │ What would you like to improve about this response?                                          │   |
|                  | │                                                                                               │   |
|                  | │ [The agent jumped straight to recommendations without asking about specific video         ]  │   |
|                  | │ [editing software. For video editing, GPU specs matter a lot - should ask about          ]  │   |
|                  | │ [whether they use Premiere, Final Cut, DaVinci Resolve, etc. Also should ask about      ]  │   |
|                  | │ [storage needs for video files.                                                          ]  │   |
|                  | │                                                                                               │   |
|                  | │ Suggested improvements:                                                                       │   |
|                  | │ [✓] Ask about specific software before recommending                                          │   |
|                  | │ [✓] Consider technical requirements (GPU, storage)                                           │   |
|                  | │ [ ] Change tone/style                                                                        │   |
|                  | │ [ ] Add more product options                                                                 │   |
|                  | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
|                  |                                                                                                     |
|                  | AI ANALYSIS                                                                                         |
|                  | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
|                  | │ 🤔 Understanding your feedback...                                                            │   |
|                  | │                                                                                               │   |
|                  | │ Key issues identified:                                                                        │   |
|                  | │ • Agent made assumptions about requirements                                                   │   |
|                  | │ • Skipped important qualifying questions for specialized use cases                           │   |
|                  | │ • Need to gather software-specific requirements for better recommendations                   │   |
|                  | │                                                                                               │   |
|                  | │ I'll update the system prompt to ensure the agent:                                           │   |
|                  | │ 1. Asks about specific software for specialized tasks                                        │   |
|                  | │ 2. Understands technical requirements before recommending                                     │   |
|                  | │ 3. Considers storage and performance needs for video editing                                 │   |
|                  | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
|                  |                                                                                                     |
|                  | PROPOSED SYSTEM PROMPT CHANGES                                              [🔍 View Full Prompt] |
|                  | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
|                  | │ File: system_prompt_v2.1.yaml → system_prompt_v2.2.yaml                                      │   |
|                  | │                                                                                               │   |
|                  | │ @@ -12,7 +12,15 @@                                                                           │   |
|                  | │  Always remember to:                                                                          │   |
|                  | │  - Ask clarifying questions when needed                                                       │   |
|                  | │ +- For specialized use cases (video editing, development, design), always ask about:         │   |
|                  | │ +  • Specific software/tools they use                                                        │   |
|                  | │ +  • Performance requirements specific to their workflow                                      │   |
|                  | │ +  • Storage needs (especially for video/media work)                                         │   |
|                  | │ +  • Whether they need portability or can prioritize performance                             │   |
|                  | │                                                                                               │   |
|                  | │ @@ -28,6 +36,11 @@                                                                           │   |
|                  | │  When discussing technical products:                                                          │   |
|                  | │  - Provide clear comparisons between options                                                  │   |
|                  | │  - Explain technical specifications in user-friendly terms                                    │   |
|                  | │ +- Never jump to recommendations without understanding:                                       │   |
|                  | │ +  • The specific software ecosystem they work in                                            │   |
|                  | │ +  • Their performance priorities                                                            │   |
|                  | │ +  • Any deal-breakers or must-have features                                                │   |
|                  | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
|                  |                                                                                                     |
|                  | [✅ Accept & Test Changes]  [✏️ Edit Diff]  [🔄 Generate Alternative]  [💬 Refine Feedback]        |
+------------------+-----------------------------------------------------------------------------------------------------+


===========================================================================================
                    DETAILED VIEW: WORKFLOW FEEDBACK (Clicked 🔄 on Agent Response)
===========================================================================================

+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                         WORKFLOW FEEDBACK - Adjusting Conversation Flow                             |
|  NAVIGATION      +-----------------------------------------------------------------------------------------------------+
|                  | Responding to: "For that budget, I'd suggest the MacBook Pro 14"..."           [✅ Accept] [❌ Cancel] |
+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                                                                                                     |
|   [Same as       | CURRENT WORKFLOW STATE                                                                              |
|    before]       | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
|                  | │  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐      ┌─────────────┐          │   |
|                  | │  │   Step 1    │      │   Step 2    │      │   Step 3    │      │   Step 4    │          │   |
|                  | │  │  Greeting   │ ───→ │  Identify   │ ───→ │   Gather    │ ───→ │  Provide    │          │   |
|                  | │  │    ✓       │      │    Need     │      │    Info     │      │  Solution   │          │   |
|                  | │  └─────────────┘      │     ✓       │      │   CURRENT   │      │     ←       │          │   |
|                  | │                       └─────────────┘      └─────────────┘      └─────────────┘          │   |
|                  | │                                                                                              │   |
|                  | │ ⚠️ ISSUE: Workflow jumped from "Identify Need" to "Provide Solution" too quickly           │   |
|                  | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
|                  |                                                                                                     |
|                  | YOUR FEEDBACK                                                                                       |
|                  | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
|                  | │ What's wrong with the workflow at this point?                                                │   |
|                  | │                                                                                               │   |
|                  | │ [The workflow needs a step for specialized requirements. When someone mentions           ]   │   |
|                  | │ [video editing or other specialized work, there should be a branch that gathers         ]   │   |
|                  | │ [detailed technical requirements before moving to recommendations.                       ]   │   |
|                  | │                                                                                               │   |
|                  | │ Workflow issues:                                                                              │   |
|                  | │ [✓] Missing conditional branch for specialized use cases                                     │   |
|                  | │ [✓] Need more granular information gathering                                                 │   |
|                  | │ [ ] Wrong sequence of steps                                                                  │   |
|                  | │ [ ] Missing error handling                                                                   │   |
|                  | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
|                  |                                                                                                     |
|                  | AI WORKFLOW REDESIGN                                                                                |
|                  | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
|                  | │ Proposed new workflow structure:                                                              │   |
|                  | │                                                                                               │   |
|                  | │  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                                │   |
|                  | │  │   Step 1    │      │   Step 2    │      │  DECISION   │                                │   |
|                  | │  │  Greeting   │ ───→ │  Identify   │ ───→ │ Specialized │                                │   |
|                  | │  └─────────────┘      │    Need     │      │   Use?      │                                │   |
|                  | │                       └─────────────┘      └──────┬──────┘                                │   |
|                  | │                                                    │                                        │   |
|                  | │                              ┌────────────────────┴────────────────────┐                   │   |
|                  | │                              ↓                                          ↓                   │   |
|                  | │                     ┌─────────────┐                           ┌─────────────┐              │   |
|                  | │                     │  Step 3A    │                           │  Step 3B    │              │   |
|                  | │                     │  Technical  │                           │   General   │              │   |
|                  | │                     │Requirements │                           │    Info     │              │   |
|                  | │                     └──────┬──────┘                           └──────┬──────┘              │   |
|                  | │                              ↓                                          ↓                   │   |
|                  | │                     ┌─────────────┐                           ┌─────────────┐              │   |
|                  | │                     │  Software   │                           │   Step 4    │              │   |
|                  | │                     │  Specific   │                           │  Provide    │              │   |
|                  | │                     │   Needs     │                           │  Solution   │              │   |
|                  | │                     └──────┬──────┘                           └─────────────┘              │   |
|                  | │                              ↓                                                              │   |
|                  | │                     ┌─────────────┐                                                        │   |
|                  | │                     │ Specialized │                                                        │   |
|                  | │                     │Recommendat. │                                                        │   |
|                  | │                     └─────────────┘                                                        │   |
|                  | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
|                  |                                                                                                     |
|                  | STEP CONFIGURATION: Step 3A - Technical Requirements (NEW)                                         |
|                  | ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   |
|                  | │ Step Name: Gather Technical Requirements                                                      │   |
|                  | │ Trigger: When user mentions: video editing, programming, design, music production, etc.      │   |
|                  | │                                                                                               │   |
|                  | │ Actions:                                                                                      │   |
|                  | │ • Ask about specific software/tools used                                                     │   |
|                  | │ • Inquire about performance requirements                                                     │   |
|                  | │ • Check storage and memory needs                                                             │   |
|                  | │ • Understand portability vs power trade-offs                                                 │   |
|                  | │                                                                                               │   |
|                  | │ Example prompts:                                                                              │   |
|                  | │ - "What video editing software do you primarily use?"                                        │   |
|                  | │ - "How large are your typical project files?"                                                │   |
|                  | │ - "Do you need to work on the go, or mostly at a desk?"                                     │   |
|                  | └─────────────────────────────────────────────────────────────────────────────────────────────┘   |
|                  |                                                                                                     |
|                  | [✅ Apply Workflow Changes]  [✏️ Edit Steps]  [🔄 Simplify]  [➕ Add More Branches]               |
+------------------+-----------------------------------------------------------------------------------------------------+


===========================================================================================
                    DETAILED VIEW: MESSAGE DETAILS (Clicked 📋 on Agent Response)
===========================================================================================

+------------------+-----------------------------------------------------------------------------------------------------+
|                  |                        MESSAGE DETAILS - LLM Prompt & Response                                      |
|  NAVIGATION      +-----------------------------------------------------------------------------------------------------+
|                  | Message: "For that budget, I'd suggest the MacBook Pro 14"..."                [← Back to Playground] |
+------------------+=====================================================+=====================================================+
|                  |                OUTGOING PROMPT TO LLM               |              INCOMING RESPONSE FROM LLM             |
|   [Same as       +-----------------------------------------------------+-----------------------------------------------------+
|    before]       | ┌─────────────────────────────────────────────┐   | ┌─────────────────────────────────────────────┐   |
|                  | │              SCROLLABLE AREA                │   | │              SCROLLABLE AREA                │   |
|                  | │                                             │   | │                                             │   |
|                  | │ SYSTEM:                                     │   | │ For that budget, I'd suggest the MacBook   │   |
|                  | │ You are a helpful and knowledgeable customer│   | │ Pro 14" or Dell XPS 15. Both are excellent │   |
|                  | │ service agent for an e-commerce platform.  │   | │ for coding and video editing.               │   |
|                  | │                                             │   | │                                             │   |
|                  | │ Your primary goals are to:                  │   | │ TOOL CALL: search_products                 │   |
|                  | │ - Assist customers with product inquiries  │   | │ ┌─────────────────────────────────────┐   │   |
|                  | │ - Help resolve order issues                │   | │ │ Input:                              │   │   |
|                  | │ - Provide personalized recommendations     │   | │ │ {                                   │   │   |
|                  | │ - Maintain a friendly and professional tone│   | │ │   "category": "laptops",            │   │   |
|                  | │                                             │   | │ │   "price_range": {                  │   │   |
|                  | │ Always remember to:                         │   | │ │     "min": 1200,                   │   │   |
|                  | │ - Ask clarifying questions when needed     │   | │ │     "max": 1700                    │   │   |
|                  | │ - Reference customer history when available│   | │ │   },                                │   │   |
|                  | │ - Escalate complex issues appropriately    │   | │ │   "features": ["video_editing",     │   │   |
|                  | │                                             │   | │ │                "programming"]       │   │   |
|                  | │ USER:                                       │   | │ │ }                                   │   │   |
|                  | │ ┌─────────────────────────────────────┐   │   | │ └─────────────────────────────────────┘   │   |
|                  | │ │ Hey, I'm looking for a new laptop   │   │   | │                                             │   |
|                  | │ │ for work. What do you recommend?    │   │   | │ TOOL OUTPUT:                                │   |
|                  | │ └─────────────────────────────────────┘   │   | │ ┌─────────────────────────────────────┐   │   |
|                  | │                                             │   | │ │ Results:                            │   │   |
|                  | │ ASSISTANT:                                  │   | │ │ [                                   │   │   |
|                  | │ I'd be happy to help you find a laptop!    │   | │ │   {                                 │   │   |
|                  | │ What's your budget and main use cases?     │   | │ │     "name": "MacBook Pro 14\"",    │   │   |
|                  | │                                             │   | │ │     "price": 1599,                  │   │   |
|                  | │ USER:                                       │   | │ │     "specs": {                      │   │   |
|                  | │ ┌─────────────────────────────────────┐   │   | │ │       "cpu": "M3 Pro",              │   │   |
|                  | │ │ Budget is around $1500. I need it   │   │   | │ │       "ram": "18GB",                │   │   |
|                  | │ │ for coding and video editing.       │   │   | │ │       "gpu": "11-core"              │   │   |
|                  | │ └─────────────────────────────────────┘   │   | │ │     }                               │   │   |
|                  | │                                             │   | │ │   },                                │   │   |
|                  | │ ASSISTANT:                                  │   | │ │   {                                 │   │   |
|                  | │                                             │   | │ │     "name": "Dell XPS 15",          │   │   |
|                  | │ [Total prompt: 1,247 tokens]               │   | │ │     "price": 1499,                  │   │   |
|                  | │                                             │   | │ │     "specs": {                      │   │   |
|                  | │                                             │   | │ │       "cpu": "i7-13700H",           │   │   |
|                  | │                                             │   | │ │       "ram": "16GB",                │   │   |
|                  | │                                             │   | │ │       "gpu": "RTX 4050"             │   │   |
|                  | │                                             │   | │ │     }                               │   │   |
|                  | │                                             │   | │ │   }                                 │   │   |
|                  | │                                             │   | │ │ ]                                   │   │   |
|                  | │                                             │   | │ └─────────────────────────────────────┘   │   |
|                  | │                                             │   | │                                             │   |
|                  | │                                             │   | │ The MacBook Pro 14" offers excellent       │   |
|                  | │                                             │   | │ performance for video editing with its     │   |
|                  | │                                             │   | │ dedicated media engine. The Dell XPS 15    │   |
|                  | │                                             │   | │ provides great value with a powerful GPU.  │   |
|                  | │                                             │   | │                                             │   |
|                  | │                                             │   | │ TOOL CALL: check_inventory                 │   |
|                  | │                                             │   | │ ┌─────────────────────────────────────┐   │   |
|                  | │                                             │   | │ │ Input:                              │   │   |
|                  | │                                             │   | │ │ {                                   │   │   |
|                  | │                                             │   | │ │   "product_ids": ["MBP14-M3",      │   │   |
|                  | │                                             │   | │ │                   "DELL-XPS15-2024"]│   │   |
|                  | │                                             │   | │ │ }                                   │   │   |
|                  | │                                             │   | │ └─────────────────────────────────────┘   │   |
|                  | │                                             │   | │                                             │   |
|                  | │                                             │   | │ TOOL OUTPUT:                                │   |
|                  | │                                             │   | │ ┌─────────────────────────────────────┐   │   |
|                  | │                                             │   | │ │ {                                   │   │   |
|                  | │                                             │   | │ │   "MBP14-M3": {                     │   │   |
|                  | │                                             │   | │ │     "available": true,              │   │   |
|                  | │                                             │   | │ │     "stock": 12,                    │   │   |
|                  | │                                             │   | │ │     "delivery": "2-3 days"          │   │   |
|                  | │                                             │   | │ │   },                                │   │   |
|                  | │                                             │   | │ │   "DELL-XPS15-2024": {              │   │   |
|                  | │                                             │   | │ │     "available": true,              │   │   |
|                  | │                                             │   | │ │     "stock": 8,                     │   │   |
|                  | │                                             │   | │ │     "delivery": "3-5 days"          │   │   |
|                  | │                                             │   | │ │   }                                 │   │   |
|                  | │                                             │   | │ │ }                                   │   │   |
|                  | │                                             │   | │ └─────────────────────────────────────┘   │   |
|                  | │                                             │   | │                                             │   |
|                  | │                                             │   | │ Both laptops are in stock. The MacBook    │   |
|                  | │                                             │   | │ can be delivered in 2-3 days, while the    │   |
|                  | │                                             │   | │ Dell would take 3-5 days...                │   |
|                  | │                                             │   | │                                             │   |
|                  | │                                             │   | │ [Total response: 2,156 tokens]             │   |
|                  | └─────────────────────────────────────────────┘   | └─────────────────────────────────────────────┘   |
|                  +-----------------------------------------------------+-----------------------------------------------------+
|                  | MODEL METADATA                                     | PERFORMANCE METRICS                                 |
|                  |----------------------------------------------------|-----------------------------------------------------|
|                  | Model: gpt-4-turbo-2024-04-09                     | Latency: 2.3s                                       |
|                  | Temperature: 0.7                                   | Tool Calls: 2                                       |
|                  | Max Tokens: 2048                                   | Total Cost: $0.0342                                 |
|                  | Timestamp: 2024-01-19 14:32:18 UTC                | Cache Hit: No                                       |
+------------------+-----------------------------------------------------+-----------------------------------------------------+