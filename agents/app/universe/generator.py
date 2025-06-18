"""Universe generation using existing project patterns."""

import yaml
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from crewai import LLM
import openai

from app.model_config.simple_config import get_model, ModelPurpose
from app.services.persona_service import PersonaService
from app.config import settings


class UniverseGenerator:
    """Generates universes using existing model config and prompt systems."""

    def __init__(self):
        """Initialize generator with existing project systems."""
        self.model_name = get_model(ModelPurpose.UNIVERSE_GENERATION)
        self.llm = LLM(model=self.model_name, temperature=settings.universe_temperature)
        self.persona_service = PersonaService()

        # Initialize OpenAI client for structured output
        import os

        self.openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Load YAML instruction files
        self.instructions = self._load_generation_instructions()

    def _generate_structured(
        self, prompt: str, schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate structured output using OpenAI's JSON schema approach."""

        try:
            # o3 models only support temperature=1 (default), so we omit it
            api_params = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "structured_output",
                        "strict": True,
                        "schema": schema,
                    },
                },
                "max_completion_tokens": settings.max_tokens_universe,
            }

            # Only add temperature for non-o3 models
            if not self.model_name.startswith("o3-"):
                api_params["temperature"] = settings.universe_temperature

            response = self.openai_client.chat.completions.create(**api_params)

            content = response.choices[0].message.content
            if content is None:
                print(f"❌ API returned None content. Response: {response}")
                print(f"❌ Finish reason: {response.choices[0].finish_reason}")
                raise Exception(
                    f"API returned None content, finish reason: {response.choices[0].finish_reason}"
                )

            return json.loads(content)

        except Exception as e:
            print(f"❌ Structured generation failed: {e}")
            raise

    def _load_generation_instructions(self) -> Dict[str, Any]:
        """Load YAML instruction files for universe generation."""
        instructions = {}
        instruction_dir = Path("prompts/universe_generation")

        instruction_files = [
            "customer_behavioral_instructions.yaml",
            "support_ticket_instructions.yaml",
            "business_model_instructions.yaml",
            "quality_standards.yaml",
        ]

        for filename in instruction_files:
            file_path = instruction_dir / filename
            if file_path.exists():
                with open(file_path, "r") as f:
                    key = filename.replace(".yaml", "").replace("_instructions", "")
                    instructions[key] = yaml.safe_load(f)
            else:
                print(f"⚠️  Instruction file not found: {filename}")

        return instructions

    def generate(self, merchant_name: str, scenario_name: str) -> Dict[str, Any]:
        """Generate a universe for the given merchant and scenario."""

        # Load merchant using unified persona service
        merchant_prompt = self.persona_service.get_persona_prompt(merchant_name, "v1.0.0")
        if not merchant_prompt:
            raise ValueError(f"No prompt found for merchant {merchant_name}")
        merchant = {"prompt": merchant_prompt}  # Maintain compatibility with existing structure
        scenario = self._load_scenario(scenario_name)

        # Generate in order to avoid circular dependencies
        business_context = self._generate_business_context(merchant, scenario)
        customers = self._generate_customers(merchant, scenario, business_context)
        support_tickets = self._generate_support_tickets(merchant, scenario, customers)

        # Create universe structure based on our agreed format
        universe = {
            "metadata": {
                "universe_id": f"{merchant_name}_{scenario_name}_v1",
                "merchant": merchant_name,
                "scenario": scenario_name,
                "generated_at": datetime.now().isoformat() + "Z",
                "generator_version": "1.0.0",
                "timeline_days": settings.universe_timeline_days,
                "current_day": settings.universe_current_day,  # Middle of timeline for steady state
            },
            "business_context": business_context,
            "timeline_events": self._generate_timeline_events(scenario),
            "customers": customers,
            "support_tickets": support_tickets,
            "ticket_categories_distribution": self._generate_ticket_distribution(
                scenario
            ),
            "product_performance": self._extract_product_performance(merchant),
        }

        return universe

    def _load_scenario(self, scenario_name: str) -> Dict[str, Any]:
        """Load scenario using unified scenario file."""
        scenario_path = Path("prompts/scenarios/all_scenarios.yaml")

        # Fallback to old files if new unified file doesn't exist
        if not scenario_path.exists():
            scenario_path = Path("prompts/scenarios/normal_business_scenarios.yaml")
            if not scenario_path.exists():
                scenario_path = Path("prompts/scenarios/business_scenarios.yaml")

        if not scenario_path.exists():
            raise FileNotFoundError("No scenario files found")

        with open(scenario_path) as f:
            scenarios = yaml.safe_load(f)

        if scenario_name not in scenarios["scenarios"]:
            available = list(scenarios["scenarios"].keys())
            raise KeyError(
                f"Scenario '{scenario_name}' not found. Available: {available}"
            )

        return scenarios["scenarios"][scenario_name]

    def _generate_business_context(
        self, merchant: Dict[str, Any], scenario: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate current business state based on scenario using LLM."""

        merchant_prompt = merchant.get("prompt", "")
        scenario_text = scenario.get("scenario", "")

        # Get instructions from YAML
        business_instructions = self.instructions.get("business_model", {})
        quality_standards = self.instructions.get("quality_standards", {})

        prompt = f"""Generate realistic business context and metrics using the provided instructions.

MERCHANT CATALOG & BUSINESS MODEL (use this data directly):
{merchant_prompt}

SCENARIO CONTEXT:
{scenario_text}

BUSINESS MODEL INTEGRATION INSTRUCTIONS:
{yaml.dump(business_instructions, default_flow_style=False)}

QUALITY STANDARDS:
{yaml.dump(quality_standards.get('business_metrics_realism', {}), default_flow_style=False)}

CRITICAL REQUIREMENTS:
- Extract ACTUAL subscription tier names and pricing from the merchant catalog above
- Generate business metrics that reflect the scenario conditions
- Use real subscription tier structure from merchant catalog (not generic names)
- Ensure metrics are internally consistent and realistic for the business model
- Include appropriate subscriber distribution across actual tiers
- NO hardcoded or generic tier names allowed

OUTPUT FORMAT:
Return a valid JSON object with this exact structure:
{{
  "current_state": {{
    "mrr": number (monthly recurring revenue),
    "subscriber_count": number,
    "churn_rate": number (percentage like 5.5),
    "csat_score": number (1-5 scale),
    "support_tickets_per_day": number,
    "average_response_time_hours": number
  }},
  "subscription_tiers": [
    {{
      "name": "EXACT tier name from merchant catalog",
      "price": number (exact price from catalog),
      "active_subscribers": number
    }}
  ]
}}"""

        # Define JSON schema for business context
        schema = {
            "type": "object",
            "properties": {
                "current_state": {
                    "type": "object",
                    "properties": {
                        "mrr": {
                            "type": "number",
                            "description": "Monthly recurring revenue",
                        },
                        "subscriber_count": {
                            "type": "integer",
                            "description": "Total active subscribers",
                        },
                        "churn_rate": {
                            "type": "number",
                            "description": "Monthly churn rate as percentage",
                        },
                        "csat_score": {
                            "type": "number",
                            "description": "Customer satisfaction score 1-5",
                        },
                        "support_tickets_per_day": {
                            "type": "integer",
                            "description": "Average daily ticket volume",
                        },
                        "average_response_time_hours": {
                            "type": "number",
                            "description": "Average response time in hours",
                        },
                    },
                    "required": [
                        "mrr",
                        "subscriber_count",
                        "churn_rate",
                        "csat_score",
                        "support_tickets_per_day",
                        "average_response_time_hours",
                    ],
                    "additionalProperties": False,
                },
                "subscription_tiers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Subscription tier name from catalog",
                            },
                            "price": {"type": "number", "description": "Monthly price"},
                            "active_subscribers": {
                                "type": "integer",
                                "description": "Number of active subscribers",
                            },
                        },
                        "required": ["name", "price", "active_subscribers"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["current_state", "subscription_tiers"],
            "additionalProperties": False,
        }

        print(f"🤖 Generating business context with {self.model_name}...")
        try:
            business_context = self._generate_structured(prompt, schema)
            print("✅ Generated business context")
            return business_context
        except Exception as e:
            print(f"❌ Failed to generate business context: {e}")
            # NO HARDCODED FALLBACKS - Fix the prompt instead
            raise Exception(
                f"Business context generation failed. Fix the LLM prompt, do not use hardcoded fallbacks: {e}"
            )

    def _extract_subscription_tiers(self, catalog_text: str) -> list:
        """Extract subscription tiers from merchant catalog - REMOVED HARDCODING."""
        # NO HARDCODED FALLBACKS - LLM must extract from catalog properly
        # If this fails, fix the LLM prompt, don't mask the problem
        raise NotImplementedError(
            "Subscription tiers must be extracted by LLM from catalog, no hardcoded fallbacks allowed"
        )

    def _generate_timeline_events(self, scenario: Dict[str, Any]) -> list:
        """Generate timeline events based on scenario using structured output."""

        scenario_text = scenario.get("scenario", "")

        prompt = f"""Generate a realistic 90-day timeline of business events for this scenario.

SCENARIO:
{scenario_text}

REQUIREMENTS:
- Create {settings.universe_events_min}-{settings.universe_events_max} events across the {settings.universe_timeline_days}-day timeline
- Events should build toward and explain the current scenario state
- Include specific dates (2024-03-30 to 2024-06-28, day 45 = 2024-05-14)
- Each event should have realistic business impact
- Mix of operational, marketing, and external events
- Make events specific to the scenario and create a narrative that leads to the current state"""

        # Define JSON schema for timeline events
        schema = {
            "type": "object",
            "properties": {
                "events": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "day": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 90,
                                "description": "Day number in timeline (1-90)",
                            },
                            "date": {
                                "type": "string",
                                "description": "Date in YYYY-MM-DD format",
                            },
                            "event": {
                                "type": "string",
                                "description": "Brief description of what happened",
                            },
                            "impact": {
                                "type": "string",
                                "enum": [
                                    "positive",
                                    "negative",
                                    "minor_negative",
                                    "none",
                                ],
                                "description": "Business impact of the event",
                            },
                        },
                        "required": ["day", "date", "event", "impact"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["events"],
            "additionalProperties": False,
        }

        print(f"🤖 Generating timeline events with {self.model_name}...")
        try:
            result = self._generate_structured(prompt, schema)
            timeline_events = result["events"]
            print(f"✅ Generated {len(timeline_events)} timeline events")
            return timeline_events
        except Exception as e:
            print(f"❌ Failed to generate timeline events: {e}")
            # Fallback to minimal events
            return [
                {
                    "day": 1,
                    "date": "2024-03-30",
                    "event": "Timeline baseline established",
                    "impact": "none",
                },
                {
                    "day": 45,
                    "date": "2024-05-14",
                    "event": "Current day - scenario state active",
                    "impact": "none",
                },
            ]

    def _generate_customers(
        self,
        merchant: Dict[str, Any],
        scenario: Dict[str, Any],
        business_context: Dict[str, Any],
    ) -> list:
        """Generate customers using structured output."""

        # Get subscription tiers from business context
        subscription_tiers = business_context["subscription_tiers"]
        tier_names = [tier["name"] for tier in subscription_tiers]

        # Get instructions from YAML
        customer_instructions = self.instructions.get("customer_behavioral", {})

        prompt = f"""Generate {settings.universe_customers_min}-{settings.universe_customers_max} realistic customers for this business with diverse behavioral patterns.

MERCHANT CATALOG & BUSINESS MODEL (use this data directly):
{merchant.get("prompt", "")}

SCENARIO CONTEXT:
{scenario.get("scenario", "")}

CUSTOMER ARCHETYPE INSTRUCTIONS:
{yaml.dump(customer_instructions.get("customer_archetypes", {}), default_flow_style=False)}

CRITICAL REQUIREMENTS:
- Use ACTUAL subscription tier names from the merchant catalog above (not generic names)
- Create diverse customer archetypes with explicit customer_type and sub_type fields:
  * gift_sender (25%): Sub-types: personal_gifter, corporate_buyer, event_gifter
  * active_subscriber (45%): Sub-types: happy_subscriber, engaged_subscriber, at_risk_subscriber, power_subscriber
  * hybrid_subscriber (18%): Active subscription + marketplace purchases
  * one_time_purchaser (20%): Sub-types: trial_converter, occasional_buyer, one_and_done, browser
  * repeat_purchaser (12%): Regular buyers avoiding subscription
- Each customer MUST have customer_type and sub_type fields
- Reference REAL products from the catalog for purchase history
- Generate realistic satisfaction scores matching sub-type (happy: 4.5-5.0, at-risk: 2.8-3.5)
- Support ticket frequency must align with customer archetype patterns
- Include customers across lifecycle stages: new, developing, mature, at-risk
- Use diverse, realistic names and appropriate email addresses
- Show realistic order counts and lifetime values for business model and customer type"""

        # Define JSON schema for customers
        schema = {
            "type": "object",
            "properties": {
                "customers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "customer_id": {
                                "type": "string",
                                "description": "Customer ID like cust_001",
                            },
                            "name": {
                                "type": "string",
                                "description": "Full customer name",
                            },
                            "email": {
                                "type": "string",
                                "description": "Customer email address",
                            },
                            "customer_type": {
                                "type": "string",
                                "enum": [
                                    "gift_sender",
                                    "active_subscriber",
                                    "hybrid_subscriber",
                                    "one_time_purchaser",
                                    "repeat_purchaser",
                                ],
                                "description": "Customer archetype category",
                            },
                            "sub_type": {
                                "type": "string",
                                "description": "Specific sub-type within the customer archetype",
                            },
                            "subscription_tier": {
                                "type": "string",
                                "description": "Subscription tier name from provided list (null for non-subscribers)",
                            },
                            "subscription_start_date": {
                                "type": "string",
                                "description": "Start date in YYYY-MM-DD format",
                            },
                            "lifetime_value": {
                                "type": "number",
                                "description": "Total lifetime value in dollars",
                            },
                            "orders_count": {
                                "type": "integer",
                                "description": "Number of orders placed",
                            },
                            "last_order_date": {
                                "type": "string",
                                "description": "Last order date in YYYY-MM-DD format",
                            },
                            "status": {
                                "type": "string",
                                "enum": ["active", "paused", "cancelled"],
                                "description": "Customer status",
                            },
                            "satisfaction_score": {
                                "type": "number",
                                "minimum": 1,
                                "maximum": 5,
                                "description": "Satisfaction score 1-5",
                            },
                            "support_tickets_count": {
                                "type": "integer",
                                "description": "Number of support tickets",
                            },
                        },
                        "required": [
                            "customer_id",
                            "name",
                            "email",
                            "customer_type",
                            "sub_type",
                            "subscription_tier",
                            "subscription_start_date",
                            "lifetime_value",
                            "orders_count",
                            "last_order_date",
                            "status",
                            "satisfaction_score",
                            "support_tickets_count",
                        ],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["customers"],
            "additionalProperties": False,
        }

        print(f"🤖 Generating customers with {self.model_name}...")
        try:
            result = self._generate_structured(prompt, schema)
            customers = result["customers"]
            print(f"✅ Generated {len(customers)} customers")
            return customers
        except Exception as e:
            print(f"❌ Failed to generate customers: {e}")
            # Fallback to minimal customers
            return [
                {
                    "customer_id": "cust_001",
                    "name": "Janet Williams",
                    "email": "jwilliams@email.com",
                    "subscription_tier": tier_names[0] if tier_names else "Standard",
                    "subscription_start_date": "2023-01-15",
                    "lifetime_value": 1200,
                    "orders_count": 12,
                    "last_order_date": "2024-05-01",
                    "status": "active",
                    "satisfaction_score": 4,
                    "support_tickets_count": 3,
                }
            ]

    def _generate_support_tickets(
        self, merchant: Dict[str, Any], scenario: Dict[str, Any], customers: list
    ) -> list:
        """Generate support tickets using structured output."""

        # Get merchant catalog info and scenario details
        merchant_prompt = merchant.get("prompt", "")
        scenario_text = scenario.get("scenario", "")

        # Create customer summaries with types for context
        customer_summaries = []
        for c in customers:
            summary = f"{c['customer_id']}: {c['customer_type']}/{c['sub_type']} - satisfaction: {c['satisfaction_score']}"
            customer_summaries.append(summary)

        # Get instructions from YAML
        ticket_instructions = self.instructions.get("support_ticket", {})
        business_instructions = self.instructions.get("business_model", {})
        quality_standards = self.instructions.get("quality_standards", {})
        customer_instructions = self.instructions.get("customer_behavioral", {})

        prompt = f"""Generate {settings.universe_tickets_min}-{settings.universe_tickets_max} realistic customer support tickets using the provided instructions.

MERCHANT CATALOG & BUSINESS MODEL (use this data directly):
{merchant_prompt}

SCENARIO CONTEXT:
{scenario_text}

CUSTOMERS WITH ARCHETYPES (use these exactly):
{chr(10).join(customer_summaries)}

CUSTOMER ARCHETYPE BEHAVIORS:
{yaml.dump(customer_instructions.get("customer_archetypes", {}), default_flow_style=False)}

SUPPORT TICKET INSTRUCTIONS:
{yaml.dump(ticket_instructions, default_flow_style=False)}

BUSINESS MODEL INTEGRATION:
{yaml.dump(business_instructions, default_flow_style=False)}

QUALITY REQUIREMENTS:
{yaml.dump(quality_standards.get('support_ticket_authenticity', {}), default_flow_style=False)}

CRITICAL REQUIREMENTS:
- MUST reference actual products from merchant catalog by specific name
- Generate tickets for day 45 of a 90-day timeline (current day: 2024-05-14)
- Match ticket patterns to customer archetypes:
  * gift_sender: delivery timing, recipient issues, bulk orders, gift messages
  * active_subscriber: subscription management, product feedback, satisfaction-based
  * hybrid_subscriber: complex orders, shipping coordination, account complexity
  * one_time_purchaser: first-time questions, returns, conversion opportunities
  * repeat_purchaser: bulk inquiries, product availability, subscription questions
- Ticket frequency and content MUST align with customer satisfaction scores
- Include realistic customer language with natural tone and occasional typos
- Reference actual business challenges mentioned in merchant profile
- NO generic product names or hardcoded content allowed"""

        # Define JSON schema for support tickets
        schema = {
            "type": "object",
            "properties": {
                "tickets": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "ticket_id": {
                                "type": "string",
                                "description": "Ticket ID like tkt_XXXX",
                            },
                            "created_at": {
                                "type": "string",
                                "description": "Creation timestamp in ISO format",
                            },
                            "customer_id": {
                                "type": "string",
                                "description": "Customer ID from provided list",
                            },
                            "category": {
                                "type": "string",
                                "enum": [
                                    "shipping",
                                    "account_management",
                                    "product_feedback",
                                    "quality_issues",
                                    "billing",
                                ],
                                "description": "Ticket category",
                            },
                            "subject": {
                                "type": "string",
                                "description": "Brief subject line",
                            },
                            "content": {
                                "type": "string",
                                "description": "Detailed customer message with natural language",
                            },
                            "sentiment": {
                                "type": "string",
                                "enum": [
                                    "positive",
                                    "negative",
                                    "neutral",
                                    "frustrated",
                                ],
                                "description": "Customer sentiment",
                            },
                            "priority": {
                                "type": "string",
                                "enum": ["low", "normal", "high"],
                                "description": "Ticket priority",
                            },
                            "status": {
                                "type": "string",
                                "enum": ["open", "resolved", "in_progress"],
                                "description": "Ticket status",
                            },
                        },
                        "required": [
                            "ticket_id",
                            "created_at",
                            "customer_id",
                            "category",
                            "subject",
                            "content",
                            "sentiment",
                            "priority",
                            "status",
                        ],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["tickets"],
            "additionalProperties": False,
        }

        print(f"🤖 Generating tickets with {self.model_name}...")
        try:
            result = self._generate_structured(prompt, schema)
            tickets = result["tickets"]
            print(f"✅ Generated {len(tickets)} tickets")
            return tickets
        except Exception as e:
            print(f"❌ Failed to generate tickets: {e}")
            # NO HARDCODED FALLBACKS - Fix the prompt instead
            raise Exception(
                f"Support ticket generation failed. Fix the LLM prompt, do not use hardcoded fallbacks: {e}"
            )

    def _extract_products(self, catalog_text: str) -> list:
        """Extract product names from merchant catalog - REMOVED HARDCODING."""
        # NO HARDCODED FALLBACKS - LLM must extract from catalog properly
        # If this fails, fix the LLM prompt, don't mask the problem
        raise NotImplementedError(
            "Products must be extracted by LLM from catalog, no hardcoded fallbacks allowed"
        )

    def _generate_ticket_distribution(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Generate ticket category distribution."""

        # Standard distribution for steady operations
        return {
            "shipping": {
                "percentage": 35,
                "average_per_day": 11,
                "common_issues": ["Where is my order?", "Shipping delay questions"],
            },
            "account_management": {
                "percentage": 25,
                "average_per_day": 8,
                "common_issues": ["Subscription upgrades", "Payment updates"],
            },
            "product_feedback": {
                "percentage": 20,
                "average_per_day": 6,
                "common_issues": ["Product reviews", "Recipe questions"],
            },
            "quality_issues": {
                "percentage": 10,
                "average_per_day": 3,
                "common_issues": ["Damaged packaging", "Missing items"],
            },
            "billing": {
                "percentage": 10,
                "average_per_day": 3,
                "common_issues": ["Charge questions", "Refund requests"],
            },
        }

    def _extract_product_performance(self, merchant: Dict[str, Any]) -> Dict[str, Any]:
        """Extract product performance from catalog."""

        # Simple extraction - would expand with LLM analysis
        return {
            "top_rated_products": [
                {
                    "name": "Sweet Heat BBQ Rub",
                    "sku": "SH-RUB-001",
                    "rating": 4.8,
                    "reviews_count": 234,
                    "inclusion_rate": 0.65,
                }
            ],
            "problematic_products": [],
        }

    def save_universe(self, universe: Dict[str, Any], output_path: str = None) -> str:
        """Save universe to YAML file."""

        if not output_path:
            universe_id = universe["metadata"]["universe_id"]
            output_path = f"data/universes/{universe_id}.yaml"

        # Ensure directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Save as YAML
        with open(output_path, "w") as f:
            yaml.dump(universe, f, default_flow_style=False, sort_keys=False)

        return output_path
