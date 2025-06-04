# Phase 4: UI Actions Pattern - Implementation Guide

## 🎯 Phase Objectives

Implement a simple, extensible pattern for CJ to embed UI elements in conversations, starting with just the Shopify OAuth button and designed to scale as needed.

**North Star Principles Applied:**
- **Simplify**: Start with just what we need (OAuth button only)
- **No Cruft**: Simple marker syntax, no complex parsing
- **Backend-Driven**: Workflows control what UI is available
- **Single Source of Truth**: One pattern for UI elements
- **Long-term Elegance**: Easy to extend when needed

## 🔬 Research & Evolution

Based on research in [`notes/interactive_ui_elements.md`](../../../notes/interactive_ui_elements.md), we explored several approaches:

### Initial Explorations:

1. **Tool-Based Approach** 
   - ❌ Complex: Required tool execution tracking
   - ❌ Blocking issues: WebSocket thread deadlocks
   - ❌ Unclear placement: Where do UI elements go in text?

2. **JSON Response Mode**
   - ❌ Unreliable: LLMs add backticks or explanations
   - ❌ Unnatural: Switches between text and structured output

3. **Complex XML Components**
   - ❌ Over-engineered: Too much for current needs
   - ❌ Heavy: Component registry, schemas, etc.

### Our Solution: Simple Inline Markers

After exploring complex approaches, we realized the most elegant solution is the simplest:

**✅ Inline Markers** (e.g., `{{oauth:shopify}}`)
- LLM places markers exactly where UI should appear
- Simple string replacement, no complex parsing
- Familiar pattern (like template languages)
- Workflow-specific enablement
- Easy to extend with new markers

As the AI Rabbit demo (2024) showed: "Choose a format that the model can reliably produce and that won't conflict with normal output."

## 🔄 How UI Markers Work

### Simple Inline Marker Flow

Instead of complex tool orchestration, CJ simply inserts markers where UI elements should appear:

```
CJ writes: "Let me connect to your store: {{oauth:shopify}}"
     ↓
Parser: Finds {{oauth:shopify}} marker
     ↓  
Parser: Replaces with placeholder "__OAUTH_BUTTON_1__"
     ↓
WebSocket: Sends text with placeholder + UI element data
     ↓
Frontend: Renders text with OAuth button at placeholder location
```

### Why This Works Better

1. **Precise Placement**: UI appears exactly where CJ puts it
2. **No Tool Complexity**: No execution tracking or blocking issues
3. **Natural Writing**: Like using markdown or templates
4. **Simple Parsing**: Just find and replace markers
5. **LLM Friendly**: Clear, unambiguous syntax

## 📋 Implementation Steps

### 1. Create Simple UI Component Parser

Create a parser for OAuth button markers (designed to be extended later):

```python
# agents/app/services/ui_components.py
"""
UI Components for Agent Responses

Currently supports only Shopify OAuth button.
Designed to be extended when needed.
"""

import re
from typing import Dict, List, Tuple, Optional

class UIComponentParser:
    """Parse UI components from agent responses."""
    
    # For now, just one pattern
    OAUTH_PATTERN = re.compile(
        r'{{oauth:shopify}}',
        re.IGNORECASE
    )
    
    def parse_oauth_buttons(self, content: str) -> Tuple[str, List[Dict]]:
        """
        Find OAuth button markers and extract them.
        
        Args:
            content: The agent's response text
            
        Returns:
            Tuple of:
            - content_with_placeholders: Text with markers replaced by placeholders
            - ui_components: List of UI component definitions
            
        Example:
            Input: "Let's connect your store: {{oauth:shopify}}"
            Output: ("Let's connect your store: __OAUTH_BUTTON_1__", 
                    [{'id': 'oauth_1', 'type': 'oauth_button', ...}])
        """
        components = []
        
        # Find all OAuth markers
        matches = list(self.OAUTH_PATTERN.finditer(content))
        
        # Process in reverse to maintain string positions
        clean_content = content
        for i, match in enumerate(reversed(matches)):
            component_id = len(matches) - i
            placeholder = f"__OAUTH_BUTTON_{component_id}__"
            
            # Replace marker with placeholder
            start, end = match.span()
            clean_content = clean_content[:start] + placeholder + clean_content[end:]
            
            # Create component definition
            components.append({
                'id': f'oauth_{component_id}',
                'type': 'oauth_button',
                'provider': 'shopify',
                'placeholder': placeholder
            })
        
        # Return in correct order (reversed back)
        return clean_content, list(reversed(components))
    
    # Future extension example (not implemented yet):
    # def parse_choices(self, content: str) -> Tuple[str, List[Dict]]:
    #     """Parse {{choices:option1,option2,option3}} markers."""
    #     pass

### 2. Workflow-Specific UI Enablement

Enable UI components at the workflow level to control what's available:

```python
# agents/app/workflows/loader.py (update existing)

class WorkflowLoader:
    """Load workflow definitions with UI component support."""

    def get_workflow(self, workflow_name: str) -> Dict[str, Any]:
        """Load workflow configuration."""
        # ... existing loading logic ...

        workflow_data = self._load_yaml(workflow_path)

        # Check if workflow enables UI components
        if workflow_data.get('ui_components', {}).get('enabled', False):
            # Add UI instructions to workflow
            ui_instructions = self._get_ui_instructions(
                workflow_data['ui_components']
            )
            workflow_data['workflow'] += f"\n\n{ui_instructions}"

        return workflow_data

    def _get_ui_instructions(self, ui_config: Dict) -> str:
        """Generate UI instructions based on workflow config."""
        instructions = []

        if 'oauth' in ui_config.get('components', []):
            instructions.append("""
UI COMPONENT AVAILABLE:
- When ready to connect Shopify, insert {{oauth:shopify}} where the button should appear
- Don't say "click the button below" - just include the marker naturally
- Example: "Let's connect your store: {{oauth:shopify}}"
""")

        return "\n".join(instructions)
```

### 3. Update Shopify Onboarding Workflow

Add UI component configuration to the workflow:

```yaml
# agents/prompts/workflows/shopify_onboarding.yaml
name: "Shopify Onboarding"
description: "Natural onboarding flow for all new conversations"
version: "1.0.0"
active: true

# Enable UI components for this workflow
ui_components:
  enabled: true
  components:
    - oauth

workflow: |
  WORKFLOW: Shopify Onboarding
  GOAL: Guide merchants through connecting Shopify and support systems

  # ... existing workflow instructions ...

  2. Shopify Connection (Adapt based on detection)
     FOR NEW USERS:
     - Explain value proposition clearly
     - When ready, insert OAuth button with: {{oauth:shopify}}
     - Continue conversation after button

     EXAMPLE:
     "I'll need read-only access to your Shopify store to analyze your support patterns.

     {{oauth:shopify}}

     Once connected, I'll be able to show you insights about your customers."
```

### 4. Minimal Middleware Integration

Update the message processor to parse UI components:

```python
# agents/app/services/message_processor.py

async def _get_cj_response(self, session, message: str, is_system: bool = False):
    """Get response from CJ agent."""

    # ... existing agent creation and execution ...

    result = crew.kickoff()
    response = result.output if hasattr(result, "output") else str(result)

    # Only parse UI components if workflow has them enabled
    if session.conversation.workflow == "shopify_onboarding":
        from app.services.ui_components import UIComponentParser
        parser = UIComponentParser()
        clean_content, ui_components = parser.parse_oauth_buttons(response)

        if ui_components:
            return {
                "type": "message_with_ui",
                "content": clean_content,
                "ui_elements": ui_components
            }

    return response
```

### 5. Frontend OAuth Button Component

Update the frontend to handle messages with UI elements:

```typescript
// homepage/src/components/MessageContent.tsx
import React from 'react';
import ReactMarkdown from 'react-markdown';
import { ShopifyOAuthButton } from './ShopifyOAuthButton';

interface UIElement {
  id: string;
  type: string;
  provider: string;
  placeholder: string;
}

interface MessageProps {
  message: {
    content: string;
    ui_elements?: UIElement[];
    conversationId: string;
  };
}

export const MessageContent: React.FC<MessageProps> = ({ message }) => {
  // Simple split by placeholder
  const parts = message.content.split(/__OAUTH_BUTTON_\d+__/);
  const buttons = message.ui_elements?.filter(el => el.type === 'oauth_button') || [];

  return (
    <div className="space-y-3">
      {parts.map((part, i) => (
        <React.Fragment key={i}>
          {part && (
            <div className="prose prose-sm">
              <ReactMarkdown>{part}</ReactMarkdown>
            </div>
          )}
          {buttons[i] && (
            <div className="my-4">
              <ShopifyOAuthButton
                conversationId={message.conversationId}
                provider={buttons[i].provider}
              />
            </div>
          )}
        </React.Fragment>
      ))}
    </div>
  );
};
```

### 6. Platform Message Handling

Update the platform layer to handle UI elements:

```python
# agents/app/platforms/web_platform.py

async def _handle_cj_response(self, session, response_data):
    """Handle CJ's response, which may include UI elements."""
    
    # Check if this is a structured response with UI elements
    if isinstance(response_data, dict) and response_data.get("type") == "message_with_ui":
        # Send message with embedded UI elements
        await self.send_message(OutgoingMessage(
            conversation_id=session.id,
            sender="cj",
            content=response_data["content"],
            ui_elements=response_data.get("ui_elements", [])
        ))
    else:
        # Regular text response
        await self.send_message(OutgoingMessage(
            conversation_id=session.id,
            sender="cj",
            content=str(response_data)
        ))

async def send_message(self, message: OutgoingMessage) -> bool:
    """Enhanced to handle UI elements."""
    
    websocket_data = {
        "type": "message",
        "data": {
            "id": message.message_id,
            "sender": message.sender,
            "content": message.content,
            "timestamp": message.timestamp,
            "metadata": message.metadata
        }
    }
    
    # Add UI elements if present
    if hasattr(message, 'ui_elements') and message.ui_elements:
        websocket_data["data"]["ui_elements"] = message.ui_elements
    
    await self.websocket.send_json(websocket_data)
    return True
```

### 7. Future Extension Pattern

When we need more UI components, we:

1. **Add new pattern to UIComponentParser:**
```python
CHOICES_PATTERN = re.compile(r'{{choices:(.*?)}}')
```

2. **Enable in specific workflow:**
```yaml
ui_components:
  enabled: true
  components:
    - oauth
    - choices
```

3. **Add parsing logic and frontend component**

### 8. Real-World Example Flow

Here's exactly how the OAuth button flows through the system:

#### Step 1: CJ Writes Response with Marker
```
CJ writes: "Let me help you connect your Shopify store so I can analyze your support patterns.

{{oauth:shopify}}

Once connected, I'll be able to see your customer data and support history."
```

#### Step 2: Parser Processes the Response
```python
# UIComponentParser finds the marker
content = "Let me help you connect your Shopify store... {{oauth:shopify}} Once connected..."

clean_content, ui_components = parser.parse_oauth_buttons(content)

# Result:
clean_content = "Let me help you connect your Shopify store... __OAUTH_BUTTON_1__ Once connected..."

ui_components = [{
    'id': 'oauth_1',
    'type': 'oauth_button',
    'provider': 'shopify',
    'placeholder': '__OAUTH_BUTTON_1__'
}]
```

#### Step 3: WebSocket Message
```json
{
    "type": "message",
    "data": {
        "sender": "cj",
        "content": "Let me help you connect your Shopify store... __OAUTH_BUTTON_1__ Once connected...",
        "ui_elements": [{
            "id": "oauth_1",
            "type": "oauth_button",
            "provider": "shopify",
            "placeholder": "__OAUTH_BUTTON_1__"
        }]
    }
}
```

#### Step 4: Frontend Renders
The frontend:
1. Splits content by placeholder
2. Renders text parts with Markdown
3. Inserts OAuth button at placeholder location
4. Result: Text flows naturally with button exactly where CJ placed it

### 9. Testing Strategy

### Unit Tests
```python
# tests/test_ui_components.py
def test_oauth_marker_parsing():
    parser = UIComponentParser()
    content = "Connect your store: {{oauth:shopify}}"
    
    clean_content, components = parser.parse_oauth_buttons(content)
    
    assert "__OAUTH_BUTTON_1__" in clean_content
    assert len(components) == 1
    assert components[0]['type'] == 'oauth_button'
    assert components[0]['provider'] == 'shopify'

def test_multiple_markers():
    parser = UIComponentParser()
    content = "First: {{oauth:shopify}} and second: {{oauth:shopify}}"
    
    clean_content, components = parser.parse_oauth_buttons(content)
    
    assert "__OAUTH_BUTTON_1__" in clean_content
    assert "__OAUTH_BUTTON_2__" in clean_content
    assert len(components) == 2
```

### Integration Tests
1. Test CJ includes markers in appropriate workflow
2. Test message processor parses markers correctly
3. Test WebSocket sends ui_elements with messages
4. Test frontend renders buttons at placeholder locations

### Manual Testing Flow
1. Start new conversation
2. Progress naturally to Shopify connection point
3. Verify CJ inserts {{oauth:shopify}} marker
4. Verify button appears where marker was placed
5. Complete OAuth flow
6. Verify CJ continues conversation appropriately

### 10. Platform Adaptations

For platforms like Slack, we can convert markers to platform-specific formats:

```python
# Future enhancement: platform-specific rendering
if platform == "slack":
    # Convert UI elements to Slack Block Kit
    blocks = convert_to_slack_blocks(ui_elements)
```

## 🏗️ Implementation Summary

### What We're Building:
- **Simple {{oauth:shopify}} marker** that CJ can use
- **Workflow-specific enablement** (only shopify_onboarding for now)
- **Basic parser** that replaces markers with placeholders
- **Frontend** that renders OAuth button where markers were

### What We're NOT Building (Yet):
- Generic component system
- Complex XML parsing
- Component registry
- Multiple UI element types
- Base prompt modifications

### Benefits:
- **Dead simple to implement**: Just string replacement
- **Solves immediate need**: OAuth button works
- **Easy to extend when needed**: Add new patterns as we go
- **No over-engineering**: Built exactly what we need
- **Workflow authors control what's available**: Per-workflow enablement

## 🚀 Future Enhancements

When we need more UI components:

1. **Choice Buttons**: `{{choices:option1,option2,option3}}`
2. **Confirmation Dialogs**: `{{confirm:question}}`
3. **Progress Indicators**: `{{progress:50}}`
4. **Rich Media**: `{{image:url}}`, `{{chart:data}}`

Each follows the same pattern:
- Simple marker syntax
- Parser extracts and replaces
- Frontend renders at location

## 📚 References

1. AI Rabbit, "LLM ChatBots 3.0: Merging LLMs with Dynamic UI Elements," Oct 2024
2. Chainlit Documentation, "Actions and Callbacks," chainlit.io
3. OpenAI Developer Community, "GPT function calling and showing results in UI," 2024
4. Dharmesh Shah, "Beyond Chat: Blending UI for an AI World," May 2025

## ✅ Success Criteria

Phase 4 is complete when:
- [ ] UIComponentParser implemented for OAuth buttons
- [ ] Workflow loader adds UI instructions
- [ ] Shopify onboarding workflow uses {{oauth:shopify}}
- [ ] Message processor parses markers
- [ ] Frontend renders OAuth button at marker location
- [ ] CJ naturally incorporates markers in conversation
- [ ] No blocking or deadlock issues

## 🔑 Key Principles

1. **Start Simple**: Just OAuth button marker
2. **Precise Placement**: UI appears exactly where CJ puts it
3. **Natural Writing**: Like using markdown
4. **Easy Extension**: Add new markers as needed
5. **No Over-Engineering**: Build what we need now

This scaled-back approach follows our North Star: simplify, simplify, simplify. We build exactly what we need for OAuth buttons, but in a way that's trivial to extend when we need more UI elements.