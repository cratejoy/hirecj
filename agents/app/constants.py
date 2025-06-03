"""Central constants for HireCJ.

Non-configurable constants that are used throughout the application.
For configurable values, use app.config.settings instead.
"""


# HTTP Status Codes
class HTTPStatus:
    """Standard HTTP status codes."""

    OK = 200
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    INTERNAL_SERVER_ERROR = 500
    SERVICE_UNAVAILABLE = 503


# WebSocket Close Codes
class WebSocketCloseCodes:
    """WebSocket close codes per RFC 6455."""

    NORMAL_CLOSURE = 1000
    GOING_AWAY = 1001
    PROTOCOL_ERROR = 1002
    UNSUPPORTED_DATA = 1003
    NO_STATUS_RECEIVED = 1005
    ABNORMAL_CLOSURE = 1006
    INVALID_FRAME_PAYLOAD_DATA = 1007
    POLICY_VIOLATION = 1008
    MESSAGE_TOO_BIG = 1009
    MISSING_EXTENSION = 1010
    INTERNAL_ERROR = 1011
    SERVICE_RESTART = 1012
    TRY_AGAIN_LATER = 1013


# Display Limits
class DisplayLimits:
    """UI display limits."""

    TRENDING_ISSUES_COUNT = 3
    SEARCH_RESULTS_COUNT = 5
    LOG_HEIGHT_PX = 300
    INPUT_WIDTH_PX = 300


# Pagination
class PaginationDefaults:
    """Default pagination values."""

    DEFAULT_LIMIT = 50
    MIN_LIMIT = 1
    MAX_LIMIT = 100


# Business Logic
class SatisfactionScores:
    """Customer satisfaction score levels."""

    VERY_UNSATISFIED = 1
    UNSATISFIED = 2
    NEUTRAL = 3
    SATISFIED = 4
    VERY_SATISFIED = 5

    @classmethod
    def get_label(cls, score: int) -> str:
        """Get human-readable label for score."""
        labels = {
            cls.VERY_UNSATISFIED: "Very Unsatisfied",
            cls.UNSATISFIED: "Unsatisfied",
            cls.NEUTRAL: "Neutral",
            cls.SATISFIED: "Satisfied",
            cls.VERY_SATISFIED: "Very Satisfied",
        }
        return labels.get(score, "Unknown")


# Time Constants (in minutes)
class TimeConstants:
    """Time-related constants in minutes."""

    MIN_RESPONSE_TIME_MINUTES = 300  # 5 hours
    MAX_RESPONSE_TIME_MINUTES = 480  # 8 hours


# String Truncation
class TruncationLimits:
    """String truncation limits for display."""

    UNIVERSE_DATA_PREVIEW = 1000


# File Format Constants
class FileFormats:
    """File format constants."""

    UNIVERSE_ID_MIN_PARTS = 3  # Format: merchant_scenario_version
