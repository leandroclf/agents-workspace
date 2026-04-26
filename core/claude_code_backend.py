import json
import os
import shutil
import subprocess

MODEL_ALIASES = {
    "claude-opus-4-7":   "opus",
    "claude-sonnet-4-6": "sonnet",
    "claude-haiku-4-5":  "haiku",
    "opus":   "opus",
    "sonnet": "sonnet",
    "haiku":  "haiku",
    "code":          "opus",
    "analysis":      "opus",
    "architecture":  "opus",
    "orchestration": "opus",
    "validation":    "sonnet",
    "summary":       "sonnet",
    "chat":          "haiku",
}

CLI_TIMEOUT = 120


class ClaudeCodeError(RuntimeError):
    """Erro ao chamar o Claude Code CLI."""


class BackendLimitError(ClaudeCodeError):
    """Rate limit ou quota esgotada — backend deve ser descartado por esta sessão."""
    def __init__(self, message: str, resets_at: float | None = None):
        super().__init__(message)
        self.resets_at = resets_at


class ClaudeCodeBackend:
    """
    Backend que usa o Claude Code CLI (`claude`) como executor.
    Usa a assinatura claude.ai do usuário — sem cobrança por API key.
    """

    def __init__(self, claude_bin: str = "claude"):
        self.claude_bin = claude_bin

    def is_available(self) -> bool:
        """Verifica se o `claude` CLI está instalado e acessível."""
        return shutil.which(self.claude_bin) is not None

    def complete(self, prompt: str, system: str = "",
                 model: str = "sonnet", max_tokens: int = 4096) -> dict:
        alias = MODEL_ALIASES.get(model, "sonnet")

        cmd = [
            self.claude_bin,
            "--print",
            "--output-format", "json",
            "--model", alias,
            "--no-session-persistence",
        ]
        if system:
            cmd += ["--system-prompt", system]

        # Remove ANTHROPIC_API_KEY do ambiente do subprocess — o CLI usa
        # credenciais da sessão instalada; uma API key placeholder causaria 401.
        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}

        try:
            proc = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=CLI_TIMEOUT,
                env=env,
            )
        except FileNotFoundError:
            raise ClaudeCodeError(
                "Claude Code CLI não encontrado. Instale via: npm install -g @anthropic-ai/claude-code"
            )
        except subprocess.TimeoutExpired:
            raise ClaudeCodeError(f"Timeout após {CLI_TIMEOUT}s aguardando resposta do claude CLI")

        if proc.returncode != 0:
            raise ClaudeCodeError(
                f"claude CLI retornou código {proc.returncode}: {proc.stderr or proc.stdout}"
            )

        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            raise ClaudeCodeError(f"Resposta inválida do claude CLI: {e}\nOutput: {proc.stdout[:200]}")

        if data.get("is_error") or data.get("subtype") == "error":
            msg = data.get("result", "unknown error")
            lower = msg.lower()
            if "hit your limit" in lower or "resets" in lower:
                raise BackendLimitError(f"Claude CLI limite atingido: {msg}")
            raise ClaudeCodeError(f"Erro do claude CLI: {msg}")

        usage = data.get("usage", {})
        return {
            "text": data.get("result", ""),
            "model": alias,
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "cost_usd": data.get("total_cost_usd", 0.0),
        }
