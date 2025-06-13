# Dev Workflow Selector Fix

## Problem
After removing `handleWorkflowChange` to implement backend-driven workflow state, the workflow selector dropdown broke with:
```
Uncaught ReferenceError: handleWorkflowChange is not defined
```

## Solution
Replaced the complex workflow transition logic with a simple dev-friendly approach:

```tsx
onChange={(e) => {
  const newWorkflow = e.target.value as WorkflowType;
  // Update local state
  setChatConfig(prev => ({ ...prev, workflow: newWorkflow }));
  // Update URL 
  const params = new URLSearchParams(window.location.search);
  params.set('workflow', newWorkflow);
  window.history.replaceState({}, '', `${window.location.pathname}?${params.toString()}`);
  // Trigger reconnect with new workflow
  window.location.reload();
}}
```

## Why This Works
1. **Simple**: Just update state and reload - no complex transition logic
2. **Clean State**: Page reload ensures fresh start with new workflow
3. **Backend-Driven**: On reload, frontend sends the new workflow in `start_conversation`
4. **Dev-Friendly**: Quick way to test different workflows

## Additional Fixes
- Imported `WORKFLOW_NAMES` from constants file instead of duplicate definition
- Removed duplicate `WORKFLOW_NAMES` object from SlackChat.tsx
- This ensures all workflows (including `shopify_post_auth`) appear in dropdown

## Usage
1. Select a workflow from dropdown
2. Page reloads with new workflow
3. Backend receives the workflow in `start_conversation`
4. Backend decides whether to honor it based on session state