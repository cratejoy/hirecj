"""
Fact-checking API routes for conversation fact verification.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
import json
from pathlib import Path

from app.agents.fact_checker import ConversationFactChecker as AsyncFactChecker
from app.agents.fact_checker import FactCheckResult
from app.universe.loader import UniverseLoader
from app.constants import HTTPStatus
from shared.protocol.models import FactCheckResultData, FactClaimData, FactIssueData

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["fact-checking"])


class FactCheckRequest(BaseModel):
    """Request to fact-check a message"""

    merchant_name: str
    scenario_name: str
    force_refresh: bool = Field(
        default=False, description="Force re-check even if cached"
    )


class FactCheckStatus(BaseModel):
    """Fact check status response"""

    status: str  # "checking", "complete", "error", "not_available"
    message_index: int
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    checking_progress: Optional[Dict[str, Any]] = None


class FactCheckProgress(BaseModel):
    """Progress update for ongoing fact check"""

    conversation_id: str
    message_index: int
    status: str  # "analyzing", "verifying_facts", "generating_report"
    facts_found: int = 0
    facts_verified: int = 0
    elapsed_seconds: float = 0.0


# Store for active fact checkers (in production, use Redis)
_active_checkers: Dict[str, AsyncFactChecker] = {}
_fact_check_results: Dict[str, Dict[int, FactCheckResult]] = {}


def _get_cache_key(conversation_id: str, message_index: int) -> str:
    """Generate cache key for fact check result"""
    return f"{conversation_id}:{message_index}"


def _get_conversation_path(conversation_id: str) -> Path:
    """Get path to conversation file"""
    return Path("data/conversations") / f"{conversation_id}.json"


def _load_conversation(conversation_id: str) -> Dict[str, Any]:
    """Load conversation from disk"""
    path = _get_conversation_path(conversation_id)
    if not path.exists():
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )

    try:
        with open(path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Invalid conversation file format: {str(e)}",
        )


def _save_conversation(conversation_id: str, conversation: Dict[str, Any]):
    """Save conversation to disk"""
    path = _get_conversation_path(conversation_id)
    with open(path, "w") as f:
        json.dump(conversation, f, indent=2, default=str)


@router.get("/conversations/{conversation_id}/fact-checks/{message_index}")
async def get_fact_check(conversation_id: str, message_index: int) -> FactCheckStatus:
    """
    Get fact-check results for a specific message.

    Returns:
    - If fact-check exists: status="complete" with results
    - If fact-check is running: status="checking" with progress
    - If no fact-check: status="not_available"
    """
    # Check if we have cached results
    if conversation_id in _fact_check_results:
        if message_index in _fact_check_results[conversation_id]:
            result = _fact_check_results[conversation_id][message_index]
            
            # Handle error case
            if isinstance(result, dict) and result.get("status") == "error":
                return FactCheckStatus(
                    status="error",
                    message_index=message_index,
                    error=result.get("error")
                )
            
            # Handle FactCheckResultData case
            if isinstance(result, FactCheckResultData):
                return FactCheckStatus(
                    status="complete",
                    message_index=message_index,
                    result=result.model_dump()
                )
            
            # Handle legacy FactCheckResult case (for backwards compatibility)
            if hasattr(result, "to_dict"):
                return FactCheckStatus(
                    status="complete",
                    message_index=message_index,
                    result=result.to_dict()
                )

    # Check if fact-check is in progress
    if conversation_id in _active_checkers:
        # Get progress info if available
        progress = {"status": "analyzing", "facts_found": 0, "facts_verified": 0}
        return FactCheckStatus(
            status="checking", message_index=message_index, checking_progress=progress
        )

    # Check conversation file for stored fact checks
    try:
        conversation = _load_conversation(conversation_id)
        if "fact_checks" in conversation:
            fact_checks = conversation["fact_checks"]
            if str(message_index) in fact_checks:
                return FactCheckStatus(
                    status="complete",
                    message_index=message_index,
                    result=fact_checks[str(message_index)],
                )
    except HTTPException as e:
        # Re-raise HTTPException to return proper 404
        raise e

    return FactCheckStatus(status="not_available", message_index=message_index)


@router.post("/conversations/{conversation_id}/fact-checks/{message_index}")
async def create_fact_check(
    conversation_id: str,
    message_index: int,
    request: FactCheckRequest,
    background_tasks: BackgroundTasks,
) -> FactCheckStatus:
    """
    Start fact-checking for a specific message.

    This runs asynchronously and returns immediately with status="checking".
    Poll the GET endpoint to check progress.
    """
    # Load conversation
    conversation = _load_conversation(conversation_id)

    # Validate message index
    messages = conversation.get("messages", [])
    if message_index < 0 or message_index >= len(messages):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Invalid message index"
        )

    message = messages[message_index]
    if message.get("sender") != "cj":
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Can only fact-check CJ messages"
        )

    # Check if already checking
    if conversation_id in _active_checkers and not request.force_refresh:
        return FactCheckStatus(
            status="checking",
            message_index=message_index,
            checking_progress={"status": "already_running"},
        )

    # Load universe data
    universe_loader = UniverseLoader()
    try:
        universe = universe_loader.load_by_merchant_scenario(
            request.merchant_name, request.scenario_name
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=f"Universe not found for {request.merchant_name}/{request.scenario_name}",
        )

    # Create fact checker
    checker = AsyncFactChecker(universe)
    _active_checkers[conversation_id] = checker

    # Start fact-checking in background
    background_tasks.add_task(
        _run_fact_check,
        conversation_id,
        message_index,
        message["content"],
        conversation,
        checker,
    )

    return FactCheckStatus(
        status="checking",
        message_index=message_index,
        checking_progress={"status": "started"},
    )


async def _run_fact_check(
    conversation_id: str,
    message_index: int,
    message_content: str,
    conversation: Dict[str, Any],
    checker: AsyncFactChecker,
):
    """Run fact check in background and save results"""
    try:
        # Perform fact check
        result = await checker.check_facts_async(
            cj_response=message_content, turn_number=message_index
        )

        # Create typed result using protocol models
        fact_check_result = FactCheckResultData(
            overall_status=result.overall_status,
            claims=[
                FactClaimData(
                    claim=claim.claim,
                    verification=claim.verification.value,
                    actual_data=claim.actual_data,
                    source=claim.source
                )
                for claim in result.claims
            ],
            issues=[
                FactIssueData(
                    severity=issue.severity.value,
                    summary=issue.summary,  # Fixed: using correct field name
                    claim=issue.claim,
                    expected=issue.expected,
                    actual=issue.actual
                )
                for issue in result.issues
            ],
            execution_time=result.execution_time,
            turn_number=result.turn_number,
            checked_at=datetime.now()
        )
        
        # Store typed result in memory cache
        if conversation_id not in _fact_check_results:
            _fact_check_results[conversation_id] = {}
        _fact_check_results[conversation_id][message_index] = fact_check_result

        # Store in conversation file using model_dump for JSON serialization
        if "fact_checks" not in conversation:
            conversation["fact_checks"] = {}
        conversation["fact_checks"][str(message_index)] = fact_check_result.model_dump(mode='json')

        # Save conversation
        _save_conversation(conversation_id, conversation)

    except Exception as e:
        logger.error(f"Fact check failed for {conversation_id}:{message_index}: {e}")
        # Store error in results - using dict for errors as they don't match FactCheckResultData
        if conversation_id not in _fact_check_results:
            _fact_check_results[conversation_id] = {}
        _fact_check_results[conversation_id][message_index] = {
            "error": str(e),
            "status": "error",
        }
    finally:
        # Clean up active checker
        if conversation_id in _active_checkers:
            del _active_checkers[conversation_id]


@router.get("/conversations/{conversation_id}/fact-checks")
async def get_all_fact_checks(conversation_id: str) -> Dict[str, Any]:
    """
    Get all fact-check results for a conversation.

    Returns a dictionary mapping message indices to fact-check results.
    """
    # Load conversation
    conversation = _load_conversation(conversation_id)

    # Get fact checks from file
    fact_checks = conversation.get("fact_checks", {})

    # Merge with in-memory results
    if conversation_id in _fact_check_results:
        for msg_idx, result in _fact_check_results[conversation_id].items():
            if isinstance(result, FactCheckResultData):
                # Use typed model's serialization
                fact_checks[str(msg_idx)] = result.model_dump()
            elif isinstance(result, FactCheckResult):
                # Legacy support for old FactCheckResult objects
                fact_checks[str(msg_idx)] = result.to_dict()
            else:
                # Raw dict (e.g., error results)
                fact_checks[str(msg_idx)] = result

    # Add status for messages currently being checked
    if conversation_id in _active_checkers:
        messages = conversation.get("messages", [])
        for i, msg in enumerate(messages):
            if msg.get("sender") == "cj" and str(i) not in fact_checks:
                fact_checks[str(i)] = {"status": "checking"}

    return {
        "conversation_id": conversation_id,
        "fact_checks": fact_checks,
        "total_messages": len(conversation.get("messages", [])),
        "cj_messages": len(
            [m for m in conversation.get("messages", []) if m.get("sender") == "cj"]
        ),
    }


@router.delete("/conversations/{conversation_id}/fact-checks/{message_index}")
async def delete_fact_check(conversation_id: str, message_index: int) -> Dict[str, str]:
    """
    Delete fact-check results for a specific message.

    This allows re-running fact checks with updated data.
    """
    # Check if fact check exists
    found_in_memory = False
    found_in_file = False

    # Remove from memory cache
    if conversation_id in _fact_check_results:
        if message_index in _fact_check_results[conversation_id]:
            del _fact_check_results[conversation_id][message_index]
            found_in_memory = True

    # Check and remove from conversation file
    try:
        conversation = _load_conversation(conversation_id)
        if (
            "fact_checks" in conversation
            and str(message_index) in conversation["fact_checks"]
        ):
            del conversation["fact_checks"][str(message_index)]
            _save_conversation(conversation_id, conversation)
            found_in_file = True
    except HTTPException:
        # Conversation doesn't exist
        pass

    if found_in_memory or found_in_file:
        return {
            "status": "deleted",
            "message": f"Fact check for message {message_index} deleted",
        }

    return {
        "status": "not_found",
        "message": f"No fact check found for message {message_index}",
    }
