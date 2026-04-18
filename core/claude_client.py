import os
from enum import Enum
from typing import Optional, Any
import anthropic
from core.adaptive_thinking import AdaptiveThinkingManager
from core.memory_system import MemorySystem


class TaskType(Enum):
    CODE = "code"
    ANALYSIS = "analysis"
    ARCHITECTURE = "architecture"
    ORCHESTRATION = "orchestration"
    VALIDATION = "validation"
    SUMMARY = "summary"
    CHAT = "chat"


MODEL_ROUTING = {
    TaskType.CODE:          "claude-opus-4-7",
    TaskType.ANALYSIS:      "claude-opus-4-7",
    TaskType.ARCHITECTURE:  "claude-opus-4-7",
    TaskType.ORCHESTRATION: "claude-opus-4-7",
    TaskType.VALIDATION:    "claude-sonnet-4-6",
    TaskType.SUMMARY:       "claude-sonnet-4-6",
    TaskType.CHAT:          "claude-haiku-4-5",
}

_CLI_ALIAS = {
    "claude-opus-4-7":   "opus",
    "claude-sonnet-4-6": "sonnet",
    "claude-haiku-4-5":  "haiku",
}

CODE_KEYWORDS = ["refator", "implement", "debug", "fix", "código", "função", "classe",
                 "teste", ".py", ".ts", ".js", "error", "bug", "compile"]
ANALYSIS_KEYWORDS = ["analis", "avali", "compar", "expliq", "por que", "performance",
                     "arquitetura", "design", "revi"]


class _AnthropicAPIBackend:
    """Backend direto via SDK Anthropic (exige API key paga)."""

    def __init__(self, api_key: Optional[str] = None, auth_token: Optional[str] = None):
        if auth_token:
            self._client = anthropic.Anthropic(auth_token=auth_token)
        else:
            key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
            self._client = anthropic.Anthropic(api_key=key)

    def complete(self, prompt: str, system: str = "",
                 model: str = "claude-sonnet-4-6", max_tokens: int = 4096) -> dict:
        kwargs: dict[str, Any] = dict(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        if system:
            kwargs["system"] = [{"type": "text", "text": system,
                                  "cache_control": {"type": "ephemeral"}}]
        response = self._client.messages.create(**kwargs)
        text = response.content[0].text if response.content else ""
        return {
            "text": text,
            "model": model,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "cost_usd": 0.0,
        }


class ClaudeClient:
    """
    Cliente principal. Aceita qualquer backend com interface .complete().
    Use make_client() para criação automática com detecção de backend.
    """

    def __init__(self, backend=None, memory: Optional[MemorySystem] = None,
                 api_key: Optional[str] = None,
                 oauth_token: Optional[str] = None,
                 oauth_manager=None):
        if backend is not None:
            self._backend = backend
        else:
            if oauth_manager and not oauth_token:
                oauth_token = oauth_manager.get_valid_token()
            self._backend = _AnthropicAPIBackend(api_key=api_key, auth_token=oauth_token)

        self.thinking_mgr = AdaptiveThinkingManager()
        self.memory = memory or MemorySystem()

    def detect_task_type(self, prompt: str) -> TaskType:
        lower = prompt.lower()
        if any(k in lower for k in CODE_KEYWORDS):
            return TaskType.CODE
        if any(k in lower for k in ANALYSIS_KEYWORDS):
            return TaskType.ANALYSIS
        return TaskType.CHAT

    def select_model(self, task_type: TaskType) -> str:
        return MODEL_ROUTING.get(task_type, "claude-sonnet-4-6")

    def chat(self, prompt: str, system: str = "",
             task_type: Optional[TaskType] = None,
             max_tokens: int = 4096) -> dict:
        if task_type is None:
            task_type = self.detect_task_type(prompt)
        model_full = self.select_model(task_type)

        from core.claude_code_backend import ClaudeCodeBackend
        if isinstance(self._backend, ClaudeCodeBackend):
            model = _CLI_ALIAS.get(model_full, "sonnet")
        else:
            model = model_full

        recent = self.memory.get_recent_interactions(limit=5)
        sys_prompt = system
        if recent and not sys_prompt:
            sys_prompt = "[Contexto recente disponível no histórico]"

        result = self._backend.complete(
            prompt=prompt,
            system=sys_prompt,
            model=model,
            max_tokens=max_tokens,
        )

        self.memory.save_interaction(
            user_message=prompt,
            assistant_response=result["text"],
            task_type=task_type.value,
            model_used=model_full,
            tokens_used=result["input_tokens"] + result["output_tokens"],
        )

        return {
            "text": result["text"],
            "model": model_full,
            "task_type": task_type.value,
            "input_tokens": result["input_tokens"],
            "output_tokens": result["output_tokens"],
        }


def make_client(memory: Optional[MemorySystem] = None,
                api_key: Optional[str] = None) -> ClaudeClient:
    """
    Factory com detecção automática de backend.

    Priority:
      1. BACKEND=claude-code → ClaudeCodeBackend (uses subscription)
      2. BACKEND=api or API key present → _AnthropicAPIBackend
      3. claude CLI available and no API key → ClaudeCodeBackend (auto)
    """
    from core.claude_code_backend import ClaudeCodeBackend

    mem = memory or MemorySystem()
    backend_env = os.environ.get("BACKEND", "").lower()
    api_key_env = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    has_real_key = bool(api_key_env) and api_key_env != "sk-ant-..."

    if backend_env == "claude-code":
        cli = ClaudeCodeBackend()
        if not cli.is_available():
            raise RuntimeError("BACKEND=claude-code mas `claude` CLI não encontrado no PATH")
        return ClaudeClient(backend=cli, memory=mem)

    if backend_env == "api" or has_real_key:
        return ClaudeClient(backend=_AnthropicAPIBackend(api_key=api_key_env or None), memory=mem)

    # Auto-detect: prefer CLI if available
    cli = ClaudeCodeBackend()
    if cli.is_available():
        return ClaudeClient(backend=cli, memory=mem)

    if has_real_key:
        return ClaudeClient(backend=_AnthropicAPIBackend(api_key=api_key_env), memory=mem)

    raise RuntimeError(
        "Nenhum backend configurado.\n"
        "Opção 1 (assinatura): defina BACKEND=claude-code no .env\n"
        "Opção 2 (API key):    defina ANTHROPIC_API_KEY no .env"
    )
