#!/usr/bin/env python3
import os
import sys
from dotenv import load_dotenv
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

console = Console()


def _make_client(memory=None):
    """Cria ClaudeClient com auto-detecção de backend (CLI ou API key)."""
    from core.claude_client import make_client
    return make_client(memory=memory)


@click.group()
def cli():
    """Workspace Inteligente com Claude 2026"""


@cli.command()
@click.argument("prompt")
@click.option("--task-type", "-t", default=None,
              type=click.Choice(["code", "analysis", "chat", "validation"]),
              help="Tipo de tarefa")
def chat(prompt: str, task_type: str):
    """Enviar mensagem para Claude com roteamento automático de modelo."""
    from core.claude_client import ClaudeClient, TaskType
    from core.memory_system import MemorySystem

    memory = MemorySystem()
    client = _make_client(memory=memory)
    tt = TaskType[task_type.upper()] if task_type else None

    with console.status("[bold green]Processando..."):
        result = client.chat(prompt=prompt, task_type=tt)

    console.print(Panel(result["text"], title=f"[cyan]{result['model']}[/cyan]",
                         subtitle=f"task:{result['task_type']} | "
                                  f"in:{result['input_tokens']} out:{result['output_tokens']} tokens"))


@cli.command()
@click.argument("task")
@click.option("--parallel/--sequential", default=True, help="Execução paralela")
def orchestrate(task: str, parallel: bool):
    """Orquestrar tarefa complexa com múltiplos agentes."""
    from core.agents.orchestrator_agent import OrchestratorAgent

    agent = OrchestratorAgent()
    with console.status("[bold blue]Orquestrando agentes..."):
        result = agent.run(task=task, parallel=parallel)

    console.print(Panel(result["consolidated_result"],
                         title=f"[magenta]Resultado — {result['subtasks_count']} subtarefas[/magenta]",
                         subtitle=f"tokens total: {result['total_tokens']}"))


@cli.command()
@click.option("--limit", "-n", default=10, help="Número de interações")
def history(limit: int):
    """Mostrar histórico de interações."""
    from core.memory_system import MemorySystem

    memory = MemorySystem()
    interactions = memory.get_recent_interactions(limit=limit)
    table = Table(title="Histórico de Interações")
    table.add_column("ID", style="dim")
    table.add_column("Tipo")
    table.add_column("Modelo")
    table.add_column("Tokens")
    table.add_column("Mensagem", max_width=60)

    for i in interactions:
        table.add_row(
            str(i["id"]),
            i["task_type"],
            i["model_used"],
            str(i["tokens_used"]),
            i["user_message"][:60],
        )
    console.print(table)


@cli.command()
@click.argument("task")
@click.option("--country", "-c", default="", help="Código de país ISO-2 (ex: BR)")
@click.option("--price", "-p", default=0.0, type=float, help="Preço base em USD")
@click.option("--countries", default="", help="Lista de países separados por vírgula para batch")
def risk(task: str, country: str, price: float, countries: str):
    """Análise de risco-país e precificação (World Bank)."""
    from core.agents.worldbank_agent import WorldBankRiskAgent
    agent = WorldBankRiskAgent()
    kwargs = {}
    if country:
        kwargs["country_code"] = country
    if price:
        kwargs["base_price"] = price
    if countries:
        kwargs["countries"] = [c.strip().upper() for c in countries.split(",") if c.strip()]
    with console.status("[bold blue]Consultando World Bank Risk..."):
        result = agent.run(task=task, **kwargs)
    console.print(Panel(result["text"], title="[cyan]WorldBank Risk Agent[/cyan]"))


@cli.command()
@click.argument("task")
@click.option("--entity", "-e", default="", help="Nome da entidade para match")
@click.option("--threshold", default=0.7, type=float, help="Confiança mínima (0-1)")
def entity(task: str, entity: str, threshold: float):
    """Resolução de entidades e enriquecimento Wikidata."""
    from core.agents.wikidata_agent import WikidataEntityAgent
    agent = WikidataEntityAgent()
    kwargs = {"confidence_threshold": threshold}
    if entity:
        kwargs["entity_name"] = entity
    with console.status("[bold blue]Consultando Wikidata..."):
        result = agent.run(task=task, **kwargs)
    console.print(Panel(result["text"], title="[cyan]Wikidata Entity Agent[/cyan]"))


@cli.command()
@click.argument("task")
@click.option("--account", "-a", default="", help="ID da conta")
@click.option("--score", "-s", default=0.0, type=float, help="Score de valor (0-100)")
def enrich(task: str, account: str, score: float):
    """Enriquecimento de leads com OpenAlex."""
    from core.agents.openalex_agent import OpenAlexEnrichmentAgent
    agent = OpenAlexEnrichmentAgent()
    kwargs = {}
    if account:
        kwargs["account_id"] = account
    if score:
        kwargs["score"] = score
    with console.status("[bold blue]Consultando OpenAlex..."):
        result = agent.run(task=task, **kwargs)
    console.print(Panel(result["text"], title="[cyan]OpenAlex Enrichment Agent[/cyan]"))


@cli.command()
@click.argument("cliente")
@click.argument("segmento")
@click.argument("objetivo")
@click.option("--orcamento", "-o", default="a definir", help="Orçamento indicado pelo cliente")
def proposal(cliente: str, segmento: str, objetivo: str, orcamento: str):
    """Gerar proposta comercial personalizada para um prospect B2B."""
    from core.agents.proposal_agent import ProposalAgent
    agent = ProposalAgent()
    with console.status("[bold green]Gerando proposta comercial..."):
        result = agent.run(args=[cliente, segmento, objetivo, orcamento])
    console.print(Panel(result["text"], title="[cyan]Proposal Agent — LF Soluções[/cyan]"))


@cli.command(name="lead-report")
@click.argument("mode", default="")
def lead_report(mode: str):
    """Gerar relatório executivo de leads com inteligência de dados.

    MODE pode ser:
      (vazio)   — demo com leads de exemplo
      demo      — demo com leads de exemplo
      '[{...}]' — JSON com leads reais (produção)
    """
    from core.agents.lead_report_agent import LeadReportAgent
    agent = LeadReportAgent()
    # Build args list: empty → demo; "demo" → demo; JSON string → real leads
    args = [] if not mode or mode == "demo" else [mode]
    with console.status("[bold blue]Gerando relatório de leads..."):
        result = agent.run(args)
    # run() returns a plain str
    console.print(Panel(result, title="[cyan]Lead Report Agent[/cyan]"))


@cli.command()
def stats():
    """Mostrar estatísticas do workspace."""
    from core.memory_system import MemorySystem
    from core.skill_manager import SkillManager

    memory = MemorySystem()
    skill_mgr = SkillManager()
    interactions = memory.get_recent_interactions(limit=10000)
    total_tokens = sum(i.get("tokens_used", 0) for i in interactions)

    table = Table(title="Estatísticas do Workspace")
    table.add_column("Métrica", style="bold")
    table.add_column("Valor", style="green")
    table.add_row("Total de interações", str(len(interactions)))
    table.add_row("Total de tokens", f"{total_tokens:,}")
    table.add_row("Skills aprendidos", str(len(skill_mgr.list_skills())))
    console.print(table)


if __name__ == "__main__":
    cli()
