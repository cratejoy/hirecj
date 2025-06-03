"""Tests for constants definitions."""

from app.constants import (
    HTTPStatus,
    WebSocketCloseCodes,
    DisplayLimits,
    PaginationDefaults,
    SatisfactionScores,
    TimeConstants,
    TruncationLimits,
    FileFormats,
)


class TestHTTPStatus:
    """Test HTTP status code constants."""

    def test_standard_status_codes(self):
        """Test that standard HTTP status codes are defined correctly."""
        assert HTTPStatus.OK == 200
        assert HTTPStatus.BAD_REQUEST == 400
        assert HTTPStatus.UNAUTHORIZED == 401
        assert HTTPStatus.FORBIDDEN == 403
        assert HTTPStatus.NOT_FOUND == 404
        assert HTTPStatus.INTERNAL_SERVER_ERROR == 500
        assert HTTPStatus.SERVICE_UNAVAILABLE == 503


class TestWebSocketCloseCodes:
    """Test WebSocket close code constants."""

    def test_websocket_close_codes(self):
        """Test that WebSocket close codes match RFC 6455."""
        assert WebSocketCloseCodes.NORMAL_CLOSURE == 1000
        assert WebSocketCloseCodes.GOING_AWAY == 1001
        assert WebSocketCloseCodes.PROTOCOL_ERROR == 1002
        assert WebSocketCloseCodes.UNSUPPORTED_DATA == 1003
        assert WebSocketCloseCodes.NO_STATUS_RECEIVED == 1005
        assert WebSocketCloseCodes.ABNORMAL_CLOSURE == 1006
        assert WebSocketCloseCodes.INVALID_FRAME_PAYLOAD_DATA == 1007
        assert WebSocketCloseCodes.POLICY_VIOLATION == 1008
        assert WebSocketCloseCodes.MESSAGE_TOO_BIG == 1009
        assert WebSocketCloseCodes.MISSING_EXTENSION == 1010
        assert WebSocketCloseCodes.INTERNAL_ERROR == 1011
        assert WebSocketCloseCodes.SERVICE_RESTART == 1012
        assert WebSocketCloseCodes.TRY_AGAIN_LATER == 1013


class TestDisplayLimits:
    """Test UI display limit constants."""

    def test_display_limits(self):
        """Test display limit values."""
        assert DisplayLimits.TRENDING_ISSUES_COUNT == 3
        assert DisplayLimits.SEARCH_RESULTS_COUNT == 5
        assert DisplayLimits.LOG_HEIGHT_PX == 300
        assert DisplayLimits.INPUT_WIDTH_PX == 300


class TestPaginationDefaults:
    """Test pagination default constants."""

    def test_pagination_values(self):
        """Test pagination default values."""
        assert PaginationDefaults.DEFAULT_LIMIT == 50
        assert PaginationDefaults.MIN_LIMIT == 1
        assert PaginationDefaults.MAX_LIMIT == 100

    def test_pagination_constraints(self):
        """Test that pagination constraints make sense."""
        assert PaginationDefaults.MIN_LIMIT <= PaginationDefaults.DEFAULT_LIMIT
        assert PaginationDefaults.DEFAULT_LIMIT <= PaginationDefaults.MAX_LIMIT


class TestSatisfactionScores:
    """Test customer satisfaction score constants."""

    def test_satisfaction_values(self):
        """Test satisfaction score values."""
        assert SatisfactionScores.VERY_UNSATISFIED == 1
        assert SatisfactionScores.UNSATISFIED == 2
        assert SatisfactionScores.NEUTRAL == 3
        assert SatisfactionScores.SATISFIED == 4
        assert SatisfactionScores.VERY_SATISFIED == 5

    def test_get_label(self):
        """Test getting human-readable labels."""
        assert SatisfactionScores.get_label(1) == "Very Unsatisfied"
        assert SatisfactionScores.get_label(2) == "Unsatisfied"
        assert SatisfactionScores.get_label(3) == "Neutral"
        assert SatisfactionScores.get_label(4) == "Satisfied"
        assert SatisfactionScores.get_label(5) == "Very Satisfied"

    def test_get_label_invalid(self):
        """Test getting label for invalid score."""
        assert SatisfactionScores.get_label(0) == "Unknown"
        assert SatisfactionScores.get_label(6) == "Unknown"
        assert SatisfactionScores.get_label(-1) == "Unknown"


class TestTimeConstants:
    """Test time-related constants."""

    def test_response_time_values(self):
        """Test response time constants."""
        assert TimeConstants.MIN_RESPONSE_TIME_MINUTES == 300  # 5 hours
        assert TimeConstants.MAX_RESPONSE_TIME_MINUTES == 480  # 8 hours

    def test_response_time_logic(self):
        """Test that min is less than max."""
        assert (
            TimeConstants.MIN_RESPONSE_TIME_MINUTES
            < TimeConstants.MAX_RESPONSE_TIME_MINUTES
        )

    def test_response_time_hours(self):
        """Test conversion to hours."""
        assert TimeConstants.MIN_RESPONSE_TIME_MINUTES / 60 == 5.0
        assert TimeConstants.MAX_RESPONSE_TIME_MINUTES / 60 == 8.0


class TestTruncationLimits:
    """Test string truncation constants."""

    def test_truncation_values(self):
        """Test truncation limit values."""
        assert TruncationLimits.UNIVERSE_DATA_PREVIEW == 1000

    def test_truncation_reasonable(self):
        """Test that truncation limits are reasonable."""
        assert TruncationLimits.UNIVERSE_DATA_PREVIEW > 100  # Not too small
        assert TruncationLimits.UNIVERSE_DATA_PREVIEW < 10000  # Not too large


class TestFileFormats:
    """Test file format constants."""

    def test_universe_id_format(self):
        """Test universe ID format constant."""
        assert FileFormats.UNIVERSE_ID_MIN_PARTS == 3

    def test_universe_id_logic(self):
        """Test that universe ID parsing logic works."""
        # Format should be: merchant_scenario_version
        test_id = "marcus_thompson_steady_operations_v1"
        parts = test_id.split("_")
        assert len(parts) >= FileFormats.UNIVERSE_ID_MIN_PARTS
