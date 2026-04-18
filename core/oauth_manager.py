import os
import sqlite3
import secrets
import hashlib
import base64
import json
import threading
import webbrowser
import requests
from datetime import datetime, timezone, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode, urlparse, parse_qs

# Endpoints Anthropic OAuth (assinatura claude.ai)
CLAUDE_AUTH_URL = "https://claude.ai/oauth/authorize"
ANTHROPIC_TOKEN_URL = "https://api.anthropic.com/v1/oauth/token"

CALLBACK_PORT = 54545
REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}/oauth/callback"

MODEL_COSTS = {
    "claude-opus-4-7":   {"input": 5.0,   "output": 25.0},
    "claude-sonnet-4-6": {"input": 3.0,   "output": 15.0},
    "claude-haiku-4-5":  {"input": 0.25,  "output": 1.25},
}

_CALLBACK_CODE: Optional[str] = None
_CALLBACK_ERROR: Optional[str] = None
_CALLBACK_EVENT = threading.Event()


class _CallbackHandler(BaseHTTPRequestHandler):
    """Captura o authorization_code do redirect OAuth."""

    def do_GET(self):
        global _CALLBACK_CODE, _CALLBACK_ERROR
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        if "code" in params:
            _CALLBACK_CODE = params["code"][0]
            body = b"<html><body><h2>Autenticado! Pode fechar esta aba.</h2></body></html>"
        elif "error" in params:
            _CALLBACK_ERROR = params.get("error_description", params["error"])[0]
            body = f"<html><body><h2>Erro: {_CALLBACK_ERROR}</h2></body></html>".encode()
        else:
            body = b"<html><body><h2>Callback recebido.</h2></body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)
        _CALLBACK_EVENT.set()

    def log_message(self, *args):
        pass  # silenciar logs do servidor


class OAuthManager:
    def __init__(self, client_id: str, client_secret: str = "",
                 db_path: str = "memory/oauth_tokens.db"):
        self.client_id = client_id
        self.client_secret = client_secret  # opcional para PKCE público
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._pkce_verifier: Optional[str] = None
        self._init_schema()

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS oauth_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    access_token TEXT UNIQUE NOT NULL,
                    refresh_token TEXT,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP,
                    usage_count INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS token_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    access_token TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    model TEXT NOT NULL,
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    total_cost_usd REAL DEFAULT 0.0,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

    # ──────────────────────────────────────────────
    # PKCE
    # ──────────────────────────────────────────────

    def generate_pkce_pair(self) -> tuple[str, str]:
        verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
        digest = hashlib.sha256(verifier.encode()).digest()
        challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
        self._pkce_verifier = verifier
        return verifier, challenge

    def build_authorization_url(self, redirect_uri: str = REDIRECT_URI,
                                 scopes: str = "org:create_api_key user:profile user:email") -> str:
        _, challenge = self.generate_pkce_pair()
        state = secrets.token_urlsafe(16)
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": scopes,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": state,
        }
        return f"{CLAUDE_AUTH_URL}?{urlencode(params)}"

    # ──────────────────────────────────────────────
    # Fluxo completo com servidor de callback local
    # ──────────────────────────────────────────────

    def authenticate_interactive(self, timeout: int = 120) -> str:
        """
        Abre o browser para autenticar com a conta claude.ai,
        aguarda o callback local, troca o código por token e armazena.
        Retorna o access_token.
        """
        global _CALLBACK_CODE, _CALLBACK_ERROR, _CALLBACK_EVENT
        _CALLBACK_CODE = None
        _CALLBACK_ERROR = None
        _CALLBACK_EVENT = threading.Event()

        auth_url = self.build_authorization_url()

        # Inicia servidor de callback em thread
        server = HTTPServer(("localhost", CALLBACK_PORT), _CallbackHandler)
        thread = threading.Thread(target=server.handle_request, daemon=True)
        thread.start()

        print(f"\nAbrindo browser para autenticação com claude.ai...")
        print(f"Se não abrir automaticamente, acesse:\n{auth_url}\n")
        webbrowser.open(auth_url)

        # Aguarda callback
        if not _CALLBACK_EVENT.wait(timeout=timeout):
            server.server_close()
            raise TimeoutError(f"Timeout aguardando callback OAuth ({timeout}s)")

        server.server_close()

        if _CALLBACK_ERROR:
            raise ValueError(f"Erro OAuth: {_CALLBACK_ERROR}")
        if not _CALLBACK_CODE:
            raise ValueError("Nenhum código de autorização recebido")

        token_data = self.exchange_code(code=_CALLBACK_CODE)
        access_token = token_data["access_token"]
        self.store_token(
            access_token=access_token,
            refresh_token=token_data.get("refresh_token", ""),
            expires_in=token_data.get("expires_in", 3600),
        )
        print("Autenticação OAuth concluída com sucesso!")
        return access_token

    # ──────────────────────────────────────────────
    # Troca de código por token
    # ──────────────────────────────────────────────

    def exchange_code(self, code: str, redirect_uri: str = REDIRECT_URI) -> dict:
        """Troca o authorization_code por access_token + refresh_token."""
        if not self._pkce_verifier:
            raise ValueError("PKCE verifier não encontrado — chame build_authorization_url() primeiro")
        payload = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": self._pkce_verifier,
        }
        if self.client_secret:
            payload["client_secret"] = self.client_secret

        resp = requests.post(ANTHROPIC_TOKEN_URL, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()

    # ──────────────────────────────────────────────
    # Refresh automático
    # ──────────────────────────────────────────────

    def refresh_access_token(self) -> Optional[str]:
        """Renova o access_token usando o refresh_token armazenado."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT refresh_token FROM oauth_tokens WHERE is_active = 1 ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        if not row or not row["refresh_token"]:
            return None

        payload = {
            "grant_type": "refresh_token",
            "refresh_token": row["refresh_token"],
            "client_id": self.client_id,
        }
        if self.client_secret:
            payload["client_secret"] = self.client_secret

        try:
            resp = requests.post(ANTHROPIC_TOKEN_URL, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            self.store_token(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token", row["refresh_token"]),
                expires_in=data.get("expires_in", 3600),
            )
            return data["access_token"]
        except Exception:
            return None

    # ──────────────────────────────────────────────
    # Armazenamento e recuperação
    # ──────────────────────────────────────────────

    def store_token(self, access_token: str, refresh_token: str, expires_in: int):
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        with self._conn() as conn:
            conn.execute("UPDATE oauth_tokens SET is_active = 0")
            conn.execute(
                """INSERT INTO oauth_tokens (access_token, refresh_token, expires_at, is_active)
                   VALUES (?, ?, ?, 1)""",
                (access_token, refresh_token, expires_at.isoformat())
            )

    def get_valid_token(self) -> Optional[str]:
        """Retorna um token válido, renovando automaticamente se necessário."""
        with self._conn() as conn:
            row = conn.execute(
                """SELECT access_token, expires_at FROM oauth_tokens
                   WHERE is_active = 1 ORDER BY created_at DESC LIMIT 1"""
            ).fetchone()
        if not row:
            return None

        expires_at = datetime.fromisoformat(row["expires_at"])
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        if now >= expires_at - timedelta(minutes=5):
            # Token prestes a expirar — tentar refresh automático
            return self.refresh_access_token()

        return row["access_token"]

    # ──────────────────────────────────────────────
    # Auditoria de uso e custos
    # ──────────────────────────────────────────────

    def log_usage(self, access_token: str, endpoint: str, model: str,
                  input_tokens: int, output_tokens: int):
        costs = MODEL_COSTS.get(model, {"input": 3.0, "output": 15.0})
        total_cost = (input_tokens / 1_000_000 * costs["input"] +
                      output_tokens / 1_000_000 * costs["output"])
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO token_usage
                   (access_token, endpoint, model, input_tokens, output_tokens, total_cost_usd)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (access_token, endpoint, model, input_tokens, output_tokens, total_cost)
            )
            conn.execute(
                """UPDATE oauth_tokens SET usage_count = usage_count + 1, last_used = CURRENT_TIMESTAMP
                   WHERE access_token = ?""",
                (access_token,)
            )

    def get_cost_stats(self) -> dict:
        with self._conn() as conn:
            row = conn.execute(
                """SELECT COUNT(*) as total_requests,
                          COALESCE(SUM(input_tokens), 0) as total_input_tokens,
                          COALESCE(SUM(output_tokens), 0) as total_output_tokens,
                          COALESCE(SUM(total_cost_usd), 0) as total_cost_usd
                   FROM token_usage"""
            ).fetchone()
        return dict(row)
