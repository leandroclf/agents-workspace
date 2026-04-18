import os
import sqlite3
import secrets
import hashlib
import base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

ANTHROPIC_OAUTH_URL = "https://console.anthropic.com/oauth/authorize"

MODEL_COSTS = {
    "claude-opus-4-7":   {"input": 5.0,   "output": 25.0},
    "claude-sonnet-4-6": {"input": 3.0,   "output": 15.0},
    "claude-haiku-4-5":  {"input": 0.25,  "output": 1.25},
}


class OAuthManager:
    def __init__(self, client_id: str, client_secret: str,
                 db_path: str = "memory/oauth_tokens.db"):
        self.client_id = client_id
        self.client_secret = client_secret
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

    def generate_pkce_pair(self) -> tuple[str, str]:
        verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
        digest = hashlib.sha256(verifier.encode()).digest()
        challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
        self._pkce_verifier = verifier
        return verifier, challenge

    def build_authorization_url(self, redirect_uri: str) -> str:
        _, challenge = self.generate_pkce_pair()
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        return f"{ANTHROPIC_OAUTH_URL}?{urlencode(params)}"

    def store_token(self, access_token: str, refresh_token: str, expires_in: int):
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        with self._conn() as conn:
            conn.execute("UPDATE oauth_tokens SET is_active = 0")
            conn.execute(
                """INSERT INTO oauth_tokens (access_token, refresh_token, expires_at, is_active)
                   VALUES (?, ?, ?, 1)""",
                (access_token, refresh_token, expires_at.isoformat())
            )

    def get_valid_token(self) -> Optional[str]:
        with self._conn() as conn:
            row = conn.execute(
                """SELECT access_token, expires_at FROM oauth_tokens
                   WHERE is_active = 1 ORDER BY created_at DESC LIMIT 1"""
            ).fetchone()
        if not row:
            return None
        expires_at = datetime.fromisoformat(row["expires_at"])
        if datetime.utcnow() >= expires_at - timedelta(minutes=5):
            return None
        return row["access_token"]

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
