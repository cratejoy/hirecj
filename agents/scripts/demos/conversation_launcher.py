#!/usr/bin/env python3
"""
Interactive conversation launcher with menu-driven interface.
Provides discovery, selection, and quick actions for conversations.
"""

import sys
import os
import json
import random
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List
import argparse

# Add project root directory to path for imports
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)

from app.conversation_catalog import (  # noqa: E402
    ConversationCatalog,
    StressLevel,
    PersonalityType,
)
from app.services.persona_service import PersonaService  # noqa: E402
from app.universe.discovery import UniverseDiscovery  # noqa: E402
from app.config import settings  # noqa: E402


class ConversationHistory:
    """Manages conversation history for quick re-runs."""

    HISTORY_FILE = Path("data/.conversation_history.json")
    MAX_HISTORY = 10

    def __init__(self):
        self.history = self._load_history()

    def _load_history(self) -> List[Dict]:
        """Load conversation history from file."""
        if self.HISTORY_FILE.exists():
            try:
                with open(self.HISTORY_FILE, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []

    def save_history(self):
        """Save conversation history to file."""
        self.HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(self.HISTORY_FILE, "w") as f:
            json.dump(self.history[-self.MAX_HISTORY :], f, indent=2)

    def add_conversation(
        self, merchant: str, scenario: str, workflow: str, cj_version: str
    ):
        """Add a conversation to history."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "merchant": merchant,
            "scenario": scenario,
            "workflow": workflow,
            "cj_version": cj_version,
        }
        self.history.append(entry)
        self.save_history()

    def get_last(self) -> Optional[Dict]:
        """Get the last conversation."""
        return self.history[-1] if self.history else None

    def get_recent(self, n: int = 5) -> List[Dict]:
        """Get recent conversations."""
        return self.history[-n:]


class ConversationLauncher:
    """Interactive menu system for launching conversations."""

    def __init__(self):
        self.catalog = ConversationCatalog()
        self.persona_service = PersonaService()
        self.history = ConversationHistory()
        self.universe_discovery = UniverseDiscovery()
        
        # Get personas from unified service
        persona_list = self.persona_service.get_all_personas()
        self.personas = {p["id"]: p for p in persona_list}
        
        self.scenarios = self.catalog.get_scenarios()
        self.workflows = self.catalog.get_workflows()
        self.cj_versions = self.catalog.get_cj_versions()

    def clear_screen(self):
        """Clear the terminal screen."""
        os.system("clear" if os.name == "posix" else "cls")

    def print_header(self, title: str):
        """Print a formatted header."""
        print("\n" + "=" * 70)
        print(f" {title}")
        print("=" * 70)

    def print_menu_item(self, key: str, value: str, selected: bool = False):
        """Print a menu item with formatting."""
        prefix = "→ " if selected else "  "
        print(f"{prefix}[{key}] {value}")

    def get_stress_emoji(self, stress: StressLevel) -> str:
        """Get emoji for stress level."""
        return {
            StressLevel.LOW: "😌",
            StressLevel.MODERATE: "😐",
            StressLevel.HIGH: "😰",
            StressLevel.CRITICAL: "🔥",
        }.get(stress, "")

    def get_personality_emoji(self, personality: PersonalityType) -> str:
        """Get emoji for personality type."""
        return {
            PersonalityType.DIRECT: "📊",
            PersonalityType.COLLABORATIVE: "🤝",
            PersonalityType.SCATTERED: "🌪️",
        }.get(personality, "")

    def show_main_menu(self) -> str:
        """Show main menu and get user choice."""
        self.clear_screen()
        self.print_header("🎭 HireCJ Conversation Launcher")

        # Show universe status
        available_combos = self.universe_discovery.get_available_combinations()
        total_possible = len(self.personas) * len(self.scenarios)
        if available_combos:
            print(
                f"\n📊 Universe Status: {len(available_combos)}/{total_possible} available"
            )
            merchants_with_data = self.universe_discovery.get_available_merchants()
            print(f"   Merchants with data: {', '.join(merchants_with_data)}")
        else:
            print("\n⚠️  No universes found! Generate some to get started.")

        print("\nWhat would you like to do?")
        print("\n[1] 🎯 Quick Start (choose from menu)")
        print("[2] 🎲 Random Conversation")
        print("[3] 📚 Recommended Combinations")
        print("[4] 🔄 Repeat Last Conversation")
        print("[5] 📜 Recent History")
        print("[6] ⚡ Express Mode (all defaults)")
        print("[7] 🔧 Custom Command")
        print("[8] 🌌 Universe Management")
        print("\n[q] Quit")

        return input("\nYour choice: ").strip().lower()

    def show_persona_menu(self) -> str:
        """Show persona selection menu."""
        self.clear_screen()
        self.print_header("Choose Your Merchant Persona")

        for i, (key, persona) in enumerate(self.personas.items(), 1):
            # Check universe availability
            scenarios_with_universe = (
                self.universe_discovery.get_scenarios_for_merchant(key)
            )
            universe_status = (
                f"✅ {len(scenarios_with_universe)} universes"
                if scenarios_with_universe
                else "⚠️  No universes"
            )

            print(
                f"\n[{i}] {persona['name']} - {persona['business']} [{universe_status}]"
            )

        print("\n[r] 🎲 Random persona (with universe)")
        print("[b] ← Back")

        choice = input("\nYour choice: ").strip().lower()

        if choice == "b":
            return None
        elif choice == "r":
            # Only choose from personas that have universes
            available_merchants = self.universe_discovery.get_available_merchants()
            if available_merchants:
                return random.choice(
                    [m for m in available_merchants if m in self.personas]
                )
            else:
                print("\n⚠️  No universes available! Generate some first.")
                input("Press Enter to continue...")
                return self.show_persona_menu()
        elif choice.isdigit() and 1 <= int(choice) <= len(self.personas):
            return list(self.personas.keys())[int(choice) - 1]
        else:
            print("Invalid choice!")
            input("Press Enter to continue...")
            return self.show_persona_menu()

    def show_scenario_menu(self, merchant: str) -> str:
        """Show scenario selection menu."""
        self.clear_screen()
        persona = self.personas[merchant]
        self.print_header(f"Choose Scenario for {persona['name']}")

        for i, (key, scenario) in enumerate(self.scenarios.items(), 1):
            stress_emoji = self.get_stress_emoji(scenario.stress_level)

            # Check if universe exists for this combination
            has_universe = self.universe_discovery.has_universe(merchant, key)
            universe_indicator = "✅" if has_universe else "❌"

            print(
                f"\n[{i}] {universe_indicator} {stress_emoji} {scenario.display_name}"
            )
            print(f"    {scenario.description[:80]}...")
            print(f"    Challenge: {scenario.main_challenge}")
            print(f"    Urgency: {scenario.urgency}")

        print("\n[r] 🎲 Random scenario (with universe)")
        print("[g] 🚀 Generate missing universe")
        print("[b] ← Back")

        choice = input("\nYour choice: ").strip().lower()

        if choice == "b":
            return None
        elif choice == "r":
            # Only choose scenarios with universes
            available_scenarios = self.universe_discovery.get_scenarios_for_merchant(
                merchant
            )
            if available_scenarios:
                return random.choice(
                    [s for s in available_scenarios if s in self.scenarios]
                )
            else:
                print(f"\n⚠️  No universes available for {persona['name']}!")
                input("Press Enter to continue...")
                return self.show_scenario_menu(merchant)
        elif choice == "g":
            self.generate_missing_universes(merchant)
            return self.show_scenario_menu(merchant)
        elif choice.isdigit() and 1 <= int(choice) <= len(self.scenarios):
            selected_scenario = list(self.scenarios.keys())[int(choice) - 1]
            # Check if universe exists
            if not self.universe_discovery.has_universe(merchant, selected_scenario):
                print(f"\n⚠️  No universe exists for {merchant}/{selected_scenario}")
                print("\nWould you like to generate it now? [y/n]")
                if input("> ").strip().lower() == "y":
                    self.generate_universe(merchant, selected_scenario)
                    return selected_scenario
                else:
                    return self.show_scenario_menu(merchant)
            return selected_scenario
        else:
            print("Invalid choice!")
            input("Press Enter to continue...")
            return self.show_scenario_menu(merchant)

    def show_workflow_menu(self, scenario: str) -> str:
        """Show workflow selection menu."""
        self.clear_screen()
        scenario_data = self.scenarios[scenario]
        self.print_header(f"Choose Workflow for {scenario_data.display_name}")

        # Show recommended workflows first
        print("\n📌 Recommended for this scenario:")
        recommended = []
        for key, workflow in self.workflows.items():
            if scenario in workflow.best_for or "all scenarios" in workflow.best_for:
                recommended.append(key)

        for i, key in enumerate(recommended, 1):
            workflow = self.workflows[key]
            print(f"\n[{i}] ⭐ {workflow.display_name}")
            print(f"    {workflow.description}")
            print(f"    Typical length: {workflow.typical_turns} turns")

        # Show other workflows
        others = [k for k in self.workflows.keys() if k not in recommended]
        if others:
            print("\n📋 Other workflows:")
            for i, key in enumerate(others, len(recommended) + 1):
                workflow = self.workflows[key]
                print(f"\n[{i}] {workflow.display_name}")
                print(f"    {workflow.description}")

        print("\n[r] 🎲 Random workflow")
        print("[b] ← Back")

        choice = input("\nYour choice: ").strip().lower()

        if choice == "b":
            return None
        elif choice == "r":
            return random.choice(list(self.workflows.keys()))
        elif choice.isdigit():
            idx = int(choice) - 1
            all_workflows = recommended + others
            if 0 <= idx < len(all_workflows):
                return all_workflows[idx]

        print("Invalid choice!")
        input("Press Enter to continue...")
        return self.show_workflow_menu(scenario)

    def show_cj_version_menu(self) -> str:
        """Show CJ version selection menu."""
        self.clear_screen()
        self.print_header("Choose CJ Version")

        versions = list(self.cj_versions.items())
        for i, (version, description) in enumerate(versions, 1):
            default = " (default)" if version == "v5.0.0" else ""
            print(f"\n[{i}] {version}{default}")
            print(f"    {description}")

        print("\n[d] Use default (v5.0.0)")
        print("[b] ← Back")

        choice = input("\nYour choice: ").strip().lower()

        if choice == "b":
            return None
        elif choice == "d":
            return "v5.0.0"
        elif choice.isdigit() and 1 <= int(choice) <= len(versions):
            return versions[int(choice) - 1][0]
        else:
            print("Invalid choice!")
            input("Press Enter to continue...")
            return self.show_cj_version_menu()

    def show_recommended_menu(self) -> Optional[Dict]:
        """Show recommended combinations menu."""
        self.clear_screen()
        self.print_header("📚 Recommended Conversations")

        recommendations = self.catalog.get_recommended_combinations()

        for i, rec in enumerate(recommendations, 1):
            persona = self.personas[rec["merchant"]]
            scenario = self.scenarios[rec["scenario"]]

            print(f"\n[{i}] {rec['name']}")
            print(f"    {rec['description']}")
            print(f"    • Merchant: {persona['name']}")
            print(f"    • Scenario: {scenario.display_name}")
            print(f"    • Workflow: {rec['workflow']}")

        print("\n[b] ← Back")

        choice = input("\nYour choice: ").strip().lower()

        if choice == "b":
            return None
        elif choice.isdigit() and 1 <= int(choice) <= len(recommendations):
            return recommendations[int(choice) - 1]
        else:
            print("Invalid choice!")
            input("Press Enter to continue...")
            return self.show_recommended_menu()

    def show_history_menu(self) -> Optional[Dict]:
        """Show conversation history menu."""
        self.clear_screen()
        self.print_header("📜 Recent Conversations")

        recent = self.history.get_recent(10)
        if not recent:
            print("\nNo conversation history yet!")
            input("\nPress Enter to continue...")
            return None

        for i, conv in enumerate(reversed(recent), 1):
            timestamp = datetime.fromisoformat(conv["timestamp"])
            time_str = timestamp.strftime("%m/%d %I:%M%p")

            persona = self.personas.get(conv["merchant"], {})
            scenario = self.scenarios.get(conv["scenario"], {})

            print(f"\n[{i}] {time_str}")
            print(f"    • {persona['name'] if persona else conv['merchant']}")
            print(f"    • {scenario.display_name if scenario else conv['scenario']}")
            print(f"    • {conv['workflow']} ({conv['cj_version']})")

        print("\n[b] ← Back")

        choice = input("\nYour choice: ").strip().lower()

        if choice == "b":
            return None
        elif choice.isdigit() and 1 <= int(choice) <= len(recent):
            return list(reversed(recent))[int(choice) - 1]
        else:
            print("Invalid choice!")
            input("Press Enter to continue...")
            return self.show_history_menu()

    def confirm_and_launch(
        self,
        merchant: str,
        scenario: str,
        workflow: str,
        cj_version: str = None,
        turns: int = 10,
    ) -> bool:
        """Show confirmation and launch conversation."""
        self.clear_screen()
        self.print_header("🚀 Ready to Launch!")

        # Use default CJ version if not specified
        if cj_version is None:
            cj_version = settings.default_cj_version

        persona = self.personas[merchant]
        scenario_data = self.scenarios[scenario]
        workflow_data = self.workflows[workflow]

        print("\n📋 Conversation Setup:")
        print(f"\n• Merchant: {persona['name']} - {persona['business']}")
        print(f"\n• Scenario: {scenario_data.display_name}")
        print(f"  {scenario_data.description[:80]}...")
        print(f"\n• Workflow: {workflow_data.display_name}")
        print(f"  {workflow_data.description}")
        print(f"\n• CJ Version: {cj_version}")
        print(f"• Max Turns: {turns}")

        # Show universe info
        universe_info = self.universe_discovery.get_universe_info(merchant, scenario)
        if universe_info:
            print("\n📊 Universe Data:")
            print(f"  • Customers: {universe_info['total_customers']}")
            print(f"  • Support Tickets: {universe_info['total_tickets']}")
            print(
                f"  • Timeline: Day {universe_info['current_day']}/{universe_info['timeline_days']}"
            )
        else:
            print("\n⚠️  No universe data available!")

        # Check if universe exists
        has_universe = self.universe_discovery.has_universe(merchant, scenario)

        if has_universe:
            print("\n[Enter] Start conversation")
        else:
            print("\n[g] 🚀 Generate universe for this scenario")
        print("[t] Change max turns (current: {})".format(turns))
        print("[b] ← Back to menu")

        choice = input("\nYour choice: ").strip().lower()

        if choice == "b":
            return False
        elif choice == "t":
            new_turns = input("Enter max turns (1-20): ").strip()
            if new_turns.isdigit() and 1 <= int(new_turns) <= 20:
                turns = int(new_turns)
            return self.confirm_and_launch(
                merchant, scenario, workflow, cj_version, turns
            )
        elif choice == "g" and not has_universe:
            self.generate_universe(merchant, scenario)
            # After generation, show confirmation again
            return self.confirm_and_launch(
                merchant, scenario, workflow, cj_version, turns
            )
        elif choice == "" and has_universe:
            # Only allow Enter to start if universe exists
            self.history.add_conversation(merchant, scenario, workflow, cj_version)
            self.launch_conversation(merchant, scenario, workflow, cj_version, turns)
            return True
        else:
            if not has_universe:
                print("\n⚠️  Cannot start conversation without universe data!")
                print("Please generate the universe first.")
                input("\nPress Enter to continue...")
                return False
            else:
                # Launch the conversation
                self.history.add_conversation(merchant, scenario, workflow, cj_version)
                self.launch_conversation(
                    merchant, scenario, workflow, cj_version, turns
                )
                return True

    def confirm_and_launch_with_reroll(
        self,
        merchant: str,
        scenario: str,
        workflow: str,
        cj_version: str = None,
        turns: int = 10,
    ):
        """Show confirmation with reroll option for random conversations."""
        self.clear_screen()
        self.print_header("🎲 Random Conversation")

        # Use default CJ version if not specified
        if cj_version is None:
            cj_version = settings.default_cj_version

        persona = self.personas[merchant]
        scenario_data = self.scenarios[scenario]
        workflow_data = self.workflows[workflow]

        print("\n📋 Random Conversation Setup:")
        print(f"\n• Merchant: {persona['name']} - {persona['business']}")
        print(f"\n• Scenario: {scenario_data.display_name}")
        print(f"  {scenario_data.description[:80]}...")
        print(f"\n• Workflow: {workflow_data.display_name}")
        print(f"  {workflow_data.description}")
        print(f"\n• CJ Version: {cj_version}")
        print(f"• Max Turns: {turns}")

        # Show universe info
        universe_info = self.universe_discovery.get_universe_info(merchant, scenario)
        if universe_info:
            print("\n📊 Universe Data:")
            print(f"  • Customers: {universe_info['total_customers']}")
            print(f"  • Support Tickets: {universe_info['total_tickets']}")
            print(
                f"  • Timeline: Day {universe_info['current_day']}/{universe_info['timeline_days']}"
            )

        print("\n[Enter] Start conversation")
        print("[r] 🎲 Roll again (different random combo)")
        print("[t] Change max turns (current: {})".format(turns))
        print("[b] ← Back to menu")

        choice = input("\nYour choice: ").strip().lower()

        if choice == "b":
            return False
        elif choice == "r":
            return "reroll"
        elif choice == "t":
            new_turns = input("Enter max turns (1-20): ").strip()
            if new_turns.isdigit() and 1 <= int(new_turns) <= 20:
                turns = int(new_turns)
            return self.confirm_and_launch_with_reroll(
                merchant, scenario, workflow, cj_version, turns
            )
        else:
            # Launch the conversation
            self.history.add_conversation(merchant, scenario, workflow, cj_version)
            self.launch_conversation(merchant, scenario, workflow, cj_version, turns)
            return True

    def launch_conversation(
        self, merchant: str, scenario: str, workflow: str, cj_version: str, turns: int
    ):
        """Launch the actual conversation."""
        # Get the script path relative to project root
        script_path = os.path.join(
            project_root, "scripts", "demos", "play_conversation_simple.py"
        )

        cmd = [
            sys.executable,
            script_path,
            "--merchant",
            merchant,
            "--scenario",
            scenario,
            "--workflow",
            workflow,
            "--cj-version",
            cj_version,
            "--turns",
            str(turns),
        ]

        print("\n🎭 Launching conversation...\n")
        subprocess.run(cmd)

    def run_quick_start(self):
        """Run the quick start menu flow."""
        merchant = self.show_persona_menu()
        if not merchant:
            return

        scenario = self.show_scenario_menu(merchant)
        if not scenario:
            return

        workflow = self.show_workflow_menu(scenario)
        if not workflow:
            return

        cj_version = self.show_cj_version_menu()
        if not cj_version:
            return

        self.confirm_and_launch(merchant, scenario, workflow, cj_version)

    def run_random(self):
        """Run a random conversation."""
        while True:
            # Only choose from combinations that have universes
            available_combos = self.universe_discovery.get_available_combinations()
            if not available_combos:
                print("\n⚠️  No universes available! Generate some first.")
                input("\nPress Enter to continue...")
                return

            # Pick a random universe combination
            merchant, scenario = random.choice(available_combos)

            # Pick a workflow that makes sense for the scenario
            suitable_workflows = [
                key
                for key, wf in self.workflows.items()
                if scenario in wf.best_for or "all scenarios" in wf.best_for
            ]
            workflow = random.choice(
                suitable_workflows
                if suitable_workflows
                else list(self.workflows.keys())
            )

            # Modified confirm_and_launch to support re-rolling
            result = self.confirm_and_launch_with_reroll(merchant, scenario, workflow)
            if result != "reroll":
                break

    def run_last(self):
        """Repeat the last conversation."""
        last = self.history.get_last()
        if not last:
            print("\nNo previous conversation found!")
            input("Press Enter to continue...")
            return

        self.confirm_and_launch(
            last["merchant"],
            last["scenario"],
            last["workflow"],
            last.get("cj_version", "v5.0.0"),
        )

    def run_express(self):
        """Run with all defaults (Marcus + growth_stall + ad_hoc_support)."""
        self.confirm_and_launch("marcus_thompson", "growth_stall", "ad_hoc_support")

    def run_custom(self):
        """Show custom command interface."""
        self.clear_screen()
        self.print_header("🔧 Custom Command")

        print("\nBase command: make conversation-play")
        print("\nAvailable options:")
        print("  MERCHANT=<name>    - Merchant persona")
        print("  SCENARIO=<name>    - Business scenario")
        print("  WORKFLOW=<name>    - Conversation workflow")
        print("  CJ_VERSION=<ver>   - CJ version")
        print("  TURNS=<n>          - Max conversation turns")

        print("\nExample:")
        print(
            "  make conversation-play MERCHANT=sarah_chen SCENARIO=churn_spike TURNS=15"
        )

        print("\nEnter your custom options (or 'b' to go back):")
        options = input("> ").strip()

        if options.lower() == "b":
            return

        # Parse and execute
        cmd = ["make", "conversation-play"]
        if options:
            cmd.extend(options.split())

        print(f"\nExecuting: {' '.join(cmd)}")
        subprocess.run(cmd)
        input("\nPress Enter to continue...")

    def run(self):
        """Main menu loop."""
        while True:
            choice = self.show_main_menu()

            if choice == "q":
                print("\n👋 Thanks for using HireCJ Conversation Launcher!")
                break
            elif choice == "1":
                self.run_quick_start()
            elif choice == "2":
                self.run_random()
            elif choice == "3":
                rec = self.show_recommended_menu()
                if rec:
                    self.confirm_and_launch(
                        rec["merchant"], rec["scenario"], rec["workflow"]
                    )
            elif choice == "4":
                self.run_last()
            elif choice == "5":
                conv = self.show_history_menu()
                if conv:
                    self.confirm_and_launch(
                        conv["merchant"],
                        conv["scenario"],
                        conv["workflow"],
                        conv.get("cj_version", "v5.0.0"),
                    )
            elif choice == "6":
                self.run_express()
            elif choice == "7":
                self.run_custom()
            elif choice == "8":
                self.show_universe_management()
            else:
                print("Invalid choice!")

            if choice in ["1", "2", "3", "4", "5", "6"]:
                input("\nPress Enter to return to main menu...")

    def generate_universe(self, merchant: str, scenario: str):
        """Generate a single universe."""
        print(f"\n🚀 Generating universe for {merchant}/{scenario}...")
        print("This may take a few minutes...\n")

        cmd = [
            "make",
            "generate-universe",
            f"MERCHANT={merchant}",
            f"SCENARIO={scenario}",
        ]

        result = subprocess.run(cmd)

        if result.returncode == 0:
            print("\n✅ Universe generated successfully!")
            # Refresh discovery to include new universe
            self.universe_discovery.refresh()
        else:
            print("\n❌ Failed to generate universe")

        input("\nPress Enter to continue...")

    def generate_missing_universes(self, merchant: str):
        """Generate all missing universes for a merchant."""
        self.clear_screen()
        self.print_header(
            f"Generate Universes for {self.personas[merchant].display_name}"
        )

        missing_scenarios = []
        for scenario_key in self.scenarios.keys():
            if not self.universe_discovery.has_universe(merchant, scenario_key):
                missing_scenarios.append(scenario_key)

        if not missing_scenarios:
            print("\n✅ All universes already exist!")
            input("\nPress Enter to continue...")
            return

        print(f"\nMissing universes for {len(missing_scenarios)} scenarios:")
        for scenario in missing_scenarios:
            print(f"  • {self.scenarios[scenario].display_name}")

        print(f"\nGenerate all {len(missing_scenarios)} universes? [y/n]")
        if input("> ").strip().lower() != "y":
            return

        for i, scenario in enumerate(missing_scenarios, 1):
            print(f"\n[{i}/{len(missing_scenarios)}] Generating {scenario}...")
            self.generate_universe(merchant, scenario)

    def show_universe_management(self):
        """Show universe management menu."""
        self.clear_screen()
        self.print_header("🌌 Universe Management")

        # Show current status
        available_combos = self.universe_discovery.get_available_combinations()
        total_possible = len(self.personas) * len(self.scenarios)

        print(f"\n📊 Current Status: {len(available_combos)}/{total_possible} universes")

        # Group by merchant
        print("\n📁 Available Universes:")
        for merchant in self.personas.keys():
            scenarios = self.universe_discovery.get_scenarios_for_merchant(merchant)
            persona = self.personas[merchant]
            if scenarios:
                print(f"\n  {persona['name']}:")
                for scenario in scenarios:
                    info = self.universe_discovery.get_universe_info(merchant, scenario)
                    if info:
                        # Get scenario display name, fallback to key if not in catalog
                        scenario_display = self.scenarios.get(scenario, None)
                        if scenario_display:
                            scenario_name = scenario_display.display_name
                        else:
                            scenario_name = scenario.replace("_", " ").title()
                        print(
                            f"    • {scenario_name} - {info['total_customers']} customers, {info['total_tickets']} tickets"
                        )
            else:
                print(f"\n  {persona['name']}: No universes")

        print("\n[1] 🚀 Generate missing universes for a merchant")
        print("[2] 🎯 Generate specific universe")
        print("[3] 🔄 Refresh universe list")
        print("[4] 📊 Show detailed universe info")
        print("\n[b] ← Back")

        choice = input("\nYour choice: ").strip().lower()

        if choice == "1":
            merchant = self.show_persona_menu()
            if merchant:
                self.generate_missing_universes(merchant)
        elif choice == "2":
            merchant = self.show_persona_menu()
            if merchant:
                scenario = self.show_scenario_menu(merchant)
                if scenario:
                    self.generate_universe(merchant, scenario)
        elif choice == "3":
            self.universe_discovery.refresh()
            print("\n✅ Universe list refreshed!")
            input("\nPress Enter to continue...")
        elif choice == "4":
            self.show_detailed_universe_info()
        elif choice == "b":
            return  # Just return, no need to press Enter
        else:
            print("Invalid choice!")
            input("Press Enter to continue...")

    def show_detailed_universe_info(self):
        """Show detailed info about a specific universe."""
        merchant = self.show_persona_menu()
        if not merchant:
            return

        scenario = self.show_scenario_menu(merchant)
        if not scenario:
            return

        info = self.universe_discovery.get_universe_info(merchant, scenario)
        if not info:
            print(f"\n❌ No universe found for {merchant}/{scenario}")
            input("\nPress Enter to continue...")
            return

        self.clear_screen()
        self.print_header(f"Universe: {merchant}/{scenario}")

        print("\n📊 Universe Details:")
        print(f"  • Path: {info['path']}")
        print(f"  • Generated: {info['generated_at']}")
        print(f"  • Timeline: {info['timeline_days']} days")
        print(f"  • Current Day: {info['current_day']}")
        print(f"  • Total Customers: {info['total_customers']}")
        print(f"  • Total Tickets: {info['total_tickets']}")

        input("\nPress Enter to continue...")


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Interactive conversation launcher for HireCJ"
    )
    parser.add_argument(
        "--direct", action="store_true", help="Skip menu and use command line args"
    )
    parser.add_argument("--merchant", help="Merchant persona")
    parser.add_argument("--scenario", help="Business scenario")
    parser.add_argument("--workflow", help="Conversation workflow")
    parser.add_argument("--cj-version", default="v5.0.0", help="CJ version")
    parser.add_argument("--turns", type=int, default=10, help="Max turns")

    args = parser.parse_args()

    launcher = ConversationLauncher()

    if args.direct and args.merchant and args.scenario:
        # Direct launch mode
        workflow = args.workflow or "ad_hoc_support"
        launcher.launch_conversation(
            args.merchant, args.scenario, workflow, args.cj_version, args.turns
        )
    else:
        # Interactive menu mode
        launcher.run()


if __name__ == "__main__":
    main()
