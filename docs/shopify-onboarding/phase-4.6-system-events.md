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
       Response: "I've prepared your daily summary for [date]. Here's what stood out..."
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

## Summary

Phase 4.6 transforms system event handling from a complex architectural change to a simple YAML update:

1. **Implementation Time**: 30 minutes (just YAML editing)
2. **Code Changes**: Zero (optional message format improvement)
3. **Testing**: Manual verification that CJ follows instructions
4. **Benefits**: Full transparency, zero complexity, immediate results

The entire "system events architecture" is really just adding clear instructions to the workflow about how to handle system messages. CJ already has all the capabilities needed - we just need to tell her what to do.

## Success Criteria

- [x] CJ responds naturally to OAuth completion
- [x] No code complexity added
- [x] Full prompt transparency maintained
- [x] Easy to extend with new events
- [x] Developers can understand behavior by reading YAML