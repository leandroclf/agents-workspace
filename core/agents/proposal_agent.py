"""Agente de geração de propostas comerciais."""
import os
from datetime import date
from core.agents.base_agent import BaseAgent

PROPOSAL_TEMPLATE = """
# Proposta Comercial — LF Soluções
**Data:** {date}
**Cliente:** {cliente}
**Segmento:** {segmento}

## Contexto
{contexto}

## Solução Proposta
{solucao}

## Entregáveis
{entregaveis}

## Investimento
{investimento}

## Próximos Passos
{proximos_passos}

---
*LF Soluções — Automação de Processos e Inteligência de Dados*
*Contato: https://wa.me/5561992491132*
"""


class ProposalAgent(BaseAgent):
    name = "proposal"
    description = "Gera propostas comerciais personalizadas para prospects B2B"
    task_type = "orchestration"
    role_description = "Você é um consultor sênior de automação B2B da LF Soluções."

    def generate(self, cliente: str, segmento: str, objetivo: str, orcamento: str = "a definir") -> str:
        prompt = f"""Você é um consultor sênior de automação B2B da LF Soluções.
Gere uma proposta comercial profissional e persuasiva para:
- Cliente: {cliente}
- Segmento: {segmento}
- Objetivo principal: {objetivo}
- Orçamento indicado: {orcamento}

A proposta deve incluir:
1. Contexto do problema (2-3 frases mostrando que entendemos a dor)
2. Solução proposta (específica para o objetivo, usando automação/dados)
3. Entregáveis concretos (lista de 4-6 itens)
4. Investimento (faixas: Essencial / Profissional / Enterprise)
5. Próximos passos (3 passos simples)

Seja direto, mostre valor, use linguagem executiva em português brasileiro."""

        result = self._call_api(task=prompt)
        text = result.get("text", "")

        today = date.today().strftime("%d/%m/%Y")
        doc = PROPOSAL_TEMPLATE.format(
            date=today,
            cliente=cliente,
            segmento=segmento,
            contexto="[ver proposta gerada abaixo]",
            solucao=text,
            entregaveis="[incluído no texto acima]",
            investimento="[incluído no texto acima]",
            proximos_passos="[incluído no texto acima]",
        )

        # Save to file
        filename = f"proposta_{cliente.lower().replace(' ', '_')}_{date.today().isoformat()}.md"
        output_path = os.path.join(os.path.expanduser("~"), "propostas", filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(doc)

        return f"Proposta gerada: {output_path}\n\n{text}"

    def run(self, task: str = "", args: list = None, **kwargs) -> dict:
        # Support CLI args list: [cliente, segmento, objetivo, orcamento?]
        if args is None:
            args = []
        if len(args) < 3:
            return {"text": "Uso: proposal <cliente> <segmento> <objetivo> [orcamento]",
                    "agent": self.name, "model": self.model,
                    "input_tokens": 0, "output_tokens": 0}
        cliente = args[0]
        segmento = args[1]
        objetivo = args[2]
        orcamento = args[3] if len(args) > 3 else "a definir"
        text = self.generate(cliente, segmento, objetivo, orcamento)
        return {"text": text, "agent": self.name, "model": self.model,
                "input_tokens": 0, "output_tokens": 0}
