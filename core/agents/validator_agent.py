from core.agents.base_agent import BaseAgent
from typing import Any


class ValidatorAgent(BaseAgent):
    name = "ValidatorAgent"
    model = "claude-sonnet-4-6"
    task_type = "validation"
    role_description = """Você é um especialista em qualidade de código e revisão técnica.
Suas responsabilidades:
- Revisar código quanto a correctude, segurança e boas práticas
- Identificar edge cases não tratados
- Verificar cobertura de testes
- Validar conformidade com padrões do projeto
- Atribuir um score de qualidade de 0 a 10

Formato de resposta esperado:
QUALITY_SCORE: X/10
ISSUES: [lista de problemas]
SUGGESTIONS: [lista de melhorias]
VERDICT: APPROVED | NEEDS_REVISION"""

    def run(self, task: str, code_to_review: str = "", **kwargs) -> dict[str, Any]:
        extra = f"```\n{code_to_review}\n```" if code_to_review else ""
        result = self._call_api(task=task, extra_context=extra)
        text = result.get("text", "")
        score_line = next((l for l in text.split("\n") if "QUALITY_SCORE" in l), "")
        try:
            score = float(score_line.split(":")[1].split("/")[0].strip())
        except Exception:
            score = 5.0
        result["quality_score"] = score
        result["approved"] = "APPROVED" in text
        return result
