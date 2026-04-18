import os
from enum import Enum
from typing import Optional
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

CODE_KEYWORDS = ["refator", "implement", "debug", "fix", "código", "função", "classe",
                 "teste", ".py", ".ts", ".js", "error", "bug", "compile"]
ANALYSIS_KEYWORDS = ["analis", "avali", "compar", "expliq", "por que", "performance",
                     "arquitetura", "design", "revi"]


def _build_anthropic_client(api_key: Optional[str] = None,
                             oauth_token: Optional[str] = None) -> anthropic.Anthropic:
    """
    Cria o cliente Anthropic priorizando OAuth (assinatura claude.ai) sobre API key.
    OAuth usa Authorization: Bearer {token} — não gera cobrança por API key.
    """
    if oauth_token:
        return anthropic.Anthropic(auth_token=oauth_token)
    env_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not env_key or env_key == "sk-ant-...":
        raise ValueError(
            "Nenhuma credencial configurada.\n"
            "Opções:\n"
            "  1. OAuth (assinatura): python3 authenticate.py\n"
            "  2. API key: defina ANTHROPIC_API_KEY no .env"
        )
    return anthropic.Anthropic(api_key=env_key)


class ClaudeClient:
    def __init__(self, api_key: Optional[str] = None,
                 oauth_token: Optional[str] = None,
                 memory: Optional[MemorySystem] = None,
                 oauth_manager=None):
        # Tenta OAuth armazenado automaticamente se oauth_manager fornecido
        if oauth_manager and not oauth_token:
            oauth_token = oauth_manager.get_valid_token()
        self.client = _build_anthropic_client(api_key=api_key, oauth_token=oauth_token)
        self._oauth_token = oauth_token
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

    def chat(self, prompt: str, system: str = "", task_type: Optional[TaskType] = None,
             max_tokens: int = 4096) -> dict:
        if task_type is None:
            task_type = self.detect_task_type(prompt)
        model = self.select_model(task_type)

        recent = self.memory.get_recent_interactions(limit=5)
        context_note = ""
        if recent:
            context_note = "\n\n[Contexto recente disponível no histórico]"

        messages = [{"role": "user", "content": prompt}]
        kwargs = dict(model=model, max_tokens=max_tokens, messages=messages)
        if system:
            kwargs["system"] = [{"type": "text", "text": system + context_note,
                                  "cache_control": {"type": "ephemeral"}}]

        response = self.client.messages.create(**kwargs)
        text = response.content[0].text if response.content else ""

        self.memory.save_interaction(
            user_message=prompt,
            assistant_response=text,
            task_type=task_type.value,
            model_used=model,
            tokens_used=response.usage.input_tokens + response.usage.output_tokens
        )

        return {
            "text": text,
            "model": model,
            "task_type": task_type.value,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
