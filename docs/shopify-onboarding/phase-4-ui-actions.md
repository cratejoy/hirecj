# Phase 4: UI Actions Pattern - Implementation Guide

## 🎯 Phase Objectives

Implement a clean, extensible pattern for CJ to trigger UI elements (buttons, choices, confirmations) that works across different frontends (web, Slack, etc.) without relying on message parsing or JSON responses.

**North Star Principles Applied:**
- **Simplify**: Use existing tool patterns CJ already knows
- **No Cruft**: No magic strings or regex parsing  
- **Backend-Driven**: CJ decides what UI to show, frontend decides how
- **Single Source of Truth**: UI action definitions in one place
- **Long-term Elegance**: Pattern works for any frontend platform

## 🔬 Research & Rationale

Based on research in [`notes/interactive_ui_elements.md`](../../../notes/interactive_ui_elements.md), the current best practices for LLM-driven UI include:

### Key Findings:
1. **Tool/Function-Based UI Actions** are more reliable than markup (AI Rabbit, 2024)
2. **Non-blocking patterns** prevent deadlocks in real-time systems (Chainlit docs)
3. **Platform abstraction** allows same agent code for multiple UIs (LangChain Slack toolkit)
4. **Structured communication** between LLM and UI ensures reliability (OpenAI community, 2024)

### Why Not Alternative Approaches:

**❌ Magic Strings/Markup**
- Fragile parsing required
- LLMs can malform the syntax
- Different syntax for each platform
- Mixes presentation with content

**❌ JSON Mode Responses**
- CJ would need to switch between text and JSON
- Risk of malformed JSON with backticks or explanations
- Unnatural conversation flow

**✅ Our Approach: Fire-and-Forget Tools**
- Uses existing CrewAI tool patterns
- No blocking or deadlocks
- Clean separation of concerns
- Natural conversation flow

## 📋 Implementation Steps

### 1. Create UI Action Tools

Create non-blocking tools that CJ can call to trigger UI elements:

```python
# agents/app/agents/ui_tools.py
"""
UI Action Tools for CJ

These tools allow CJ to trigger UI elements in the frontend.
They are "fire-and-forget" - they complete immediately without blocking.
"""

from typing import List, Optional
from crewai_tools import tool

@tool("show_oauth_button")
def show_oauth_button(provider: str, context: Optional[str] = None) -> str:
    """
    Request OAuth connection button to be shown.
    
    Args:
        provider: OAuth provider name (shopify, freshdesk, zendesk)
        context: Optional explanation of why connection is needed
        
    Returns:
        Confirmation that button will be shown (non-blocking)
    """
    return f"[OAuth button for {provider} will be displayed]"

@tool("offer_choices") 
def offer_choices(options: List[str], question: str) -> str:
    """
    Show multiple choice buttons to the user.
    
    Args:
        options: List of choices to present as buttons
        question: The question being asked
        
    Returns:
        Confirmation that choices will be shown (non-blocking)
    """
    return f"[Choice buttons will be displayed with {len(options)} options]"

@tool("request_confirmation")
def request_confirmation(question: str, yes_text: str = "Yes", no_text: str = "No") -> str:
    """
    Show confirmation dialog with yes/no buttons.
    
    Args:
        question: What to confirm
        yes_text: Text for yes button (default: "Yes")
        no_text: Text for no button (default: "No")
        
    Returns:
        Confirmation that dialog will be shown (non-blocking)
    """
    return "[Confirmation dialog will be displayed]"

@tool("show_form")
def show_form(fields: List[dict], title: str) -> str:
    """
    Show a form with multiple input fields.
    
    Args:
        fields: List of field definitions [{name, type, label, required}]
        title: Form title
        
    Returns:
        Confirmation that form will be shown (non-blocking)
    """
    return f"[Form '{title}' with {len(fields)} fields will be displayed]"

# Export tools for CJ to use
UI_TOOLS = [
    show_oauth_button,
    offer_choices,
    request_confirmation,
    show_form
]
```

### 2. Update CJ Agent to Include UI Tools

```python
# agents/app/agents/cj_agent.py

def _load_tools(self) -> List[Any]:
    """Load appropriate tools based on data agent."""
    tools = []
    
    # Existing data tools
    if self.data_agent:
        # ... existing tool loading ...
        
    # Add UI tools for web/interactive platforms
    if self.platform_type in ["web", "slack"]:
        from app.agents.ui_tools import UI_TOOLS
        tools.extend(UI_TOOLS)
        logger.info(f"[CJ_AGENT] Loaded {len(UI_TOOLS)} UI action tools")
    
    return tools
```

### 3. Tool Call Interceptor

Create a service to detect and extract UI tool calls:

```python
# agents/app/services/ui_action_handler.py
"""
UI Action Handler

Intercepts UI tool calls from CJ and converts them to frontend messages.
"""

from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class UIActionHandler:
    """Handles UI action tool calls from agents."""
    
    # Set of UI tool names we intercept
    UI_TOOL_NAMES = {
        "show_oauth_button",
        "offer_choices",
        "request_confirmation",
        "show_form"
    }
    
    def extract_ui_actions(self, tool_calls: List[Any]) -> List[Dict[str, Any]]:
        """
        Extract UI actions from tool calls.
        
        Args:
            tool_calls: List of tool calls from agent execution
            
        Returns:
            List of UI action dictionaries
        """
        ui_actions = []
        
        for call in tool_calls:
            if hasattr(call, 'name') and call.name in self.UI_TOOL_NAMES:
                action = {
                    "action": call.name,
                    "data": call.args if hasattr(call, 'args') else {},
                    "id": str(getattr(call, 'id', None) or hash(call))
                }
                ui_actions.append(action)
                logger.info(f"[UI_ACTION] Extracted {call.name} action")
        
        return ui_actions
    
    def should_wait_for_response(self, action: str) -> bool:
        """
        Determine if an action expects a user response.
        
        Some actions like forms or choices expect input back,
        while others like notifications don't.
        """
        return action in ["offer_choices", "request_confirmation", "show_form"]
```

### 4. Update Message Processor

Modify the message processor to handle UI actions:

```python
# agents/app/services/message_processor.py

async def _get_cj_response(self, session, message: str, is_system: bool = False):
    """Get response from CJ agent with UI action handling."""
    
    # Get CJ's response and any tool calls
    response = await session.agent.arun(message)
    
    # Extract any UI actions from tool calls
    ui_actions = []
    if hasattr(session.agent, '_last_tool_calls'):
        ui_handler = UIActionHandler()
        ui_actions = ui_handler.extract_ui_actions(session.agent._last_tool_calls)
    
    # Return both response and UI actions
    return {
        "content": response,
        "ui_elements": ui_actions
    }
```

### 5. WebSocket Protocol Update

Update the WebSocket handler to send UI elements with messages:

```python
# agents/app/platforms/web_platform.py

async def send_message(self, message: OutgoingMessage) -> bool:
    """Send message with optional UI elements."""
    
    # Check if message has UI elements
    if isinstance(message.content, dict) and "ui_elements" in message.content:
        # Send structured message with UI elements
        data = {
            "type": "message",
            "data": {
                "sender": message.sender,
                "content": message.content["content"],
                "timestamp": message.timestamp,
                "ui_elements": message.content["ui_elements"]
            }
        }
    else:
        # Regular text message
        data = {
            "type": "message", 
            "data": {
                "sender": message.sender,
                "content": str(message.content),
                "timestamp": message.timestamp
            }
        }
    
    await self.websocket.send_json(data)
    return True
```

### 6. Frontend UI Element Renderer

Update the frontend to render UI elements embedded in messages:

```typescript
// homepage/src/components/MessageContent.tsx
import React from 'react';
import ReactMarkdown from 'react-markdown';
import { ShopifyOAuthButton } from './ShopifyOAuthButton';
import { ChoiceButtons } from './ChoiceButtons';
import { ConfirmationDialog } from './ConfirmationDialog';

interface UIElement {
  action: string;
  data: any;
  id: string;
}

interface MessageContentProps {
  content: string;
  ui_elements?: UIElement[];
  conversationId: string;
  onUIAction?: (action: string, data: any) => void;
}

export const MessageContent: React.FC<MessageContentProps> = ({
  content,
  ui_elements,
  conversationId,
  onUIAction
}) => {
  const renderUIElement = (element: UIElement) => {
    switch (element.action) {
      case 'show_oauth_button':
        return (
          <ShopifyOAuthButton
            key={element.id}
            conversationId={conversationId}
            provider={element.data.provider}
            onComplete={(result) => onUIAction?.('oauth_complete', result)}
          />
        );
        
      case 'offer_choices':
        return (
          <ChoiceButtons
            key={element.id}
            options={element.data.options}
            question={element.data.question}
            onSelect={(choice) => onUIAction?.('choice_selected', { choice })}
          />
        );
        
      case 'request_confirmation':
        return (
          <ConfirmationDialog
            key={element.id}
            question={element.data.question}
            yesText={element.data.yes_text}
            noText={element.data.no_text}
            onConfirm={(confirmed) => onUIAction?.('confirmation', { confirmed })}
          />
        );
        
      default:
        return null;
    }
  };
  
  return (
    <div>
      <div className="text-sm prose prose-sm max-w-none prose-invert">
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>
      
      {ui_elements && ui_elements.length > 0 && (
        <div className="mt-4 space-y-2">
          {ui_elements.map(renderUIElement)}
        </div>
      )}
    </div>
  );
};
```

### 7. Update CJ's Prompts

Add instructions for using UI tools in appropriate contexts:

```yaml
# agents/prompts/workflows/shopify_onboarding.yaml

# Add to workflow instructions:
UI INTERACTION GUIDELINES:
- Use show_oauth_button tool when ready for Shopify connection
- Don't say "click the button below" - the tool handles display
- Continue conversation naturally after calling UI tools
- For choices, use offer_choices instead of numbered lists

EXAMPLE OAUTH FLOW:
CJ: "I'll need to connect to your Shopify store to analyze your data."
[Call: show_oauth_button(provider="shopify", context="To analyze support patterns")]
CJ: "Once connected, I'll be able to show you insights about..."
[User completes OAuth]
CJ: "Perfect! I can now see your store data..."
```

### 8. Platform Adaptations

#### Slack Implementation
```python
# agents/app/platforms/slack_platform.py

async def format_ui_elements_for_slack(self, ui_elements: List[dict]) -> List[dict]:
    """Convert UI elements to Slack Block Kit format."""
    blocks = []
    
    for element in ui_elements:
        if element["action"] == "show_oauth_button":
            blocks.append({
                "type": "actions",
                "elements": [{
                    "type": "button",
                    "text": {"type": "plain_text", "text": f"Connect {element['data']['provider'].title()}"},
                    "url": f"{settings.auth_url}/oauth/{element['data']['provider']}/authorize",
                    "action_id": f"oauth_{element['data']['provider']}"
                }]
            })
            
        elif element["action"] == "offer_choices":
            buttons = []
            for i, option in enumerate(element["data"]["options"]):
                buttons.append({
                    "type": "button",
                    "text": {"type": "plain_text", "text": option},
                    "value": option,
                    "action_id": f"choice_{i}"
                })
            blocks.append({
                "type": "actions",
                "elements": buttons
            })
    
    return blocks
```

## 🧪 Testing Strategy

### Unit Tests
```python
# tests/test_ui_tools.py
def test_show_oauth_button():
    result = show_oauth_button(provider="shopify", context="test")
    assert "shopify" in result
    assert "displayed" in result

def test_ui_action_extraction():
    handler = UIActionHandler()
    mock_calls = [MockToolCall(name="show_oauth_button", args={"provider": "shopify"})]
    actions = handler.extract_ui_actions(mock_calls)
    assert len(actions) == 1
    assert actions[0]["action"] == "show_oauth_button"
```

### Integration Tests
1. Test CJ can call UI tools during conversation
2. Test UI elements appear in WebSocket messages
3. Test frontend renders UI elements correctly
4. Test Slack formatting works

### Manual Testing Flow
1. Start conversation with CJ
2. Progress to Shopify connection point
3. Verify OAuth button appears in message
4. Complete OAuth flow
5. Verify CJ continues appropriately

## 🏗️ Architecture Benefits

### 1. **No Blocking**
- CJ completes responses without waiting
- UI elements are "fire-and-forget"
- No WebSocket thread deadlocks

### 2. **Clean Separation**
- CJ decides WHAT to show (tool call)
- Frontend decides HOW to show it (rendering)
- Platform adapters handle platform-specific formatting

### 3. **Extensibility**
Easy to add new UI elements:
```python
@tool("show_progress_bar")
def show_progress_bar(percent: int, label: str) -> str:
    """Show a progress indicator."""
    return "[Progress bar will be displayed]"
```

### 4. **Reliability**
- Tool calls are structured and validated
- No regex parsing or magic strings
- Type safety with tool parameters

## 🚀 Future Enhancements

1. **Stateful UI Elements**
   - Progress bars that update
   - Forms that validate in real-time
   - Multi-step wizards

2. **Rich Media**
   - Image carousels
   - Charts and graphs
   - Video embeds

3. **Advanced Interactions**
   - Drag and drop
   - Date/time pickers
   - File uploads

4. **Context Preservation**
   - Remember which UI elements were shown
   - Allow CJ to reference previous choices
   - Support "undo" operations

## 📚 References

1. AI Rabbit, "LLM ChatBots 3.0: Merging LLMs with Dynamic UI Elements," Oct 2024
2. Chainlit Documentation, "Actions and Callbacks," chainlit.io
3. OpenAI Developer Community, "GPT function calling and showing results in UI," 2024
4. Dharmesh Shah, "Beyond Chat: Blending UI for an AI World," May 2025
5. LangChain Slack Toolkit Documentation
6. Slack Block Kit UI Framework Documentation

## ✅ Success Criteria

Phase 4 is complete when:
- [ ] UI tools are implemented and available to CJ
- [ ] Tool calls are intercepted and converted to UI elements
- [ ] Frontend renders UI elements within messages
- [ ] OAuth button appears when CJ calls the tool
- [ ] Pattern works for both web and Slack
- [ ] No blocking or deadlock issues
- [ ] CJ can naturally incorporate UI elements in conversation

## 🔑 Key Principles

1. **Tools Over Text**: CJ uses tools, not magic strings
2. **Non-Blocking**: UI actions complete immediately
3. **Platform Agnostic**: Same CJ code, different renderers
4. **User Control**: Frontend owns the actual UI implementation
5. **Natural Flow**: Conversation continues without interruption

This pattern sets the foundation for rich, interactive AI conversations while maintaining the simplicity and reliability our North Star principles demand.