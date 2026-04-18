from core.agents.base_agent import BaseAgent
from typing import Any


class AnalysisAgent(BaseAgent):
    name = "AnalysisAgent"
    model = "claude-opus-4-7"
    task_type = "analysis"
    role_description = """Você é um especialista em análise de sistemas e performance.
Suas responsabilidades:
- Analisar código e arquitetura em profundidade
- Identificar gargalos de performance
- Comparar abordagens técnicas com tradeoffs claros
- Fornecer métricas e evidências concretas
- Propor melhorias fundamentadas

Seja analítico, objetivo e apresente conclusões com evidências."""

    def run(self, task: str, subject: str = "", **kwargs) -> dict[str, Any]:
        extra = f"Objeto de análise: {subject}" if subject else ""
        return self._call_api(task=task, extra_context=extra)
