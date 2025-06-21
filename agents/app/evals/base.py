"""Base evaluation classes for HireCJ evals framework."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Union
from enum import Enum
import difflib
import logging
from openai import OpenAI

from ..config import settings

logger = logging.getLogger(__name__)


class EvalStatus(Enum):
    """Status of an evaluation."""
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    SKIP = "skip"


@dataclass
class EvalSample:
    """A single evaluation sample."""
    eval_id: str
    sample_id: str
    input: Dict[str, Any]
    ideal: Optional[Dict[str, Any]] = None
    actual: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class EvalResult:
    """Result of evaluating a single sample."""
    sample_id: str
    status: EvalStatus
    score: float  # 0.0 to 1.0
    reason: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class CJEval(ABC):
    """Base class for all HireCJ evaluations."""
    
    def __init__(self, **kwargs):
        """Initialize with eval-specific arguments."""
        self.args = kwargs
        
    @abstractmethod
    def eval_sample(self, sample: EvalSample) -> EvalResult:
        """Evaluate a single sample.
        
        Args:
            sample: The sample to evaluate
            
        Returns:
            EvalResult with status, score, and details
        """
        pass
    
    def __repr__(self):
        return f"{self.__class__.__name__}({self.args})"


class ExactMatch(CJEval):
    """Exact matching of responses."""
    
    def __init__(self, case_sensitive: bool = False, strip_whitespace: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.case_sensitive = case_sensitive
        self.strip_whitespace = strip_whitespace
        
    def eval_sample(self, sample: EvalSample) -> EvalResult:
        """Check if actual response exactly matches ideal response."""
        try:
            # Extract expected and actual values
            expected = sample.ideal.get("response", "")
            actual = sample.actual.get("response", "")
            
            # Normalize based on settings
            if self.strip_whitespace:
                expected = expected.strip()
                actual = actual.strip()
                
            if not self.case_sensitive:
                expected = expected.lower()
                actual = actual.lower()
            
            # Check match
            matches = expected == actual
            
            return EvalResult(
                sample_id=sample.sample_id,
                status=EvalStatus.PASS if matches else EvalStatus.FAIL,
                score=1.0 if matches else 0.0,
                reason=None if matches else f"Expected: '{expected}', Got: '{actual}'",
                details={
                    "expected": expected,
                    "actual": actual,
                    "normalized": {
                        "case_sensitive": self.case_sensitive,
                        "strip_whitespace": self.strip_whitespace
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Error in ExactMatch eval: {e}")
            return EvalResult(
                sample_id=sample.sample_id,
                status=EvalStatus.ERROR,
                score=0.0,
                error=str(e)
            )


class FuzzyMatch(CJEval):
    """Fuzzy matching with configurable threshold."""
    
    def __init__(self, threshold: float = 0.8, algorithm: str = "ratio", **kwargs):
        super().__init__(**kwargs)
        self.threshold = threshold
        self.algorithm = algorithm
        
    def eval_sample(self, sample: EvalSample) -> EvalResult:
        """Check if actual response fuzzy matches ideal response."""
        try:
            # Extract expected and actual values
            expected = sample.ideal.get("response", "")
            actual = sample.actual.get("response", "")
            
            # Calculate similarity based on algorithm
            if self.algorithm == "ratio":
                similarity = difflib.SequenceMatcher(None, expected, actual).ratio()
            elif self.algorithm == "partial":
                # Check if expected is substring of actual
                similarity = 1.0 if expected.lower() in actual.lower() else 0.0
            else:
                raise ValueError(f"Unknown algorithm: {self.algorithm}")
            
            # Check if similarity meets threshold
            passes = similarity >= self.threshold
            
            return EvalResult(
                sample_id=sample.sample_id,
                status=EvalStatus.PASS if passes else EvalStatus.FAIL,
                score=similarity,
                reason=None if passes else f"Similarity {similarity:.2f} below threshold {self.threshold}",
                details={
                    "expected": expected,
                    "actual": actual,
                    "similarity": similarity,
                    "threshold": self.threshold,
                    "algorithm": self.algorithm
                }
            )
            
        except Exception as e:
            logger.error(f"Error in FuzzyMatch eval: {e}")
            return EvalResult(
                sample_id=sample.sample_id,
                status=EvalStatus.ERROR,
                score=0.0,
                error=str(e)
            )


class Includes(CJEval):
    """Checks if response includes required elements."""
    
    def __init__(self, case_sensitive: bool = False, all_required: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.case_sensitive = case_sensitive
        self.all_required = all_required
        
    def eval_sample(self, sample: EvalSample) -> EvalResult:
        """Check if actual response includes required elements."""
        try:
            # Extract required elements and actual response
            required_elements = sample.ideal.get("must_include", [])
            actual = sample.actual.get("response", "")
            
            if not self.case_sensitive:
                actual = actual.lower()
                required_elements = [elem.lower() for elem in required_elements]
            
            # Check which elements are included
            included = []
            missing = []
            
            for element in required_elements:
                if element in actual:
                    included.append(element)
                else:
                    missing.append(element)
            
            # Calculate score
            if not required_elements:
                score = 1.0
                passes = True
            else:
                score = len(included) / len(required_elements)
                passes = len(missing) == 0 if self.all_required else len(included) > 0
            
            return EvalResult(
                sample_id=sample.sample_id,
                status=EvalStatus.PASS if passes else EvalStatus.FAIL,
                score=score,
                reason=None if passes else f"Missing required elements: {missing}",
                details={
                    "required": required_elements,
                    "included": included,
                    "missing": missing,
                    "all_required": self.all_required
                }
            )
            
        except Exception as e:
            logger.error(f"Error in Includes eval: {e}")
            return EvalResult(
                sample_id=sample.sample_id,
                status=EvalStatus.ERROR,
                score=0.0,
                error=str(e)
            )


class ModelGraded(CJEval):
    """Uses another model to grade the response.
    
    This is a base class for model-graded evals. Subclasses should
    implement the grading prompt and scoring logic.
    """
    
    def __init__(self, grader_model: str = "gpt-4", temperature: float = 0.0, 
                 max_tokens: int = 100, **kwargs):
        super().__init__(**kwargs)
        self.grader_model = grader_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Initialize OpenAI client if API key is available
        self.client = None
        if settings.openai_api_key:
            self.client = OpenAI(api_key=settings.openai_api_key)
        else:
            logger.warning("No OpenAI API key found in settings - ModelGraded evals will fail")
        
    def eval_sample(self, sample: EvalSample) -> EvalResult:
        """Grade the response using another model."""
        try:
            # Get the response to evaluate
            response = sample.actual.get("response", "")
            
            # Get grading prompt from args or use default
            grading_prompt_template = self.args.get("grading_prompt")
            if not grading_prompt_template:
                grading_prompt_template = self.create_grading_prompt(sample)
            
            # Format the prompt with the response
            grading_prompt = grading_prompt_template.format(response=response)
            
            # Call OpenAI API
            try:
                if not self.client:
                    raise ValueError("OpenAI client not initialized - missing API key")
                    
                completion = self.client.chat.completions.create(
                    model=self.grader_model,
                    messages=[
                        {"role": "system", "content": "You are an evaluation assistant. Follow the instructions exactly."},
                        {"role": "user", "content": grading_prompt}
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
                
                grading_response = completion.choices[0].message.content.strip()
                
            except Exception as e:
                # If OpenAI fails, return error
                logger.error(f"OpenAI API error: {e}")
                return EvalResult(
                    sample_id=sample.sample_id,
                    status=EvalStatus.ERROR,
                    score=0.0,
                    error=f"OpenAI API error: {str(e)}"
                )
            
            # Parse the response
            if "PASS" in grading_response and "FAIL" not in grading_response:
                status = EvalStatus.PASS
                score = 1.0
            elif "FAIL" in grading_response:
                status = EvalStatus.FAIL
                score = 0.0
            else:
                # If we can't parse, return error
                return EvalResult(
                    sample_id=sample.sample_id,
                    status=EvalStatus.ERROR,
                    score=0.0,
                    error=f"Could not parse grading response: {grading_response}"
                )
            
            # Extract reason (everything after PASS/FAIL)
            reason = grading_response.replace("PASS", "").replace("FAIL", "").strip(" -")
            
            return EvalResult(
                sample_id=sample.sample_id,
                status=status,
                score=score,
                reason=reason if reason else grading_response,
                details={
                    "response_evaluated": response,
                    "grader_model": self.grader_model,
                    "grading_response": grading_response
                }
            )
            
        except Exception as e:
            logger.error(f"Error in ModelGraded eval: {e}")
            return EvalResult(
                sample_id=sample.sample_id,
                status=EvalStatus.ERROR,
                score=0.0,
                error=str(e)
            )
    
    def create_grading_prompt(self, sample: EvalSample) -> str:
        """Create the prompt for the grading model.
        
        Subclasses should override this method.
        """
        raise NotImplementedError("Subclasses must implement create_grading_prompt")
    
    def parse_grading_response(self, response: str) -> tuple[float, str]:
        """Parse the grading model's response into score and reason.
        
        Subclasses should override this method.
        
        Returns:
            Tuple of (score, reason)
        """
        raise NotImplementedError("Subclasses must implement parse_grading_response")