"""
Unified async fact-checking engine for verifying CJ's claims against universe data.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import json
from datetime import datetime
import aiohttp
import yaml
from pathlib import Path
import logging

from app.model_config.simple_config import get_model, get_api_key, ModelPurpose
from app.agents.tool_output_parser import ToolOutputParser
from app.config import settings

logger = logging.getLogger(__name__)


class VerificationStatus(Enum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    INCORRECT = "INCORRECT"


class Severity(Enum):
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"


@dataclass
class FactClaim:
    """Represents a factual claim made by CJ"""

    claim: str
    verification: VerificationStatus
    actual_data: Optional[str] = None
    source: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim": self.claim,
            "verification": self.verification.value,
            "actual_data": self.actual_data,
            "source": self.source,
        }


@dataclass
class FactIssue:
    """Represents a fact-checking issue found"""

    severity: Severity
    summary: str
    claim: Optional[str] = None
    expected: Optional[str] = None
    actual: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity.value,
            "summary": self.summary,
            "claim": self.claim,
            "expected": self.expected,
            "actual": self.actual,
        }


@dataclass
class FactCheckResult:
    """Result of fact-checking a CJ response"""

    overall_status: str  # "PASS", "WARNING", "FAIL"
    claims: List[FactClaim] = field(default_factory=list)
    issues: List[FactIssue] = field(default_factory=list)
    execution_time: float = 0.0
    turn_number: Optional[int] = None

    @property
    def has_issues(self) -> bool:
        return len(self.issues) > 0

    @property
    def critical_issues(self) -> List[FactIssue]:
        return [i for i in self.issues if i.severity == Severity.CRITICAL]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_status": self.overall_status,
            "claims": [c.to_dict() for c in self.claims],
            "issues": [i.to_dict() for i in self.issues],
            "execution_time": self.execution_time,
            "turn_number": self.turn_number,
        }


class ConversationFactChecker:
    """Async fact-checker for CJ's responses against universe data"""

    def __init__(
        self,
        universe_data: Dict[str, Any],
        evaluator_model: Optional[str] = None,
        enable_strict_mode: bool = None,
    ):
        """Initialize fact checker

        Args:
            universe_data: Universe data containing facts to check against
            evaluator_model: Optional model name for evaluation
            enable_strict_mode: Whether to use strict fact-checking mode
        """
        self.universe_data = universe_data
        self.tool_parser = ToolOutputParser()

        # Load configuration first
        self.config = {}
        self.prompts = {}
        self.error_messages = {}

        try:
            self._load_config()
            self._load_prompts()
            self._load_error_messages()
        except Exception as e:
            # If loading fails, use defaults
            logger.warning(f"Failed to load config/prompts: {e}, using defaults")
            self.config = {"evaluation_modes": {"strict_mode": False}}
            self.prompts = {
                "system_prompt": "You are a fact checker.",
                "extract_claims_prompt": "Extract claims from: {cj_response}\n\nContext: {context}",
            }
            self.error_messages = {}

        # Set mode
        if enable_strict_mode is None:
            enable_strict_mode = self.config.get("evaluation_modes", {}).get(
                "strict_mode", False
            )
        self.strict_mode = enable_strict_mode

        # Get model configuration
        self.model = evaluator_model or get_model(ModelPurpose.TEST_EVALUATION)
        self.api_key = get_api_key(self.model)
        # Use configured OpenAI API URL
        self.base_url = settings.openai_api_url

        # Cache for results
        self._cache: Dict[int, FactCheckResult] = {}

    def _load_config(self):
        """Load configuration from YAML"""
        config_path = (
            Path(__file__).parent.parent.parent
            / "prompts"
            / "fact_checking"
            / "config.yaml"
        )
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

    def _load_prompts(self):
        """Load prompts from YAML"""
        prompts_path = (
            Path(__file__).parent.parent.parent
            / "prompts"
            / "fact_checking"
            / "prompts.yaml"
        )
        with open(prompts_path, "r") as f:
            self.prompts = yaml.safe_load(f)

    def _load_error_messages(self):
        """Load error messages from YAML"""
        errors_path = (
            Path(__file__).parent.parent.parent
            / "prompts"
            / "fact_checking"
            / "error_messages.yaml"
        )
        with open(errors_path, "r") as f:
            self.error_messages = yaml.safe_load(f)

    async def extract_claims(
        self,
        cj_response: str,
        tool_outputs: List[Dict[str, Any]] = None,
        context_window: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Extract factual claims from CJ's response

        Args:
            cj_response: The response text to analyze
            tool_outputs: Optional tool outputs referenced in response
            context_window: Optional conversation context

        Returns:
            Dict containing extracted claims
        """
        # Build context
        context_parts = []

        # Add tool outputs if available
        if tool_outputs:
            context_parts.append(
                f"Tool outputs referenced:\n{self._format_tool_outputs(tool_outputs)}"
            )

        # Add conversation context if available
        if context_window:
            context_str = "\n".join(
                [f"{msg['sender']}: {msg['content']}" for msg in context_window[-3:]]
            )
            context_parts.append(f"Recent conversation:\n{context_str}")

        # Add universe data summary
        context_parts.append(
            f"Universe data summary:\n{json.dumps(self.universe_data, indent=2)[:settings.universe_data_preview_length]}..."
        )

        context = "\n\n".join(context_parts)

        # Build prompt
        prompt = self.prompts["extract_claims_prompt"].format(
            cj_response=cj_response, context=context
        )

        # Call API
        start_time = datetime.now()
        claims_data = await self._call_api(prompt)
        execution_time = (datetime.now() - start_time).total_seconds()

        claims_data["execution_time"] = execution_time
        return claims_data

    async def _call_api(self, prompt: str) -> Dict[str, Any]:
        """Call OpenAI API with the prompt (async version)"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Get API configuration from YAML
        api_config = self.config["api"]

        data = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": self.prompts["system_prompt"],
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": api_config["temperature"],
            "max_tokens": api_config["max_tokens"],
            "response_format": {"type": api_config["response_format"]},
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.base_url, headers=headers, json=data
            ) as response:
                response.raise_for_status()
                result = await response.json()

        content = result["choices"][0]["message"]["content"]

        # Extract JSON from response
        return self._extract_json(content)

    def _format_tool_outputs(self, tool_outputs: List[Dict[str, Any]]) -> str:
        """Format tool outputs for prompt context"""
        if not tool_outputs:
            return "No tool outputs in this turn"

        formatted = []
        for output in tool_outputs:
            tool_name = output.get("tool", "unknown")
            tool_input = output.get("input", "")
            tool_output = output.get("output", "")
            formatted.append(
                f"Tool: {tool_name}\nInput: {tool_input}\nOutput: {tool_output}"
            )

        return "\n\n".join(formatted)

    def _extract_json(self, response: str) -> Dict[str, Any]:
        """Extract JSON from API response"""
        # Implementation remains the same as sync version
        return json.loads(response)

    def verify_claims(self, claims_data: Dict[str, Any]) -> FactCheckResult:
        """Verify extracted claims against universe data"""
        # This method doesn't do I/O, so it can remain synchronous
        claims = []
        issues = []

        # Process each claim from the claims_data
        for claim_info in claims_data.get("claims", []):
            claim_text = claim_info.get("claim", "")
            verification_str = claim_info.get("verification", "UNVERIFIED")
            actual_data = claim_info.get("actual_data")
            source = claim_info.get("source", "universe_data")

            # Convert string verification to enum
            try:
                verification = VerificationStatus[verification_str]
            except KeyError:
                verification = VerificationStatus.UNVERIFIED

            claim = FactClaim(
                claim=claim_text,
                verification=verification,
                actual_data=actual_data,
                source=source,
            )
            claims.append(claim)

        # Process any issues from the claims_data
        for issue_info in claims_data.get("issues", []):
            severity_str = issue_info.get("severity", "minor")
            try:
                severity = Severity(severity_str)
            except ValueError:
                severity = Severity.MINOR

            issue = FactIssue(
                severity=severity,
                summary=issue_info.get("summary", ""),
                claim=issue_info.get("claim"),
                expected=issue_info.get("expected"),
                actual=issue_info.get("actual"),
            )
            issues.append(issue)

        # Determine overall status
        if any(issue.severity == Severity.CRITICAL for issue in issues):
            overall_status = "FAIL"
        elif any(issue.severity == Severity.MAJOR for issue in issues):
            overall_status = "WARNING"
        else:
            overall_status = "PASS"

        return FactCheckResult(
            overall_status=overall_status,
            claims=claims,
            issues=issues,
            execution_time=claims_data.get("execution_time", 0.0),
        )

    def parse_tool_outputs(self, captured_output: str) -> List[Dict[str, Any]]:
        """Parse tool outputs from captured string"""
        return self.tool_parser.parse_tool_outputs(captured_output)

    async def check_facts(
        self,
        cj_response: str,
        tool_outputs: List[Dict[str, Any]] = None,
        captured_output: str = None,
        turn_number: int = 0,
        context_window: Optional[List[Dict[str, Any]]] = None,
    ) -> FactCheckResult:
        """Main async method to check facts in CJ's response

        Args:
            cj_response: CJ's response text
            tool_outputs: Structured tool outputs (if available)
            captured_output: Raw captured output string (if tool_outputs not provided)
            turn_number: Turn number in conversation
            context_window: Recent conversation context

        Returns:
            FactCheckResult with verification details
        """
        # Check cache first
        if turn_number in self._cache:
            cached_result = self._cache[turn_number]
            logger.info(f"Returning cached result for turn {turn_number}")
            return cached_result

        try:
            # Parse tool outputs if needed
            if captured_output and not tool_outputs:
                tool_outputs = self.parse_tool_outputs(captured_output)

            # Extract claims (async)
            claims_data = await self.extract_claims(
                cj_response, tool_outputs, context_window
            )

            # Verify claims (sync - no I/O)
            result = self.verify_claims(claims_data)
            result.turn_number = turn_number

            # Cache result
            self._cache[turn_number] = result

            return result

        except Exception as e:
            logger.error(f"Error checking facts: {e}")
            return FactCheckResult(
                overall_status="ERROR",
                turn_number=turn_number,
                issues=[
                    FactIssue(
                        severity=Severity.CRITICAL,
                        summary=f"Fact-checking error: {str(e)}",
                    )
                ],
            )
