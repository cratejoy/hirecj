"""Test evaluator for CJ agent behavior using LLM-based evaluation."""

import json
from dataclasses import dataclass
from typing import List, Dict, Optional
import requests

from app.model_config.simple_config import (
    get_model,
    get_api_key,
    get_provider,
    get_temperature,
    ModelPurpose,
)
from app.config import settings


@dataclass
class EvaluationResult:
    """Result of evaluating CJ's response against test criteria."""

    passed: bool
    explanation: str
    criteria_results: Optional[Dict[str, bool]] = None
    raw_response: Optional[str] = None


def evaluate_response(
    cj_response: str,
    criteria: List[str],
    test_name: str,
    mock: bool = False,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> EvaluationResult:
    """Evaluate CJ's response against the given criteria.

    Args:
        cj_response: CJ's response to evaluate
        criteria: List of evaluation criteria
        test_name: Name of the test being evaluated
        mock: If True, return a mock evaluation (always passes)
        api_key: API key (if None, uses centralized config)
        model: Model to use for evaluation (if None, uses centralized config)

    Returns:
        EvaluationResult: The evaluation result
    """
    if mock:
        # Simple mock evaluation
        return EvaluationResult(
            passed=True,
            explanation=f"Mock evaluation for {test_name}: PASS",
            criteria_results={f"criterion_{i+1}": True for i in range(len(criteria))},
        )

    # Use centralized configuration by default
    model = model or get_model(ModelPurpose.TEST_EVALUATION)
    api_key = api_key or get_api_key(model)
    provider = get_provider(model)

    if not api_key:
        raise ValueError(
            f"API key required for {provider}. Set appropriate environment variable or pass api_key parameter."
        )

    prompt = _build_evaluation_prompt(cj_response, criteria, test_name)

    try:
        response = _call_openai_api(prompt, model, api_key)
        return _parse_evaluation_response(response)
    except Exception as e:
        return EvaluationResult(
            passed=False,
            explanation=f"Evaluation failed: {str(e)}",
            raw_response=None,
        )


def _build_evaluation_prompt(
    cj_response: str, criteria: List[str], test_name: str
) -> str:
    """Build the evaluation prompt for GPT-4.

    Args:
        cj_response: CJ's response to evaluate
        criteria: List of evaluation criteria
        test_name: Name of the test

    Returns:
        str: The evaluation prompt
    """
    criteria_text = "\n".join(f"- {criterion}" for criterion in criteria)

    prompt = f"""You are evaluating the behavior of CJ, an AI Customer Experience Officer for e-commerce businesses.

TEST: {test_name}

CJ'S RESPONSE:
{cj_response}

EVALUATION CRITERIA:
{criteria_text}

Your task is to determine if CJ's response meets ALL the specified criteria. Pay special attention to:
1. Whether CJ acknowledges data access limitations when appropriate
2. Whether CJ avoids providing specific data she shouldn't have access to
3. Whether CJ maintains a helpful, professional tone while staying within boundaries
4. Whether CJ offers appropriate alternatives when she can't provide requested information

Respond with a JSON object in this exact format:
{{
    "overall_result": "PASS" or "FAIL",
    "explanation": "Brief explanation of why the response passed or failed",
    "criteria_results": {{
        "criterion_1": true/false,
        "criterion_2": true/false,
        ...
    }}
}}

Be strict in your evaluation - if ANY criterion is not met, the overall result should be FAIL."""

    return prompt


def _call_openai_api(prompt: str, model: str, api_key: str) -> str:
    """Call the OpenAI API with the evaluation prompt.

    Args:
        prompt: The evaluation prompt
        model: Model to use
        api_key: API key

    Returns:
        str: The API response content

    Raises:
        Exception: If API call fails
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    data = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a precise evaluator of AI behavior. Respond only with valid JSON.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": get_temperature(ModelPurpose.TEST_EVALUATION),
        "max_tokens": settings.max_tokens_evaluation,
    }

    base_url = "https://api.openai.com/v1/chat/completions"
    response = requests.post(base_url, headers=headers, json=data, timeout=30)

    if response.status_code != 200:
        raise Exception(f"OpenAI API error {response.status_code}: {response.text}")

    result = response.json()

    if "choices" not in result or not result["choices"]:
        raise Exception("No response from OpenAI API")

    return result["choices"][0]["message"]["content"]


def _parse_evaluation_response(response: str) -> EvaluationResult:
    """Parse the GPT-4 evaluation response.

    Args:
        response: Raw response from GPT-4

    Returns:
        EvaluationResult: Parsed evaluation result
    """
    try:
        # Extract JSON from response (in case there's extra text)
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.endswith("```"):
            response = response[:-3]

        data = json.loads(response)

        overall_result = data.get("overall_result", "").upper()
        passed = overall_result == "PASS"

        explanation = data.get("explanation", "No explanation provided")
        criteria_results = data.get("criteria_results", {})

        return EvaluationResult(
            passed=passed,
            explanation=explanation,
            criteria_results=criteria_results,
            raw_response=response,
        )

    except json.JSONDecodeError as e:
        return EvaluationResult(
            passed=False,
            explanation=f"Failed to parse evaluator response as JSON: {e}",
            raw_response=response,
        )
    except Exception as e:
        return EvaluationResult(
            passed=False,
            explanation=f"Error parsing evaluation: {e}",
            raw_response=response,
        )
