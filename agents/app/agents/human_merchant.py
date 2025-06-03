"""
Human merchant interface for interactive conversations.
Allows a human to play the role of the merchant.
"""

from datetime import datetime

from app.models import Message, BusinessScenario, MerchantPersona, ConversationState


class HumanMerchantInterface:
    """Interface for human to play merchant role in conversations."""

    def __init__(self, persona: MerchantPersona, scenario: BusinessScenario):
        self.persona = persona
        self.scenario = scenario
        self.first_message = True

    def display_briefing(self):
        """Show the human their role and scenario context."""
        print("\n" + "=" * 60)
        print("YOUR ROLE")
        print("=" * 60)
        print(f"\nYou are: {self.persona.name}")
        print(f"Business: {self.persona.business_name}")
        print(f"Industry: {self.persona.industry}")
        print(f"\nCurrent Situation: {self.scenario.description}")
        print(f"Stress Level: {self.scenario.stress_level.value.upper()}")

        # Show key metrics
        print("\nKey Metrics:")
        print(f"  • Subscribers: {self.scenario.subscriber_count:,}")
        print(f"  • MRR: ${self.scenario.mrr:,}")
        print(f"  • Churn Rate: {self.scenario.churn_rate:.1%}")
        print(f"  • CAC: ${self.scenario.cac:.2f}")

        # Show recent events
        if self.scenario.recent_events:
            print("\nRecent Events:")
            for event in self.scenario.recent_events[:3]:
                print(f"  • {event.description}")

        # Show current problems
        if self.scenario.current_problems:
            print("\nCurrent Problems:")
            for problem in self.scenario.current_problems[:3]:
                print(f"  • {problem.description}")

        print(f"\nYour Communication Style: {self.persona.communication_style}")
        print(f"Your Current Mood: {self.persona.current_emotional_state}")

        print("\n" + "=" * 60)
        print("CONVERSATION STARTING...")
        print("=" * 60)
        print("\nCJ will message you shortly. Respond as your character would.")
        print("Type 'help' for commands, or just type naturally.\n")

    async def get_response(
        self, context: ConversationState, cj_message: Message
    ) -> Message:
        """Get human input as merchant response."""
        # Display CJ's message nicely
        print("\n\033[94mCJ:\033[0m")
        print(self._format_cj_message(cj_message.content))

        # Show quick context reminder if not first message
        if not self.first_message:
            self._show_quick_context()

        self.first_message = False

        # Get human input
        while True:
            try:
                user_input = input(f"\n\033[92m{self.persona.name}:\033[0m ")

                # Handle special commands
                if user_input.lower() == "help":
                    self._show_help()
                    continue
                elif user_input.lower() == "context":
                    self.display_briefing()
                    continue
                elif user_input.lower() == "metrics":
                    self._show_current_metrics()
                    continue
                elif user_input.lower() == "quit":
                    raise KeyboardInterrupt()
                elif user_input.strip() == "":
                    print("(Please type a message or 'help' for commands)")
                    continue

                # Create message
                return Message(
                    sender=self.persona.name,
                    content=user_input,
                    timestamp=datetime.now(),
                    debug_info={"human_played": True},
                )

            except KeyboardInterrupt:
                print("\n\nEnding conversation...")
                raise

    def _format_cj_message(self, content: str) -> str:
        """Format CJ's message for display."""
        # Handle ASCII art daily flash reports
        lines = content.split("\n")
        formatted_lines = []

        for line in lines:
            # Indent slightly for readability
            formatted_lines.append(f"  {line}")

        return "\n".join(formatted_lines)

    def _show_quick_context(self):
        """Show quick context reminder."""
        print(
            f"\n\033[90m(You are {self.persona.name}, stress: {self.scenario.stress_level.value})\033[0m",
            end="",
        )

    def _show_help(self):
        """Show available commands."""
        print("\nCommands:")
        print("  help     - Show this help")
        print("  context  - Show full role briefing again")
        print("  metrics  - Show current business metrics")
        print("  quit     - End conversation")
        print("\nOr just type naturally as your character would!")

    def _show_current_metrics(self):
        """Show current business metrics."""
        print("\nCurrent Metrics:")
        print(f"  • Subscribers: {self.scenario.subscriber_count:,}")
        print(f"  • MRR: ${self.scenario.mrr:,}")
        print(f"  • Churn Rate: {self.scenario.churn_rate:.1%}")
        print(f"  • CAC: ${self.scenario.cac:.2f}")
        print(f"  • Outstanding Tickets: {self.scenario.outstanding_tickets}")

    async def send_message(self, message: str) -> Message:
        """Send a message (for workflow initiation)."""
        print(f"\n\033[92m{self.persona.name}:\033[0m {message}")
        return Message(
            sender=self.persona.name,
            content=message,
            timestamp=datetime.now(),
            debug_info={"human_played": True},
        )
