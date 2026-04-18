from abc import ABC
from typing import Optional, Any
from core.memory_system import MemorySystem
from core.skill_manager import SkillManager
from core.adaptive_thinking import AdaptiveThinkingManager
from core.claude_client import ClaudeClient, TaskType, make_client


class BaseAgent(ABC):
    name: str = "BaseAgent"
    role_description: str = "Assistente genérico."
    model: str = "claude-sonnet-4-6"
    task_type: str = "chat"

    def __init__(self, memory: Optional[MemorySystem] = None,
                 skill_manager: Optional[SkillManager] = None,
                 api_key: Optional[str] = None,
                 client: Optional[ClaudeClient] = None):
        self.memory = memory or MemorySystem()
        self.skill_manager = skill_manager or SkillManager()
        self.thinking_mgr = AdaptiveThinkingManager()
        if client is not None:
            self._client = client
        else:
            self._client = make_client(memory=self.memory, api_key=api_key)

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
        prompt = task
        if extra_context:
            prompt = f"{task}\n\n**Contexto adicional:**\n{extra_context}"

        task_type_map = {
            "code":          TaskType.CODE,
            "analysis":      TaskType.ANALYSIS,
            "architecture":  TaskType.ARCHITECTURE,
            "orchestration": TaskType.ORCHESTRATION,
            "validation":    TaskType.VALIDATION,
            "summary":       TaskType.SUMMARY,
            "chat":          TaskType.CHAT,
            "execution":     TaskType.CHAT,
        }
        tt = task_type_map.get(self.task_type, TaskType.CHAT)

        result = self._client.chat(
            prompt=prompt,
            system=system,
            task_type=tt,
            max_tokens=max_tokens,
        )
        return {
            "text": result["text"],
            "model": result["model"],
            "agent": self.name,
            "input_tokens": result["input_tokens"],
            "output_tokens": result["output_tokens"],
        }
