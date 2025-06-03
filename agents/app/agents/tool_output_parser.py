"""
Parser for extracting tool outputs from CrewAI execution logs.
"""

import re
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ToolCall:
    """Represents a single tool call and its output"""

    tool_name: str
    tool_input: Dict[str, Any]
    tool_output: Any
    raw_output: str
    error: Optional[str] = None


class ToolOutputParser:
    """Parses tool outputs from CrewAI execution logs"""

    # Regex patterns for different CrewAI output formats
    PATTERNS = {
        # Pattern: "Tool: tool_name"
        "tool_start": re.compile(r"^Tool:\s*(\w+)", re.MULTILINE),
        # Pattern: "Tool Input: {...}" or "Tool Input: ..."
        "tool_input": re.compile(
            r"^Tool Input:\s*(.+?)(?=^Tool Output:|^Tool:|^Final Answer:|^Error:|$)",
            re.MULTILINE | re.DOTALL,
        ),
        # Pattern: "Tool Output: ..." (captures until next section)
        "tool_output": re.compile(
            r"^Tool Output:\s*(.+?)(?=\n\nTool:|\n\nFinal Answer:|\n\nThought:|\n\nAction:|\n\nBased on|\Z)",
            re.MULTILINE | re.DOTALL,
        ),
        # Pattern for error outputs
        "tool_error": re.compile(
            r"^Error:\s*(.+?)(?=^Tool:|^Final Answer:|^Thought:|^Action:|$)",
            re.MULTILINE | re.DOTALL,
        ),
        # Alternative patterns for different CrewAI versions
        "action_format": re.compile(r"Action:\s*(\w+)\[(.*?)\]", re.DOTALL),
        "observation_format": re.compile(
            r"Observation:\s*(.+?)(?=Action:|Thought:|Final Answer:|$)", re.DOTALL
        ),
    }

    def parse(self, captured_output: str) -> List[ToolCall]:
        """Parse tool calls from CrewAI captured output"""
        tool_calls = []

        # Try standard format first
        tool_calls.extend(self._parse_standard_format(captured_output))

        # Try alternative format if no results
        if not tool_calls:
            tool_calls.extend(self._parse_action_format(captured_output))

        return tool_calls

    def _parse_standard_format(self, output: str) -> List[ToolCall]:
        """Parse standard CrewAI format (Tool: / Tool Input: / Tool Output:)"""
        tool_calls = []

        # Split by tool occurrences
        tool_sections = re.split(r"^Tool:", output, flags=re.MULTILINE)[1:]

        for section in tool_sections:
            # Add back "Tool:" prefix for parsing
            section = "Tool:" + section

            # Extract tool name
            tool_match = self.PATTERNS["tool_start"].search(section)
            if not tool_match:
                continue

            tool_name = tool_match.group(1)

            # Extract input
            input_match = self.PATTERNS["tool_input"].search(section)
            tool_input = {}
            if input_match:
                input_str = input_match.group(1).strip()
                try:
                    # Try to parse as JSON
                    tool_input = json.loads(input_str)
                except json.JSONDecodeError:
                    # If not JSON, store as string
                    tool_input = {"input": input_str}

            # Extract output or error
            output_match = self.PATTERNS["tool_output"].search(section)
            error_match = self.PATTERNS["tool_error"].search(section)

            if output_match:
                output_str = output_match.group(1).strip()
                tool_output, parsed_output = self._parse_tool_output(output_str)

                tool_calls.append(
                    ToolCall(
                        tool_name=tool_name,
                        tool_input=tool_input,
                        tool_output=tool_output,
                        raw_output=parsed_output or output_str,
                    )
                )
            elif error_match:
                error_str = error_match.group(1).strip()
                tool_calls.append(
                    ToolCall(
                        tool_name=tool_name,
                        tool_input=tool_input,
                        tool_output=None,
                        raw_output=error_str,
                        error=error_str,
                    )
                )

        return tool_calls

    def _parse_action_format(self, output: str) -> List[ToolCall]:
        """Parse alternative CrewAI format (Action: tool[input])"""
        tool_calls = []

        # Find all action/observation pairs
        action_matches = list(self.PATTERNS["action_format"].finditer(output))

        for i, action_match in enumerate(action_matches):
            tool_name = action_match.group(1)
            input_str = action_match.group(2).strip()

            # Parse input
            try:
                tool_input = json.loads(input_str) if input_str else {}
            except json.JSONDecodeError:
                tool_input = {"input": input_str}

            # Find corresponding observation
            start_pos = action_match.end()
            end_pos = (
                action_matches[i + 1].start()
                if i + 1 < len(action_matches)
                else len(output)
            )

            section = output[start_pos:end_pos]
            obs_match = self.PATTERNS["observation_format"].search(section)

            if obs_match:
                output_str = obs_match.group(1).strip()
                tool_output, parsed_output = self._parse_tool_output(output_str)

                tool_calls.append(
                    ToolCall(
                        tool_name=tool_name,
                        tool_input=tool_input,
                        tool_output=tool_output,
                        raw_output=parsed_output or output_str,
                    )
                )

        return tool_calls

    def _parse_tool_output(self, output_str: str) -> tuple[Any, Optional[str]]:
        """Parse tool output string, attempting JSON parsing"""
        # Clean up the output
        output_str = output_str.strip()

        # Remove markdown code blocks if present
        if "```" in output_str:
            # Extract content between triple backticks
            import re

            code_block_match = re.search(
                r"```(?:json)?\s*\n?(.*?)\n?```", output_str, re.DOTALL
            )
            if code_block_match:
                output_str = code_block_match.group(1).strip()

        # Try to parse as JSON
        try:
            return json.loads(output_str), output_str
        except json.JSONDecodeError:
            # Check if it looks like a JSON object or array
            if (output_str.startswith("{") and output_str.endswith("}")) or (
                output_str.startswith("[") and output_str.endswith("]")
            ):
                # Try to fix common JSON issues
                try:
                    # Replace single quotes with double quotes
                    fixed = output_str.replace("'", '"')
                    return json.loads(fixed), fixed
                except (json.JSONDecodeError, ValueError):
                    pass

            # Return as string if not JSON
            return output_str, None

    def extract_tool_outputs_for_fact_checking(
        self, captured_output: str
    ) -> List[Dict[str, Any]]:
        """Extract tool outputs in format expected by fact checker"""
        tool_calls = self.parse(captured_output)

        result = []
        for call in tool_calls:
            if call.error:
                continue  # Skip errored calls

            result.append(
                {
                    "tool": call.tool_name,
                    "input": call.tool_input,
                    "output": call.tool_output,
                }
            )

        return result
