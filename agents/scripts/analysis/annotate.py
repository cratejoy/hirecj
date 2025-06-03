#!/usr/bin/env python3
"""
Simple annotation tool for conversations.
Allows adding inline comments to specific messages.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import argparse
from typing import Dict, Any, Optional


def load_conversation(file_path: str) -> Dict[str, Any]:
    """Load conversation from JSON file."""
    with open(file_path, "r") as f:
        return json.load(f)


def save_conversation(file_path: str, conversation: Dict[str, Any]):
    """Save conversation back to JSON file."""
    with open(file_path, "w") as f:
        json.dump(conversation, f, indent=2, default=str)


def display_conversation(conversation: Dict[str, Any]):
    """Display conversation with message numbers."""
    print("\n" + "=" * 60)
    print("CONVERSATION")
    print("=" * 60 + "\n")

    messages = conversation.get("messages", [])
    for i, msg in enumerate(messages):
        sender = msg.get("sender", "Unknown")
        content = msg.get("content", "")
        annotation = msg.get("annotation", "")

        # Color coding for sender
        if sender == "CJ":
            print(f"\033[94m[{i}] CJ:\033[0m")
        else:
            print(f"\033[92m[{i}] {sender}:\033[0m")

        # Print content
        print(f"    {content[:100]}..." if len(content) > 100 else f"    {content}")

        # Show existing annotation if any
        if annotation:
            print(f"    \033[93m→ Annotation: {annotation}\033[0m")

        print()


def parse_annotation(input_str: str) -> tuple[Optional[int], Optional[str]]:
    """Parse annotation input like '3 dislike too formal'."""
    parts = input_str.strip().split(" ", 1)

    if not parts:
        return None, None

    try:
        msg_index = int(parts[0])
        annotation = parts[1] if len(parts) > 1 else None
        return msg_index, annotation
    except ValueError:
        return None, None


def annotate_conversation(file_path: str):
    """Interactive annotation loop."""
    conversation = load_conversation(file_path)
    messages = conversation.get("messages", [])

    print("\nAnnotation Commands:")
    print("  <number> <comment>  - Add annotation to message")
    print("  <number> -          - Remove annotation from message")
    print("  show                - Show conversation again")
    print("  save                - Save and exit")
    print("  quit                - Save and exit")
    print("\nExamples:")
    print("  3 like good data")
    print("  5 dislike too formal")
    print("  7 needs work - should mention specific metrics")

    display_conversation(conversation)

    while True:
        try:
            user_input = input("\n> ").strip()

            if user_input.lower() == "quit":
                save_conversation(file_path, conversation)
                print(f"✓ Saved annotations to {file_path}")
                break

            if user_input.lower() == "save":
                save_conversation(file_path, conversation)
                print(f"✓ Saved annotations to {file_path}")
                break

            if user_input.lower() == "show":
                display_conversation(conversation)
                continue

            msg_index, annotation = parse_annotation(user_input)

            if msg_index is None:
                print("Invalid input. Use format: <number> <comment>")
                continue

            if msg_index < 0 or msg_index >= len(messages):
                print(
                    f"Invalid message number. Must be between 0 and {len(messages)-1}"
                )
                continue

            if annotation == "-":
                # Remove annotation
                if "annotation" in messages[msg_index]:
                    del messages[msg_index]["annotation"]
                    print(f"✓ Removed annotation from message {msg_index}")
            elif annotation:
                # Add/update annotation
                messages[msg_index]["annotation"] = annotation
                messages[msg_index]["annotated_at"] = datetime.now().isoformat()
                print(f"✓ Added annotation to message {msg_index}")
            else:
                print("No annotation text provided")

        except KeyboardInterrupt:
            print("\n\nExiting without saving.")
            break
        except Exception as e:
            print(f"Error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Annotate conversation messages")
    parser.add_argument(
        "conversation_file", nargs="?", help="Path to conversation JSON file"
    )
    parser.add_argument(
        "--latest", action="store_true", help="Annotate the most recent conversation"
    )

    args = parser.parse_args()

    if args.latest or not args.conversation_file:
        # Find most recent conversation
        conv_dir = Path("data/conversations")
        conversations = list(conv_dir.glob("*.json"))
        if not conversations:
            print("No conversations found in data/conversations/")
            sys.exit(1)

        latest = max(conversations, key=lambda p: p.stat().st_mtime)
        file_path = str(latest)
        print(f"Annotating latest conversation: {latest.name}")
    else:
        file_path = args.conversation_file

    if not Path(file_path).exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    annotate_conversation(file_path)


if __name__ == "__main__":
    main()
