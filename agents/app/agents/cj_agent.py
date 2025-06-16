"""CJ Agent - AI Customer Support Lead for merchant conversations."""

from typing import Dict, Any, Optional, List
from crewai import Agent
from app.models import ConversationState
from app.model_config.simple_config import get_model, get_provider, ModelPurpose
from shared.logging_config import get_logger
from app.config import settings
from app.agents.universe_data_agent import UniverseDataAgent

logger = get_logger(__name__)


class CJAgent:
    """CJ agent for customer support conversations."""

    def __init__(
        self,
        merchant_name: str,
        scenario_name: str,
        cj_version: str = None,
        enable_caching: bool = None,
        enable_fact_checking: bool = None,
        **kwargs,
    ):
        self.merchant_name = merchant_name
        self.scenario_name = scenario_name
        self.cj_version = cj_version or settings.default_cj_version
        # Use global settings if not explicitly provided
        self.enable_fact_checking = (
            enable_fact_checking
            if enable_fact_checking is not None
            else settings.enable_fact_checking
        )
        self.enable_caching = (
            enable_caching
            if enable_caching is not None
            else settings.enable_prompt_caching
        )

        # Get model configuration
        self.model_name = get_model(ModelPurpose.CONVERSATION_CJ)
        self.provider = get_provider(self.model_name)

        logger.info(f"[CJ_AGENT] Using model: {self.model_name}")
        if self.enable_caching and self.provider == "anthropic":
            logger.info("[CJ_AGENT] Caching enabled for Anthropic model")

        # Extract common parameters
        self.data_agent: Optional[UniverseDataAgent] = kwargs.pop("data_agent", None)
        self.user_id: Optional[str] = kwargs.pop("user_id", None)
        self.workflow_name = kwargs.pop("workflow_name", None)
        self.conversation_state = kwargs.pop("conversation_state", None)
        self.scenario_context = kwargs.pop("scenario_context", "")
        self.verbose = kwargs.pop("verbose", True)
        self.oauth_metadata = kwargs.pop("oauth_metadata", None)
        
        # DIAGNOSTIC: Log agent initialization
        from datetime import datetime
        logger.warning(f"[AGENT_INIT] Creating CJ agent - merchant={merchant_name}, workflow={self.workflow_name}, "
                      f"oauth_present={bool(self.oauth_metadata)}, timestamp={datetime.now()}")

        # Log memory status
        if self.user_id:
            # Facts will be loaded when needed
            fact_count = 0  # We'll get actual count when we load facts
            logger.info(f"[CJ_AGENT] Initialized with {fact_count} merchant memory facts")
        else:
            logger.info(f"[CJ_AGENT] Initialized without merchant memory")

        # Load prompts and tools
        self._load_components()

        # Create the CrewAI agent
        self.agent = self._create_agent(**kwargs)

    def _load_components(self):
        """Load prompts, workflows, and tools."""
        from app.prompts.loader import PromptLoader
        from app.workflows.loader import WorkflowLoader

        prompt_loader = PromptLoader()
        workflow_loader = WorkflowLoader()

        # Load prompt template
        self.prompt_data = prompt_loader.load_cj_prompt(self.cj_version)
        self.prompt_template = self.prompt_data.get("prompt", "")

        # Load workflow if specified
        self.workflow_data = None
        if self.workflow_name:
            self.workflow_data = workflow_loader.get_workflow(self.workflow_name)

        # Load tools
        self.tools = self._load_tools()

    def _build_context(self) -> Dict[str, Any]:
        """Build context for prompt formatting."""
        context = {
            "scenario": self.scenario_name.replace("_", " ").title(),
            "merchant_name": self.merchant_name.replace("_", " ").title(),
            "workflow_name": "",
            "workflow_details": "",
            "recent_context": self._format_conversation_history(),
        }

        # Add workflow context
        if self.workflow_name and self.workflow_data:
            context["workflow_name"] = self.workflow_name.upper().replace("_", " ")
            context["workflow_details"] = self.workflow_data.get("workflow", "")

            # Add onboarding-specific context if available
            if self.workflow_name == "shopify_onboarding":
                onboarding_context = self._extract_onboarding_context()
                if onboarding_context:
                    context["workflow_details"] += f"\n\nCURRENT ONBOARDING STATE:\n{onboarding_context}"

        return context

    def _format_conversation_history(self, limit: int = None) -> str:
        """Format recent conversation history."""
        if limit is None:
            limit = settings.recent_history_limit

        if not self.conversation_state or not hasattr(
            self.conversation_state, "context_window"
        ):
            logger.debug("[CJ_AGENT] No conversation state provided")
            return "No previous messages."

        if not self.conversation_state.context_window:
            logger.debug("[CJ_AGENT] Empty context window")
            return "No previous messages."

        history = []
        messages = self.conversation_state.context_window[-limit:]

        for msg in messages:
            sender = msg.sender.upper()
            content = msg.content
            # Truncate very long messages
            if len(content) > settings.max_message_length:
                content = content[: settings.max_message_length - 3] + "..."
            history.append(f"{sender}: {content}")

        logger.info(f"[CJ_AGENT] Including {len(messages)} messages in context")
        formatted_history = "\n".join(history)
        logger.debug(f"[CJ_AGENT] Formatted history:\n{formatted_history}")
        return formatted_history

    def _load_tools(self) -> List[Any]:
        """Load appropriate tools based on data agent and workflow."""
        tools = []

        # Check if we should load database tools for support_daily workflow
        if self.workflow_name == "support_daily":
            try:
                from app.agents.database_tools import create_database_tools

                db_tools = create_database_tools(merchant_name=self.merchant_name)
                tools.extend(db_tools)
                logger.info(f"[CJ_AGENT] Loaded {len(db_tools)} database tools for support_daily workflow")

                # Log tool names for visibility
                db_tool_names = [tool.name for tool in db_tools]
                logger.info(f"[CJ_AGENT] Database tools: {', '.join(db_tool_names)}")
            except Exception as e:
                logger.warning(f"[CJ_AGENT] Could not load database tools: {e}")

        # Conditionally load Shopify tools if OAuth metadata is present
        logger.info(f"[CJ_AGENT] OAuth metadata check: oauth_metadata={self.oauth_metadata}")
        # TEMPORARY: Always load Shopify tools for testing
        if True or (self.oauth_metadata and self.oauth_metadata.get("provider") == "shopify"):
            try:
                from app.agents.shopify_tools import create_shopify_tools

                shopify_tools = create_shopify_tools()
                tools.extend(shopify_tools)
                logger.info(f"[CJ_AGENT] Loaded {len(shopify_tools)} Shopify tools")
                shopify_tool_names = [tool.name for tool in shopify_tools]
                logger.info(f"[CJ_AGENT] Shopify tools: {', '.join(shopify_tool_names)}")
            except Exception as e:
                logger.warning(f"[CJ_AGENT] Could not load Shopify tools: {e}")
        else:
            logger.info(f"[CJ_AGENT] Shopify tools not loaded: oauth_metadata={self.oauth_metadata}")

        if not self.data_agent:
            logger.debug("[CJ_AGENT] No data agent provided, skipping universe tools")
            return tools

        # Universe data agent
        if self.data_agent is not None:
            try:
                from app.agents.universe_tools import create_universe_tools

                universe_tools = create_universe_tools(self.data_agent)
                tools.extend(universe_tools)
                logger.info(f"[CJ_AGENT] Loaded {len(universe_tools)} universe tools")
                # Log tool names for visibility
                universe_tool_names = [tool.name for tool in universe_tools]
                logger.info(f"[CJ_AGENT] Universe tools: {', '.join(universe_tool_names)}")
            except Exception as e:
                logger.warning(f"[CJ_AGENT] Could not load universe tools: {e}")
        # No longer support deprecated data agents
        else:
            logger.warning(
                f"[CJ_AGENT] Unknown data agent type: {type(self.data_agent)}. "
                "Please use UniverseDataAgent instead."
            )

        return tools

    def _extract_onboarding_context(self) -> str:
        """Extract onboarding-specific context from conversation state."""
        context_parts = []

        if not self.conversation_state or not self.conversation_state.context_window:
            context_parts.append("Phase: New conversation - start with warm greeting")
        else:
            # Simple phase tracking based on conversation length
            message_count = len(self.conversation_state.context_window)

            if message_count <= 2:
                context_parts.append("Phase: Initial greeting - focus on making merchant comfortable")
            elif message_count <= 4:
                context_parts.append("Phase: Early conversation - naturally explore their needs")
            else:
                context_parts.append("Phase: Established conversation - guide based on merchant responses")

        # Check for OAuth status in session (passed through kwargs or state)
        oauth_metadata = getattr(self, 'oauth_metadata', None)
        if oauth_metadata and oauth_metadata.get('authenticated'):
            is_new = oauth_metadata.get('is_new_merchant', True)
            shop_domain = oauth_metadata.get('shop_domain', 'their store')

            if is_new:
                context_parts.append(f"OAuth Status: NEW merchant authenticated from {shop_domain} - they just connected their Shopify store for the first time!")
            else:
                context_parts.append(f"OAuth Status: RETURNING merchant authenticated from {shop_domain} - they've used HireCJ before")
        else:
            context_parts.append("OAuth Status: Not yet authenticated - guide them to connect their Shopify store when appropriate")

        return "\n".join(context_parts)

    def _create_agent(self, **kwargs) -> Agent:
        """Create the CrewAI agent instance."""
        # Build context and format prompt
        context = self._build_context()
        backstory = self.prompt_template.format(**context)

        # Add scenario context if provided
        if self.scenario_context:
            backstory = (
                f"CURRENT BUSINESS CONTEXT:\n{self.scenario_context}\n\n{backstory}"
            )

        # Add universe info if available
        if self.data_agent is not None:
            universe_info = self._get_universe_info()
            backstory += universe_info

        # Add merchant memory facts if available
        if self.user_id:
            # Get facts from user_identity
            from shared.user_identity import get_user_facts
            all_facts = get_user_facts(self.user_id)
            # Get up to 20 most recent facts
            facts = [f['fact'] for f in all_facts[-20:]]
            if facts:
                logger.info(f"[CJ_AGENT] [MEMORY] Injecting {len(facts)} facts into context for {self.merchant_name}")
                memory_context = "\n\nThings I know about this merchant from previous conversations:\n"
                for i, fact in enumerate(facts, 1):
                    memory_context += f"- {fact}\n"
                    logger.debug(f"[CJ_AGENT] [MEMORY] Fact {i}: {fact[:100]}...")
                backstory += memory_context
            else:
                logger.info(f"[CJ_AGENT] [MEMORY] No facts to inject for {self.merchant_name}")
        else:
            logger.info(f"[CJ_AGENT] [MEMORY] No merchant memory available for context")

        # Log agent creation
        logger.info("[CJ_AGENT] Creating CJ agent:")
        logger.info(f"[CJ_AGENT] - Merchant: {self.merchant_name}")
        logger.info(f"[CJ_AGENT] - Scenario: {self.scenario_name}")
        logger.info(f"[CJ_AGENT] - Workflow: {self.workflow_name or 'chat'}")
        logger.info(f"[CJ_AGENT] - Version: {self.cj_version}")
        logger.info(f"[CJ_AGENT] - Tools: {len(self.tools)} available")
        if self.tools:
            tool_names = [tool.name for tool in self.tools]
            logger.info(f"[CJ_AGENT] - Tool names: {', '.join(tool_names)}")
        logger.info(
            f"[CJ_AGENT] - Caching: {'enabled' if self.enable_caching and self.provider == 'anthropic' else 'disabled'}"
        )

        # Create agent with appropriate configuration
        agent_config = {
            "role": "CJ - AI Customer Support Lead",
            "goal": f"Provide excellent customer support as CJ for {self.merchant_name}",
            "backstory": backstory,
            "tools": self.tools,
            "verbose": self.verbose,
            "allow_delegation": False,
            "llm": self.model_name,
            **kwargs,
        }

        return Agent(**agent_config)

    def _get_universe_info(self) -> str:
        """Get universe context information."""
        if not self.data_agent:
            return ""

        try:
            universe = self.data_agent.universe
            metadata = universe.get("metadata", {})
            customers = universe.get("customers", [])
            tickets = universe.get("support_tickets", [])

            info = f"""
UNIVERSE DATA CONTEXT:
- Universe ID: {metadata.get('universe_id', 'unknown')}
- Current Day: {metadata.get('current_day', 'unknown')}/90
- Total Customers: {len(customers)}
- Total Tickets: {len(tickets)}
- Business MRR: ${self.data_agent.base_metrics.get('mrr', 0):,}
- CSAT: {self.data_agent.base_metrics.get('csat_score', 0)}/5

You have structured tools available to access detailed universe data. Use them to answer specific questions.
"""
            return info
        except Exception as e:
            logger.warning(f"[CJ_AGENT] Error building universe info: {e}")
            return ""


def create_cj_agent(
    merchant_name: str,
    scenario_name: str,
    cj_version: str = None,
    enable_caching: bool = None,
    enable_fact_checking: bool = None,
    workflow_name: Optional[str] = None,
    conversation_state: Optional[ConversationState] = None,
    data_agent: Optional[UniverseDataAgent] = None,
    user_id: Optional[str] = None,
    oauth_metadata: Optional[Dict[str, Any]] = None,
    scenario_context: str = "",
    verbose: bool = True,
    **kwargs,
) -> Agent:
    """Create a CJ agent for customer support conversations.

    Args:
        merchant_name: Name of the merchant persona (e.g., "marcus_thompson")
        scenario_name: Name of the business scenario (e.g., "high_volume_holiday")
        cj_version: Version of CJ prompts to use (default: from settings.default_cj_version)
        enable_caching: Enable Anthropic prompt caching (default: True)
        enable_fact_checking: Enable fact checking capabilities (default: True)
        workflow_name: Optional workflow name (e.g., "daily_briefing")
        conversation_state: Optional conversation state with history
        data_agent: Optional data agent for tools (UniverseDataAgent or other)
        user_id: Optional user ID for loading facts from database
        oauth_metadata: Optional OAuth metadata dict with authentication info
        scenario_context: Optional additional scenario context
        verbose: Enable verbose output (default: True)
        **kwargs: Additional arguments passed to Agent constructor

    Returns:
        Configured CJ agent ready for use
    """
    # DIAGNOSTIC: Log agent creation
    from datetime import datetime
    logger.warning(f"[AGENT_CREATE] create_cj_agent called - merchant={merchant_name}, scenario={scenario_name}, "
                  f"workflow={workflow_name}, oauth_present={bool(oauth_metadata)}, "
                  f"has_existing_state={bool(conversation_state)}, timestamp={datetime.now()}")
    
    cj = CJAgent(
        merchant_name=merchant_name,
        scenario_name=scenario_name,
        cj_version=cj_version,
        enable_caching=enable_caching,
        enable_fact_checking=enable_fact_checking,
        workflow_name=workflow_name,
        conversation_state=conversation_state,
        data_agent=data_agent,
        user_id=user_id,
        oauth_metadata=oauth_metadata,
        scenario_context=scenario_context,
        verbose=verbose,
        **kwargs,
    )
    return cj.agent
