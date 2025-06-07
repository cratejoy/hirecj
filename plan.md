# Workflow-Driven Requirements Plan

## 📊 Current Status Summary

### ✅ Completed Phases
1. **Phase 1: Foundation** - Onboarding workflow, CJ agent, OAuth button component
2. **Phase 2: Auth Flow Integration** - OAuth callbacks, shop domain identifier, context updates
3. **Phase 3.7: OAuth 2.0 Implementation** - Full OAuth flow with HMAC verification, token storage
4. **Phase 4.0: True Environment Centralization** - Single .env pattern with automatic distribution
5. **Phase 4.1: UI Actions Pattern** - Parser, workflow config, WebSocket integration
6. **Phase 4.5: User Identity & Persistence** - PostgreSQL user identity, fact storage, session management
7. **Phase 4.6: System Events Architecture** - YAML-based system event handling for OAuth responses

### 🎯 Current Priority
**Workflow-Driven Requirements** - Move all workflow requirements into YAML files, remove ALL hardcoded logic (3 hours)

### 🔜 Next Phases
- **Phase 4.7: Backend-Authoritative User Identity** - Fix user identity to be backend-only
- **Phase 5: Quick Value Demo** - Show immediate value after Shopify connection

---

## 🌟 North Star Principles

1. **Simplify, Simplify, Simplify**: Every decision should make the code simpler, not more complex
2. **No Cruft**: Remove all redundant code, validation, and unnecessary complexity
3. **Break It & Fix It Right**: No backwards compatibility shims - make breaking changes and migrate properly
4. **Long-term Elegance**: Choose performant, compiler-enforced solutions that prevent subtle bugs
5. **Backend-Driven**: Let the backend handle complexity, frontend should be a thin client
6. **Single Source of Truth**: One pattern, one way to do things, no alternatives
7. **No Over-Engineering**: Design for current needs only - no hypothetical features
8. **Thoughtful Logging & Instrumentation**: Appropriate visibility into system behavior

---

## 🔧 Workflow-Driven Requirements (Current Task)

### Problem
Workflow requirements are hardcoded in multiple places:
- Frontend has `if (workflow === 'shopify_onboarding' || workflow === 'support_daily')`
- Backend has `if workflow == "shopify_onboarding":`
- No single source of truth for what each workflow needs

### Solution
Move ALL workflow requirements into their YAML files. Zero hardcoded workflow names in code.

### Phase 1: Add Requirements to Workflow YAMLs (30 min)

**Task**: Add `requirements` section to each workflow YAML file.

**Files to update**:
- `/agents/prompts/workflows/shopify_onboarding.yaml`
- `/agents/prompts/workflows/ad_hoc_support.yaml`
- `/agents/prompts/workflows/support_daily.yaml`
- `/agents/prompts/workflows/daily_briefing.yaml`
- `/agents/prompts/workflows/weekly_review.yaml`
- `/agents/prompts/workflows/crisis_response.yaml`

**Add this section to each**:
```yaml
# shopify_onboarding.yaml
requirements:
  merchant: false      # Don't need merchant context
  scenario: false      # Don't need scenario context
  authentication: false # Can start without auth

# ad_hoc_support.yaml
requirements:
  merchant: true       # Need to know which merchant
  scenario: true       # Need business context
  authentication: true # Must be authenticated

# support_daily.yaml
requirements:
  merchant: true       # Need merchant for database queries
  scenario: false      # Don't need specific scenario
  authentication: false # Can work without auth

# daily_briefing.yaml, weekly_review.yaml, crisis_response.yaml
requirements:
  merchant: true
  scenario: true
  authentication: true
```

### Phase 2: Backend Reads & Serves Requirements (1 hour)

**Task 1**: Update WorkflowLoader to include requirements

File: `/agents/app/workflows/loader.py`
```python
def get_workflow(self, name: str) -> Dict[str, Any]:
    """Get a workflow by name."""
    if name not in self.workflows:
        available = ", ".join(self.list_workflows())
        raise ValueError(f"Workflow '{name}' not found. Available: {available}")
    
    workflow_data = self.workflows[name].copy()  # Don't modify cached version
    
    # Ensure requirements exist with sensible defaults
    if 'requirements' not in workflow_data:
        # Default: require everything (safer default)
        workflow_data['requirements'] = {
            'merchant': True,
            'scenario': True,
            'authentication': True
        }
    
    # Check if workflow enables UI components
    if workflow_data.get('ui_components', {}).get('enabled', False):
        # Add UI instructions to workflow
        ui_instructions = self._get_ui_instructions(
            workflow_data['ui_components']
        )
        workflow_data['workflow'] += f"\n\n{ui_instructions}"
    
    return workflow_data

def get_workflow_requirements(self, name: str) -> Dict[str, bool]:
    """Get just the requirements for a workflow."""
    workflow = self.get_workflow(name)
    return workflow.get('requirements', {
        'merchant': True,
        'scenario': True,
        'authentication': True
    })
```

**Task 2**: Add requirements to conversation_started message

File: `/agents/app/platforms/web_platform.py`

Add import at top:
```python
from app.workflows.loader import WorkflowLoader
```

In `__init__`:
```python
self.workflow_loader = WorkflowLoader()
```

In `handle_websocket_message`, modify conversation_started section:
```python
# Get workflow requirements
workflow_data = self.workflow_loader.get_workflow(workflow)
workflow_requirements = workflow_data.get('requirements', {})

# Send conversation started with requirements
await websocket.send_json({
    "type": "conversation_started",
    "data": {
        "conversation_id": conversation_id,
        "session_id": session.id,
        "merchant": merchant,
        "scenario": scenario,
        "workflow": workflow,
        "workflow_requirements": workflow_requirements,
        "user_id": session.user_id,
    }
})
```

**Task 3**: Remove hardcoded workflow checks

File: `/agents/app/platforms/web_platform.py`

DELETE:
```python
# For onboarding workflow, we don't require merchant/scenario upfront
workflow = start_data.get("workflow")
if workflow == "shopify_onboarding":
    merchant = start_data.get("merchant_id", "onboarding_user")
    scenario = start_data.get("scenario", "onboarding")
else:
    merchant = start_data.get("merchant_id", "demo_merchant")
    scenario = start_data.get("scenario", "normal_day")
```

REPLACE WITH:
```python
workflow = start_data.get("workflow", "ad_hoc_support")

# Get workflow requirements
workflow_data = self.workflow_loader.get_workflow(workflow)
requirements = workflow_data.get('requirements', {})

# Use requirements to determine defaults and validation
if not requirements.get('merchant', True):
    # Workflow doesn't require merchant
    merchant = start_data.get("merchant_id", "onboarding_user")
else:
    # Workflow requires merchant
    merchant = start_data.get("merchant_id")
    if not merchant:
        await self._send_error(websocket, "Merchant ID required for this workflow")
        return

if not requirements.get('scenario', True):
    # Workflow doesn't require scenario
    scenario = start_data.get("scenario", "default")
else:
    # Workflow requires scenario
    scenario = start_data.get("scenario")
    if not scenario:
        await self._send_error(websocket, "Scenario required for this workflow")
        return
```

Also DELETE any other hardcoded workflow checks like:
```python
if workflow in ["daily_briefing", "weekly_review", "ad_hoc_support", "shopify_onboarding", "support_daily"]:
```

### Phase 3: Frontend Uses Backend Requirements (1 hour)

**Task 1**: Store requirements from backend

File: `/homepage/src/hooks/useWebSocketChat.ts`

Add state for requirements:
```typescript
// Add near other refs
const workflowRequirementsRef = useRef<Record<string, any>>({});

// In message handler
case 'conversation_started':
  wsLogger.info('Conversation started', data.data);
  
  // Store workflow requirements
  if (data.data.workflow_requirements) {
    workflowRequirementsRef.current = data.data.workflow_requirements;
    wsLogger.info('Received workflow requirements:', data.data.workflow_requirements);
  }
  
  // ... rest of existing code
  break;
```

**Task 2**: Replace hardcoded workflow checks in SlackChat

File: `/homepage/src/pages/SlackChat.tsx`

Add state for requirements:
```typescript
const [workflowRequirements, setWorkflowRequirements] = useState<Record<string, any>>({});
```

DELETE:
```typescript
const isRealChat = useMemo(() =>
    !showConfigModal && !!chatConfig.conversationId && !!chatConfig.workflow && 
    // For onboarding and support_daily workflows, we don't need merchantId/scenarioId initially
    (chatConfig.workflow === 'shopify_onboarding' || chatConfig.workflow === 'support_daily' || (!!chatConfig.scenarioId && !!chatConfig.merchantId)),
    [showConfigModal, chatConfig]
);
```

REPLACE WITH:
```typescript
const canConnect = useMemo(() => {
    if (!chatConfig.conversationId || !chatConfig.workflow) return false;
    if (showConfigModal) return false;
    
    // Get requirements from backend (with safe fallback)
    const requirements = workflowRequirements[chatConfig.workflow] || {
        merchant: true,
        scenario: true
    };
    
    // Validate against requirements
    if (requirements.merchant && !chatConfig.merchantId) {
        console.warn(`[CONNECTION] ${chatConfig.workflow} requires merchant but none provided`);
        return false;
    }
    
    if (requirements.scenario && !chatConfig.scenarioId) {
        console.warn(`[CONNECTION] ${chatConfig.workflow} requires scenario but none provided`);
        return false;
    }
    
    console.log(`[CONNECTION] ${chatConfig.workflow} requirements met, can connect`);
    return true;
}, [showConfigModal, chatConfig, workflowRequirements]);
```

Update all uses of `isRealChat` to `canConnect`.

Pass requirements callback to WebSocket hook:
```typescript
const wsChat = useWebSocketChat({
    enabled: canConnect,
    conversationId: chatConfig.conversationId,
    merchantId: chatConfig.merchantId || '',
    scenario: chatConfig.scenarioId || '',
    workflow: chatConfig.workflow || 'ad_hoc_support',
    onError: handleChatError,
    onWorkflowUpdated: handleWorkflowChange,
    onRequirementsReceived: (reqs) => {
        console.log('[SlackChat] Received workflow requirements:', reqs);
        setWorkflowRequirements(reqs);
    }
});
```

**Task 3**: Remove hardcoded checks in connection key

File: `/homepage/src/hooks/useWebSocketChat.ts`

DELETE:
```typescript
// For onboarding and support_daily workflows, we don't need merchant/scenario
if (workflow === 'shopify_onboarding' || workflow === 'support_daily') {
    const key = `${conversationId}`;
    wsLogger.info('Connection key for ${workflow}', { key });
    return key;
}
```

REPLACE WITH:
```typescript
// Connection key always uses same format
// Requirements determine if we can connect, not the key format
const key = `${conversationId}-${merchantId || 'none'}-${scenario || 'none'}`;
wsLogger.info('Connection key computed', { key, workflow });
return key;
```

Add callback prop:
```typescript
interface UseWebSocketChatProps {
    // ... existing props
    onRequirementsReceived?: (requirements: Record<string, any>) => void;
}
```

Call it when requirements received:
```typescript
case 'conversation_started':
    // ... existing code
    
    if (data.data.workflow_requirements && onRequirementsReceived) {
        onRequirementsReceived(data.data.workflow_requirements);
    }
    break;
```

### Phase 4: Enhanced Debug Interface (30 min)

File: `/homepage/src/pages/SlackChat.tsx`

Update debug interface:
```typescript
why: () => {
    console.group('%c❓ Why is CJ not connected?', 'color: #FF6B6B; font-size: 14px; font-weight: bold');
    
    if (showConfigModal) {
        console.log('❌ Configuration modal is open');
    }
    
    if (!chatConfig.conversationId || !chatConfig.workflow) {
        console.log('❌ Missing basic configuration');
    }
    
    const requirements = workflowRequirements[chatConfig.workflow] || {
        merchant: true,
        scenario: true,
        authentication: true
    };
    
    console.log('📋 Workflow:', chatConfig.workflow);
    console.log('✅ Requirements:', requirements);
    console.log('📦 Current config:', {
        merchantId: chatConfig.merchantId || 'none',
        scenarioId: chatConfig.scenarioId || 'none',
        isAuthenticated: !!userSession.isConnected
    });
    
    // Check each requirement
    if (requirements.merchant && !chatConfig.merchantId) {
        console.log('❌ Missing required merchantId');
    } else if (requirements.merchant) {
        console.log('✅ Has required merchantId:', chatConfig.merchantId);
    }
    
    if (requirements.scenario && !chatConfig.scenarioId) {
        console.log('❌ Missing required scenarioId');
    } else if (requirements.scenario) {
        console.log('✅ Has required scenarioId:', chatConfig.scenarioId);
    }
    
    if (requirements.authentication && !userSession.isConnected) {
        console.log('❌ Authentication required but not connected');
    } else if (requirements.authentication) {
        console.log('✅ Authenticated:', userSession.merchantId);
    }
    
    if (canConnect) {
        console.log('✅ All requirements met! Should be connecting...');
        console.log('WebSocket state:', wsChat.connectionState);
    } else {
        console.log('❌ Cannot connect due to missing requirements');
    }
    
    console.groupEnd();
},

requirements: () => {
    console.group('%c📋 Workflow Requirements', 'color: #4CAF50; font-size: 14px; font-weight: bold');
    console.table(workflowRequirements);
    console.groupEnd();
}
```

### What Gets Deleted

1. **Frontend**:
   - All `chatConfig.workflow === 'shopify_onboarding'` checks
   - All `chatConfig.workflow === 'support_daily'` checks
   - The entire hardcoded workflow list in `isRealChat`
   - Special case handling in connection key logic

2. **Backend**:
   - All `if workflow == "shopify_onboarding":` checks
   - All hardcoded workflow lists
   - Special case merchant/scenario defaults per workflow

### Benefits

1. **Single Source of Truth**: Workflow YAMLs define their own requirements
2. **No More Hardcoding**: Zero workflow names in conditional logic
3. **Self-Documenting**: Requirements visible in workflow files
4. **Extensible**: New workflows just work by declaring requirements
5. **Backend Authority**: Frontend gets requirements from backend
6. **Better Debugging**: Clear visibility into what each workflow needs

### Success Metrics

- Zero hardcoded workflow names in code
- Adding a new workflow requires only creating a YAML file
- Debug interface clearly shows requirements vs provided values
- No silent connection failures

### Timeline: 3 hours total

1. ✅ Phase 1: Add requirements to YAMLs (30 min)
2. ✅ Phase 2: Backend parsing & serving (1 hour)
3. ✅ Phase 3: Frontend implementation (1 hour)
4. ✅ Phase 4: Debug interface (30 min)

---

## 🚀 Future Phases

### Phase 4.7: Backend-Authoritative User Identity
Fix user identity generation to be backend-only, preventing ID mismatches.

### Phase 5: Quick Value Demo
Show immediate value after Shopify connection with progressive data disclosure.

---

## 🚨 What We're NOT Building

- **No** complex state management libraries
- **No** over-abstraction of simple concepts
- **No** backwards compatibility with old hardcoded system
- **No** frontend-specific workflow knowledge
- **No** special cases or exceptions

Focus: Make workflows self-describing with their requirements in YAML.