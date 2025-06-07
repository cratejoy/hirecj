# Phase 4.6.6: Complete Workflow-Driven Requirements

## Overview

Phase 4.6.5 successfully implemented the backend portion of workflow-driven requirements, moving workflow configuration into YAML files. However, the frontend implementation was skipped, and several backend services still contain hardcoded workflow checks. This phase completes the implementation to achieve truly workflow-driven architecture with zero hardcoded workflow logic.

## Current State

### ✅ What Was Accomplished in Phase 4.6.5

1. **YAML Configuration**
   - Added `requirements` section to all 6 workflow YAMLs
   - Added `behavior` section to all 6 workflow YAMLs
   - Defined initial actions, transitions, and requirements per workflow

2. **Backend Infrastructure**
   - Updated `WorkflowLoader` with:
     - `get_workflow_requirements()` method
     - `get_workflow_behavior()` method
   - Updated `web_platform.py` to:
     - Use YAML requirements for validation and defaults
     - Send `workflow_requirements` to frontend in `conversation_started` message
     - Replace hardcoded initial messages with behavior-driven logic
     - Replace hardcoded transitions with YAML configuration

### ❌ What Remains Hardcoded

#### Frontend Files

1. **`homepage/src/pages/SlackChat.tsx`** (line 120-125)
   ```typescript
   const isRealChat = useMemo(() =>
       !showConfigModal && !!chatConfig.conversationId && !!chatConfig.workflow && 
       // For onboarding and support_daily workflows, we don't need merchantId/scenarioId initially
       (chatConfig.workflow === 'shopify_onboarding' || chatConfig.workflow === 'support_daily' || (!!chatConfig.scenarioId && !!chatConfig.merchantId)),
       [showConfigModal, chatConfig]
   );
   ```

2. **`homepage/src/hooks/useWebSocketChat.ts`**
   - Lines 161-166: Hardcoded connection key logic
   ```typescript
   // For onboarding and support_daily workflows, we don't need merchant/scenario
   if (workflow === 'shopify_onboarding' || workflow === 'support_daily') {
       const key = `${conversationId}`;
       wsLogger.info('Connection key for ${workflow}', { key });
       return key;
   }
   ```
   - Lines 469-470: Hardcoded default values in `start_conversation`

#### Backend Files

1. **`agents/app/services/message_processor.py`** (line 184)
   ```python
   # Only parse UI components if workflow has them enabled
   if session.conversation.workflow == "shopify_onboarding":
       from app.services.ui_components import UIComponentParser
       parser = UIComponentParser()
   ```

2. **`agents/app/agents/cj_agent.py`**
   - Line 108: Onboarding context
   ```python
   if self.workflow_name == "shopify_onboarding":
       onboarding_context = self._extract_onboarding_context()
   ```
   - Line 151: Database tools
   ```python
   if self.workflow_name == "support_daily":
       tools.extend([...database_tools...])
   ```

3. **`agents/app/cache_warming.py`** (line 173)
   ```python
   if workflow_id not in ["daily_briefing", "weekly_review"]:
       # Skip non-CJ initiated workflows
   ```

## Implementation Plan

### Task 1: Frontend Implementation (1 hour)

#### 1.1 Update SlackChat.tsx

**File**: `homepage/src/pages/SlackChat.tsx`

**Changes**:
1. Add state for workflow requirements:
   ```typescript
   const [workflowRequirements, setWorkflowRequirements] = useState<Record<string, any>>({});
   ```

2. Replace `isRealChat` with `canConnect`:
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

3. Update all references from `isRealChat` to `canConnect`

4. Pass requirements callback to WebSocket hook:
   ```typescript
   onRequirementsReceived: (reqs) => {
       console.log('[SlackChat] Received workflow requirements:', reqs);
       setWorkflowRequirements(reqs);
   }
   ```

#### 1.2 Update useWebSocketChat.ts

**File**: `homepage/src/hooks/useWebSocketChat.ts`

**Changes**:
1. Add callback prop:
   ```typescript
   interface UseWebSocketChatProps {
       // ... existing props
       onRequirementsReceived?: (requirements: Record<string, any>) => void;
   }
   ```

2. Remove hardcoded connection key logic:
   ```typescript
   // DELETE the hardcoded check
   // REPLACE WITH:
   const key = `${conversationId}-${merchantId || 'none'}-${scenario || 'none'}`;
   wsLogger.info('Connection key computed', { key, workflow });
   return key;
   ```

3. Handle requirements in `conversation_started`:
   ```typescript
   case 'conversation_started':
       // ... existing code
       if (data.data.workflow_requirements && onRequirementsReceived) {
           onRequirementsReceived(data.data.workflow_requirements);
       }
       break;
   ```

4. Remove hardcoded defaults in start_conversation message

### Task 2: Backend Cleanup (30 min)

#### 2.1 Update message_processor.py

**File**: `agents/app/services/message_processor.py`

**Change**: Use workflow configuration instead of hardcoded check
```python
# Load workflow to check UI components
workflow_loader = WorkflowLoader()
workflow_data = workflow_loader.get_workflow(session.conversation.workflow)

# Only parse UI components if workflow has them enabled
if workflow_data.get('ui_components', {}).get('enabled', False):
    from app.services.ui_components import UIComponentParser
    parser = UIComponentParser()
```

#### 2.2 Update cj_agent.py

**File**: `agents/app/agents/cj_agent.py`

**Changes**:
1. Load workflow configuration in `__init__`:
   ```python
   self.workflow_loader = WorkflowLoader()
   self.workflow_config = self.workflow_loader.get_workflow(workflow_name)
   ```

2. Replace onboarding context check:
   ```python
   # Use workflow config instead of hardcoded check
   if self.workflow_config.get('behavior', {}).get('extract_onboarding_context', False):
       onboarding_context = self._extract_onboarding_context()
   ```

3. Replace database tools check:
   ```python
   # Check workflow config for tool availability
   if self.workflow_config.get('tools', {}).get('database_enabled', False):
       tools.extend([...database_tools...])
   ```

#### 2.3 Update cache_warming.py

**File**: `agents/app/cache_warming.py`

**Change**: Use workflow configuration
```python
# Load workflows to check cache warming config
workflow_loader = WorkflowLoader()
cj_initiated_workflows = []
for workflow_name in workflow_loader.list_workflows():
    workflow_data = workflow_loader.get_workflow(workflow_name)
    if workflow_data.get('cache_warming', {}).get('cj_initiated', False):
        cj_initiated_workflows.append(workflow_name)

# Use the dynamic list
if workflow_id not in cj_initiated_workflows:
    # Skip non-CJ initiated workflows
```

### Task 3: Enhanced YAML Configuration (30 min)

#### 3.1 Update support_daily.yaml

Add tools configuration:
```yaml
tools:
  database_enabled: true
  available:
    - get_recent_ticket_from_db
    - get_support_dashboard_from_db
    - search_tickets_in_db
```

#### 3.2 Update shopify_onboarding.yaml

Already has `ui_components` section, add behavior flag:
```yaml
behavior:
  initiator: "cj"
  extract_onboarding_context: true  # NEW
  initial_action:
    type: "process_message"
    # ... rest remains same
```

#### 3.3 Update daily_briefing.yaml and weekly_review.yaml

Add cache warming configuration:
```yaml
cache_warming:
  cj_initiated: true
  refresh_interval: 3600  # 1 hour in seconds
```

## Success Criteria

1. **Zero Hardcoded Workflow Names**: No workflow names in conditional logic anywhere
2. **Frontend Uses Backend Requirements**: Frontend validates based on requirements from backend
3. **All Behavior in YAML**: Tool availability, UI components, cache warming all configured in YAML
4. **Consistent Connection Logic**: Same connection key format for all workflows
5. **Clean Codebase**: No `if workflow === 'shopify_onboarding'` type checks

## Testing

1. **Frontend Connection Tests**:
   - Verify shopify_onboarding connects without merchant/scenario
   - Verify ad_hoc_support requires both merchant and scenario
   - Verify support_daily connects with just merchant

2. **Backend Behavior Tests**:
   - Verify UI components only parse for workflows with `ui_components.enabled: true`
   - Verify database tools only available for workflows with `tools.database_enabled: true`
   - Verify cache warming only runs for workflows with `cache_warming.cj_initiated: true`

3. **New Workflow Test**:
   - Create a new test workflow YAML
   - Verify it works without any code changes

## Benefits

1. **True Single Source of Truth**: YAML files define ALL workflow behavior
2. **Zero Code Changes for New Workflows**: Just create a YAML file
3. **Self-Documenting**: Workflow behavior visible in YAML
4. **Consistent Architecture**: Backend drives all decisions
5. **Maintainable**: No scattered hardcoded checks to update

## Timeline

- Frontend Implementation: 1 hour
- Backend Cleanup: 30 minutes  
- YAML Configuration: 30 minutes
- Testing: 30 minutes (optional but recommended)

**Total: 2 hours** (2.5 hours with testing)