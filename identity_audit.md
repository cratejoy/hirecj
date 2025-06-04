# HireCJ Debug System Audit & Proposal

## Current State Analysis

### 1. Available State Data

#### Session Manager (`session_manager.py`)
- **Session ID**: Unique identifier for each session
- **Conversation Data**: Full conversation object with messages
- **Merchant Info**: `merchant_name`, `scenario_name`
- **Universe Data Agent**: Optional data agent for scenario-specific data
- **Merchant Memory**: Facts accumulated across all conversations
- **Session Metrics**: Message count, errors, response times
- **Activity Tracking**: Created/last activity timestamps, active status

#### WebSocket Platform (`web_platform.py`)
- **Connection State**: Active WebSocket connections mapped by conversation ID
- **Session Data**: IP address, user agent, session start time
- **Message Types**: Handles multiple message types (message, start_conversation, fact_check, oauth_complete, etc.)
- **Progress Callbacks**: Real-time "thinking" status updates
- **OAuth Metadata**: Authentication status, shop domain, is_new merchant flag

#### Message Processor (`message_processor.py`)
- **Conversation Context**: Last 10 messages in context window
- **Progress Events**: Thinking status (initializing, generating)
- **LLM Prompts**: Full prompt sent to CJ including chat history
- **Response Tracking**: Execution time, error counts
- **UI Components**: Parsed UI elements (OAuth buttons, etc.)
- **Background Tasks**: Fact extraction running asynchronously

### 2. CJ's Internal State

#### CJ Agent (`cj_agent.py`)
- **Model Configuration**: Model name, provider, caching status
- **Prompt Template**: Loaded from version-specific prompt files
- **Workflow Data**: Current workflow configuration and details
- **Conversation History**: Formatted recent messages (truncated for context)
- **Available Tools**: Universe data tools loaded based on scenario
- **Memory Facts**: All merchant facts available to CJ
- **OAuth Context**: Authentication status and merchant type (new/returning)

### 3. Frontend Capabilities

#### Current Implementation (`SlackChat.tsx`)
- **Basic State**: Messages array, typing indicator, connection status
- **Configuration**: Scenario, merchant, workflow selection
- **OAuth Handling**: Success/error callbacks, status updates
- **Toast Notifications**: Error and success messages
- **No Debug Features**: Currently no debug panel or state inspection

## Proposed Debug Panel System

### Design Principles
1. **Non-intrusive**: Hidden by default, doesn't affect normal UX
2. **Real-time Updates**: Live state changes via WebSocket
3. **Developer-friendly**: Clear organization, searchable/filterable
4. **Production-ready**: Can be enabled with feature flag
5. **Elegant UI**: Matches HireCJ design language

### Debug Information Architecture

#### 1. Session & Connection Tab
```
Session ID: abc123...
Conversation ID: web_session_xyz...
Status: Connected ✓
Started: 2025-01-06 10:30:45
Last Activity: 10 seconds ago
WebSocket: Active (15 messages)
```

#### 2. Merchant Context Tab
```
Merchant: marcus_thompson
Scenario: steady_operations
Workflow: shopify_onboarding
OAuth Status: Authenticated ✓
  - Provider: Shopify
  - Shop: example.myshopify.com
  - New Merchant: Yes
  - Connected At: 2025-01-06 10:31:22
```

#### 3. CJ State Tab
```
Model: claude-3-5-sonnet-latest
Version: v1
Caching: Enabled ✓
Current Phase: OAuth complete response

Available Tools: (3)
  - get_merchant_kpis
  - get_customer_segments
  - get_recent_orders

Memory Facts: (12)
  - "Store sells outdoor gear"
  - "Primary demographic is 25-45"
  - "Ships internationally"
  [Show all...]
```

#### 4. Conversation Context Tab
```
Context Window: 10 messages
Total Messages: 25

Recent Context:
MERCHANT: Hi, I need help setting up
CJ: Hey there! Welcome to HireCJ...
MERCHANT: I run an outdoor gear store
CJ: That's awesome! Outdoor gear...
[OAuth Button Clicked]
SYSTEM: New Shopify merchant authenticated
CJ: Perfect! I can see your store...
```

#### 5. Real-time Events Tab
```
[10:31:45] WS_RECEIVE: type=message, size=45
[10:31:45] SESSION_CHECK: Found existing session
[10:31:46] CJ_THINKING: status=initializing
[10:31:46] LLM_PROMPT: 850 chars, 7 messages
[10:31:48] CJ_THINKING: status=generating
[10:31:52] LLM_RESPONSE: 245 chars
[10:31:52] UI_PARSER: Found 1 OAuth button
[10:31:52] WS_SEND: type=cj_message with UI
[10:31:58] WS_RECEIVE: type=oauth_complete
[10:31:58] OAUTH_UPDATE: merchant_id=shop_123
```

#### 6. Performance Tab
```
Session Metrics:
  Messages: 25
  Errors: 0
  Avg Response Time: 2.3s
  Total Time: 3m 45s

Last Response:
  Prompt Size: 850 chars
  Response Size: 245 chars
  Processing Time: 3.2s
  UI Elements: 1
```

### Implementation Plan

#### Backend Changes

1. **New WebSocket Message Type**: `debug_update`
```python
# In web_platform.py
async def send_debug_update(self, websocket, debug_data):
    if self.debug_enabled:  # Feature flag
        await websocket.send_json({
            "type": "debug_update",
            "data": debug_data,
            "timestamp": datetime.now().isoformat()
        })
```

2. **Debug Data Collection Points**
```python
# Add debug hooks throughout the system
self._send_debug_update("session_created", {
    "session_id": session.id,
    "merchant": session.merchant_name,
    "scenario": session.scenario_name,
    "memory_facts": len(session.merchant_memory.facts)
})
```

3. **Debug API Endpoint**
```python
@router.get("/api/debug/{conversation_id}")
async def get_debug_state(conversation_id: str):
    """Get current debug state snapshot"""
    # Collect all available debug data
    return {
        "session": session_data,
        "connection": connection_data,
        "cj_state": cj_state,
        "performance": metrics
    }
```

#### Frontend Implementation

1. **Debug Panel Component**
```typescript
// components/DebugPanel.tsx
interface DebugPanelProps {
  conversationId: string;
  isOpen: boolean;
  onClose: () => void;
}

const DebugPanel: React.FC<DebugPanelProps> = ({
  conversationId,
  isOpen,
  onClose
}) => {
  const [activeTab, setActiveTab] = useState('session');
  const debugState = useDebugState(conversationId);
  
  // Panel UI with tabs, real-time updates, etc.
};
```

2. **Debug Hook**
```typescript
// hooks/useDebugState.ts
export const useDebugState = (conversationId: string) => {
  const [debugData, setDebugData] = useState<DebugState>({});
  
  // Subscribe to debug updates via WebSocket
  // Fetch initial state
  // Handle real-time updates
  
  return debugData;
};
```

3. **Keyboard Shortcut**
```typescript
// In SlackChat.tsx
useEffect(() => {
  const handleKeyPress = (e: KeyboardEvent) => {
    if (e.metaKey && e.shiftKey && e.key === 'D') {
      setDebugPanelOpen(prev => !prev);
    }
  };
  
  window.addEventListener('keydown', handleKeyPress);
  return () => window.removeEventListener('keydown', handleKeyPress);
}, []);
```

### Debug Panel UI Mockup

```
┌─────────────────────────────────────────────────────────┐
│ Debug Panel                                         [X] │
├─────────────────────────────────────────────────────────┤
│ Session │ Merchant │ CJ State │ Context │ Events │ Perf │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Session Information                                     │
│ ───────────────────                                    │
│ ID: abc123-def456-789                                  │
│ Status: ● Connected                                     │
│ Started: 10:30:45 AM (5m ago)                         │
│ Messages: 25                                           │
│                                                         │
│ WebSocket Connection                                    │
│ ────────────────────                                   │
│ State: Active ✓                                        │
│ Latency: 45ms                                          │
│ Messages Sent: 15                                      │
│ Messages Received: 10                                  │
│                                                         │
│ [Copy Session Data] [Export Conversation]              │
└─────────────────────────────────────────────────────────┘
```

### Feature Flags & Configuration

```python
# In config.py
class Settings:
    # Debug features
    enable_debug_panel: bool = env.bool("ENABLE_DEBUG_PANEL", True)
    debug_panel_production: bool = env.bool("DEBUG_PANEL_PRODUCTION", False)
    debug_websocket_messages: bool = env.bool("DEBUG_WEBSOCKET_MESSAGES", True)
```

### Security Considerations

1. **Production Access**: Require special permission or auth token
2. **Data Sanitization**: Remove sensitive data from debug output
3. **Rate Limiting**: Prevent debug data from overwhelming the system
4. **Audit Logging**: Track who accesses debug information

### Benefits

1. **Developer Experience**
   - Instant visibility into CJ's decision-making
   - Easy debugging of conversation flow issues
   - Performance monitoring and optimization

2. **Customer Support**
   - Help debug merchant issues in real-time
   - Understand why CJ responded a certain way
   - Identify and fix conversation breakdowns

3. **Product Insights**
   - Track which tools CJ uses most
   - Identify common conversation patterns
   - Monitor OAuth success rates

### Next Steps

1. Implement backend debug data collection
2. Create WebSocket debug message protocol
3. Build frontend debug panel component
4. Add keyboard shortcuts and UI polish
5. Test with various scenarios
6. Document debug features for team

This debug system will provide unprecedented visibility into CJ's operation while maintaining the clean, simple interface that users expect.