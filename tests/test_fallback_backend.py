import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest
from unittest.mock import MagicMock
from core.fallback_backend import FallbackBackend
from core.claude_code_backend import BackendLimitError


def _ok_backend(text="ok"):
    b = MagicMock()
    b.complete.return_value = {
        "text": text, "model": "sonnet",
        "input_tokens": 5, "output_tokens": 10, "cost_usd": 0.0,
    }
    b.is_available.return_value = True
    return b


def _limit_backend():
    b = MagicMock()
    b.complete.side_effect = BackendLimitError("limite atingido")
    b.is_available.return_value = True
    return b


def test_returns_first_backend_result_when_no_limit():
    b1 = _ok_backend("primeiro")
    b2 = _ok_backend("segundo")
    fb = FallbackBackend([b1, b2])
    result = fb.complete(prompt="teste")
    assert result["text"] == "primeiro"
    b2.complete.assert_not_called()


def test_falls_through_to_second_on_limit_error():
    b1 = _limit_backend()
    b2 = _ok_backend("fallback")
    fb = FallbackBackend([b1, b2])
    result = fb.complete(prompt="teste")
    assert result["text"] == "fallback"


def test_falls_through_to_third_when_both_limited():
    b1 = _limit_backend()
    b2 = _limit_backend()
    b3 = _ok_backend("terceiro")
    fb = FallbackBackend([b1, b2, b3])
    result = fb.complete(prompt="teste")
    assert result["text"] == "terceiro"


def test_raises_limit_error_when_all_exhausted():
    b1 = _limit_backend()
    b2 = _limit_backend()
    fb = FallbackBackend([b1, b2])
    with pytest.raises(BackendLimitError):
        fb.complete(prompt="teste")


def test_non_limit_error_propagates_immediately():
    b1 = MagicMock()
    b1.complete.side_effect = RuntimeError("timeout real")
    b2 = _ok_backend("nunca alcançado")
    fb = FallbackBackend([b1, b2])
    with pytest.raises(RuntimeError, match="timeout real"):
        fb.complete(prompt="teste")
    b2.complete.assert_not_called()


def test_raises_value_error_on_empty_backends():
    with pytest.raises(ValueError):
        FallbackBackend([])


def test_is_available_true_if_any_available():
    b1 = MagicMock()
    b1.is_available.return_value = False
    b2 = MagicMock()
    b2.is_available.return_value = True
    fb = FallbackBackend([b1, b2])
    assert fb.is_available() is True


def test_is_available_false_if_none_available():
    b1 = MagicMock()
    b1.is_available.return_value = False
    fb = FallbackBackend([b1])
    assert fb.is_available() is False
