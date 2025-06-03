#!/usr/bin/env python3
"""
Simple version of play conversation that works with existing infrastructure.
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from pathlib import Path
import argparse
from typing import Optional, Dict, Any
from uuid import uuid4
import threading
import time
import queue

# Add project root directory to path for imports
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)


from app.models import Conversation, Message  # noqa: E402
from app.scenarios.loader import ScenarioLoader  # noqa: E402
from app.workflows.loader import WorkflowLoader  # noqa: E402
from app.config import settings  # noqa: E402

# Import API adapter - this is now the only way to interact with CJ
from app.agents.api_adapter import create_cj_agent, Crew, Task  # noqa: E402
from app.agents.universe_data_agent import UniverseDataAgent  # noqa: E402
from app.prompts.loader import PromptLoader  # noqa: E402
from app.agents.fact_checker import (  # noqa: E402
    ConversationFactChecker as AsyncFactChecker,
)
import yaml  # noqa: E402


def load_fact_check_messages():
    """Load fact-check status messages from YAML"""
    # Go up to project root, then down to prompts
    project_root = Path(__file__).parent.parent.parent
    message_path = project_root / "prompts" / "fact_checking" / "error_messages.yaml"
    with open(message_path, "r") as f:
        data = yaml.safe_load(f)
    return data["status_messages"]


# Load messages once at module level
FACT_CHECK_MESSAGES = load_fact_check_messages()


class ConversationMetrics:
    """Track metrics for the conversation."""

    def __init__(self):
        self.total_prompts = 0
        self.total_tools_called = 0
        self.total_time = 0.0
        self.turn_metrics = []

    def add_turn(self, prompts: int, tools: int, time_taken: float):
        self.total_prompts += prompts
        self.total_tools_called += tools
        self.total_time += time_taken
        self.turn_metrics.append(
            {"prompts": prompts, "tools": tools, "time": time_taken}
        )

    def get_summary(self) -> str:
        if not self.turn_metrics:
            return "📊 No metrics recorded"

        avg_time = self.total_time / len(self.turn_metrics)
        avg_prompts = self.total_prompts / len(self.turn_metrics)
        avg_tools = self.total_tools_called / len(self.turn_metrics)

        return (
            f"📊 Session Summary:\n"
            f"   • Total: {self.total_prompts} prompts, {self.total_tools_called} tools, {self.total_time:.1f}s\n"
            f"   • Average per turn: {avg_prompts:.1f} prompts, {avg_tools:.1f} tools, {avg_time:.1f}s\n"
            f"   • Turns completed: {len(self.turn_metrics)}"
        )


class ProgressMonitor:
    """Monitor and display progress of CJ's thinking."""

    def __init__(self):
        self.status_queue = queue.Queue()
        self.tools_called = 0
        self.start_time = None
        self.current_status = "thinking"
        self.current_agent = "CJ"
        self.stop_event = threading.Event()
        self.last_update = time.time()

    def update_status(self, status: str, tool_name: str = None):
        """Update the current status."""
        if tool_name:
            self.tools_called += 1
            self.status_queue.put(("tool", tool_name))
        else:
            self.status_queue.put(("status", status))
        self.last_update = time.time()

    def update_agent(self, agent_name: str):
        """Update which agent is currently active."""
        self.current_agent = agent_name
        self.status_queue.put(("agent", agent_name))
        self.last_update = time.time()

    def display_progress(self):
        """Display progress in a single updating line."""
        indicators = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        i = 0

        # Status icons for different activities
        status_icons = {
            "thinking": "🤔",
            "analyzing": "🔍",
            "checking": "📊",
            "writing": "✍️",
            "finalizing": "🎯",
            "executing": "⚡",
            "delegating": "🤝",
            "initializing": "🚀",
            "preparing": "⚙️",
            "processing": "🔄",
            "working hard": "💪",
            "setting up": "🛠️",
            "loading data agent": "📦",
            "api call": "🌐",
            "planning": "📋",
            "starting task": "🎬",
            "generating response": "💭",
        }

        # Agent icons
        agent_icons = {
            "CJ": "🎯",
            "DataProviderAgent": "📊",
            "UniverseDataAgent": "🎫",
            "Tool": "🔧",
        }

        while not self.stop_event.is_set():
            # Check for status updates (non-blocking)
            updates_processed = 0
            while updates_processed < 5:  # Process up to 5 updates per cycle
                try:
                    update_type, update_value = self.status_queue.get_nowait()
                    if update_type == "status":
                        self.current_status = update_value
                    elif update_type == "agent":
                        self.current_agent = update_value
                    elif update_type == "tool":
                        # Brief flash of tool name
                        elapsed = (
                            time.time() - self.start_time if self.start_time else 0
                        )
                        agent_icon = agent_icons.get(self.current_agent, "🤖")
                        status_text = f"\033[94m{self.current_agent} is {self.current_status}... [{agent_icon} → {update_value}] ({self.tools_called} tools, {elapsed:.1f}s)\033[0m"
                        print(f"\r\033[K{status_text}", end="", flush=True)
                        time.sleep(0.3)  # Show tool name briefly
                    updates_processed += 1
                except queue.Empty:
                    break

            # Always show regular update
            elapsed = time.time() - self.start_time if self.start_time else 0
            icon = status_icons.get(self.current_status, "💭")
            agent_icon = agent_icons.get(self.current_agent, "🤖")

            # Add some dynamic status messages based on elapsed time
            if elapsed > 15 and self.tools_called == 0:
                self.current_status = "processing"
            elif elapsed > 30 and self.tools_called < 2:
                self.current_status = "working hard"

            status_text = f"\033[94m{agent_icon} {self.current_agent} is {self.current_status} {indicators[i % len(indicators)]} [{icon}] ({self.tools_called} tools, {elapsed:.1f}s)\033[0m"
            print(f"\r\033[K{status_text}", end="", flush=True)

            i += 1
            time.sleep(0.1)  # Update every 100ms for smooth animation

    def start(self):
        """Start monitoring."""
        self.start_time = time.time()
        self.display_thread = threading.Thread(target=self.display_progress)
        self.display_thread.daemon = True
        self.display_thread.start()

    def stop(self) -> Dict[str, any]:
        """Stop monitoring and return metrics."""
        self.stop_event.set()
        if hasattr(self, "display_thread"):
            self.display_thread.join()

        elapsed = time.time() - self.start_time if self.start_time else 0
        return {"tools_called": self.tools_called, "time_taken": elapsed}


# Progress tracking with output interception
class OutputInterceptor:
    """Intercept stdout to monitor CrewAI's real-time output."""

    def __init__(self, monitor: Optional[ProgressMonitor] = None):
        self.monitor = monitor
        self.original_stdout = sys.stdout
        self.buffer = []

    def write(self, text):
        # Capture the text
        self.buffer.append(text)

        # Don't pass through any output - we'll handle display separately
        # This prevents duplicate printing of CJ's responses

        # Update monitor based on output
        if self.monitor and text.strip():
            # Look for agent transitions
            if "Working Agent:" in text:
                agent_name = text.split("Working Agent:")[-1].strip()
                if agent_name:
                    self.monitor.update_agent(agent_name)
            elif "Starting Task:" in text:
                self.monitor.update_status("starting task")
            elif "Thought:" in text:
                self.monitor.update_status("thinking")
            elif "Action:" in text:
                self.monitor.update_status("planning")
            elif (
                "API call" in text.lower()
                or "openai" in text.lower()
                or "anthropic" in text.lower()
            ):
                self.monitor.update_status("api call")
            elif "Using tool:" in text:
                tool_name = text.split("Using tool:")[-1].strip()
                if tool_name:
                    self.monitor.update_status("using tool", tool_name)
            elif "Tool:" in text and "Input:" in text:
                # Extract tool name from "Tool: tool_name"
                tool_match = text.split("Tool:")[-1].split("Input:")[0].strip()
                if tool_match:
                    self.monitor.update_status("calling tool", tool_match)
            elif "Tool Output:" in text or "Observation:" in text:
                self.monitor.update_status("analyzing")
            elif "Final Answer:" in text:
                self.monitor.update_status("finalizing")
            elif "Delegation:" in text:
                self.monitor.update_status("delegating")

        # Don't show the output in non-debug mode
        return

    def flush(self):
        pass

    def get_output(self):
        return "".join(self.buffer)


def run_crew_with_progress(
    crew: Crew, monitor: Optional[ProgressMonitor] = None
) -> tuple[Any, str]:
    """Run crew and capture real progress updates."""
    if monitor and not getattr(crew, "verbose", False):
        # Temporarily enable verbose mode to capture output
        original_verbose = crew.verbose
        crew.verbose = True

        # Intercept output to monitor progress
        interceptor = OutputInterceptor(monitor)
        old_stdout = sys.stdout
        sys.stdout = interceptor

        try:
            # Show that we're about to start the actual AI work
            if monitor:
                monitor.update_status("generating response")

            # Simple approach: just let the existing monitor keep running
            # It will show the spinning indicator during the blocking call
            result = crew.kickoff()
            # Get the captured output
            captured = interceptor.get_output()
            return result, captured
        finally:
            # Restore original settings
            sys.stdout = old_stdout
            crew.verbose = original_verbose
    else:
        # Normal execution or already verbose
        if monitor:
            monitor.update_status("generating response")
        result = crew.kickoff()
        return result, ""


# Hook into CrewAI's execution to get real metrics
def count_llm_calls_in_response(response_str: str) -> Dict[str, int]:
    """Count LLM calls and tool usage from the response."""
    metrics = {
        "thoughts": response_str.count("Thought:"),
        "tool_calls": response_str.count("Using tool:"),
        "tool_outputs": response_str.count("Tool Output:"),
        "prompts": 1,  # Base prompt
    }

    # Estimate total prompts (initial + one per thought + retries)
    metrics["prompts"] = max(1, metrics["thoughts"]) + metrics["tool_calls"]

    # Extract tool names
    tool_names = []
    if "Using tool:" in response_str:
        lines = response_str.split("\n")
        for i, line in enumerate(lines):
            if "Using tool:" in line:
                tool_name = line.split("Using tool:")[-1].strip()
                tool_names.append(tool_name)

    return metrics, tool_names


def save_conversation(conversation, quiet=False):
    """Save conversation to JSON file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    merchant = conversation.merchant_name.replace(" ", "_").lower()
    scenario = conversation.scenario_name.replace(" ", "_").lower()
    workflow = (
        conversation.workflow.replace(" ", "_").lower()
        if conversation.workflow
        else "chat"
    )

    filename = f"{merchant}_{scenario}_{workflow}_human_played_{timestamp}.json"
    filepath = Path("data/conversations") / filename

    # Ensure directory exists
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dict
    conv_dict = {
        "id": conversation.id,
        "created_at": conversation.created_at.isoformat(),
        "scenario_name": conversation.scenario_name,
        "merchant_name": conversation.merchant_name,
        "cj_version": conversation.cj_version,
        "workflow": conversation.workflow,
        "messages": [
            {
                "timestamp": msg.timestamp.isoformat(),
                "sender": msg.sender,
                "content": msg.content,
                "metadata": msg.metadata,
            }
            for msg in conversation.messages
        ],
        "state": {
            "workflow": conversation.state.workflow,
        },
    }

    # Save as JSON
    with open(filepath, "w") as f:
        json.dump(conv_dict, f, indent=2, default=str)

    if not quiet:
        print(f"\n💾 Conversation saved to: {filepath}")


def display_briefing(merchant_name: str, scenario_data: dict, persona_data: dict):
    """Display role briefing for human player."""
    # Try to get business info from conversation catalog
    try:
        from app.conversation_catalog import ConversationCatalog

        catalog = ConversationCatalog()
        personas = catalog.get_personas()
        if merchant_name in personas:
            business_name = personas[merchant_name].business
        else:
            business_name = persona_data.get("business_name", "Your Business")
    except Exception:
        business_name = persona_data.get("business_name", "Your Business")

    print("\n" + "=" * 60)
    print("YOUR ROLE")
    print("=" * 60)
    print(f"\nYou are: {merchant_name.replace('_', ' ').title()}")
    print(f"Business: {business_name}")
    print(f"Industry: {persona_data.get('industry', 'E-commerce')}")

    print(
        f"\nCurrent Situation: {scenario_data.get('description', scenario_data['scenario'][:100])}"
    )
    print(f"Stress Level: {scenario_data.get('stress_level', 'HIGH').upper()}")

    # Show key metrics if available
    print("\nKey Metrics:")
    if "metrics" in scenario_data:
        metrics = scenario_data["metrics"]
        print(f"  • Subscribers: {metrics.get('subscribers', 'Unknown')}")
        print(f"  • MRR: ${metrics.get('mrr', 'Unknown')}")
        print(f"  • Churn Rate: {metrics.get('churn_rate', 'Unknown')}")
        print(f"  • CAC: ${metrics.get('cac', 'Unknown')}")
    else:
        print("  • [Metrics will be provided by CJ]")

    print(
        f"\nYour Communication Style: {persona_data.get('communication_style', 'direct and brief')}"
    )
    print(f"Your Current Mood: {persona_data.get('emotional_state', 'stressed')}")


def display_fact_check_result(result):
    """Display fact-check results in a readable format."""
    if not result:
        return

    # Status indicator
    status_emoji = {"PASS": "✅", "WARNING": "⚠️", "FAIL": "❌", "ERROR": "🚨"}.get(
        result.overall_status, "❓"
    )

    print(f"\n\033[90m{status_emoji} Fact-Check Result: {result.overall_status}\033[0m")

    # Show claims summary
    if result.claims:
        verified = sum(1 for c in result.claims if c.verification.value == "VERIFIED")
        unverified = sum(
            1 for c in result.claims if c.verification.value == "UNVERIFIED"
        )
        incorrect = sum(1 for c in result.claims if c.verification.value == "INCORRECT")

        print(
            f"\033[90m   Claims: {len(result.claims)} total ({verified} verified, {unverified} unverified, {incorrect} incorrect)\033[0m"
        )

        # Show all claims with their verification status
        print("\033[90m   \nDetailed Claims:\033[0m")
        for claim in result.claims:
            # Color based on verification status
            if claim.verification.value == "VERIFIED":
                status_color = "\033[92m"  # Green
                status_symbol = "✓"
            elif claim.verification.value == "UNVERIFIED":
                status_color = "\033[93m"  # Yellow
                status_symbol = "?"
            else:  # INCORRECT
                status_color = "\033[91m"  # Red
                status_symbol = "✗"

            print(f"{status_color}   {status_symbol} {claim.claim}\033[0m")

            # Show actual data if available
            if claim.actual_data:
                print(f"\033[90m     → Universe data: {claim.actual_data}\033[0m")

    # Show issues if any
    if result.issues:
        print("\033[90m   \nIssues found:\033[0m")
        for issue in result.issues:
            severity_color = {
                "minor": "\033[93m",  # Yellow
                "major": "\033[91m",  # Light red
                "critical": "\033[31m",  # Bold red
            }.get(issue.severity.value, "\033[90m")

            print(
                f"{severity_color}   • [{issue.severity.value.upper()}] {issue.summary}\033[0m"
            )
            if issue.claim:
                print(f"\033[90m     Claim: {issue.claim}\033[0m")
            if issue.expected and issue.actual:
                print(f"\033[90m     Expected: {issue.expected}\033[0m")
                print(f"\033[90m     Actual: {issue.actual}\033[0m")


def format_cj_message(content: str) -> str:
    """Format CJ's message for display."""
    lines = content.split("\n")
    formatted_lines = []

    for line in lines:
        # Indent slightly for readability
        formatted_lines.append(f"  {line}")

    return "\n".join(formatted_lines)


async def play_conversation(
    merchant_name: str,
    scenario_name: str,
    cj_version: str = None,
    workflow_name: Optional[str] = None,
    max_turns: int = 10,
    debug: bool = False,
    fact_check: bool = False,
    fact_check_verbose: bool = False,
):
    """Generate conversation with human playing merchant role."""
    # Initialize metrics
    metrics = ConversationMetrics()

    # Load scenario
    scenario_loader = ScenarioLoader()
    scenario_data = scenario_loader.get_scenario(scenario_name)

    # Load merchant persona
    prompt_loader = PromptLoader()
    persona_data = prompt_loader.load_merchant_persona(merchant_name)

    # Display briefing
    display_briefing(merchant_name, scenario_data, persona_data)

    # Use default CJ version if not specified
    if cj_version is None:
        cj_version = settings.default_cj_version

    # Create conversation
    conversation = Conversation(
        id=str(uuid4()),
        created_at=datetime.now(),
        scenario_name=scenario_name,
        merchant_name=merchant_name,
        cj_version=cj_version,
        workflow=workflow_name,
    )

    # Print conversation starting message once
    print("\n" + "=" * 60)
    print("CONVERSATION STARTING...")
    print("=" * 60)
    print("\nCJ will message you shortly. Respond as your character would.")
    print("Type 'help' for commands, or just type naturally.\n")

    print("\n🎭 Starting conversation...")
    print("🔄 Initializing agents...")  # Simple immediate feedback

    # Start initial progress monitor for setup
    setup_monitor = ProgressMonitor()
    setup_monitor.start()
    setup_monitor.update_status("setting up")

    # Setup workflow if specified
    if workflow_name:
        workflow_loader = WorkflowLoader()
        workflow_data = workflow_loader.get_workflow(workflow_name)
        conversation.state.workflow = workflow_name
        conversation.state.workflow_details = workflow_data.get("workflow", "")

    # Create universe data agent
    setup_monitor.update_status("loading universe data")
    data_agent = UniverseDataAgent(
        merchant_name=merchant_name, scenario_name=scenario_name
    )

    # Initialize fact-checker if enabled
    fact_checker = None
    if fact_check:
        setup_monitor.update_status("initializing fact-checker")
        # Get universe data from data agent
        universe_data = data_agent.universe
        fact_checker = AsyncFactChecker(universe_data)

    # Stop setup monitor
    setup_monitor.stop()
    print("\r" + " " * 80 + "\r", end="")  # Clear the progress line

    # Determine who starts based on workflow
    merchant_starts = False
    if workflow_name:
        # Check if this is a merchant-initiated workflow
        if workflow_name in ["ad_hoc_support", "crisis_response", "ad_hoc_question"]:
            merchant_starts = True

    try:
        # Generate conversation turns
        for turn in range(max_turns):
            # For merchant-initiated workflows, get merchant input first on turn 0
            if turn == 0 and merchant_starts:
                # Get initial merchant message
                user_input = input(
                    f"\033[92m{merchant_name.replace('_', ' ').title()}:\033[0m "
                )

                # Handle special commands
                if user_input.lower() == "help":
                    print("\nCommands:")
                    print("  help     - Show this help")
                    print("  quit     - End conversation")
                    print("\nOr just type naturally as your character would!")
                    continue
                elif user_input.lower() == "quit":
                    print("\nEnding conversation...")
                    break

                # Add merchant message
                merchant_message = Message(
                    timestamp=datetime.now(),
                    sender=merchant_name,
                    content=user_input,
                )
                conversation.add_message(merchant_message)

            # Start progress monitor early to show we're working
            monitor = None
            if turn == 0 and not merchant_starts:
                print()  # New line for first turn
            monitor = ProgressMonitor()
            monitor.start()
            monitor.update_status("initializing")

            # Create CJ agent with current state
            monitor.update_status("creating agent")
            cj_agent = create_cj_agent(
                merchant_name=merchant_name,
                scenario_name=scenario_name,
                workflow_name=workflow_name,
                prompt_version=cj_version,
                # Use global setting
            )

            # Update status after agent creation
            monitor.update_status("preparing")

            # CJ's turn - simple task descriptions since context is managed by backend
            if turn == 0 and workflow_name and not merchant_starts:
                task_description = (
                    f"Start the {workflow_name} workflow for {merchant_name}"
                )
            else:
                # Simple task description - context is passed via the backend
                task_description = "Respond helpfully to the merchant's message"

            # Create and execute CJ task
            cj_task = Task(
                description=task_description,
                agent=cj_agent,
                expected_output="A helpful message to the merchant",
            )

            # Create crew
            crew = Crew(agents=[cj_agent], tasks=[cj_task], verbose=debug)

            # Run with progress monitoring if not in debug mode
            cj_response, captured_output = run_crew_with_progress(
                crew, monitor if not debug else None
            )

            # Use captured output for metrics if available, otherwise use response
            analysis_str = captured_output if captured_output else str(cj_response)
            response_str = str(cj_response)

            # Count actual LLM calls and tool usage
            llm_metrics, tool_names = count_llm_calls_in_response(analysis_str)

            # Stop progress monitor and get timing
            turn_metrics = {"prompts": 1, "tools": 0, "time": 0}  # Default
            if monitor:
                turn_data = monitor.stop()
                turn_metrics = {
                    "prompts": llm_metrics["prompts"],
                    "tools": llm_metrics["tool_calls"],
                    "time": turn_data["time_taken"],
                    "thoughts": llm_metrics["thoughts"],
                    "tool_names": tool_names,
                }
                metrics.add_turn(
                    turn_metrics["prompts"], turn_metrics["tools"], turn_metrics["time"]
                )
                print("\r" + " " * 80 + "\r", end="")  # Clear progress line

            # Look for "Final Answer:" pattern
            if "Final Answer:" in response_str and not debug:
                content = response_str.split("Final Answer:")[-1].strip()
            else:
                content = response_str

            # Add CJ message
            cj_message = Message(
                timestamp=datetime.now(),
                sender="CJ",
                content=content,
                metadata={"turn": turn, "human_played": True, "metrics": turn_metrics},
            )
            conversation.messages.append(cj_message)

            # Display CJ's message with metrics
            print("\033[94mCJ:\033[0m")
            print(format_cj_message(content))
            if not debug and monitor:
                # Show detailed metrics
                tools_info = (
                    f"{turn_metrics['tools']} tools"
                    if turn_metrics["tools"] > 0
                    else "no tools"
                )
                if turn_metrics.get("tool_names"):
                    tools_list = ", ".join(turn_metrics["tool_names"])
                    tools_info = f"{turn_metrics['tools']} tools ({tools_list})"

                print(
                    f"\n\033[90m[{turn_metrics['prompts']} prompts, {turn_metrics.get('thoughts', 0)} thoughts, {tools_info}, {turn_metrics['time']:.1f}s]\033[0m"
                )

            # Update conversation state
            conversation.state.context_window.append(cj_message)
            if len(conversation.state.context_window) > 10:
                conversation.state.context_window.pop(0)

            # Start fact-checking if enabled
            fact_check_future = None
            if fact_checker and captured_output:
                # Show fact-checking status
                print(
                    f"\n\033[90m{FACT_CHECK_MESSAGES['fact_check_in_progress']}\033[0m",
                    end="",
                    flush=True,
                )

                # Start async fact-checking
                fact_check_future = fact_checker.check_facts(
                    cj_response=content,
                    captured_output=captured_output,
                    turn_number=turn,
                )

                # Store reference in message metadata
                cj_message.metadata["fact_check_future"] = fact_check_future

                # Check if result is already available (from cache)
                if fact_check_future.done():
                    result = fact_check_future.result()
                    if result.has_issues:
                        print(
                            f"\r\033[90m{FACT_CHECK_MESSAGES['fact_check_complete_issues']}     \033[0m"
                        )
                    else:
                        print(
                            f"\r\033[90m{FACT_CHECK_MESSAGES['fact_check_complete_clear']}     \033[0m"
                        )
                    if fact_check_verbose:
                        display_fact_check_result(result)

            # Check if fact-check completed while waiting
            if fact_check_future and not fact_check_future.done():
                # Start a background thread to notify when complete
                import threading

                def check_completion():
                    result = fact_checker.wait_for_result(
                        fact_check_future, timeout=30.0
                    )
                    if result and result.has_issues:
                        print(
                            f"\r\033[90m{FACT_CHECK_MESSAGES['fact_check_complete_issues']}\033[0m"
                        )
                    elif result:
                        print(
                            f"\r\033[90m{FACT_CHECK_MESSAGES['fact_check_complete_clear']}\033[0m"
                        )
                    # Reprint the prompt since we just overwrote it
                    print(
                        f"\n\033[92m{merchant_name.replace('_', ' ').title()}:\033[0m ",
                        end="",
                        flush=True,
                    )

                thread = threading.Thread(target=check_completion, daemon=True)
                thread.start()

            # Get human response after CJ's response
            # Skip only if this is the last turn of the conversation
            if turn < max_turns - 1:
                while True:
                    try:
                        user_input = input(
                            f"\n\033[92m{merchant_name.replace('_', ' ').title()}:\033[0m "
                        )

                        # Handle special commands
                        if user_input.lower() == "help":
                            print("\nCommands:")
                            print("  help     - Show this help")
                            print("  metrics  - Show conversation metrics")
                            if fact_check:
                                print(
                                    "  f        - Show fact-check results for last response"
                                )
                            print("  quit     - End conversation")
                            print("\nOr just type naturally as your character would!")
                            continue
                        elif user_input.lower() == "metrics":
                            print(f"\n{metrics.get_summary()}\n")
                            continue
                        elif (
                            user_input.lower() == "f"
                            and fact_check
                            and fact_check_future
                        ):
                            # Show fact-check results
                            if fact_check_future.done():
                                result = fact_check_future.result()
                                display_fact_check_result(result)
                            else:
                                # Wait a bit for results
                                print(
                                    f"\n\033[90m{FACT_CHECK_MESSAGES['fact_check_waiting']}\033[0m"
                                )
                                result = fact_checker.wait_for_result(
                                    fact_check_future, timeout=3.0
                                )
                                if result:
                                    display_fact_check_result(result)
                                else:
                                    print(
                                        f"\033[90m{FACT_CHECK_MESSAGES['fact_check_timeout']}\033[0m"
                                    )
                            continue
                        elif user_input.lower() == "quit":
                            raise KeyboardInterrupt()
                        elif user_input.strip() == "":
                            print("(Please type a message or 'help' for commands)")
                            continue

                        break

                    except KeyboardInterrupt:
                        raise

                # Add merchant message
                merchant_message = Message(
                    timestamp=datetime.now(),
                    sender=merchant_name.replace("_", " ").title(),
                    content=user_input,
                    metadata={"turn": turn, "human_played": True},
                )
                conversation.messages.append(merchant_message)

                # Update conversation state
                conversation.state.context_window.append(merchant_message)
                if len(conversation.state.context_window) > 10:
                    conversation.state.context_window.pop(0)

        # Save conversation
        save_conversation(conversation)
        print("\n✅ Conversation complete!")
        print(f"\n{metrics.get_summary()}")

        # Clean up fact-checker
        # Note: ConversationFactChecker doesn't have a shutdown method

        # Ask if user wants to annotate
        response = input("\nWould you like to annotate this conversation? (y/n): ")
        if response.lower() == "y":
            import subprocess

            subprocess.run([sys.executable, "scripts/annotate.py", "--latest"])

    except KeyboardInterrupt:
        print("\n\n❌ Conversation ended by user")
        # Still save partial conversation
        save_conversation(conversation)
        print("Partial conversation saved.")
        print(f"\n{metrics.get_summary()}")

        # Clean up fact-checker
        # Note: ConversationFactChecker doesn't have a shutdown method

        # Ask if user wants to annotate even when quitting early
        try:
            response = input("\nWould you like to annotate this conversation? (y/n): ")
            if response.lower() == "y":
                import subprocess

                subprocess.run([sys.executable, "scripts/annotate.py", "--latest"])
        except Exception:
            pass  # If they Ctrl+C again, just exit
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


def main():
    print("🚀 Loading conversation system...")  # Immediate feedback

    parser = argparse.ArgumentParser(
        description="Play the role of a merchant in conversation with CJ"
    )
    parser.add_argument(
        "--merchant",
        default="marcus_thompson",
        help="Merchant persona to play (default: marcus_thompson)",
    )
    parser.add_argument(
        "--scenario",
        default="steady_operations",
        help="Business scenario (default: steady_operations)",
    )
    parser.add_argument(
        "--cj-version",
        default="v5.0.0",
        help="CJ prompt version (default: v5.0.0)",
    )
    parser.add_argument(
        "--workflow",
        help="Conversation workflow (e.g., daily_briefing, crisis_response)",
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=10,
        help="Maximum conversation turns (default: 10)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show agent thoughts and tool usage",
    )
    parser.add_argument(
        "--fact-check",
        action="store_true",
        default=True,
        help="Enable fact-checking of CJ's responses (default: enabled)",
    )
    parser.add_argument(
        "--no-fact-check",
        action="store_false",
        dest="fact_check",
        help="Disable fact-checking",
    )
    parser.add_argument(
        "--fact-check-verbose",
        action="store_true",
        help="Show detailed fact-checking results",
    )

    args = parser.parse_args()

    # Run async function
    try:
        asyncio.run(
            play_conversation(
                merchant_name=args.merchant,
                scenario_name=args.scenario,
                cj_version=args.cj_version,
                workflow_name=args.workflow,
                max_turns=args.turns,
                debug=args.debug,
                fact_check=args.fact_check,
                fact_check_verbose=args.fact_check_verbose,
            )
        )
    except KeyboardInterrupt:
        # Clean exit without traceback
        sys.exit(0)


if __name__ == "__main__":
    main()
