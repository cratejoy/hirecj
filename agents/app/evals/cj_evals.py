"""HireCJ-specific evaluators."""

import logging
from typing import List, Dict, Any, Set
from collections import defaultdict

from .base import CJEval, EvalSample, EvalResult, EvalStatus, ModelGraded

logger = logging.getLogger(__name__)


class ToolSelectionAccuracy(CJEval):
    """Evaluates whether CJ selects appropriate tools for the task."""
    
    def __init__(self, mode: str = "strict", weights: Dict[str, float] = None, 
                 tool_categories: Dict[str, List[str]] = None, **kwargs):
        super().__init__(**kwargs)
        self.mode = mode
        self.weights = weights or {
            "correct_tool": 1.0,
            "acceptable_alternative": 0.8,
            "unnecessary_tool": -0.3,
            "missing_tool": -0.5
        }
        self.tool_categories = tool_categories or {}
        
    def eval_sample(self, sample: EvalSample) -> EvalResult:
        """Evaluate tool selection accuracy."""
        try:
            # Extract tool information
            actual_tools = set(sample.actual.get("tool_calls", []))
            
            # Get expected tools from ideal
            tool_selection = sample.ideal.get("tool_selection", {})
            should_use_tool = tool_selection.get("should_use_tool", False)
            acceptable_tools = set(tool_selection.get("acceptable_tools", []))
            unacceptable_tools = set(tool_selection.get("unacceptable_tools", []))
            
            # Handle case where no tools should be used
            if not should_use_tool:
                if len(actual_tools) == 0:
                    return EvalResult(
                        sample_id=sample.sample_id,
                        status=EvalStatus.PASS,
                        score=1.0,
                        reason="Correctly did not use any tools",
                        details={
                            "expected_tools": False,
                            "actual_tools": list(actual_tools)
                        }
                    )
                else:
                    return EvalResult(
                        sample_id=sample.sample_id,
                        status=EvalStatus.FAIL,
                        score=0.0,
                        reason=f"Used tools when none were needed: {actual_tools}",
                        details={
                            "expected_tools": False,
                            "actual_tools": list(actual_tools),
                            "unnecessary_tools": list(actual_tools)
                        }
                    )
            
            # Calculate score based on tool usage
            score = 0.0
            correct_tools = actual_tools & acceptable_tools
            wrong_tools = actual_tools & unacceptable_tools
            unnecessary_tools = actual_tools - acceptable_tools - unacceptable_tools
            missing_tools = acceptable_tools - actual_tools
            
            # Apply weights
            score += len(correct_tools) * self.weights["correct_tool"]
            score += len(wrong_tools) * self.weights.get("wrong_tool", -1.0)
            score += len(unnecessary_tools) * self.weights["unnecessary_tool"]
            score += len(missing_tools) * self.weights["missing_tool"]
            
            # Check for acceptable alternatives through categories
            if self.tool_categories and self.mode != "strict":
                for tool in unnecessary_tools.copy():
                    # Check if tool is in same category as an acceptable tool
                    for category, tools_in_category in self.tool_categories.items():
                        if tool in tools_in_category:
                            # Check if any acceptable tool is in same category
                            if any(t in tools_in_category for t in acceptable_tools):
                                unnecessary_tools.remove(tool)
                                score += self.weights["acceptable_alternative"]
                                break
            
            # Normalize score to 0-1 range
            max_possible_score = len(acceptable_tools) * self.weights["correct_tool"]
            if max_possible_score > 0:
                normalized_score = max(0, min(1, score / max_possible_score))
            else:
                normalized_score = 1.0 if len(actual_tools) == 0 else 0.0
            
            # Determine pass/fail
            if self.mode == "strict":
                passes = correct_tools == acceptable_tools and len(wrong_tools) == 0
            else:
                passes = len(correct_tools) > 0 and len(wrong_tools) == 0
            
            # Build reason
            reasons = []
            if correct_tools:
                reasons.append(f"Used correct tools: {correct_tools}")
            if wrong_tools:
                reasons.append(f"Used unacceptable tools: {wrong_tools}")
            if unnecessary_tools:
                reasons.append(f"Used unnecessary tools: {unnecessary_tools}")
            if missing_tools:
                reasons.append(f"Missing required tools: {missing_tools}")
                
            reason = "; ".join(reasons) if reasons else "Tool selection correct"
            
            return EvalResult(
                sample_id=sample.sample_id,
                status=EvalStatus.PASS if passes else EvalStatus.FAIL,
                score=normalized_score,
                reason=reason,
                details={
                    "actual_tools": list(actual_tools),
                    "acceptable_tools": list(acceptable_tools),
                    "unacceptable_tools": list(unacceptable_tools),
                    "correct_tools": list(correct_tools),
                    "wrong_tools": list(wrong_tools),
                    "unnecessary_tools": list(unnecessary_tools),
                    "missing_tools": list(missing_tools),
                    "mode": self.mode
                }
            )
            
        except Exception as e:
            logger.error(f"Error in ToolSelectionAccuracy eval: {e}")
            return EvalResult(
                sample_id=sample.sample_id,
                status=EvalStatus.ERROR,
                score=0.0,
                error=str(e)
            )


class ResponseQuality(ModelGraded):
    """Evaluates CJ's response quality across multiple dimensions."""
    
    def __init__(self, metrics: List[str] = None, threshold: float = 0.85, 
                 grading_prompt: str = None, **kwargs):
        super().__init__(**kwargs)
        self.metrics = metrics or [
            "helpfulness",
            "relevance", 
            "tone_appropriateness",
            "clarity",
            "actionability"
        ]
        self.threshold = threshold
        self.grading_prompt_template = grading_prompt
        
    def create_grading_prompt(self, sample: EvalSample) -> str:
        """Create the prompt for grading response quality."""
        if self.grading_prompt_template:
            prompt = self.grading_prompt_template
        else:
            prompt = f"""Evaluate the assistant's response on the following criteria:
- Helpfulness: Does the response address the user's needs?
- Relevance: Is the response on-topic and appropriate?
- Tone: Does CJ maintain the right tone for the persona/scenario?
- Clarity: Is the response clear and easy to understand?
- Actionability: Does CJ provide specific, actionable advice?

User Input: {sample.actual.get('user_input', '')}
Assistant Response: {sample.actual.get('response', '')}
Context: {sample.input.get('context', {})}

Score each criterion from 0-1 and provide an overall score.
Format your response as:
SCORES: helpfulness=X.X, relevance=X.X, tone=X.X, clarity=X.X, actionability=X.X
OVERALL: X.X
REASON: Brief explanation"""

        return prompt
        
    def eval_sample(self, sample: EvalSample) -> EvalResult:
        """Evaluate response quality using model grading.
        
        Note: This is a placeholder that returns mock results.
        In production, this would call the grading model.
        """
        # For now, return a mock result based on response length
        # In production, this would use create_grading_prompt and call the model
        response = sample.actual.get("response", "")
        
        # Simple heuristic scoring for testing
        score = min(1.0, len(response) / 200)  # Longer responses score higher up to 200 chars
        
        return EvalResult(
            sample_id=sample.sample_id,
            status=EvalStatus.PASS if score >= self.threshold else EvalStatus.FAIL,
            score=score,
            reason=f"Response quality score: {score:.2f}",
            details={
                "metrics": self.metrics,
                "threshold": self.threshold,
                "response_length": len(response),
                "note": "Mock scoring - production would use model grading"
            }
        )


class GroundingRelevance(ModelGraded):
    """Evaluates the relevance and quality of grounding queries."""
    
    def __init__(self, min_relevance: float = 0.7, **kwargs):
        super().__init__(**kwargs)
        self.min_relevance = min_relevance
        
    def eval_sample(self, sample: EvalSample) -> EvalResult:
        """Evaluate grounding query relevance.
        
        Note: Placeholder implementation.
        """
        grounding_queries = sample.actual.get("grounding_queries", [])
        
        if not grounding_queries:
            # No grounding queries - might be OK depending on context
            return EvalResult(
                sample_id=sample.sample_id,
                status=EvalStatus.SKIP,
                score=0.0,
                reason="No grounding queries to evaluate",
                details={
                    "grounding_queries": []
                }
            )
            
        # Mock evaluation - in production would use model grading
        return EvalResult(
            sample_id=sample.sample_id,
            status=EvalStatus.PASS,
            score=0.8,
            reason="Grounding queries appear relevant (mock evaluation)",
            details={
                "grounding_queries": grounding_queries,
                "min_relevance": self.min_relevance,
                "note": "Mock evaluation - production would use model grading"
            }
        )


class ToolUsageEfficiency(CJEval):
    """Evaluates efficient use of tools (avoiding redundant calls)."""
    
    def __init__(self, max_redundancy: float = 0.1, max_calls_per_turn: int = 5,
                 check_sequencing: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.max_redundancy = max_redundancy
        self.max_calls_per_turn = max_calls_per_turn
        self.check_sequencing = check_sequencing
        
    def eval_sample(self, sample: EvalSample) -> EvalResult:
        """Evaluate tool usage efficiency.
        
        Note: Placeholder implementation.
        """
        tool_calls = sample.actual.get("tool_calls", [])
        
        if not tool_calls:
            return EvalResult(
                sample_id=sample.sample_id,
                status=EvalStatus.SKIP,
                score=0.0,
                reason="No tool calls to evaluate",
                details={"tool_calls": []}
            )
            
        # Check for redundant calls
        unique_calls = set(tool_calls)
        redundancy_ratio = 1 - (len(unique_calls) / len(tool_calls)) if tool_calls else 0
        
        # Check call count
        too_many_calls = len(tool_calls) > self.max_calls_per_turn
        
        # Calculate score
        score = 1.0
        if redundancy_ratio > self.max_redundancy:
            score -= 0.3
        if too_many_calls:
            score -= 0.2
            
        passes = score >= 0.7 and redundancy_ratio <= self.max_redundancy
        
        return EvalResult(
            sample_id=sample.sample_id,
            status=EvalStatus.PASS if passes else EvalStatus.FAIL,
            score=max(0, score),
            reason=f"Tool efficiency: {len(tool_calls)} calls, {redundancy_ratio:.1%} redundancy",
            details={
                "total_calls": len(tool_calls),
                "unique_calls": len(unique_calls),
                "redundancy_ratio": redundancy_ratio,
                "max_redundancy": self.max_redundancy,
                "max_calls_per_turn": self.max_calls_per_turn
            }
        )


class WorkflowCompliance(CJEval):
    """Ensures responses follow workflow-specific rules."""
    
    def __init__(self, strict_mode: bool = True, check_required_elements: bool = True,
                 check_transitions: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.strict_mode = strict_mode
        self.check_required_elements = check_required_elements
        self.check_transitions = check_transitions
        
    def eval_sample(self, sample: EvalSample) -> EvalResult:
        """Evaluate workflow compliance.
        
        Note: Placeholder - would need workflow rules to implement fully.
        """
        workflow = sample.input.get("context", {}).get("workflow", "unknown")
        
        # Placeholder logic - in production would check actual workflow rules
        return EvalResult(
            sample_id=sample.sample_id,
            status=EvalStatus.PASS,
            score=1.0,
            reason=f"Workflow compliance check passed for {workflow}",
            details={
                "workflow": workflow,
                "strict_mode": self.strict_mode,
                "note": "Placeholder - needs workflow rules implementation"
            }
        )