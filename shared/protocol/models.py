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

class FactCheckStartedData(BaseModel):
    messageIndex: int
    status: Literal["checking"] = "checking"

class FactCheckCompleteData(BaseModel):
    messageIndex: int
    result: Dict[str, Any]

class FactCheckErrorData(BaseModel):
    messageIndex: int
    error: str

class WorkflowUpdatedData(BaseModel):
    workflow: str
    previous: Optional[str] = None

class OAuthProcessedData(BaseModel):
    success: bool
    is_new: Optional[bool] = None
    merchant_id: Optional[str] = None
    shop_domain: Optional[str] = None
    error: Optional[str] = None

class LogoutCompleteData(BaseModel):
    message: str

class WorkflowTransitionCompleteData(BaseModel):
    workflow: str
    message: str


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

class OAuthCompleteMsg(BaseModel):
    type: Literal["oauth_complete"]
    data: Dict[str, Any]

class SystemEventMsg(BaseModel):
    type: Literal["system_event"]
    data: Dict[str, Any]

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
        OAuthCompleteMsg,
        SystemEventMsg,
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
    connected_at: Optional[str] = None

    messageCount: Optional[int] = None
    messages: Optional[List[Dict[str, Any]]] = None
    workflow_requirements: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None


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

class FactCheckStartedMsg(BaseModel):
    type: Literal["fact_check_started"]
    data: FactCheckStartedData

class FactCheckCompleteMsg(BaseModel):
    type: Literal["fact_check_complete"]
    data: FactCheckCompleteData

class FactCheckErrorMsg(BaseModel):
    type: Literal["fact_check_error"]
    data: FactCheckErrorData

class WorkflowUpdatedMsg(BaseModel):
    type: Literal["workflow_updated"]
    data: WorkflowUpdatedData

class WorkflowTransitionCompleteMsg(BaseModel):
    type: Literal["workflow_transition_complete"]
    data: WorkflowTransitionCompleteData

class FactCheckStatusMsg(BaseModel):
    type: Literal["fact_check_status"]
    data: Dict[str, Any]          # e.g. {"messageIndex": int, "status": str, ...}

class OAuthProcessedMsg(BaseModel):
    type: Literal["oauth_processed"]
    data: OAuthProcessedData

class LogoutCompleteMsg(BaseModel):
    type: Literal["logout_complete"]
    data: LogoutCompleteData

class PongMsg(BaseModel):
    type: Literal["pong"]
    timestamp: datetime

class DebugResponseMsg(BaseModel):
    type: Literal["debug_response"]
    data: Dict[str, Any]

class DebugEventMsg(BaseModel):
    type: Literal["debug_event"]
    data: Dict[str, Any]

OutgoingMessage = Annotated[
    Union[
        ConversationStartedMsg,
        CJMessageMsg,
        CJThinkingMsg,
        FactCheckStartedMsg,
        FactCheckCompleteMsg,
        FactCheckErrorMsg,
        FactCheckStatusMsg,
        WorkflowUpdatedMsg,
        WorkflowTransitionCompleteMsg,
        OAuthProcessedMsg,
        LogoutCompleteMsg,
        PongMsg,
        DebugResponseMsg,
        DebugEventMsg,
        ErrorMsg,
        SystemMsg,
    ],
    Field(discriminator="type"),
]
