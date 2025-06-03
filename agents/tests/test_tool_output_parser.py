"""
Unit tests for the tool output parser.
"""

import pytest
from app.agents.tool_output_parser import ToolOutputParser


class TestToolOutputParser:
    """Test the tool output parsing functionality"""

    @pytest.fixture
    def parser(self):
        """Create a parser instance"""
        return ToolOutputParser()

    def test_parse_standard_format(self, parser):
        """Test parsing standard CrewAI output format"""
        output = """
Thought: I need to check the support dashboard to see the current metrics.

Tool: get_support_dashboard
Tool Input: {}
Tool Output: {
    "queue_status": {
        "total_tickets": 45,
        "open_tickets": 25,
        "in_progress": 15,
        "resolved_today": 5
    },
    "metrics": {
        "avg_response_time": 2.5,
        "satisfaction_score": 4.2
    }
}

Based on the dashboard, there are 25 open tickets.
"""

        tool_calls = parser.parse(output)

        assert len(tool_calls) == 1
        assert tool_calls[0].tool_name == "get_support_dashboard"
        assert tool_calls[0].tool_input == {}
        assert isinstance(tool_calls[0].tool_output, dict)
        assert tool_calls[0].tool_output["queue_status"]["open_tickets"] == 25
        assert tool_calls[0].error is None

    def test_parse_multiple_tools(self, parser):
        """Test parsing multiple tool calls"""
        output = """
Tool: get_support_dashboard
Tool Input: {}
Tool Output: {"queue_size": 30}

Tool: get_customer_profile
Tool Input: {"customer_id": "CUST123"}
Tool Output: {
    "name": "John Smith",
    "subscription": "Premium",
    "satisfaction": 5
}

Final Answer: Checked dashboard and customer profile.
"""

        tool_calls = parser.parse(output)

        assert len(tool_calls) == 2
        assert tool_calls[0].tool_name == "get_support_dashboard"
        assert tool_calls[1].tool_name == "get_customer_profile"
        assert tool_calls[1].tool_input == {"customer_id": "CUST123"}
        assert tool_calls[1].tool_output["name"] == "John Smith"

    def test_parse_error_output(self, parser):
        """Test parsing tool errors"""
        output = """
Tool: get_customer_profile
Tool Input: {"customer_id": "INVALID"}
Error: Customer not found: INVALID

Tool: get_support_dashboard
Tool Input: {}
Tool Output: {"status": "ok"}
"""

        tool_calls = parser.parse(output)

        assert len(tool_calls) == 2
        assert tool_calls[0].error == "Customer not found: INVALID"
        assert tool_calls[0].tool_output is None
        assert tool_calls[1].error is None
        assert tool_calls[1].tool_output == {"status": "ok"}

    def test_parse_action_observation_format(self, parser):
        """Test parsing alternative Action/Observation format"""
        output = """
Thought: Let me check the dashboard.

Action: get_support_dashboard[{}]
Observation: {
    "queue_status": {
        "open_tickets": 20
    }
}

Action: search_support_tickets[{"query": "shipping"}]
Observation: Found 5 tickets matching "shipping"
"""

        tool_calls = parser.parse(output)

        assert len(tool_calls) == 2
        assert tool_calls[0].tool_name == "get_support_dashboard"
        assert tool_calls[0].tool_output["queue_status"]["open_tickets"] == 20
        assert tool_calls[1].tool_name == "search_support_tickets"
        assert tool_calls[1].tool_input == {"query": "shipping"}
        assert tool_calls[1].tool_output == 'Found 5 tickets matching "shipping"'

    def test_parse_non_json_output(self, parser):
        """Test parsing non-JSON tool outputs"""
        output = """
Tool: get_business_timeline
Tool Input: {"days": 7}
Tool Output: Recent events:
- Day 1: Launched new product
- Day 3: Server maintenance
- Day 7: Holiday sale started

Tool: get_trending_issues
Tool Input: {}
Tool Output: ["shipping_delays", "product_quality", "billing_issues"]
"""

        tool_calls = parser.parse(output)

        assert len(tool_calls) == 2
        assert isinstance(tool_calls[0].tool_output, str)
        assert "Launched new product" in tool_calls[0].tool_output
        assert isinstance(tool_calls[1].tool_output, list)
        assert "shipping_delays" in tool_calls[1].tool_output

    def test_parse_markdown_json(self, parser):
        """Test parsing JSON wrapped in markdown code blocks"""
        output = """
Tool: get_support_dashboard
Tool Input: {}
Tool Output: ```json
{
    "status": "active",
    "tickets": 42
}
```

Done checking dashboard.
"""

        tool_calls = parser.parse(output)

        assert len(tool_calls) == 1
        assert tool_calls[0].tool_output == {"status": "active", "tickets": 42}

    def test_extract_for_fact_checking(self, parser):
        """Test extraction in fact-checking format"""
        output = """
Tool: get_support_dashboard
Tool Input: {}
Tool Output: {"open_tickets": 25}

Tool: get_customer_profile
Tool Input: {"customer_id": "ERROR"}
Error: Customer not found

Tool: get_trending_issues
Tool Input: {}
Tool Output: {"issues": ["shipping", "quality"]}
"""

        fact_check_outputs = parser.extract_tool_outputs_for_fact_checking(output)

        # Should exclude the errored call
        assert len(fact_check_outputs) == 2
        assert fact_check_outputs[0]["tool"] == "get_support_dashboard"
        assert fact_check_outputs[0]["output"]["open_tickets"] == 25
        assert fact_check_outputs[1]["tool"] == "get_trending_issues"
        assert "shipping" in fact_check_outputs[1]["output"]["issues"]

    def test_parse_empty_output(self, parser):
        """Test parsing empty or no tool calls"""
        output = """
Just thinking about the problem.
No tools needed for this response.
"""

        tool_calls = parser.parse(output)
        assert len(tool_calls) == 0

    def test_parse_malformed_json(self, parser):
        """Test handling of malformed JSON"""
        output = """
Tool: get_data
Tool Input: {'key': 'value'}
Tool Output: {'status': 'ok', 'count': 10}
"""

        tool_calls = parser.parse(output)

        assert len(tool_calls) == 1
        # Parser should handle single quotes
        assert tool_calls[0].tool_output == {"status": "ok", "count": 10}
