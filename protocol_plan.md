# Centralized WebSocket Protocol Management Plan

**Status:** Proposed
**Date:** 2025-06-13
**Author:** Code Analyst

## 1. Overview & Goal

The project currently defines WebSocket message structures independently in both the Python backend (`agents` service) and the TypeScript frontend (`homepage`). This manual synchronization is error-prone and leads to protocol drift, causing bugs and increasing maintenance overhead.

The goal of this plan is to establish a **Single Source of Truth** for the WebSocket protocol. We will define the protocol schema in one language, automatically generate the corresponding models for the other, and place them in a shared location. This will ensure that the frontend and backend are always in sync, providing strong typing and validation from end to end.

**Version Alignment**

The monorepo already runs on **Pydantic v2** (≥ 2.5).  
Consequently every code example below assumes Pydantic v2 syntax and we will
generate TypeScript with **datamodel-code-generator ≥ 0.25**, which has first-class
support for Pydantic v2.  
All previous mentions of the now-incompatible `pydantic-to-typescript`
package have been removed.

## 2. Problem Statement

*   **Protocol Drift:** Any change to a message structure must be manually replicated in both the frontend and backend. It's easy to forget a field or introduce a type mismatch.
*   **No Contract:** There is no formal contract between the client and server. Developers must visually inspect code in two different languages to understand the protocol.
*   **Brittle Communication:** Mismatches often lead to silent failures or runtime errors that are difficult to debug (e.g., a message is dropped, or a field is unexpectedly `undefined`).
*   **Development Overhead:** Onboarding new developers is slower, as they must learn the protocol from two separate, unsynchronized sources.

<!-- (Message-shape drift bullet removed; now addressed by models) -->

## 3. Proposed Solution

We will adopt a **Python-first, code-generation** approach. The protocol will be defined using Pydantic models within the Python ecosystem. These models will then be used to generate TypeScript interfaces for the frontend. The Pydantic models are the single source of truth, replacing any manually maintained tables or documentation.

### 3.3. New Directory Structure

The protocol's source of truth (Python models) will live in `shared/`, but the generated TypeScript code will live directly in `homepage/src/` to be easily accessible by Vite.

```
/
├── shared/
│   ├── protocol/
│   │   ├── __init__.py
│   │   └── models.py           # Pydantic models (Source of Truth)
│   └── ...
├── homepage/
│   ├── src/
│   │   ├── protocol/
│   │   │   └── generated.ts    # Generated TypeScript interfaces
│   │   └── ...
└── ...
```

*   `shared/protocol/models.py`: The canonical Pydantic models.
*   `homepage/src/protocol/generated.ts`: The auto-generated TypeScript interfaces. **This file should be committed to the repository** to simplify the frontend build process.
This is the definitive policy: the generated file **is tracked in git**.  
CI will verify it is up-to-date; local pre-commit hooks (optional) can auto-run the generator.

## 4. Implementation Plan

### Phase 1: Setup and Initial Model Definition

1.  **Directory Structure:** The plan is to create the directory structure as outlined above.
2. **Install tooling**  
   List `datamodel-code-generator>=0.25.0` in **both**  
   • `shared/setup.py` – so the package is available when `shared` is installed in
     editable mode, and  
   • `agents/requirements.txt` – so the generator is present in production /
     container builds of the `agents` service.  
   (If you maintain `agents/requirements-dev.txt`, add it there as well for local
   developer convenience.)
3.  **Define Core Models:** In `shared/protocol/models.py`, define the message structures to match the runtime reality.

    *Example (`models.py`):*
    ```python
    from pydantic import BaseModel, Field
    from typing import Literal, Union, Optional, Annotated, Dict, Any, List
    from datetime import datetime

    # --- Payloads for nested data objects ---
    class StartConversationData(BaseModel):
        workflow: str
        merchant_id: Optional[str] = None
        scenario_id: Optional[str] = None

    class FactCheckData(BaseModel):
        messageIndex: int
        forceRefresh: bool = False

    class DebugRequestData(BaseModel):
        # This is the inner `data` object for a debug_request.
        # The field must be `type` to match the handler.
        type: Literal["snapshot", "session", "state", "metrics", "prompts"]

    class WorkflowTransitionData(BaseModel):
        new_workflow: str
        user_initiated: bool = False

    # --- Incoming Messages (Client -> Server) ---
    class StartConversationMessage(BaseModel):
        type: Literal["start_conversation"]
        data: StartConversationData

    class UserMessage(BaseModel):
        type: Literal["message"]
        text: str  # Flat structure

    class EndConversationMessage(BaseModel):
        type: Literal["end_conversation"]

    class FactCheckMessage(BaseModel):
        type: Literal["fact_check"]
        data: FactCheckData
        
    class PingMessage(BaseModel):
        type: Literal["ping"]

    class DebugRequestMessage(BaseModel):
        type: Literal["debug_request"]
        data: DebugRequestData

    class WorkflowTransitionMessage(BaseModel):
        type: Literal["workflow_transition"]
        data: WorkflowTransitionData

    class LogoutMessage(BaseModel):
        type: Literal["logout"]

    IncomingMessage = Annotated[
        Union[
            StartConversationMessage, UserMessage, EndConversationMessage,
            FactCheckMessage, PingMessage, DebugRequestMessage, 
            WorkflowTransitionMessage, LogoutMessage
        ],
        Field(discriminator="type"),
    ]

    # --- Outgoing Messages (Server -> Client) ---
    class ConversationStartedData(BaseModel):
        conversationId: str
        merchantId: Optional[str]
        scenario: Optional[str]
        workflow: str

    class CJMessageData(BaseModel):
        content: str
        factCheckStatus: str
        timestamp: datetime
        ui_elements: Optional[List[Dict[str, Any]]] = None

    class PongMessage(BaseModel):
        type: Literal["pong"]
        timestamp: datetime

    class ErrorMessage(BaseModel):
        type: Literal["error"]
        text: str
    
    class SystemMessage(BaseModel):
        type: Literal["system"]
        text: str

    class ConversationStartedMessage(BaseModel):
        type: Literal["conversation_started"]
        data: ConversationStartedData

    class CJMessage(BaseModel):
        type: Literal["cj_message"]
        data: CJMessageData

    # ... other outgoing messages would be modeled here ...

    OutgoingMessage = Annotated[
        Union[
            ConversationStartedMessage,
            CJMessage,
            PongMessage,
            ErrorMessage,
            SystemMessage
        ],
        Field(discriminator="type"),
    ]
    ```
4.  **Generation Script:** Use `datamodel-code-generator` via a shell script or command.

    *Example Generation Command (run from monorepo root):*
    ```bash
    datamodel-codegen --input shared/protocol/models.py \
                      --input-file-type module \
                      --output homepage/src/protocol/generated.ts \
                      --output-file-type typescript
    ```

### Phase 2: Backend Integration

1.  **Modify `agents` service:** Update `agents/app/platforms/web/websocket_handler.py` (and its sub-handlers) to use the new models.
2.  **Update Python Imports:** Since `shared` is already in the `PYTHONPATH` for services, you can import the models directly.
3.  **Type WebSocket Messages:** In the `handle_connection` loop, parse the incoming JSON into the `IncomingMessage` model. This provides automatic, type-safe validation.

    *Before:*
    ```python
    async for message in websocket.iter_json():
        message_type = message.get("type", "message")
        # ... manual parsing and validation ...
    ```

    *After (using `match` statement for elegance):*
    ```python
    from shared.protocol.models import (
        IncomingMessage, UserMessage, StartConversationMessage, DebugRequestMessage
    )
    from pydantic import ValidationError

    async for raw_message in websocket.iter_json():
        try:
            message = IncomingMessage.model_validate(raw_message)
            
            # Use pattern matching for clean, type-safe routing.
            # This requires passing the validated model object to the handlers.
            match message:
                case UserMessage():
                    await self.message_handlers.handle_message(
                        websocket, conversation_id, message.model_dump()
                    )
                case StartConversationMessage():
                    await self.message_handlers.handle_start_conversation(
                        websocket, conversation_id, message.model_dump()
                    )
                case DebugRequestMessage():
                     await self.message_handlers.handle_debug_request(
                        websocket, conversation_id, message.model_dump()
                    )
                # ... add cases for all other message types
                case _:
                    logger.warning(f"No handler for message type: {message.type}")

        except ValidationError as e:
            # Pydantic raises an error for invalid message structures
            await self.platform.send_error(websocket, f"Invalid message format: {e.errors()}")
    ```

### Phase 3: Frontend Integration

1.  **Run Generator:** Execute `python shared/protocol/generate_ts.py` from the repository root.
2.  **Verify Output:** Check `shared/protocol/generated/ts/index.ts` to ensure the TypeScript interfaces were generated correctly.
3.  **Update `homepage`:** Refactor frontend code to use these shared types.
4.  **Modify `useWebSocketChat.ts`:** Replace locally-defined interfaces with imported types from `../protocol/generated`.
5.  **Type `sendMessage`:** Ensure that the `sendMessage` function and other message construction logic builds objects that conform to the new, stricter interfaces (e.g., `StartConversationMessage`). This will immediately catch bugs where incorrect fields are being sent.

### Phase 4: Expansion and Finalization

1.  **Migrate All Payloads:** Systematically convert every single message type (`cj_message`, `fact_check_complete`, `error`, etc.) into Pydantic models in `shared/protocol/models.py`. This includes client-bound messages as well for full-protocol coverage.
2.  **Regenerate:** Run the generation script again.
3.  **Refactor:** Update the backend and frontend code that produces or consumes these messages to use the new typed models.
4.  **CI/CD Integration:** This is a critical step to prevent future drift. See section 6.

## 5. New Developer Workflow

When a developer needs to change the WebSocket protocol (e.g., add a field to a message):

1.  **Edit Python:** They modify the Pydantic model in `shared/protocol/models.py`.
2.  **Run Script:** They run the `datamodel-code-generator` command (or a wrapper shell script) from the root directory to regenerate `homepage/src/protocol/generated.ts`.
3.  **Commit Both:** They commit the changes to **both** the Python model and the auto-generated TypeScript file.
4.  **Update Logic:** They update the relevant Python and TypeScript code to utilize the new field(s). The TypeScript compiler and Pydantic validators will guide them.

## 6. Risks & Mitigations

*   **Risk:** Developers forget to run the generation script, causing the committed code to be out of sync.
    *   **Mitigation:** **Implement a CI Check.** Add a step to the CI pipeline that runs the generation script and then uses `git diff --exit-code homepage/src/protocol/generated.ts`. If there's a diff, it means the generated file is stale, and the build fails. This forces developers to commit the up-to-date version. A pre-commit hook can also be used for local development.

*   **Risk:** The `datamodel-code-generator` tool might have issues with very complex types.
    *   **Mitigation:** This tool is more robust, but it's still good practice to keep protocol models simple and focused on data transfer. Avoid complex custom types or validators in the Pydantic models destined for generation.

*   **Risk:** Initial refactoring effort is significant.
    *   **Mitigation:** The phased implementation plan is designed to manage this. We can start with just one or two message types to prove the workflow and then incrementally migrate the rest.
