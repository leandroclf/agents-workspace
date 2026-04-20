"""
Testes de integração que validam o fluxo completo sem chamar a API real.
Usam mocks para substituir chamadas externas.
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from unittest.mock import patch, MagicMock


def make_mock_response(text: str = "resultado mock", input_tokens: int = 100,
                       output_tokens: int = 200):
    resp = MagicMock()
    resp.content = [MagicMock(text=text)]
    resp.usage = MagicMock(input_tokens=input_tokens, output_tokens=output_tokens)
    return resp


@patch("anthropic.Anthropic")
def test_full_chat_flow(mock_anthropic_cls, tmp_path):
    """Fluxo completo: usuário → detecção → modelo → memória → resposta."""
    from core.claude_client import ClaudeClient
    from core.memory_system import MemorySystem

    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = make_mock_response("def hello(): pass")

    memory = MemorySystem(db_path=str(tmp_path / "test.db"))
    client = ClaudeClient(api_key="test", memory=memory)

    result = client.chat("Escreva uma função Python hello world")
    assert result["text"] == "def hello(): pass"
    assert result["model"] == "claude-opus-4-7"
    assert result["task_type"] == "code"

    interactions = memory.get_recent_interactions(limit=1)
    assert len(interactions) == 1
    assert interactions[0]["task_type"] == "code"


@patch("anthropic.Anthropic")
def test_skill_injection_flow(mock_anthropic_cls, tmp_path, monkeypatch):
    """Skills relevantes devem ser injetadas no system prompt."""
    # Force API backend so anthropic.Anthropic mock is actually used
    monkeypatch.setenv("BACKEND", "api")
    from core.agents.coder_agent import CoderAgent
    from core.memory_system import MemorySystem
    from core.skill_manager import SkillManager, Skill

    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = make_mock_response("código refatorado")

    memory = MemorySystem(db_path=str(tmp_path / "mem.db"))
    skills = SkillManager(db_path=str(tmp_path / "sk.db"))
    skills.save_skill(Skill("py_refactor", "Refatora Python", "Refatore: {code}", tags=["python"]))

    agent = CoderAgent(memory=memory, skill_manager=skills, api_key="test")
    result = agent.run(task="refactor this python code", language="python")

    call_kwargs = mock_client.messages.create.call_args[1]
    system_text = call_kwargs["system"][0]["text"]
    assert "py_refactor" in system_text
    assert result["text"] == "código refatorado"


@patch("anthropic.Anthropic")
def test_error_handler_retry_flow(mock_anthropic_cls, tmp_path):
    """Deve retentar em RateLimitError e ter sucesso na 2ª tentativa."""
    import anthropic
    from core.error_handler import RobustErrorHandler
    from core.claude_client import ClaudeClient
    from core.memory_system import MemorySystem

    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_response = make_mock_response("resposta após retry")

    call_count = [0]
    def side_effect(**kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise anthropic.RateLimitError(
                message="rate", response=MagicMock(status_code=429), body={}
            )
        return mock_response
    mock_client.messages.create.side_effect = side_effect

    memory = MemorySystem(db_path=str(tmp_path / "m.db"))
    cc = ClaudeClient(api_key="test", memory=memory)
    handler = RobustErrorHandler(max_retries=2, base_delay=0.001)

    result = handler.execute_with_retry(lambda: cc.chat("olá"))
    assert result["text"] == "resposta após retry"
    assert call_count[0] == 2
