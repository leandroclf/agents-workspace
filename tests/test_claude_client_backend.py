import pytest
import os
import sys
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from unittest.mock import patch, MagicMock
from core.claude_client import ClaudeClient, TaskType, make_client
from core.claude_code_backend import ClaudeCodeBackend
from core.memory_system import MemorySystem


def _mock_backend(text="mock response"):
    backend = MagicMock()
    backend.complete.return_value = {
        "text": text,
        "model": "sonnet",
        "input_tokens": 10,
        "output_tokens": 20,
        "cost_usd": 0.001,
    }
    return backend


def test_client_accepts_explicit_backend(tmp_path):
    memory = MemorySystem(db_path=str(tmp_path / "m.db"))
    backend = _mock_backend("resposta via CLI")
    client = ClaudeClient(backend=backend, memory=memory)
    result = client.chat("oi")
    assert result["text"] == "resposta via CLI"
    backend.complete.assert_called_once()


def test_client_passes_system_prompt_to_backend(tmp_path):
    memory = MemorySystem(db_path=str(tmp_path / "m.db"))
    backend = _mock_backend()
    client = ClaudeClient(backend=backend, memory=memory)
    client.chat("refatore main.py", system="Você é expert em Python.")
    call_kwargs = backend.complete.call_args[1]
    assert "Python" in call_kwargs.get("system", "")


def test_client_routes_model_by_task_type(tmp_path):
    memory = MemorySystem(db_path=str(tmp_path / "m.db"))
    backend = _mock_backend()
    client = ClaudeClient(backend=backend, memory=memory)
    client.chat("refatore o arquivo.py", task_type=TaskType.CODE)
    call_kwargs = backend.complete.call_args[1]
    # CODE → opus
    assert call_kwargs["model"] in ("claude-opus-4-7", "opus")


def test_make_client_uses_claude_code_when_env_set(tmp_path, monkeypatch):
    monkeypatch.setenv("BACKEND", "claude-code")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    memory = MemorySystem(db_path=str(tmp_path / "m.db"))
    with patch("core.claude_code_backend.ClaudeCodeBackend.is_available", return_value=True), \
         patch("core.codex_backend.CodexBackend.is_available", return_value=False):
        client = make_client(memory=memory)
    # Com codex indisponível, retorna ClaudeCodeBackend direto
    assert isinstance(client._backend, ClaudeCodeBackend)


def test_make_client_builds_fallback_chain_when_both_available(tmp_path, monkeypatch):
    monkeypatch.setenv("BACKEND", "claude-code")
    monkeypatch.setenv("FALLBACK_CHAIN_ENABLED", "true")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    memory = MemorySystem(db_path=str(tmp_path / "m.db"))
    with patch("core.claude_code_backend.ClaudeCodeBackend.is_available", return_value=True), \
         patch("core.codex_backend.CodexBackend.is_available", return_value=True):
        client = make_client(memory=memory)
    from core.fallback_backend import FallbackBackend
    assert isinstance(client._backend, FallbackBackend)


def test_make_client_falls_back_to_api_key(tmp_path, monkeypatch):
    monkeypatch.setenv("BACKEND", "api")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    memory = MemorySystem(db_path=str(tmp_path / "m.db"))
    with patch("anthropic.Anthropic"):
        client = make_client(memory=memory)
    assert not isinstance(client._backend, ClaudeCodeBackend)


def test_chat_saves_interaction_to_memory(tmp_path):
    memory = MemorySystem(db_path=str(tmp_path / "m.db"))
    backend = _mock_backend("resposta salva")
    client = ClaudeClient(backend=backend, memory=memory)
    client.chat("minha pergunta")
    interactions = memory.get_recent_interactions(limit=1)
    assert len(interactions) == 1
    assert "minha pergunta" in interactions[0]["user_message"]


@patch("subprocess.run")
def test_fallback_chain_routes_code_task_to_claude_opus(mock_run, tmp_path):
    from core.fallback_backend import FallbackBackend

    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=json.dumps({
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "result": "ok",
            "usage": {"input_tokens": 1, "output_tokens": 1},
            "total_cost_usd": 0.0,
        }),
        stderr="",
    )
    memory = MemorySystem(db_path=str(tmp_path / "m.db"))
    client = ClaudeClient(backend=FallbackBackend([ClaudeCodeBackend()]), memory=memory)
    client.chat("implemente um modulo", task_type=TaskType.CODE)

    cmd = mock_run.call_args[0][0]
    assert cmd[cmd.index("--model") + 1] == "opus"
