#!/usr/bin/env python3
"""Conversation generator using CrewAI agents with workflow support."""

import argparse
import json
import os
import sys
from datetime import datetime
from uuid import uuid4

# Add parent directory to path for local imports
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)


from app.models import Conversation, Message  # noqa: E402
from app.workflows.loader import WorkflowLoader  # noqa: E402
from app.config import settings  # noqa: E402

# Import API adapter - this is now the only way to interact with CJ
from app.agents.api_adapter import create_cj_agent, Crew, Task  # noqa: E402
from app.agents.merchant_agent import create_merchant_agent  # noqa: E402


def display_conversation(
    conversation: Conversation, show_prompts: bool = False, markdown_mode: bool = False
):
    """Display a conversation in a readable format."""
    if markdown_mode:
        # First show clean conversation
        print("# Conversation\n")
        print(f"**Merchant:** {conversation.merchant_name}  ")
        print(f"**Scenario:** {conversation.scenario_name}  ")
        if conversation.workflow:
            print(f"**Workflow:** {conversation.workflow}  ")
        print("\n---\n")

        # Show just the messages
        for msg in conversation.messages:
            if msg.sender == "merchant":
                print(f"**Merchant** ({msg.timestamp.strftime('%H:%M:%S')}):\n")
            else:
                print(f"**CJ** ({msg.timestamp.strftime('%H:%M:%S')}):\n")
            print(msg.content)
            print("\n---\n")

        # Then show debug section if requested
        if show_prompts:
            print("\n# Debugging Conversation Log\n")
            print(f"**Merchant:** {conversation.merchant_name}  ")
            print(f"**Scenario:** {conversation.scenario_name}  ")
            if conversation.workflow:
                print(f"**Workflow:** {conversation.workflow}  ")
            print("\n---\n")
    else:
        print(f"\n{'='*60}")
        print(
            f"🎭 CONVERSATION: {conversation.merchant_name} × {conversation.scenario_name}"
        )
        if conversation.workflow:
            print(f"📋 WORKFLOW: {conversation.workflow}")
        print(f"{'='*60}\n")

    # Skip detailed messages if we already showed the clean conversation in markdown mode
    if markdown_mode and not show_prompts:
        # Summary section for clean conversation
        print("\n## Summary\n")
        print(f"- **Total messages:** {len(conversation.messages)}")
        print(f"- **Conversation ID:** `{conversation.id}`")
        return

    for i, msg in enumerate(conversation.messages):
        # Show debug info if enabled
        if show_prompts and msg.metadata and "debug_info" in msg.metadata:
            debug = msg.metadata["debug_info"]
            if markdown_mode:
                print("\n## Debug Context\n")
                print(f"### Prompt for {msg.sender.upper()}\n")
                print("```")
                print(debug.get("prompt", ""))
                print("```\n")

                if debug.get("tools"):
                    print("**Available Tools:**")
                    for tool in debug["tools"]:
                        print(f"- {tool}")
                    print()

                if debug.get("task"):
                    print(f"**Task:** {debug['task']}\n")
            else:
                print(f"\n{'━'*80}")
                print("📝 PROMPT CONTEXT FOR " + msg.sender.upper() + ":")
                print("━" * 80)

                # Show full prompt in indented block
                prompt_lines = debug.get("prompt", "").split("\n")
                for line in prompt_lines:
                    print(f"    {line}")

                # Show tools if available
                if debug.get("tools"):
                    print("\n🔧 AVAILABLE TOOLS:")
                    for tool in debug["tools"]:
                        print(f"    • {tool}")

                # Show task description
                if debug.get("task"):
                    print(f"\n📋 TASK: {debug['task']}")

                print(f"{'━'*80}\n")

        # Show tool calls if present
        if show_prompts and msg.metadata and "tool_calls" in msg.metadata:
            if markdown_mode:
                print("\n### Tool Calls\n")
                for tool_call in msg.metadata["tool_calls"]:
                    print(f"**Tool:** `{tool_call['tool']}`\n")
                    if tool_call.get("input"):
                        print("**Input:**")
                        print("```json")
                        print(tool_call["input"])
                        print("```\n")
                    print("**Output:**")
                    print("```")
                    print(tool_call["output"].strip())
                    print("```\n")
            else:
                print(f"\n{'─'*60}")
                print("🔧 TOOL CALLS:")
                print("─" * 60)
                for tool_call in msg.metadata["tool_calls"]:
                    print(f"\n  📞 Tool: {tool_call['tool']}")
                    if tool_call.get("input"):
                        print(f"  📥 Input: {tool_call['input']}")
                    print("  📤 Output:")
                    output_lines = tool_call["output"].split("\n")
                    for line in output_lines:
                        print(f"      {line}")
                print(f"{'─'*60}\n")

        # Show the actual message
        if markdown_mode:
            if msg.sender == "merchant":
                print(f"\n### 🧑‍💼 MERCHANT ({msg.timestamp.strftime('%H:%M:%S')})\n")
            else:
                print(f"\n### 🤖 CJ ({msg.timestamp.strftime('%H:%M:%S')})\n")

            # Handle multi-line messages properly
            print(msg.content)
            print()
        else:
            if msg.sender == "merchant":
                print(f"🧑‍💼 MERCHANT ({msg.timestamp.strftime('%H:%M:%S')}):")
            else:
                print(f"🤖 CJ ({msg.timestamp.strftime('%H:%M:%S')}):")

            print(f"   {msg.content}")
            print()

    # Summary section
    if markdown_mode:
        print("\n---\n")
        print("## Summary\n")
        print(f"- **Total messages:** {len(conversation.messages)}")
        print(f"- **Conversation ID:** `{conversation.id}`")
    else:
        print(f"{'='*60}")
        print(f"📊 Summary: {len(conversation.messages)} messages")
        print(f"💾 Conversation ID: {conversation.id}")


def save_conversation(
    conversation: Conversation,
    output_dir: str = "data/conversations",
    quiet: bool = False,
):
    """Save conversation to JSON file."""
    os.makedirs(output_dir, exist_ok=True)

    filename = f"{conversation.merchant_name}_{conversation.scenario_name}"
    if conversation.workflow:
        filename += f"_{conversation.workflow}"
    filename += f"_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = os.path.join(output_dir, filename)

    # Convert to JSON-serializable dict
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

    with open(filepath, "w") as f:
        json.dump(conv_dict, f, indent=2)

    if not quiet:
        print(f"\n💾 Saved to: {filepath}")


def generate_conversation_with_crew(
    merchant_name: str,
    scenario_name: str,
    cj_version: str = None,
    workflow_name: str = None,
    merchant_opens: str = None,
    num_turns: int = 3,
) -> Conversation:
    """Generate a conversation using CrewAI agents."""

    # Load scenario for context
    # scenario_loader = ScenarioLoader()
    # Note: Scenario data loaded but not used - kept for future expansion

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

    # Setup workflow if specified
    if workflow_name:
        workflow_loader = WorkflowLoader()
        workflow_data = workflow_loader.get_workflow(workflow_name)
        conversation.state.workflow = workflow_name
        conversation.state.workflow_details = workflow_data.get("workflow", "")

    # Generate conversation turns
    for turn in range(num_turns):
        # Create agents with current conversation state
        cj_agent = create_cj_agent(
            merchant_name=merchant_name,
            scenario_name=scenario_name,
            workflow_name=workflow_name,
            prompt_version=cj_version,
            # Use global setting
        )

        merchant_agent = create_merchant_agent(
            merchant_name=merchant_name,
            scenario_name=scenario_name,
            conversation_state=conversation.state,
        )

        # Determine who speaks
        if turn == 0 and merchant_opens:
            # Merchant starts
            speaker_agent = merchant_agent
            speaker_name = "merchant"
            task_description = f"Start the conversation with: {merchant_opens}"
        elif turn == 0 and workflow_name:
            # CJ starts with workflow
            speaker_agent = cj_agent
            speaker_name = "cj"
            task_description = "Start the conversation following your workflow"
        else:
            # Alternate turns or respond naturally
            last_speaker = (
                conversation.messages[-1].sender if conversation.messages else None
            )
            if last_speaker == "cj":
                speaker_agent = merchant_agent
                speaker_name = "merchant"
                task_description = (
                    "Respond to CJ's last message naturally as a business owner"
                )
            else:
                speaker_agent = cj_agent
                speaker_name = "cj"
                task_description = "Respond helpfully to the merchant's message"

        # Create task for this turn
        task = Task(
            description=task_description,
            expected_output="A natural conversational response",
            agent=speaker_agent,
        )

        # Run the task
        crew = Crew(agents=[speaker_agent], tasks=[task], verbose=False)
        result = crew.kickoff()

        # Extract the actual response content
        # CrewAI sometimes returns the raw ReAct format, so we need to extract the final answer
        content = str(result)

        # Check if this is a ReAct format response
        if "Final Answer:" in content:
            # Extract everything after "Final Answer:"
            content = content.split("Final Answer:")[-1].strip()
        elif "```" in content and "Thought:" in content:
            # This is the ReAct format with markdown - extract the final answer
            if "the final answer to the original input question" in content:
                # This is a malformed response, try to extract actual content
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    if "Thought:" in line and i > 0:
                        # Take everything before the Thought line
                        content = "\n".join(lines[:i]).strip()
                        break

        # For now, skip tool call parsing since we're not capturing stdout
        # TODO: Implement proper tool call extraction from result if needed
        tool_calls = []

        # Add message to conversation with debug info
        debug_info = {
            "prompt": speaker_agent.backstory,  # Full prompt, no truncation
            "task": task_description,
            "tools": (
                [tool.name for tool in speaker_agent.tools]
                if hasattr(speaker_agent, "tools") and speaker_agent.tools
                else []
            ),
        }

        metadata = {"debug_info": debug_info}
        if tool_calls:
            metadata["tool_calls"] = tool_calls

        message = Message(
            timestamp=datetime.now(),
            sender=speaker_name,
            content=content,
            metadata=metadata,
        )
        conversation.add_message(message)

    return conversation


def main():
    """Main function to run conversation generation."""
    parser = argparse.ArgumentParser(
        description="Generate a conversation between a merchant and CJ with optional workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Daily briefing workflow
  python scripts/generate_conversation.py --workflow daily_briefing

  # Crisis response for Sarah
  python scripts/generate_conversation.py --merchant sarah_chen --scenario churn_spike --workflow crisis_response

  # Merchant-initiated conversation
  python scripts/generate_conversation.py --merchant-opens "why did our churn spike yesterday??"

  # No workflow - just helpful CJ
  python scripts/generate_conversation.py --merchant marcus_thompson --scenario growth_stall

  # Clean markdown output for Google Docs
  python scripts/generate_conversation.py --workflow daily_briefing --debug --markdown

Available workflows:
  - daily_briefing (morning check-in with metrics)
  - crisis_response (urgent issue handling)
  - weekly_review (comprehensive analysis)
  - ad_hoc_support (merchant-initiated)

Available merchants:
  - marcus_thompson (BBQ box, data-focused, stressed)
  - sarah_chen (Beauty box, collaborative, thoughtful)

Available scenarios:
  - growth_stall (plateau after initial growth)
  - churn_spike (crisis mode, quality issues)
  - scaling_chaos (viral growth problems)
  - competitor_threat (new competitor pressure)
  - return_to_growth (post-COVID recovery)
        """,
    )

    parser.add_argument(
        "--merchant", default="marcus_thompson", help="Merchant persona to use"
    )
    parser.add_argument(
        "--scenario", default="growth_stall", help="Business scenario to use"
    )
    parser.add_argument(
        "--cj-version",
        default="v4.0.0",
        help="CJ prompt version (v4.0.0 has workflow awareness)",
    )
    parser.add_argument(
        "--workflow",
        help="Optional workflow to follow (daily_briefing, crisis_response, etc.)",
    )
    parser.add_argument(
        "--merchant-opens", help="Let the merchant start with a specific message"
    )
    parser.add_argument(
        "--turns", type=int, default=3, help="Number of conversation turns"
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Don't display the conversation"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Show prompts and context between messages"
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Output in clean markdown format for Google Docs",
    )

    args = parser.parse_args()

    try:
        # Generate conversation
        if not args.markdown:
            print("🚀 Generating conversation with CrewAI agents...")
            print(f"   Merchant: {args.merchant}")
            print(f"   Scenario: {args.scenario}")
            print(f"   CJ Version: {args.cj_version}")
            if args.workflow:
                print(f"   Workflow: {args.workflow}")
            if args.merchant_opens:
                print(f"   Opening: '{args.merchant_opens}'")
            print(f"   Turns: {args.turns}")

        conversation = generate_conversation_with_crew(
            merchant_name=args.merchant,
            scenario_name=args.scenario,
            cj_version=args.cj_version,
            workflow_name=args.workflow,
            merchant_opens=args.merchant_opens,
            num_turns=args.turns,
        )

        # Display conversation
        if not args.quiet:
            display_conversation(
                conversation, show_prompts=args.debug, markdown_mode=args.markdown
            )

        # Always save conversation
        save_conversation(conversation, quiet=args.markdown)

        if not args.markdown:
            print("\n✅ Done!")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
