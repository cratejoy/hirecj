"""Merchant Agent - Represents the business owner in conversations."""

from crewai import Agent
from app.prompts.loader import PromptLoader
from app.scenarios.loader import ScenarioLoader
from app.model_config.simple_config import get_model, ModelPurpose


def create_merchant_agent(
    merchant_name: str, scenario_name: str, conversation_state=None
) -> Agent:
    """Create merchant agent with scenario context."""
    prompt_loader = PromptLoader()
    scenario_loader = ScenarioLoader()

    # Load merchant persona
    merchant_data = prompt_loader.load_merchant_persona(merchant_name, "v1.0.0")
    merchant_prompt = merchant_data["prompt"]

    # Load scenario
    scenario_data = scenario_loader.get_scenario(scenario_name)
    scenario_text = scenario_data["scenario"]

    # Build full backstory
    backstory = f"{merchant_prompt}\n\nCURRENT SITUATION:\n{scenario_text}"

    # Add conversation context if available
    if conversation_state and conversation_state.context_window:
        history = []
        for msg in conversation_state.context_window[-5:]:  # Last 5 messages
            history.append(f"{msg.sender.upper()}: {msg.content}")
        backstory += "\n\nRECENT CONVERSATION:\n" + "\n".join(history)

    return Agent(
        role=f"{merchant_name} - Business Owner",
        goal="Get help from CJ to solve business problems and grow the company",
        backstory=backstory,
        verbose=True,
        allow_delegation=False,
        llm=get_model(ModelPurpose.CONVERSATION_MERCHANT),
    )
