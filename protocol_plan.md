# Centralized WebSocket Protocol Management Plan

**Status:** Proposed
**Date:** 2025-06-13
**Author:** Code Analyst

## 1. Overview & Goal

The project currently defines WebSocket message structures independently in both the Python backend (`agents` service) and the TypeScript frontend (`homepage`). This manual synchronization is error-prone and leads to protocol drift, causing bugs and increasing maintenance overhead.

The goal of this plan is to establish a **Single Source of Truth** for the WebSocket protocol. We will define the protocol schema in one language, automatically generate the corresponding models for the other, and place them in a shared location. This will ensure that the frontend and backend are always in sync, providing strong typing and validation from end to end.

## 2. Problem Statement

*   **Protocol Drift:** Any change to a message structure must be manually replicated in both the frontend and backend. It's easy to forget a field or introduce a type mismatch.
*   **No Contract:** There is no formal contract between the client and server. Developers must visually inspect code in two different languages to understand the protocol.
*   **Brittle Communication:** Mismatches often lead to silent failures or runtime errors that are difficult to debug (e.g., a message is dropped, or a field is unexpectedly `undefined`).
*   **Development Overhead:** Onboarding new developers is slower, as they must learn the protocol from two separate, unsynchronized sources.

## 3. Proposed Solution

We will adopt a **Python-first, code-generation** approach. The protocol will be defined using Pydantic models within the Python ecosystem. These models will then be used to generate TypeScript interfaces for the frontend.

### 3.1. Single Source of Truth: Python & Pydantic

Python (specifically, Pydantic) is the ideal source of truth for the following reasons:
*   **Backend Validation is Non-Negotiable:** The backend *must* validate all incoming data for security and data integrity. Pydantic is already the standard for this in FastAPI. Using Pydantic as the source means our validation models *are* the protocol definition.
*   **Existing Tooling:** Pydantic is already used extensively across the `agents` service.
*   **Rich Type System:** Pydantic's type system is robust and has excellent support for introspection, which is necessary for code generation.

### 3.2. Generation Tooling: `pydantic-to-typescript`

We will use the `pydantic-to-typescript` library. It's a lightweight, effective tool that directly converts Pydantic models into TypeScript interfaces.

A simple Python script will be created to orchestrate this generation, ensuring that all necessary models are exported correctly.

### 3.3. New Directory Structure

To facilitate sharing, we will create a new top-level directory named `protocol`.

```
/
├── agents/
├── homepage/
├── protocol/
│   ├── python/
│   │   └── hirecj_protocol/
│   │       ├── __init__.py
│   │       └── messages.py  # Pydantic models (Source of Truth)
│   ├── ts/
│   │   └── index.ts         # Generated TypeScript interfaces
│   └── generate_ts_models.py # Generation script
└── ...other project folders
```

*   `protocol/python/`: Will contain the canonical Pydantic models. This will be a standard Python package.
*   `protocol/ts/`: Will contain the auto-generated TypeScript interfaces. This file should be marked with a "DO NOT EDIT" header.
*   `protocol/generate_ts_models.py`: The script that reads from `python/` and writes to `ts/`.

## 4. Implementation Plan

### Phase 1: Setup and Initial Model Definition

1.  **Create Directory Structure:** Create the `protocol/` directory and its subdirectories as outlined above.
2.  **Install Tooling:** Add `pydantic-to-typescript` to the development dependencies for the `agents` service.
3.  **Define Core Models:** In `protocol/python/hirecj_protocol/messages.py`, define the base message structures.

    *Example (`messages.py`):*
    ```python
    from pydantic import BaseModel, Field
    from typing import Literal, Union, List, Dict, Any

    # --- Payloads for different message types ---

    class StartConversationData(BaseModel):
        type: Literal["start_conversation"]
        workflow: str
        merchant_id: str | None = None
        scenario_id: str | None = None

    class UserMessageData(BaseModel):
        type: Literal["message"]
        text: str

    class DebugRequestData(BaseModel):
        type: Literal["debug_request"]
        debug_type: Literal["snapshot", "session", "state", "metrics", "prompts"]

    # --- Discriminated Union for Payloads ---
    
    # This is the main model that the websocket will expect.
    # The `discriminator='type'` tells Pydantic to look at the `type` field
    # to determine which model to validate against.
    WebSocketMessage = Annotated[
        Union[
            StartConversationData,
            UserMessageData,
            DebugRequestData,
        ],
        Field(discriminator="type"),
    ]

    ```
4.  **Create Generation Script:** Create `protocol/generate_ts_models.py`.

    *Example (`generate_ts_models.py`):*
    ```python
    from pathlib import Path
    from pydantic_to_typescript import generate_typescript_defs

    # Assumes script is run from the repository root
    py_module_path = Path("protocol/python/hirecj_protocol/messages.py")
    ts_output_path = Path("protocol/ts/index.ts")

    # Ensure output directory exists
    ts_output_path.parent.mkdir(exist_ok=True)
    
    header = "//\n// DO NOT EDIT. THIS FILE IS AUTO-GENERATED BY `pydantic-to-typescript`\n//\n"

    # Generate the file content first
    ts_defs = generate_typescript_defs(py_module_path, json_dump_kwargs={'indent': 2})

    # Write header and content to file
    with open(ts_output_path, 'w') as f:
        f.write(header)
        f.write(ts_defs)

    print(f"✅ TypeScript models generated at {ts_output_path}")
    ```

### Phase 2: Backend Integration

1.  **Modify `agents` service:** Update `agents/app/platforms/web/websocket_handler.py` and its sub-handlers (`message_handlers.py`, `session_handlers.py`, etc.).
2.  **Install Protocol Package:** The `agents` service will need to install the local `protocol` package in editable mode. Add `.` to `sys.path` or configure `PYTHONPATH`. A `pyproject.toml` in the `protocol/python` directory can define it as a package.
3.  **Type WebSocket Messages:** In the `handle_connection` loop, parse the incoming JSON into the `WebSocketMessage` model.

    *Before:*
    ```python
    async for message in websocket.iter_json():
        message_type = message.get("type", "message")
        # ... manual parsing and validation ...
    ```

    *After:*
    ```python
    from hirecj_protocol.messages import WebSocketMessage
    from pydantic import ValidationError

    async for raw_message in websocket.iter_json():
        try:
            message = WebSocketMessage.model_validate(raw_message)
            # Now message is a fully typed and validated Pydantic object
            if message.type == 'start_conversation':
                # message is now guaranteed to be StartConversationData
                await self.message_handlers.handle_start_conversation(..., message)
        except ValidationError as e:
            # Handle bad message format
            ...
    ```

### Phase 3: Frontend Integration

1.  **Run Generator:** Execute `python protocol/generate_ts_models.py` from the repository root.
2.  **Verify Output:** Check `protocol/ts/index.ts` to ensure the TypeScript interfaces were generated correctly.
3.  **Update `homepage`:** Refactor the frontend code to use these shared types.
4.  **Modify `useWebSocketChat.ts`:** Replace locally-defined `Message` interfaces with the imported types from `../../protocol/ts`.
5.  **Type `sendMessage`:** Ensure that the `sendMessage` function and other message construction logic builds objects that conform to the new, stricter interfaces. This will immediately catch bugs where incorrect fields are being sent.

### Phase 4: Expansion and Finalization

1.  **Migrate All Payloads:** Systematically convert every single message type (`cj_message`, `fact_check_complete`, `error`, etc.) into Pydantic models in `messages.py`. This includes client-bound messages as well for full-protocol coverage.
2.  **Regenerate:** Run the generation script again.
3.  **Refactor:** Update the backend and frontend code that produces or consumes these messages to use the new typed models.
4.  **CI/CD Integration:** This is a critical step to prevent future drift. See section 6.

## 5. New Developer Workflow

When a developer needs to change the WebSocket protocol (e.g., add a field to a message):

1.  **Edit Python:** They modify the Pydantic model in `protocol/python/hirecj_protocol/messages.py`.
2.  **Run Script:** They run `python protocol/generate_ts_models.py` from the root directory.
3.  **Commit Both:** They commit the changes to **both** the Python model and the auto-generated TypeScript file.
4.  **Update Logic:** They update the relevant Python and TypeScript code to utilize the new field(s). The TypeScript compiler and Pydantic validators will guide them.

## 6. Risks & Mitigations

*   **Risk:** Developers forget to run the generation script, causing the committed code to be out of sync.
    *   **Mitigation:** **Implement a CI Check.** Add a step to the CI pipeline that runs `generate_ts_models.py` and then uses `git diff --exit-code protocol/ts/index.ts`. If there's a diff, it means the generated file is stale, and the build fails. This forces developers to commit the up-to-date version. A pre-commit hook can also be used for local development.

*   **Risk:** The `pydantic-to-typescript` tool might not support a complex type we need.
    *   **Mitigation:** Keep the protocol models simple and focused on data transfer. Avoid complex custom types in the Pydantic models destined for generation. Test complex cases early.

*   **Risk:** Initial refactoring effort is significant.
    *   **Mitigation:** The phased implementation plan is designed to manage this. We can start with just one or two message types to prove the workflow and then incrementally migrate the rest.
