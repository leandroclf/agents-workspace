import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from unittest.mock import patch, MagicMock
import anthropic
from core.error_handler import RobustErrorHandler

def test_retry_on_rate_limit_error():
    handler = RobustErrorHandler(max_retries=2, base_delay=0.01)
    call_count = [0]

    def flaky_fn():
        call_count[0] += 1
        if call_count[0] < 3:
            raise anthropic.RateLimitError(
                message="rate limit",
                response=MagicMock(status_code=429),
                body={}
            )
        return "success"

    result = handler.execute_with_retry(flaky_fn)
    assert result == "success"
    assert call_count[0] == 3

def test_fallback_model_on_overload():
    handler = RobustErrorHandler(max_retries=1, base_delay=0.01)
    result = handler.get_fallback_model("claude-opus-4-7")
    assert result == "claude-sonnet-4-6"

def test_fallback_model_chain():
    handler = RobustErrorHandler()
    assert handler.get_fallback_model("claude-sonnet-4-6") == "claude-haiku-4-5"
    assert handler.get_fallback_model("claude-haiku-4-5") is None

def test_raises_after_max_retries():
    handler = RobustErrorHandler(max_retries=2, base_delay=0.01)
    def always_fails():
        raise anthropic.RateLimitError(
            message="rate limit",
            response=MagicMock(status_code=429),
            body={}
        )
    with pytest.raises(anthropic.RateLimitError):
        handler.execute_with_retry(always_fails)
