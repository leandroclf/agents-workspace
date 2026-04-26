#!/usr/bin/env python3
"""
Script rápido para analisar código com os agentes de análise.

Uso:
    python3 analyze_code.py --file path/to/file.py --type code
    python3 analyze_code.py --code "def f(x): return x+1" --type security
    python3 analyze_code.py --url https://github.com/user/repo --type architecture
"""

import click
import sys
from pathlib import Path
from core.agents.code_analysis_agent import (
    CodeAnalysisAgent,
    SecurityAnalysisAgent,
    ArchitectureAnalysisAgent,
)
from core.memory_system import MemorySystem


AGENT_MAP = {
    "code": CodeAnalysisAgent,
    "security": SecurityAnalysisAgent,
    "architecture": ArchitectureAnalysisAgent,
}


@click.command()
@click.option(
    "--file",
    type=click.Path(exists=True),
    help="Caminho para arquivo .py, .ts, .js, .go, etc",
)
@click.option(
    "--code",
    help="Código inline (Python, JS, etc)",
)
@click.option(
    "--type",
    type=click.Choice(["code", "security", "architecture"], case_sensitive=False),
    default="code",
    help="Tipo de análise",
)
@click.option(
    "--task",
    default="Faça uma análise profunda deste código",
    help="Descrição da tarefa personalizada",
)
def main(file: str, code: str, type: str, task: str):
    """Analisa código com agentes especializados."""

    # 1. Carregar código
    if file:
        code_text = Path(file).read_text()
        print(f"📄 Analisando: {file}\n")
    elif code:
        code_text = code
        print(f"💻 Analisando código inline...\n")
    else:
        click.echo("❌ Forneça --file ou --code", err=True)
        sys.exit(1)

    # 2. Selecionar agente
    agent_class = AGENT_MAP.get(type.lower(), CodeAnalysisAgent)
    memory = MemorySystem()
    agent = agent_class(memory=memory)

    # 3. Executar análise
    click.echo(f"🔍 Executando {agent.name}...\n")
    click.echo("=" * 70)

    try:
        result = agent.run(task=task, code=code_text)

        # 4. Exibir resultado
        click.echo(result["text"])
        click.echo("=" * 70)
        click.echo(
            f"\n📊 Modelo: {result['model']} | Tokens: "
            f"{result['input_tokens']}+{result['output_tokens']}"
        )

        # 5. Salvar na memória
        memory.save_interaction(
            user_message=task,
            assistant_response=result["text"],
            task_type=type,
            model_used=result["model"],
            tokens_used=result["input_tokens"] + result["output_tokens"],
        )
        click.echo("✓ Análise salva no histórico")

    except Exception as e:
        click.echo(f"❌ Erro: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
