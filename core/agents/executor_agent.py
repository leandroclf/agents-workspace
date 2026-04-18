from core.agents.base_agent import BaseAgent
from typing import Any


class ExecutorAgent(BaseAgent):
    name = "ExecutorAgent"
    model = "claude-sonnet-4-6"
    task_type = "execution"
    role_description = """Você é um agente de execução focado em ação.
Suas responsabilidades:
- Executar subtarefas definidas com precisão
- Seguir instruções passo a passo
- Reportar status e resultados claramente
- Identificar bloqueios imediatamente
- Manter outputs concisos e estruturados

Seja direto, preciso e orientado a resultados."""

    def run(self, task: str, step_context: str = "", **kwargs) -> dict[str, Any]:
        return self._call_api(task=task, extra_context=step_context)
