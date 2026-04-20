import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest
from unittest.mock import patch, MagicMock
from core.codex_backend import CodexBackend, CodexLimitError, _parse_codex_jsonl
from core.claude_code_backend import BackendLimitError


def _make_jsonl(text: str = "resposta codex",
                input_tokens: int = 10, output_tokens: int = 20,
                used_percent: float = 0.0, balance: str = "100") -> str:
    response_item = json.dumps({
        "type": "response_item",
        "payload": {
            "content": [{"type": "output_text", "text": text}]
        }
    })
    token_count = json.dumps({
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {
                "last_token_usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                }
            },
            "rate_limits": {
                "primary": {"used_percent": used_percent, "resets_at": 9999999},
                "credits": {"balance": balance},
            }
        }
    })
    return response_item + "\n" + token_count + "\n"


@patch("subprocess.run")
def test_complete_returns_text(mock_run):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=_make_jsonl("olá do codex"),
        stderr=""
    )
    backend = CodexBackend()
    result = backend.complete(prompt="oi", model="chat")
    assert result["text"] == "olá do codex"
    assert result["input_tokens"] == 10
    assert result["output_tokens"] == 20


@patch("subprocess.run")
def test_correct_model_selected_by_task_key(mock_run, monkeypatch):
    monkeypatch.delenv("CODEX_MODEL", raising=False)
    mock_run.return_value = MagicMock(
        returncode=0, stdout=_make_jsonl(), stderr=""
    )
    backend = CodexBackend()
    result = backend.complete(prompt="escreva código", model="code")
    # Without CODEX_MODEL override, uses account default (no -m flag)
    assert result["model"] == "codex-default"
    cmd = mock_run.call_args[0][0]
    assert "-m" not in cmd


@patch("subprocess.run")
def test_system_prompt_passed_as_config_flag(mock_run):
    mock_run.return_value = MagicMock(
        returncode=0, stdout=_make_jsonl(), stderr=""
    )
    backend = CodexBackend()
    backend.complete(prompt="tarefa", system="Você é expert.", model="chat")
    cmd = mock_run.call_args[0][0]
    system_configs = [cmd[i + 1] for i, v in enumerate(cmd) if v == "-c"]
    assert any("system.prompt" in c for c in system_configs)


@patch("subprocess.run")
def test_codex_model_override_is_used_when_set(mock_run, monkeypatch):
    monkeypatch.setenv("CODEX_MODEL", "gpt-5.4-mini")
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=_make_jsonl(),
        stderr=""
    )
    backend = CodexBackend()
    result = backend.complete(prompt="tarefa", model="code")
    cmd = mock_run.call_args[0][0]
    assert "-m" in cmd
    idx = cmd.index("-m")
    assert cmd[idx + 1] == "gpt-5.4-mini"
    assert result["model"] == "gpt-5.4-mini"


@patch("subprocess.run")
def test_complete_raises_codex_limit_on_high_usage(mock_run):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=_make_jsonl(used_percent=100.0),
        stderr=""
    )
    backend = CodexBackend()
    with pytest.raises(CodexLimitError):
        backend.complete(prompt="teste")


@patch("subprocess.run")
def test_complete_raises_codex_limit_on_zero_credits(mock_run):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=_make_jsonl(used_percent=0.0, balance="0"),
        stderr=""
    )
    backend = CodexBackend()
    with pytest.raises(CodexLimitError):
        backend.complete(prompt="teste")


def test_codex_limit_error_is_backend_limit_error():
    err = CodexLimitError("teste", resets_at=12345.0)
    assert isinstance(err, BackendLimitError)
    assert err.resets_at == 12345.0


def test_is_available_returns_bool():
    backend = CodexBackend()
    assert isinstance(backend.is_available(), bool)
