"""Agente de geração de propostas comerciais."""
import os
import re
from datetime import date
from pathlib import Path
from core.agents.base_agent import BaseAgent

PROPOSALS_DIR = Path(os.environ.get("PROPOSALS_DIR", str(Path.home() / "propostas")))

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

    def _safe_filename(self, cliente: str) -> str:
        """Remove path separators and special chars, keep alphanumeric/spaces/hyphens."""
        safe = re.sub(r'[^\w\s\-]', '', cliente, flags=re.UNICODE)
        safe = re.sub(r'\s+', '_', safe.strip())
        return safe[:80] or "cliente"

    def _save_proposal(self, content: str, cliente: str) -> Path:
        PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"proposta_{self._safe_filename(cliente)}_{date.today().isoformat()}.md"
        output_path = (PROPOSALS_DIR / filename).resolve()
        # Security: ensure path is inside PROPOSALS_DIR
        if not str(output_path).startswith(str(PROPOSALS_DIR.resolve())):
            raise ValueError(f"Path traversal detectado: {output_path}")
        output_path.write_text(content, encoding="utf-8")
        return output_path

    def generate(self, cliente: str, segmento: str, objetivo: str, orcamento: str = "a definir") -> dict:
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

        output_path = self._save_proposal(doc, cliente)
        result_text = f"Proposta gerada: {output_path}\n\n{text}"

        return {"text": result_text, "file": str(output_path), "cliente": cliente}

    def run(self, task: str = "", args: list = None, **kwargs) -> dict:
        # Support CLI args list: [cliente, segmento, objetivo, orcamento?]
        # When called from orchestrator with a single description string, parse it.
        if args is None:
            args = []
        if len(args) == 1:
            # Single free-form description — split on spaces as best-effort parsing:
            # e.g. "Empresa XYZ saúde acelerar vendas" → cliente=words[0..1], segmento=words[2], objetivo=rest
            parts = args[0].split()
            if len(parts) >= 3:
                cliente = parts[0]
                segmento = parts[1]
                objetivo = " ".join(parts[2:])
                args = [cliente, segmento, objetivo]
            else:
                # Fall through to the usage error below
                args = args[0].split()
        if len(args) < 3:
            return {"text": "Uso: proposal <cliente> <segmento> <objetivo> [orcamento]",
                    "agent": self.name, "model": self.model,
                    "input_tokens": 0, "output_tokens": 0}
        cliente = args[0]
        segmento = args[1]
        objetivo = args[2]
        orcamento = args[3] if len(args) > 3 else "a definir"
        result = self.generate(cliente, segmento, objetivo, orcamento)
        return {"text": result["text"], "agent": self.name, "model": self.model,
                "input_tokens": 0, "output_tokens": 0}
