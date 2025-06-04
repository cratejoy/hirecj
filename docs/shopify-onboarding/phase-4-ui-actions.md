# Phase 4: UI Actions Pattern - Implementation Guide

## 🎯 Phase Objectives

Implement a simple, extensible pattern for CJ to embed UI elements in conversations, starting with just the Shopify OAuth button and designed to scale as needed.

**North Star Principles Applied:**
- **Simplify**: Start with just what we need (OAuth button only)
- **No Cruft**: Simple marker syntax, no complex parsing
- **Backend-Driven**: Workflows control what UI is available
- **Single Source of Truth**: One pattern for UI elements
- **Long-term Elegance**: Easy to extend when needed

## ✅ Implementation Checklist

Phase 4 is complete when all sub-phases are complete:

- [x] **Phase 4.1**: Parser implementation and unit tests passing
- [x] **Phase 4.2**: Workflow configuration tested and working
- [ ] **Phase 4.3**: Message processor integration verified
- [ ] **Phase 4.4**: Platform layer passing UI elements
- [ ] **Phase 4.5**: Frontend rendering buttons correctly
- [ ] **End-to-End**: Complete flow tested manually

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

## 📋 Phased Implementation Approach

We'll implement UI Actions in phases, testing each step before moving to the next. This ensures each component works correctly before integration.

### Phase 4.1: Parser Implementation & Testing

**Goal**: Create and test the UI component parser in isolation

#### Step 1: Create the Parser

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
```

#### Step 2: Test the Parser

Create unit tests to verify the parser works correctly:

```python
# tests/test_ui_components.py
import pytest
from app.services.ui_components import UIComponentParser

def test_single_oauth_marker():
    """Test parsing a single OAuth marker."""
    parser = UIComponentParser()
    content = "Let's connect your store: {{oauth:shopify}}"
    
    clean_content, components = parser.parse_oauth_buttons(content)
    
    # Verify content has placeholder
    assert clean_content == "Let's connect your store: __OAUTH_BUTTON_1__"
    
    # Verify component extracted
    assert len(components) == 1
    assert components[0]['type'] == 'oauth_button'
    assert components[0]['provider'] == 'shopify'
    assert components[0]['placeholder'] == '__OAUTH_BUTTON_1__'

def test_multiple_oauth_markers():
    """Test parsing multiple OAuth markers."""
    parser = UIComponentParser()
    content = "First: {{oauth:shopify}} and second: {{oauth:shopify}}"
    
    clean_content, components = parser.parse_oauth_buttons(content)
    
    # Verify both placeholders
    assert "__OAUTH_BUTTON_1__" in clean_content
    assert "__OAUTH_BUTTON_2__" in clean_content
    assert len(components) == 2

def test_no_markers():
    """Test content without markers passes through unchanged."""
    parser = UIComponentParser()
    content = "This is regular content with no markers"
    
    clean_content, components = parser.parse_oauth_buttons(content)
    
    assert clean_content == content
    assert len(components) == 0

def test_case_insensitive():
    """Test marker parsing is case insensitive."""
    parser = UIComponentParser()
    content = "Connect: {{OAUTH:SHOPIFY}}"
    
    clean_content, components = parser.parse_oauth_buttons(content)
    
    assert "__OAUTH_BUTTON_1__" in clean_content
    assert len(components) == 1
```

#### Step 3: Run Tests

```bash
# Run the parser tests
pytest tests/test_ui_components.py -v

# Expected output:
# test_ui_components.py::test_single_oauth_marker PASSED
# test_ui_components.py::test_multiple_oauth_markers PASSED
# test_ui_components.py::test_no_markers PASSED
# test_ui_components.py::test_case_insensitive PASSED
```

**✅ Phase 4.1 Complete When:**
- [ ] Parser implementation complete
- [ ] All unit tests passing
- [ ] Parser handles edge cases (empty content, no markers, multiple markers)

---

### Phase 4.2: Workflow Configuration

**Goal**: Update workflow loader to support UI components and test it works

#### Step 1: Update Workflow Loader

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

#### Step 2: Update Shopify Onboarding Workflow

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

#### Step 3: Test Workflow Loading

```python
# tests/test_workflow_ui_components.py
def test_workflow_loads_ui_instructions():
    """Test that UI instructions are added to workflow."""
    loader = WorkflowLoader()
    workflow_data = loader.get_workflow("shopify_onboarding")
    
    # Verify UI instructions were added
    assert "UI COMPONENT AVAILABLE" in workflow_data['workflow']
    assert "{{oauth:shopify}}" in workflow_data['workflow']

def test_workflow_without_ui_components():
    """Test workflows without UI components aren't modified."""
    loader = WorkflowLoader()
    # Assuming we have a workflow without UI components
    workflow_data = loader.get_workflow("basic_workflow")
    
    # Should not contain UI instructions
    assert "UI COMPONENT AVAILABLE" not in workflow_data['workflow']
```

#### Step 4: Manual Test with CJ

Test that CJ receives and uses the UI instructions:

```python
# Quick test script to verify CJ sees UI instructions
from app.agents.cj_agent import CJAgent

# Create CJ with shopify_onboarding workflow
cj = CJAgent(workflow_name="shopify_onboarding")

# Check that the workflow includes UI instructions
print("UI instructions in workflow:", "{{oauth:shopify}}" in cj.workflow_prompt)
```

**✅ Phase 4.2 Complete When:**
- [x] Workflow loader supports UI component configuration
- [x] Shopify onboarding workflow has UI components enabled
- [x] Tests verify UI instructions are added to workflow
- [x] Manual test confirms CJ sees UI instructions

---

### Phase 4.3: Message Processor Integration

**Goal**: Integrate the parser into message processing and verify it extracts UI elements

#### Step 1: Update Message Processor

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

#### Step 2: Test Message Processing

```python
# tests/test_message_processor_ui.py
import pytest
from unittest.mock import Mock, patch

async def test_message_processor_parses_ui_elements():
    """Test that message processor extracts UI elements from CJ response."""
    processor = MessageProcessor()
    
    # Mock session with shopify_onboarding workflow
    mock_session = Mock()
    mock_session.conversation.workflow = "shopify_onboarding"
    
    # Mock CJ response with marker
    with patch.object(processor, '_create_crew') as mock_crew:
        mock_result = Mock()
        mock_result.output = "Let's connect: {{oauth:shopify}}"
        mock_crew.return_value.kickoff.return_value = mock_result
        
        response = await processor._get_cj_response(mock_session, "test message")
        
    # Verify response structure
    assert response['type'] == 'message_with_ui'
    assert '__OAUTH_BUTTON_1__' in response['content']
    assert len(response['ui_elements']) == 1
    assert response['ui_elements'][0]['type'] == 'oauth_button'

async def test_message_processor_no_ui_for_other_workflows():
    """Test that other workflows don't get UI parsing."""
    processor = MessageProcessor()
    
    # Mock session with different workflow
    mock_session = Mock()
    mock_session.conversation.workflow = "other_workflow"
    
    # Mock CJ response with marker (should be ignored)
    with patch.object(processor, '_create_crew') as mock_crew:
        mock_result = Mock()
        mock_result.output = "Text with {{oauth:shopify}}"
        mock_crew.return_value.kickoff.return_value = mock_result
        
        response = await processor._get_cj_response(mock_session, "test message")
        
    # Should return raw response
    assert isinstance(response, str)
    assert "{{oauth:shopify}}" in response
```

#### Step 3: Integration Test

Test the full flow from message to parsed response:

```bash
# Run integration test
python -m pytest tests/test_message_processor_ui.py -v

# Manual test with actual conversation
# Start a conversation and verify CJ's response includes markers
```

**✅ Phase 4.3 Complete When:**
- [ ] Message processor integrates UIComponentParser
- [ ] Only shopify_onboarding workflow gets UI parsing
- [ ] Tests verify UI elements are extracted correctly
- [ ] Integration test shows full flow working

---

### Phase 4.4: Platform Layer Updates

**Goal**: Update platform layer to pass UI elements through WebSocket

#### Step 1: Update Web Platform

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

#### Step 2: Test WebSocket Message Format

```python
# tests/test_web_platform_ui.py
async def test_websocket_includes_ui_elements():
    """Test that UI elements are included in WebSocket messages."""
    platform = WebPlatform()
    mock_websocket = Mock()
    platform.websocket = mock_websocket
    
    # Create message with UI elements
    message = OutgoingMessage(
        conversation_id="test-123",
        sender="cj",
        content="Connect here: __OAUTH_BUTTON_1__",
        ui_elements=[{
            'id': 'oauth_1',
            'type': 'oauth_button',
            'provider': 'shopify',
            'placeholder': '__OAUTH_BUTTON_1__'
        }]
    )
    
    await platform.send_message(message)
    
    # Verify WebSocket data
    sent_data = mock_websocket.send_json.call_args[0][0]
    assert sent_data['data']['ui_elements'] is not None
    assert len(sent_data['data']['ui_elements']) == 1
    assert sent_data['data']['ui_elements'][0]['type'] == 'oauth_button'
```

#### Step 3: Manual WebSocket Test

```javascript
// Test in browser console
ws = new WebSocket('ws://localhost:8001/ws/...');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('UI Elements:', data.data?.ui_elements);
};
```

**✅ Phase 4.4 Complete When:**
- [ ] Platform layer handles structured responses with UI elements
- [ ] WebSocket messages include ui_elements field
- [ ] Tests verify UI elements are passed through
- [ ] Manual test shows UI elements in WebSocket messages

---

### Phase 4.5: Frontend Implementation

**Goal**: Implement frontend rendering of OAuth buttons at placeholder locations

#### Step 1: Create MessageContent Component

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

#### Step 2: Frontend Unit Tests

```typescript
// homepage/src/components/__tests__/MessageContent.test.tsx
import { render, screen } from '@testing-library/react';
import { MessageContent } from '../MessageContent';

describe('MessageContent', () => {
  it('renders OAuth button at placeholder location', () => {
    const message = {
      content: 'Connect your store: __OAUTH_BUTTON_1__',
      ui_elements: [{
        id: 'oauth_1',
        type: 'oauth_button',
        provider: 'shopify',
        placeholder: '__OAUTH_BUTTON_1__'
      }],
      conversationId: 'test-123'
    };

    render(<MessageContent message={message} />);

    // Check text is rendered
    expect(screen.getByText(/Connect your store:/)).toBeInTheDocument();
    
    // Check button is rendered
    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('handles messages without UI elements', () => {
    const message = {
      content: 'Regular message without UI elements',
      conversationId: 'test-123'
    };

    render(<MessageContent message={message} />);

    expect(screen.getByText(/Regular message/)).toBeInTheDocument();
  });

  it('renders multiple buttons in correct positions', () => {
    const message = {
      content: 'First: __OAUTH_BUTTON_1__ Second: __OAUTH_BUTTON_2__',
      ui_elements: [
        { id: 'oauth_1', type: 'oauth_button', provider: 'shopify', placeholder: '__OAUTH_BUTTON_1__' },
        { id: 'oauth_2', type: 'oauth_button', provider: 'shopify', placeholder: '__OAUTH_BUTTON_2__' }
      ],
      conversationId: 'test-123'
    };

    render(<MessageContent message={message} />);

    const buttons = screen.getAllByRole('button');
    expect(buttons).toHaveLength(2);
  });
});
```

#### Step 3: Run Frontend Tests

```bash
# Run component tests
npm test MessageContent

# Run in watch mode for development
npm test -- --watch
```

#### Step 4: End-to-End Test

Test the complete flow from CJ to rendered button:

1. Start new conversation
2. Progress to Shopify connection point
3. Verify CJ inserts `{{oauth:shopify}}` marker
4. Verify button appears in correct position
5. Click button and verify OAuth flow starts

**✅ Phase 4.5 Complete When:**
- [ ] MessageContent component splits content by placeholders
- [ ] OAuth buttons render at placeholder locations
- [ ] Unit tests verify component behavior
- [ ] End-to-end test shows complete flow working

---

## 🎉 Phase 4 Implementation Complete!

With all phases complete, you now have:
- ✅ Parser that extracts UI markers from CJ's responses
- ✅ Workflow configuration to enable UI components
- ✅ Message processor integration
- ✅ Platform layer passing UI elements through WebSocket
- ✅ Frontend rendering buttons at exact marker locations

---

## 🚀 Future Extensions

When we need more UI components, follow the same phased approach:

### Adding Choice Buttons

1. **Phase 1: Update Parser**
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

3. **Phase 3: Add parsing logic**
4. **Phase 4: Update frontend component**
5. **Phase 5: Test end-to-end**

Each new UI element follows the same pattern:
- Simple marker syntax
- Parser extracts and replaces
- Frontend renders at location

---

## 🔄 Example: Complete Flow

Here's how the OAuth button flows through all phases:

1. **CJ writes**: `"Connect your store: {{oauth:shopify}}"`
2. **Parser extracts**: `"Connect your store: __OAUTH_BUTTON_1__"` + UI element data
3. **WebSocket sends**: Message with content and ui_elements array
4. **Frontend renders**: Text with OAuth button at placeholder location

---

## 📚 References

1. AI Rabbit, "LLM ChatBots 3.0: Merging LLMs with Dynamic UI Elements," Oct 2024
2. Chainlit Documentation, "Actions and Callbacks," chainlit.io
3. OpenAI Developer Community, "GPT function calling and showing results in UI," 2024
4. Dharmesh Shah, "Beyond Chat: Blending UI for an AI World," May 2025

---

## 🔑 Key Implementation Principles

1. **Start Simple**: Just OAuth button marker
2. **Test Each Phase**: Verify before moving to next
3. **Precise Placement**: UI appears exactly where CJ puts it
4. **Natural Writing**: Like using markdown
5. **No Over-Engineering**: Build what we need now

This phased approach ensures each component works correctly before integration, reducing debugging time and ensuring a solid foundation for future UI elements.