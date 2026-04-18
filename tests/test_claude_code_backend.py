import pytest
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from unittest.mock import patch, MagicMock
from core.claude_code_backend import ClaudeCodeBackend, ClaudeCodeError, BackendLimitError


def _make_cli_response(text: str = "resposta mock", input_tokens: int = 10,
                        output_tokens: int = 20) -> str:
    return json.dumps({
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "result": text,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        },
        "total_cost_usd": 0.001,
    })


@patch("subprocess.run")
def test_complete_returns_text(mock_run):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=_make_cli_response("Olá mundo"),
        stderr=""
    )
    backend = ClaudeCodeBackend()
    result = backend.complete(prompt="oi", model="haiku")
    assert result["text"] == "Olá mundo"
    assert result["input_tokens"] == 10
    assert result["output_tokens"] == 20


@patch("subprocess.run")
def test_complete_with_system_prompt(mock_run):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=_make_cli_response("resultado"),
        stderr=""
    )
    backend = ClaudeCodeBackend()
    backend.complete(prompt="tarefa", system="Você é um expert.", model="sonnet")
    call_args = mock_run.call_args
    cmd = call_args[0][0]
    assert "--system-prompt" in cmd
    assert "Você é um expert." in cmd


@patch("subprocess.run")
def test_complete_with_model_alias(mock_run):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=_make_cli_response(),
        stderr=""
    )
    backend = ClaudeCodeBackend()
    backend.complete(prompt="teste", model="opus")
    cmd = mock_run.call_args[0][0]
    assert "--model" in cmd
    idx = cmd.index("--model")
    assert cmd[idx + 1] == "opus"


@patch("subprocess.run")
def test_complete_raises_on_cli_error(mock_run):
    mock_run.return_value = MagicMock(
        returncode=1,
        stdout="",
        stderr="command not found: claude"
    )
    backend = ClaudeCodeBackend()
    with pytest.raises(ClaudeCodeError) as exc_info:
        backend.complete(prompt="teste")
    assert "claude" in str(exc_info.value).lower()


@patch("subprocess.run")
def test_complete_raises_on_is_error_true(mock_run):
    error_response = json.dumps({
        "type": "result",
        "subtype": "error",
        "is_error": True,
        "result": "Something went wrong",
        "usage": {"input_tokens": 0, "output_tokens": 0},
    })
    mock_run.return_value = MagicMock(returncode=0, stdout=error_response, stderr="")
    backend = ClaudeCodeBackend()
    with pytest.raises(ClaudeCodeError):
        backend.complete(prompt="teste")


def test_is_available_returns_bool():
    backend = ClaudeCodeBackend()
    result = backend.is_available()
    assert isinstance(result, bool)


@patch("subprocess.run")
def test_prompt_sent_via_stdin(mock_run):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=_make_cli_response("ok"),
        stderr=""
    )
    backend = ClaudeCodeBackend()
    backend.complete(prompt="meu prompt especial", model="haiku")
    call_kwargs = mock_run.call_args[1]
    assert call_kwargs.get("input") == "meu prompt especial"


@patch("subprocess.run")
def test_raises_backend_limit_error_on_hit_your_limit(mock_run):
    limit_response = json.dumps({
        "type": "result",
        "subtype": "error",
        "is_error": True,
        "result": "You've hit your limit · resets 12pm",
        "usage": {"input_tokens": 0, "output_tokens": 0},
    })
    mock_run.return_value = MagicMock(returncode=0, stdout=limit_response, stderr="")
    backend = ClaudeCodeBackend()
    with pytest.raises(BackendLimitError):
        backend.complete(prompt="teste")


@patch("subprocess.run")
def test_raises_claude_code_error_on_other_is_error(mock_run):
    error_response = json.dumps({
        "type": "result",
        "subtype": "error",
        "is_error": True,
        "result": "Some other error occurred",
        "usage": {"input_tokens": 0, "output_tokens": 0},
    })
    mock_run.return_value = MagicMock(returncode=0, stdout=error_response, stderr="")
    backend = ClaudeCodeBackend()
    with pytest.raises(ClaudeCodeError) as exc_info:
        backend.complete(prompt="teste")
    assert not isinstance(exc_info.value, BackendLimitError)
