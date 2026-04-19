"""Agente de relatório de leads com inteligência de dados."""
from core.agents.base_agent import BaseAgent


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

    def run(self, task: str = "", **kwargs) -> dict:
        # Demo mode: generate sample report
        sample_leads = [
            {"empresa": "Clínica São Paulo", "pais": "BR", "setor": "saúde", "contato": "Diretor"},
            {"empresa": "Agro Export LTDA", "pais": "BR", "setor": "agronegócio", "contato": "CEO"},
            {"empresa": "TechCo Solutions", "pais": "US", "setor": "tecnologia", "contato": "CTO"},
        ]
        text = self.generate_report(sample_leads)
        return {"text": text, "agent": self.name, "model": self.model,
                "input_tokens": 0, "output_tokens": 0}
