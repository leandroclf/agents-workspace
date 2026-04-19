"""Agente de relatório de leads com inteligência de dados."""
from core.agents.base_agent import BaseAgent

DEMO_MODE_WARNING = (
    "[DEMO] Usando leads de exemplo — NÃO use em produção. "
    "Para leads reais, chame run_production(leads) ou CLI: "
    "lead-report '[{\"empresa\":\"X\",\"pais\":\"BR\"}]'"
)

DEMO_LEADS = [
    {"empresa": "Clínica São Paulo", "pais": "BR", "setor": "saúde", "contato": "Diretor"},
    {"empresa": "Agro Export LTDA", "pais": "BR", "setor": "agronegócio", "contato": "CEO"},
    {"empresa": "TechCo Solutions", "pais": "US", "setor": "tecnologia", "contato": "CTO"},
]


class LeadReportAgent(BaseAgent):
    name = "lead-report"
    description = "Gera relatório executivo de leads com scores de risco e valor"
    task_type = "analysis"
    role_description = "Você é um analista de inteligência comercial B2B da LF Soluções."

    def generate_report(self, leads: list) -> str:
        """
        leads: [{"empresa": "XYZ", "pais": "BR", "setor": "saude", "contato": "CEO"}]
        """
        leads_text = "\n".join([
            f"- {l['empresa']} ({l.get('pais', 'BR')}) — {l.get('setor', 'não informado')} — {l.get('contato', '')}"
            for l in leads
        ])

        prompt = f"""Você é um analista de inteligência comercial B2B da LF Soluções.
Analise esta lista de leads e gere um relatório executivo com:

1. **Ranking de prioridade** (quais contatar primeiro e por quê)
2. **Perfil de risco por país** (usando conhecimento sobre mercados B2B)
3. **Oportunidade por setor** (potencial de automação)
4. **Recomendação de abordagem** (como personalizar o pitch para cada perfil)
5. **Próximas ações** (top 3 ações imediatas)

Leads:
{leads_text}

Formato: relatório executivo em markdown, linguagem direta, máximo 500 palavras."""

        result = self._call_api(task=prompt)
        return result.get("text", "")

    def run(self, args: list[str] = None, task: str = "", **kwargs) -> dict:
        """Demo mode — uses hardcoded sample leads for convenience.

        For production use, call run_production(leads) directly or pass a JSON
        string as the first element of args.

        Args:
            args: [] or ["demo"] → demo mode; [json_string] → real leads.

        Returns:
            Report as a plain string.
        """
        if args is None:
            args = []
        if not args or args == ["demo"]:
            import sys
            print(DEMO_MODE_WARNING, file=sys.stderr)
            text = self.generate_report(DEMO_LEADS)
        else:
            # Try to parse JSON leads from first arg
            try:
                import json
                leads = json.loads(args[0])
                if not isinstance(leads, list):
                    raise ValueError("leads must be a list")
                text = self.generate_report(leads)
            except (json.JSONDecodeError, ValueError) as e:
                text = f"Erro ao parsear leads: {e}\nUso: lead-report '[{{\"empresa\":\"X\",\"pais\":\"BR\"}}]'"
        return {"text": text, "agent": self.name, "model": self.model,
                "input_tokens": 0, "output_tokens": 0}

    def run_production(self, leads: list[dict]) -> str:
        """Production entry point — pass real lead dicts directly.

        This is the preferred method for programmatic/production use.
        Bypasses demo mode entirely and never prints warnings.

        Args:
            leads: List of lead dicts, e.g.
                   [{"empresa": "X", "pais": "BR", "setor": "tech", "contato": "CEO"}]

        Returns:
            Report as a plain string.
        """
        if not isinstance(leads, list):
            raise TypeError("leads must be a list of dicts")
        return self.generate_report(leads)
