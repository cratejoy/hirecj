# Phase 4.6: System Events Architecture - Implementation Guide

## 🌟 North Star Principles

1. **Simplify, Simplify, Simplify**: Every decision should make the code simpler, not more complex
2. **No Cruft**: Remove all redundant code, validation, and unnecessary complexity
3. **Break It & Fix It Right**: No backwards compatibility shims - make breaking changes and migrate properly
4. **Long-term Elegance**: Choose performant, compiler-enforced solutions that prevent subtle bugs
5. **Backend-Driven**: Let the backend handle complexity, frontend should be a thin client
6. **Single Source of Truth**: One pattern, one way to do things, no alternatives
7. **No Over-Engineering**: Design for current needs only - no hypothetical features
8. **Thoughtful Logging & Instrumentation**: Appropriate visibility into system behavior

## 🎯 Critical Design Principle: Prompt Transparency

**No Hidden Prompt Mutations**: Prompts should NEVER be modified at runtime in ways that are hard to debug. Everything CJ sees should be visible by looking at:
1. Base prompt file (e.g., `v6.0.1.yaml`)
2. Workflow file (e.g., `shopify_onboarding.yaml`)

This enables developers to understand exactly what CJ will do without runtime debugging.

## Overview

Phase 4.6 adds system event handling instructions directly to workflow YAML files. This solves the current problem where CJ receives system messages (like OAuth completion) but doesn't know how to respond naturally.

## The Problem

Currently, when OAuth completes:
1. Frontend sends `oauth_complete` message
2. Backend creates system message: "New Shopify merchant authenticated from {shop}"
3. CJ receives: "Context update: {message}\n\nRespond appropriately to this authentication update."
4. CJ has no specific instructions on what "appropriately" means
5. Result: Awkward silence or generic response

## The Solution: Workflow-Visible Instructions

Add explicit system event handling instructions to the workflow YAML that CJ already sees:

```yaml
workflow: |
  WORKFLOW: Shopify Onboarding
  ... existing workflow content ...
  
  SYSTEM EVENT HANDLING:
  When you receive a message from sender "system", handle these specific events:
  
  For "New Shopify merchant authenticated from [store]":
  - First respond: "Perfect! I've successfully connected to your store at [store]."
  - Then say: "Give me just a moment to look around and get familiar with your setup..."
  - (In Phase 5, you'll start gathering store insights here)
  
  For "Returning Shopify merchant authenticated from [store]":
  - First respond: "Welcome back! I've reconnected to [store]."
  - Then say: "Let me quickly refresh my memory about your store..."
  
  For "Store insights loaded":
  - Share the insights naturally in the conversation
  
  For any other system messages:
  - Use the context provided to respond appropriately
```

## Current Architecture: How CJ Sees Prompts

Before we implement system events, it's important to understand how CJ currently receives instructions:

### 1. Base Prompt Structure
CJ's base prompt (e.g., `v6.0.1.yaml`) contains:
```yaml
# CJ's identity and core instructions
You are CJ, a customer support specialist...

## 📋 ACTIVE WORKFLOW: {workflow_name}

{workflow_details}

---
# Rest of base prompt
```

### 2. Runtime Assembly
When CJ is created:
1. Base prompt is loaded from YAML
2. Workflow content is loaded from workflow YAML
3. They're combined via simple template substitution
4. Result: `base prompt + workflow = complete prompt`

### 3. What CJ Actually Sees
```
You are CJ, a customer support specialist...

## 📋 ACTIVE WORKFLOW: SHOPIFY ONBOARDING

WORKFLOW: Shopify Onboarding
GOAL: Guide merchants through setup...
[All workflow instructions including system event handling]

---
Recent conversation: ...
```

## Implementation Steps

### Step 1: Update Workflow YAML (Only Step Needed!)

**File:** `agents/prompts/workflows/shopify_onboarding.yaml`

Add this section at the end of the workflow content:

```yaml
workflow: |
  WORKFLOW: Shopify Onboarding
  GOAL: Guide merchants through connecting Shopify and support systems
  
  ... existing workflow content ...
  
  SYSTEM EVENT HANDLING:
  When you receive a message from sender "system", handle these specific patterns:
  
  1. OAuth Completion Events:
     - Pattern: "New Shopify merchant authenticated from [store_domain]"
       Response: 
       "Perfect! I've successfully connected to your store at [store_domain].
        Give me just a moment to look around and get familiar with your setup..."
     
     - Pattern: "Returning Shopify merchant authenticated from [store_domain]"
       Response:
       "Welcome back! I've reconnected to [store_domain].
        Let me quickly refresh my memory about your store..."
  
  2. Data Loading Events:
     - Pattern: "Store insights loaded"
       Response: Share the insights naturally based on what was loaded
     
     - Pattern: "Background task completed: [task_name]"
       Response: Acknowledge and share relevant information
  
  3. Error Events:
     - Pattern: "OAuth failed: [reason]"
       Response: 
       "I had trouble connecting to your Shopify store. [reason]
        Would you like to try again? {{oauth:shopify}}"
  
  4. General System Messages:
     - For any other system message, use the context to respond naturally
     - System messages provide context updates, not user queries
     - Acknowledge important changes, ignore internal updates
```

That's it! No code changes needed. CJ already:
- Receives system messages with `sender="system"`  
- Has access to workflow instructions
- Knows how to parse patterns and respond accordingly

### Optional: Improve System Message Format (Minor Code Change)

If we want clearer system messages, update `web_platform.py`:

```python
# In web_platform.py oauth_complete handler
if is_new:
    oauth_context = f"New Shopify merchant authenticated from {shop_domain}"
else:
    oauth_context = f"Returning Shopify merchant authenticated from {shop_domain}"
```

But even this is optional - the current messages work fine with the workflow instructions.

## Why This Approach Is Superior

### 1. **Complete Prompt Transparency**
- Open `shopify_onboarding.yaml` to see ALL system event handling
- No hidden prompt mutations at runtime
- Debugging is trivial: `workflow content = what CJ sees`

### 2. **Zero Code Complexity**
- No new classes or methods
- No dynamic prompt injection
- No hidden state machines

### 3. **Workflow-Specific Control**
- Each workflow can handle system events differently
- Easy to test: just read the YAML
- Easy to modify: just edit the YAML

### 4. **Natural Language Instructions**
- CJ already understands conversational instructions
- No need for complex data structures
- Pattern matching happens naturally in the LLM

## Testing the Implementation

### 1. Update the Workflow YAML
Add the SYSTEM EVENT HANDLING section to `shopify_onboarding.yaml`

### 2. Test OAuth Flow
1. Complete Shopify OAuth
2. Observe CJ's response to the system message
3. Verify she follows the workflow instructions

### 3. Expected Behavior
```
System: "New Shopify merchant authenticated from test-store.myshopify.com"
CJ: "Perfect! I've successfully connected to your store at test-store.myshopify.com."
CJ: "Give me just a moment to look around and get familiar with your setup..."
```

## Future System Events

Adding new system events is trivial:

```yaml
SYSTEM EVENT HANDLING:
  ... existing events ...
  
  5. Support System Events:
     - Pattern: "Freshdesk connected: [account_name]"
       Response: "Excellent! I've connected to your Freshdesk account."
     
     - Pattern: "Support tickets loaded: [count] tickets"
       Response: "I can see you have [count] open support tickets. Let me analyze them..."
  
  6. Scheduled Events:
     - Pattern: "Daily summary ready for [date]"
       Response: "I've prepared your daily report for [date]. Here's what stood out..."
```

## Developer Guidelines: Prompt Transparency

### The Golden Rule
**Everything CJ sees must be visible in static files:**
1. Base prompt: `agents/prompts/cj/versions/v6.0.1.yaml`
2. Workflow prompt: `agents/prompts/workflows/shopify_onboarding.yaml`
3. Final prompt = Base + Workflow (simple concatenation)

### What NOT to Do
❌ Dynamic prompt modifications at runtime
❌ Hidden context injections
❌ Complex prompt assembly logic
❌ Runtime conditionals that change prompts

### What TO Do
✅ All instructions in YAML files
✅ Simple template variable substitution only
✅ Clear separation of base + workflow
✅ Easy to understand what CJ will do

## Workflow Transitions Extension

### The Problem
Users who are already authenticated (returning users or those who reload the page) get stuck in the onboarding workflow, leading to a poor experience where they have to go through onboarding again.

### The Solution: Workflow Transitions via System Events

Using the same system events pattern, we can enable smooth workflow transitions mid-conversation.

#### 1. Add Transition Patterns to YAMLs

**In `shopify_onboarding.yaml`:**
```yaml
SYSTEM EVENT HANDLING:
  ... existing patterns ...
  
  5. Already Authenticated Detection:
     - Pattern: "Existing session detected: [shop_domain] with workflow transition to [new_workflow]"
       Response:
       "Welcome back! I see you're already connected to [shop_domain].
        
        I'll switch to support mode so I can help you right away. How can I assist you today?"
       Note: After this response, the system will switch to the new workflow
```

**In `ad_hoc_support.yaml`:**
```yaml
SYSTEM EVENT HANDLING:
  1. Workflow Transition Arrival:
     - Pattern: "Transitioned from [previous_workflow] workflow"
       Response: Continue naturally from the context without re-introducing yourself
       Note: The user just saw your transition message, so jump right into helping
```

#### 2. Minimal Code Changes

**Add to `session_manager.py`:**
```python
def update_workflow(self, session_id: str, new_workflow: str) -> bool:
    """Update session workflow mid-conversation."""
    session = self.get_session(session_id)
    if session:
        # Update both places workflow is stored
        session.conversation.workflow = new_workflow
        session.conversation.state.workflow = new_workflow
        
        # Load new workflow data
        workflow_loader = WorkflowLoader()
        workflow_data = workflow_loader.load_workflow(new_workflow)
        if workflow_data:
            session.conversation.state.workflow_details = workflow_data.get("workflow", "")
        
        logger.info(f"[WORKFLOW_SWITCH] {session_id}: {session.conversation.workflow} → {new_workflow}")
        return True
    return False
```

**Add to `web_platform.py` in start_conversation handler:**
```python
# Check if starting onboarding but already authenticated
if workflow == "shopify_onboarding" and session and session.user_id:
    # Get shop domain from session
    shop_domain = session.shop_domain or session.merchant_name or "your store"
    
    # Send transition notification
    transition_msg = f"Existing session detected: {shop_domain} with workflow transition to ad_hoc_support"
    
    # Let CJ acknowledge before switching
    await self.message_processor.process_message(
        session=session,
        message=transition_msg,
        sender="system"
    )
    
    # Update workflow after CJ responds
    self.session_manager.update_workflow(conversation_id, "ad_hoc_support")
    
    # Optional: Notify the new workflow about the transition
    await self.message_processor.process_message(
        session=session,
        message="Transitioned from shopify_onboarding workflow",
        sender="system"
    )
```

### Example Flow

```
User: [Returns to site, already authenticated as test-store.myshopify.com]
System: "Existing session detected: test-store.myshopify.com with workflow transition to ad_hoc_support"
CJ: "Welcome back! I see you're already connected to test-store.myshopify.com. I'll switch to support mode so I can help you right away. How can I assist you today?"
[Workflow switches to ad_hoc_support]
System: "Transitioned from shopify_onboarding workflow"
[CJ now operates in ad_hoc_support mode]
User: "Show me today's orders"
CJ: [Responds with order data, no re-introduction needed]
```

### General Workflow Transitions

Building on the already-authenticated pattern, we can enable general workflow transitions for any reason.

#### 1. Add Patterns to ALL Workflows

Each workflow needs two patterns: departure and arrival.

**Example for `ad_hoc_support.yaml`:**
```yaml
SYSTEM EVENT HANDLING:
  # When leaving this workflow
  - Pattern: "User requested transition to [new_workflow] workflow"
    Response: "Switching to [new_workflow] mode as requested."
  
  # When arriving at this workflow
  - Pattern: "Transitioned from [previous_workflow] workflow"
    Response: "How can I help you today?"
```

**Example for `daily_briefing.yaml`:**
```yaml
SYSTEM EVENT HANDLING:
  # When leaving this workflow
  - Pattern: "User requested transition to [new_workflow] workflow"
    Response: "I'll pause the daily briefing and switch to [new_workflow] mode."
  
  # When arriving at this workflow
  - Pattern: "Transitioned from [previous_workflow] workflow"
    Response: "Let's review your daily metrics. Here's what stands out today..."
```

#### 2. Frontend Integration - Current Problem & Elegant Fix

**Current Problematic Behavior:**
The frontend currently destroys the entire conversation when workflows change:

```typescript
// ❌ CURRENT BAD PATTERN in SlackChat.tsx
setChatConfig(prev => ({ 
  ...prev, 
  workflow: newWorkflow,
  conversationId: uuidv4() // 🚨 NEW ID = NEW CONVERSATION = LOST CONTEXT
}));
```

This causes:
- WebSocket disconnection/reconnection
- New backend session creation
- Complete loss of conversation history
- Poor user experience

**Elegant Fix Following North Stars:**

```typescript
// ✅ NEW ELEGANT PATTERN in SlackChat.tsx

const handleWorkflowChange = useCallback((newWorkflow: string) => {
  // Don't change if already in target workflow
  if (newWorkflow === chatConfig.workflow) {
    return;
  }
  
  // Keep same conversation, just transition workflows
  if (wsChat.isConnected) {
    // Send transition request to backend
    wsChat.sendWorkflowTransition(newWorkflow);
    
    // Update local state ONLY - keep same conversationId
    setChatConfig(prev => ({ 
      ...prev, 
      workflow: newWorkflow
      // NO conversationId change! Context preserved by backend
    }));
  } else {
    // Only if not connected, update config for next connection
    setChatConfig(prev => ({ 
      ...prev, 
      workflow: newWorkflow
    }));
  }
}, [chatConfig.workflow, wsChat]);

// In useWebSocketChat.ts - add this method
const sendWorkflowTransition = useCallback((newWorkflow: string) => {
  if (wsRef.current?.readyState === WebSocket.OPEN) {
    const message = JSON.stringify({
      type: 'workflow_transition',
      data: {
        new_workflow: newWorkflow,
        user_initiated: true
      }
    });
    wsRef.current.send(message);
    wsLogger.info('Sent workflow transition request', { newWorkflow });
  }
}, []);

// Handle backend's workflow_updated response
case 'workflow_updated':
  const { workflow: updatedWorkflow, previous } = wsData.data;
  wsLogger.info('Workflow updated by backend', { 
    from: previous, 
    to: updatedWorkflow 
  });
  // Optionally update any UI state here
  break;
```

**URL Parameter Handling:**
```typescript
// Watch for query string changes but DON'T recreate conversation
useEffect(() => {
  const workflowParam = searchParams.get('workflow');
  if (workflowParam && workflowParam !== chatConfig.workflow) {
    handleWorkflowChange(workflowParam); // Uses transition, not recreation
  }
}, [searchParams, chatConfig.workflow, handleWorkflowChange]);
```

**Key Design Principles:**
1. **Backend-Driven**: Frontend just requests, backend decides what happens
2. **Preserve Context**: Same conversationId = same context
3. **Simple State**: Only update workflow field, nothing else
4. **No Reconnection**: WebSocket stays connected throughout

#### 3. Backend Handler

**Add to `web_platform.py`:**
```python
elif message_type == "workflow_transition":
    transition_data = data.get("data", {})
    new_workflow = transition_data.get("new_workflow")
    
    # Validate workflow exists
    workflow_loader = WorkflowLoader()
    if not workflow_loader.workflow_exists(new_workflow):
        await self._send_error(websocket, f"Unknown workflow: {new_workflow}")
        return
    
    # Get current workflow for context
    current_workflow = session.conversation.workflow
    
    # Don't transition if already in target workflow
    if current_workflow == new_workflow:
        logger.info(f"[WORKFLOW] Already in {new_workflow}, skipping transition")
        return
    
    # Send transition announcement to current workflow
    if transition_data.get("user_initiated"):
        transition_msg = f"User requested transition to {new_workflow} workflow"
    else:
        transition_msg = f"System requested transition to {new_workflow} workflow"
    
    # Let current workflow say goodbye
    await self.message_processor.process_message(
        session=session,
        message=transition_msg,
        sender="system"
    )
    
    # Update the workflow
    success = self.session_manager.update_workflow(conversation_id, new_workflow)
    if not success:
        await self._send_error(websocket, "Failed to update workflow")
        return
    
    # Let new workflow say hello
    arrival_msg = f"Transitioned from {current_workflow} workflow"
    await self.message_processor.process_message(
        session=session,
        message=arrival_msg,
        sender="system"
    )
    
    # Notify frontend of successful transition
    await websocket.send_json({
        "type": "workflow_updated",
        "data": {
            "workflow": new_workflow,
            "previous": current_workflow
        }
    })
```

### Other Use Cases This Enables

1. **Crisis Detection**
   ```yaml
   Pattern: "Crisis detected: [metric] exceeded threshold with workflow transition to crisis_response"
   Response: "I've detected an urgent situation with your [metric]. Let me help you address this immediately."
   ```

2. **Natural Language Requests**
   ```python
   # In message processing, detect workflow requests
   if "show me daily metrics" in message.lower():
       # Trigger transition to daily_briefing
   ```

3. **Scheduled Transitions**
   ```yaml
   Pattern: "Scheduled transition to [workflow_name] at [time]"
   Response: "It's time for your [workflow_name]. Let's get started."
   ```

## Summary

Phase 4.6 now includes comprehensive system event handling and workflow transitions:

### Components

1. **System Events** (30 minutes) ✅
   - OAuth completion responses
   - Error handling patterns
   - Future event placeholders

2. **Workflow Transitions** (90 minutes total)
   
   **2a. Already-Authenticated Detection** (40 minutes)
   - Auto-transition from onboarding → ad_hoc_support
   - Natural acknowledgment of existing session
   - Smooth user experience for returning users
   
   **2b. General Workflow Transitions** (50 minutes)
   - User-initiated transitions via UI or query string
   - System-initiated transitions (crisis, scheduling)
   - Natural departure/arrival acknowledgments
   - Frontend workflow selector integration

### Total Implementation

**Backend (Completed):**
- **Time**: ~2 hours
- **Code Changes**: ~180 lines
- **YAML Changes**: ~105 lines across 6 workflows
- **Status**: ✅ Fully implemented and tested

**Frontend (Required):**
- **Time**: ~30 minutes
- **Code Changes**: ~40 lines total
  - Remove conversationId regeneration: -4 lines
  - Add sendWorkflowTransition method: +15 lines
  - Update handleWorkflowChange: +20 lines
  - Add workflow_updated handler: +9 lines
- **Benefits**: 
  - Preserves conversation context
  - No WebSocket reconnection
  - Smooth user experience
  - Backend controls transition behavior

The implementation maintains our principle of prompt transparency - all transition behavior is visible in the workflow YAMLs, with minimal supporting code to handle the mechanics.

## Success Criteria

**Backend (Completed):**
- [x] CJ responds naturally to OAuth completion
- [x] No code complexity added for basic events
- [x] Full prompt transparency maintained
- [x] Already-authenticated users skip onboarding automatically
- [x] Backend supports workflow transitions via messages
- [x] CJ acknowledges all transitions naturally
- [x] Session manager preserves conversation context
- [x] Backend sends workflow_updated notifications
- [x] Easy to extend with new events
- [x] Developers can understand behavior by reading YAML

**Frontend (Pending):**
- [ ] Workflow dropdown sends transition messages (not new conversations)
- [ ] Same conversationId maintained across workflow changes
- [ ] WebSocket connection stays open during transitions
- [ ] Frontend handles workflow_updated messages
- [ ] Query string changes trigger transitions (not recreations)
- [ ] User sees smooth transition with context preserved