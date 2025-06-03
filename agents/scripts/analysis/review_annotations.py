#!/usr/bin/env python3
"""
Review annotations across all conversations.
Find patterns in what's liked/disliked.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
import argparse
from typing import Dict, List, Any


def load_all_conversations(
    directory: str = "data/conversations",
) -> List[Dict[str, Any]]:
    """Load all conversation files that have annotations."""
    conversations = []
    conv_dir = Path(directory)

    for file_path in conv_dir.glob("*.json"):
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                # Only include if it has annotations
                if any(msg.get("annotation") for msg in data.get("messages", [])):
                    data["_file_path"] = str(file_path)
                    conversations.append(data)
        except Exception as e:
            print(f"Error loading {file_path}: {e}", file=sys.stderr)

    return conversations


def extract_annotations(
    conversations: List[Dict[str, Any]], filter_text: str = None
) -> Dict[str, List[Dict]]:
    """Extract and group annotations by pattern."""
    grouped = defaultdict(list)

    for conv in conversations:
        file_name = Path(conv["_file_path"]).name
        scenario = conv.get("scenario", "unknown")
        merchant = conv.get("merchant_persona", "unknown")

        for i, msg in enumerate(conv.get("messages", [])):
            annotation = msg.get("annotation", "")
            if not annotation:
                continue

            # Apply filter if specified
            if filter_text and filter_text.lower() not in annotation.lower():
                continue

            # Group by annotation type (first word)
            annotation_type = annotation.split()[0].lower() if annotation else "other"

            grouped[annotation_type].append(
                {
                    "file": file_name,
                    "scenario": scenario,
                    "merchant": merchant,
                    "message_index": i,
                    "sender": msg.get("sender", "Unknown"),
                    "content": msg.get("content", "")[:100] + "...",
                    "annotation": annotation,
                    "annotated_at": msg.get("annotated_at", "unknown"),
                }
            )

    return grouped


def print_grouped_annotations(grouped: Dict[str, List[Dict]]):
    """Print annotations grouped by type."""
    print("\n" + "=" * 60)
    print("ANNOTATION REVIEW")
    print("=" * 60)

    for annotation_type, annotations in sorted(grouped.items()):
        print(
            f"\n\033[1m{annotation_type.upper()} ({len(annotations)} annotations)\033[0m"
        )
        print("-" * 40)

        # Group by scenario
        by_scenario = defaultdict(list)
        for ann in annotations:
            by_scenario[ann["scenario"]].append(ann)

        for scenario, scenario_anns in sorted(by_scenario.items()):
            print(f"\n  Scenario: {scenario}")
            for ann in scenario_anns:
                print(f"    [{ann['message_index']}] {ann['sender']}: {ann['content']}")
                print(f"    \033[93m→ {ann['annotation']}\033[0m")
                print(f"    File: {ann['file']}")
                print()


def print_summary(grouped: Dict[str, List[Dict]]):
    """Print summary statistics."""
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    total = sum(len(anns) for anns in grouped.values())
    print(f"\nTotal annotations: {total}")

    print("\nBy type:")
    for annotation_type, annotations in sorted(
        grouped.items(), key=lambda x: -len(x[1])
    ):
        print(
            f"  {annotation_type}: {len(annotations)} ({len(annotations)/total*100:.1f}%)"
        )

    print("\nBy scenario:")
    scenario_counts = defaultdict(int)
    for annotations in grouped.values():
        for ann in annotations:
            scenario_counts[ann["scenario"]] += 1

    for scenario, count in sorted(scenario_counts.items(), key=lambda x: -x[1]):
        print(f"  {scenario}: {count}")

    print("\nBy sender:")
    sender_counts = defaultdict(int)
    for annotations in grouped.values():
        for ann in annotations:
            sender_counts[ann["sender"]] += 1

    for sender, count in sorted(sender_counts.items(), key=lambda x: -x[1]):
        print(f"  {sender}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Review conversation annotations")
    parser.add_argument(
        "--filter", "-f", help="Filter annotations containing this text"
    )
    parser.add_argument(
        "--type", "-t", help="Filter by annotation type (like, dislike, etc)"
    )
    parser.add_argument("--scenario", "-s", help="Filter by scenario name")
    parser.add_argument(
        "--summary-only", action="store_true", help="Show only summary statistics"
    )

    args = parser.parse_args()

    # Load conversations
    conversations = load_all_conversations()

    if not conversations:
        print("No annotated conversations found.")
        sys.exit(0)

    print(f"Found {len(conversations)} annotated conversations")

    # Extract annotations
    filter_text = args.filter or args.type
    grouped = extract_annotations(conversations, filter_text)

    # Apply scenario filter if specified
    if args.scenario:
        for annotation_type in grouped:
            grouped[annotation_type] = [
                ann
                for ann in grouped[annotation_type]
                if args.scenario.lower() in ann["scenario"].lower()
            ]

    # Remove empty groups
    grouped = {k: v for k, v in grouped.items() if v}

    if not grouped:
        print("No annotations match the specified filters.")
        sys.exit(0)

    # Display results
    if not args.summary_only:
        print_grouped_annotations(grouped)

    print_summary(grouped)


if __name__ == "__main__":
    main()
