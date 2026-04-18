from abc import ABC
from typing import Optional, Any
from core.memory_system import MemorySystem
from core.skill_manager import SkillManager
from core.adaptive_thinking import AdaptiveThinkingManager
import anthropic
import os


class BaseAgent(ABC):
    name: str = "BaseAgent"
    role_description: str = "Assistente genérico."
    model: str = "claude-sonnet-4-6"
    task_type: str = "chat"

    def __init__(self, memory: Optional[MemorySystem] = None,
                 skill_manager: Optional[SkillManager] = None,
                 api_key: Optional[str] = None):
        self.memory = memory or MemorySystem()
        self.skill_manager = skill_manager or SkillManager()
        self.thinking_mgr = AdaptiveThinkingManager()
        self.client = anthropic.Anthropic(api_key=api_key or os.environ["ANTHROPIC_API_KEY"])

    def build_system_prompt(self, task: str = "") -> str:
        parts = [f"# {self.name}\n\n{self.role_description}"]
        if self.skill_manager and task:
            injection = self.skill_manager.build_skill_injection_text(query=task, top_k=3)
            if injection:
                parts.append(injection)
        recent = self.memory.get_recent_interactions(limit=3)
        if recent:
            parts.append("## Contexto Recente\n" +
                         "\n".join(f"- {r['task_type']}: {r['user_message'][:80]}" for r in recent))
        return "\n\n".join(parts)

    def run(self, task: str, **kwargs) -> dict[str, Any]:
        return self._call_api(task=task)

    def _call_api(self, task: str, extra_context: str = "",
                  max_tokens: int = 4096) -> dict:
        system = self.build_system_prompt(task=task)
        if extra_context:
            task = f"{task}\n\n**Contexto adicional:**\n{extra_context}"

        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": task}],
        )
        text = response.content[0].text if response.content else ""
        self.memory.save_interaction(
            user_message=task[:500],
            assistant_response=text[:2000],
            task_type=self.task_type,
            model_used=self.model,
            tokens_used=response.usage.input_tokens + response.usage.output_tokens,
        )
        return {
            "text": text,
            "model": self.model,
            "agent": self.name,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
