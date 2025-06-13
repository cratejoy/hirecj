from pydantic import BaseModel, Field
from typing import Optional, Union, Literal, Annotated, Dict, Any, List
from datetime import datetime

# ───── nested payload objects ───────────────────────────────────────────────
class StartConversationData(BaseModel):
    workflow: Optional[str] = None
    merchant_id: Optional[str] = None
    scenario_id: Optional[str] = None


class FactCheckData(BaseModel):
    messageIndex: int
    forceRefresh: bool = False


class DebugRequestData(BaseModel):
    type: Literal["snapshot", "session", "state", "metrics", "prompts"]


class WorkflowTransitionData(BaseModel):
    new_workflow: str
    user_initiated: bool = False


class CJThinkingData(BaseModel):
    status: str
    elapsed: Optional[float] = None
    toolsCalled: Optional[int] = None
    currentTool: Optional[str] = None


class CJMessageData(BaseModel):
    content: str
    factCheckStatus: Optional[str] = "available"
    timestamp: datetime
    ui_elements: Optional[List[Dict[str, Any]]] = None


# ───── incoming (client → server) envelopes ────────────────────────────────
class StartConversationMsg(BaseModel):
    type: Literal["start_conversation"]
    data: StartConversationData


class UserMsg(BaseModel):
    type: Literal["message"]
    text: str


class EndConversationMsg(BaseModel):
    type: Literal["end_conversation"]


class FactCheckMsg(BaseModel):
    type: Literal["fact_check"]
    data: FactCheckData


class DebugRequestMsg(BaseModel):
    type: Literal["debug_request"]
    data: DebugRequestData


class WorkflowTransitionMsg(BaseModel):
    type: Literal["workflow_transition"]
    data: WorkflowTransitionData


class PingMsg(BaseModel):
    type: Literal["ping"]


class LogoutMsg(BaseModel):
    type: Literal["logout"]


IncomingMessage = Annotated[
    Union[
        StartConversationMsg,
        UserMsg,
        EndConversationMsg,
        FactCheckMsg,
        DebugRequestMsg,
        WorkflowTransitionMsg,
        PingMsg,
        LogoutMsg,
    ],
    Field(discriminator="type"),
]

# ───── outgoing (server → client) envelopes ────────────────────────────────
class ConversationStartedData(BaseModel):
    conversationId: str
    merchantId: Optional[str] = None
    scenario: Optional[str] = None
    workflow: str
    sessionId: Optional[str] = None
    resumed: Optional[bool] = None


class ConversationStartedMsg(BaseModel):
    type: Literal["conversation_started"]
    data: ConversationStartedData


class CJMessageMsg(BaseModel):
    type: Literal["cj_message"]
    data: CJMessageData


class CJThinkingMsg(BaseModel):
    type: Literal["cj_thinking"]
    data: CJThinkingData


class ErrorMsg(BaseModel):
    type: Literal["error"]
    text: str


class SystemMsg(BaseModel):
    type: Literal["system"]
    text: str


OutgoingMessage = Annotated[
    Union[
        ConversationStartedMsg,
        CJMessageMsg,
        CJThinkingMsg,
        ErrorMsg,
        SystemMsg,
    ],
    Field(discriminator="type"),
]
