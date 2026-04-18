from core.agents.base_agent import BaseAgent
from typing import Any


class CoderAgent(BaseAgent):
    name = "CoderAgent"
    model = "claude-opus-4-7"
    task_type = "code"
    role_description = """Você é um especialista em desenvolvimento de software.
Suas responsabilidades:
- Escrever código limpo, testável e bem documentado
- Refatorar código existente para melhor legibilidade e performance
- Identificar e corrigir bugs
- Seguir os princípios SOLID, DRY e YAGNI
- Adicionar testes unitários relevantes

Sempre forneça código funcional com blocos de código bem marcados."""

    def run(self, task: str, code_context: str = "", language: str = "python",
            **kwargs) -> dict[str, Any]:
        extra = f"Linguagem: {language}"
        if code_context:
            extra += f"\n\nCódigo atual:\n```{language}\n{code_context}\n```"
        return self._call_api(task=task, extra_context=extra)
