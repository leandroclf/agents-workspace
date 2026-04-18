#!/usr/bin/env python3
"""
Autenticação OAuth com claude.ai (usa assinatura — sem cobrança por API key).

Uso:
    python3 authenticate.py

O que acontece:
  1. Abre o browser em claude.ai/oauth/authorize
  2. Você faz login com sua conta claude.ai (Pro/Max)
  3. Redireciona de volta para localhost:54545/oauth/callback
  4. O código é trocado por access_token + refresh_token
  5. Tokens ficam armazenados em memory/oauth_tokens.db
  6. O workspace passa a usar OAuth automaticamente (sem API key)

Pré-requisito:
  Configure no .env:
    ANTHROPIC_CLIENT_ID=seu_client_id
    ANTHROPIC_CLIENT_SECRET=seu_client_secret  (opcional para PKCE público)

  Para obter o client_id:
    Acesse: https://console.anthropic.com/settings/oauth-apps
    Crie um OAuth App com redirect_uri: http://localhost:54545/oauth/callback
"""

import os
import sys
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

from core.oauth_manager import OAuthManager

console = Console()


def main():
    console.print(Panel(
        "[bold cyan]Workspace Inteligente — Autenticação OAuth[/bold cyan]\n\n"
        "Este processo usa sua assinatura [bold]claude.ai[/bold] (Pro/Max)\n"
        "para autenticar sem cobrar por API key separada.",
        title="OAuth Setup"
    ))

    client_id = os.environ.get("ANTHROPIC_CLIENT_ID", "").strip()
    client_secret = os.environ.get("ANTHROPIC_CLIENT_SECRET", "").strip()

    if not client_id or client_id == "...":
        console.print("\n[red]ANTHROPIC_CLIENT_ID não configurado no .env[/red]")
        console.print("\nPara obter seu client_id:")
        console.print("  1. Acesse [link]https://console.anthropic.com/settings/oauth-apps[/link]")
        console.print("  2. Crie um OAuth App")
        console.print("  3. Use redirect_uri: [cyan]http://localhost:54545/oauth/callback[/cyan]")
        console.print("  4. Copie o client_id para o .env\n")
        sys.exit(1)

    console.print(f"\n[dim]client_id: {client_id[:8]}...[/dim]")

    # Verificar se já existe token válido
    oauth = OAuthManager(client_id=client_id, client_secret=client_secret)
    existing = oauth.get_valid_token()
    if existing:
        console.print("\n[green]Token OAuth válido já está armazenado![/green]")
        stats = oauth.get_cost_stats()
        console.print(f"Requisições realizadas: {stats['total_requests']}")
        if not Confirm.ask("Deseja reautenticar mesmo assim?"):
            console.print("\n[cyan]Workspace pronto para uso com OAuth.[/cyan]")
            console.print("Execute: python3 cli.py --help")
            return

    # Executar fluxo OAuth interativo
    console.print("\n[yellow]Iniciando fluxo OAuth...[/yellow]")
    console.print("O browser será aberto. Faça login com sua conta claude.ai.\n")

    try:
        token = oauth.authenticate_interactive(timeout=180)
        console.print(f"\n[bold green]Autenticação concluída![/bold green]")
        console.print(f"Token armazenado em: [dim]memory/oauth_tokens.db[/dim]")
        console.print("\nAgora você pode usar o workspace:")
        console.print("  [cyan]python3 cli.py chat 'sua pergunta'[/cyan]")
        console.print("  [cyan]python3 cli.py stats[/cyan]")

        # Atualizar .env para indicar que OAuth está ativo
        _update_env_oauth_mode()

    except TimeoutError as e:
        console.print(f"\n[red]Timeout: {e}[/red]")
        console.print("Tente novamente ou verifique o client_id.")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Erro durante autenticação: {e}[/red]")
        sys.exit(1)


def _update_env_oauth_mode():
    """Marca no .env que o modo OAuth está ativo."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path) as f:
        content = f.read()
    if "AUTH_MODE=oauth" not in content:
        with open(env_path, "a") as f:
            f.write("\nAUTH_MODE=oauth\n")


if __name__ == "__main__":
    main()
