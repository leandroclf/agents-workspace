import json
import os
import shutil
import subprocess

from core.claude_code_backend import BackendLimitError

CODEX_MODEL_MAP = {
    "code":          ("gpt-5.3-codex", "high"),
    "architecture":  ("gpt-5.4",       "high"),
    "analysis":      ("gpt-5.4",       "medium"),
    "orchestration": ("gpt-5.4",       "high"),
    "validation":    ("gpt-5.4-mini",  "low"),
    "summary":       ("gpt-5.4-mini",  "low"),
    "chat":          ("gpt-5.4-mini",  "low"),
}

CLI_TIMEOUT = 180


class CodexLimitError(BackendLimitError):
    """Quota Codex esgotada."""


class CodexBackend:
    """
    Backend que usa o Codex CLI (`codex exec`) como executor.
    Usa a assinatura OpenAI do usuário.
    """

    def __init__(self, codex_bin: str = "codex"):
        self.codex_bin = codex_bin

    def is_available(self) -> bool:
        return shutil.which(self.codex_bin) is not None

    def complete(self, prompt: str, system: str = "",
                 model: str = "chat", max_tokens: int = 4096) -> dict:
        task_key = model if model in CODEX_MODEL_MAP else "chat"
        codex_model, effort = CODEX_MODEL_MAP[task_key]

        cmd = [
            self.codex_bin, "exec",
            "--json",
            "--skip-git-repo-check",
            "-m", codex_model,
            "-c", f"model_reasoning_effort={effort}",
        ]
        if system:
            cmd += ["-c", f"system.prompt={system}"]

        cmd.append(prompt)

        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=CLI_TIMEOUT,
                env=env,
            )
        except FileNotFoundError:
            raise RuntimeError(
                "Codex CLI não encontrado. Instale via: npm install -g @openai/codex"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Timeout após {CLI_TIMEOUT}s aguardando Codex CLI")

        text, input_tok, output_tok = _parse_codex_jsonl(proc.stdout)

        if not text and proc.returncode != 0:
            raise RuntimeError(f"Codex CLI erro ({proc.returncode}): {proc.stderr[:200]}")

        return {
            "text": text,
            "model": codex_model,
            "input_tokens": input_tok,
            "output_tokens": output_tok,
            "cost_usd": 0.0,
        }


def _parse_codex_jsonl(output: str) -> tuple[str, int, int]:
    """Extrai texto final e tokens do JSONL do Codex. Lança CodexLimitError se rate limit."""
    text = ""
    input_tok = output_tok = 0
    for line in output.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        etype = event.get("type")
        payload = event.get("payload", {})
        if etype == "response_item":
            for block in payload.get("content", []):
                if block.get("type") == "output_text":
                    text = block.get("text", text)
        elif etype == "event_msg" and payload.get("type") == "token_count":
            info = payload.get("info", {})
            usage = info.get("last_token_usage", {})
            input_tok = usage.get("input_tokens", 0)
            output_tok = usage.get("output_tokens", 0)
            rl = payload.get("rate_limits", {})
            primary = rl.get("primary", {})
            credits = rl.get("credits", {})
            if primary.get("used_percent", 0) >= 95 or credits.get("balance") == "0":
                resets_at = primary.get("resets_at")
                raise CodexLimitError(
                    f"Codex rate limit atingido ({primary.get('used_percent')}%)",
                    resets_at=resets_at,
                )
    return text, input_tok, output_tok
