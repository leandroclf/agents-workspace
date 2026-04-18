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
    """Cria ClaudeClient preferindo OAuth se disponível, fallback para API key."""
    from core.claude_client import ClaudeClient
    from core.memory_system import MemorySystem
    from core.oauth_manager import OAuthManager

    mem = memory or MemorySystem()
    client_id = os.environ.get("ANTHROPIC_CLIENT_ID", "").strip()
    client_secret = os.environ.get("ANTHROPIC_CLIENT_SECRET", "").strip()

    if client_id and client_id != "...":
        oauth = OAuthManager(client_id=client_id, client_secret=client_secret)
        token = oauth.get_valid_token()
        if token:
            return ClaudeClient(oauth_token=token, memory=mem)

    return ClaudeClient(memory=mem)


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
