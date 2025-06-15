# WebSocket Protocol

This directory contains the WebSocket protocol definitions for HireCJ, implemented as Pydantic models that can be automatically converted to TypeScript types using pydantic-to-typescript.

## Structure

- `models.py` - Pydantic models defining all WebSocket message types
- `generate.sh` - Script to generate TypeScript types using pydantic-to-typescript

## Generated Files

The TypeScript types are generated in `homepage/src/protocol/`:
- `generated.ts` - Auto-generated TypeScript interfaces
- `index.ts` - Convenient exports for importing

## Usage

### Regenerating TypeScript Types

From the project root, run:

```bash
make generate-protocol
```

This will:
1. Use pydantic-to-typescript (pydantic2ts) to generate TypeScript interfaces
2. Output them to `homepage/src/protocol/generated.ts`
3. The discriminated unions are defined in `homepage/src/protocol/index.ts`

#### Prerequisites

The following tools must be installed:
- `pydantic-to-typescript` - Python package that converts Pydantic models to TypeScript
- `json-schema-to-typescript` - Node package required by pydantic-to-typescript

These are automatically installed when you set up the project.

### Adding New Message Types

1. Add the new message type to `models.py`:
   ```python
   class MyNewData(BaseModel):
       field1: str
       field2: Optional[int] = None

   class MyNewMsg(BaseModel):
       type: Literal["my_new_message"]
       data: MyNewData
   ```

2. Add it to the appropriate discriminated union:
   ```python
   IncomingMessage = Annotated[
       Union[
           # ... existing messages ...
           MyNewMsg,
       ],
       Field(discriminator="type"),
   ]
   ```

3. Regenerate the TypeScript types:
   ```bash
   make generate-protocol
   ```

4. The TypeScript types will be automatically available in the frontend:
   ```typescript
   import { MyNewMsg, IncomingMessage } from '@/protocol';
   ```

## Message Types

### Incoming Messages (Client → Server)
- `StartConversationMsg` - Initialize a new conversation
- `UserMsg` - User text message
- `EndConversationMsg` - End the conversation
- `FactCheckMsg` - Request fact checking
- `DebugRequestMsg` - Debug information request
- `WorkflowTransitionMsg` - Change workflow
- `PingMsg` - Keepalive ping
- `LogoutMsg` - User logout
- `OAuthCompleteMsg` - OAuth flow completion
- `SystemEventMsg` - System events

### Outgoing Messages (Server → Client)
- `ConversationStartedMsg` - Conversation initialized
- `CJMessageMsg` - CJ's response message
- `CJThinkingMsg` - CJ thinking status
- `FactCheckStartedMsg` - Fact check initiated
- `FactCheckCompleteMsg` - Fact check results
- `FactCheckErrorMsg` - Fact check error
- `FactCheckStatusMsg` - Fact check status update
- `WorkflowUpdatedMsg` - Workflow changed
- `WorkflowTransitionCompleteMsg` - Workflow transition complete
- `OAuthProcessedMsg` - OAuth processing result
- `LogoutCompleteMsg` - Logout confirmation
- `PongMsg` - Keepalive response
- `DebugResponseMsg` - Debug information
- `DebugEventMsg` - Debug event
- `ErrorMsg` - Error message
- `SystemMsg` - System message

## Type Safety

Both Python and TypeScript use discriminated unions for type safety:

### Python
```python
def handle_message(msg: IncomingMessage):
    if msg.type == "message":
        # TypeScript knows msg is UserMsg
        print(msg.text)
    elif msg.type == "start_conversation":
        # TypeScript knows msg is StartConversationMsg
        print(msg.data.workflow)
```

### TypeScript
```typescript
function handleMessage(msg: OutgoingMessage) {
    switch (msg.type) {
        case "cj_message":
            // TypeScript knows msg is CJMessageMsg
            console.log(msg.data.content);
            break;
        case "error":
            // TypeScript knows msg is ErrorMsg
            console.log(msg.text);
            break;
    }
}
```

## Development Workflow

1. Make changes to `models.py`
2. Run `make generate-protocol`
3. TypeScript types are automatically updated
4. Both frontend and backend have synchronized types

This ensures type safety across the entire WebSocket communication layer.