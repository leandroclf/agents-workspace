# Claude Code CLI Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Substituir as chamadas diretas à API Anthropic (que exigem API key paga) por chamadas ao Claude Code CLI (`claude`), usando a assinatura claude.ai do usuário sem custo adicional por API key.

**Architecture:** Criar `ClaudeCodeBackend` — um wrapper subprocess em torno do `claude` CLI — que expõe a mesma interface do `AnthropicAPIBackend`. O `ClaudeClient` e o `BaseAgent` detectam automaticamente qual backend usar (env var `BACKEND=claude-code` ou fallback para API key). Nenhum outro componente (agentes, orchestrator, Flask API, CLI) precisa mudar.

**Tech Stack:** Python `subprocess.run`, `claude` CLI (já instalado via Claude Code), JSON parsing, env var `BACKEND`, aliases de modelo (`sonnet`, `opus`, `haiku`).

---

## Como o Claude Code CLI funciona (contexto técnico)

```bash
# Comando básico usado por este backend:
echo "prompt do usuário" | claude -p \
  --output-format json \
  --system-prompt "system prompt aqui" \
  --model sonnet \
  --no-session-persistence

# Resposta JSON:
{
  "type": "result",
  "subtype": "success",
  "is_error": false,
  "result": "texto da resposta",
  "usage": {
    "input_tokens": 45,
    "output_tokens": 123,
    "cache_creation_input_tokens": 0,
    "cache_read_input_tokens": 0
  },
  "total_cost_usd": 0.025,
  "modelUsage": { ... }
}
```

**Aliases de modelo** (usados no `--model`):
- `opus` → claude-opus-4-7 (tarefas complexas: code, analysis, orchestration)
- `sonnet` → claude-sonnet-4-6 (tarefas médias: validation, summary)
- `haiku` → claude-haiku-4-5 (tarefas simples: chat)

---

## Mapa de Arquivos

```
~/claude-workspace/
├── core/
│   ├── claude_code_backend.py    # CRIAR: wrapper subprocess do claude CLI
│   ├── claude_client.py          # MODIFICAR: factory de backend (auto-detect)
│   └── agents/
│       └── base_agent.py         # MODIFICAR: _call_api usa backend abstrato
├── tests/
│   └── test_claude_code_backend.py  # CRIAR: testes unitários com mock subprocess
├── .env.example                  # MODIFICAR: documentar BACKEND=claude-code
└── OPERATIONS.md                 # MODIFICAR: instrução de uso sem API key
```

---

## Task 1: ClaudeCodeBackend — wrapper do CLI

**Files:**
- Create: `~/claude-workspace/core/claude_code_backend.py`
- Create: `~/claude-workspace/tests/test_claude_code_backend.py`

- [ ] **Step 1: Escrever testes que falham**

```bash
cat > ~/claude-workspace/tests/test_claude_code_backend.py << 'EOF'
import pytest
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from unittest.mock import patch, MagicMock
from core.claude_code_backend import ClaudeCodeBackend, ClaudeCodeError


def _make_cli_response(text: str = "resposta mock", input_tokens: int = 10,
                        output_tokens: int = 20) -> str:
    return json.dumps({
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "result": text,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        },
        "total_cost_usd": 0.001,
    })


@patch("subprocess.run")
def test_complete_returns_text(mock_run):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=_make_cli_response("Olá mundo"),
        stderr=""
    )
    backend = ClaudeCodeBackend()
    result = backend.complete(prompt="oi", model="haiku")
    assert result["text"] == "Olá mundo"
    assert result["input_tokens"] == 10
    assert result["output_tokens"] == 20


@patch("subprocess.run")
def test_complete_with_system_prompt(mock_run):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=_make_cli_response("resultado"),
        stderr=""
    )
    backend = ClaudeCodeBackend()
    backend.complete(prompt="tarefa", system="Você é um expert.", model="sonnet")
    call_args = mock_run.call_args
    cmd = call_args[0][0]
    assert "--system-prompt" in cmd
    assert "Você é um expert." in cmd


@patch("subprocess.run")
def test_complete_with_model_alias(mock_run):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=_make_cli_response(),
        stderr=""
    )
    backend = ClaudeCodeBackend()
    backend.complete(prompt="teste", model="opus")
    cmd = mock_run.call_args[0][0]
    assert "--model" in cmd
    idx = cmd.index("--model")
    assert cmd[idx + 1] == "opus"


@patch("subprocess.run")
def test_complete_raises_on_cli_error(mock_run):
    mock_run.return_value = MagicMock(
        returncode=1,
        stdout="",
        stderr="command not found: claude"
    )
    backend = ClaudeCodeBackend()
    with pytest.raises(ClaudeCodeError) as exc_info:
        backend.complete(prompt="teste")
    assert "claude" in str(exc_info.value).lower()


@patch("subprocess.run")
def test_complete_raises_on_is_error_true(mock_run):
    error_response = json.dumps({
        "type": "result",
        "subtype": "error",
        "is_error": True,
        "result": "Something went wrong",
        "usage": {"input_tokens": 0, "output_tokens": 0},
    })
    mock_run.return_value = MagicMock(returncode=0, stdout=error_response, stderr="")
    backend = ClaudeCodeBackend()
    with pytest.raises(ClaudeCodeError):
        backend.complete(prompt="teste")


def test_is_available_returns_bool():
    backend = ClaudeCodeBackend()
    result = backend.is_available()
    assert isinstance(result, bool)


@patch("subprocess.run")
def test_prompt_sent_via_stdin(mock_run):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=_make_cli_response("ok"),
        stderr=""
    )
    backend = ClaudeCodeBackend()
    backend.complete(prompt="meu prompt especial", model="haiku")
    call_kwargs = mock_run.call_args[1]
    assert call_kwargs.get("input") == "meu prompt especial"
EOF
```

- [ ] **Step 2: Rodar para confirmar falha**

```bash
cd ~/claude-workspace && venv/bin/pytest tests/test_claude_code_backend.py -v 2>&1 | head -15
# Esperado: ModuleNotFoundError: No module named 'core.claude_code_backend'
```

- [ ] **Step 3: Implementar ClaudeCodeBackend**

```bash
cat > ~/claude-workspace/core/claude_code_backend.py << 'EOF'
import json
import shutil
import subprocess
from typing import Optional

# Mapeamento de TaskType → alias do modelo no claude CLI
MODEL_ALIASES = {
    "claude-opus-4-7":   "opus",
    "claude-sonnet-4-6": "sonnet",
    "claude-haiku-4-5":  "haiku",
    # Aceita aliases diretos também
    "opus":   "opus",
    "sonnet": "sonnet",
    "haiku":  "haiku",
}

# Timeout para chamadas ao CLI (segundos)
CLI_TIMEOUT = 120


class ClaudeCodeError(RuntimeError):
    """Erro ao chamar o Claude Code CLI."""


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
        """
        Executa uma chamada ao Claude Code CLI e retorna o resultado estruturado.

        Args:
            prompt: Mensagem do usuário (enviada via stdin)
            system: System prompt (passado com --system-prompt)
            model: Alias do modelo ('opus', 'sonnet', 'haiku') ou nome completo
            max_tokens: Ignorado no CLI (controlado pela assinatura), mantido por compatibilidade

        Returns:
            dict com: text, model, input_tokens, output_tokens, cost_usd
        """
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

        try:
            proc = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=CLI_TIMEOUT,
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
            raise ClaudeCodeError(f"Erro do claude CLI: {data.get('result', 'unknown error')}")

        usage = data.get("usage", {})
        return {
            "text": data.get("result", ""),
            "model": alias,
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "cost_usd": data.get("total_cost_usd", 0.0),
        }
EOF
```

- [ ] **Step 4: Rodar testes**

```bash
cd ~/claude-workspace && venv/bin/pytest tests/test_claude_code_backend.py -v
# Esperado: 7 passed
```

- [ ] **Step 5: Commit**

```bash
cd ~/claude-workspace && git add core/claude_code_backend.py tests/test_claude_code_backend.py
git commit -m "feat: add ClaudeCodeBackend — subprocess wrapper for claude CLI (uses subscription)"
```

---

## Task 2: Refatorar ClaudeClient com factory de backend

**Files:**
- Modify: `~/claude-workspace/core/claude_client.py` (linhas 1-87)
- Create: `~/claude-workspace/tests/test_claude_client_backend.py`

- [ ] **Step 1: Escrever testes que falham**

```bash
cat > ~/claude-workspace/tests/test_claude_client_backend.py << 'EOF'
import pytest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from unittest.mock import patch, MagicMock
from core.claude_client import ClaudeClient, TaskType, make_client
from core.claude_code_backend import ClaudeCodeBackend
from core.memory_system import MemorySystem


def _mock_backend(text="mock response"):
    backend = MagicMock()
    backend.complete.return_value = {
        "text": text,
        "model": "sonnet",
        "input_tokens": 10,
        "output_tokens": 20,
        "cost_usd": 0.001,
    }
    return backend


def test_client_accepts_explicit_backend(tmp_path):
    memory = MemorySystem(db_path=str(tmp_path / "m.db"))
    backend = _mock_backend("resposta via CLI")
    client = ClaudeClient(backend=backend, memory=memory)
    result = client.chat("oi")
    assert result["text"] == "resposta via CLI"
    backend.complete.assert_called_once()


def test_client_passes_system_prompt_to_backend(tmp_path):
    memory = MemorySystem(db_path=str(tmp_path / "m.db"))
    backend = _mock_backend()
    client = ClaudeClient(backend=backend, memory=memory)
    client.chat("refatore main.py", system="Você é expert em Python.")
    call_kwargs = backend.complete.call_args[1]
    assert "Python" in call_kwargs.get("system", "")


def test_client_routes_model_by_task_type(tmp_path):
    memory = MemorySystem(db_path=str(tmp_path / "m.db"))
    backend = _mock_backend()
    client = ClaudeClient(backend=backend, memory=memory)
    client.chat("refatore o arquivo.py", task_type=TaskType.CODE)
    call_kwargs = backend.complete.call_args[1]
    # CODE → opus
    assert call_kwargs["model"] in ("claude-opus-4-7", "opus")


def test_make_client_uses_claude_code_when_env_set(tmp_path, monkeypatch):
    monkeypatch.setenv("BACKEND", "claude-code")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    memory = MemorySystem(db_path=str(tmp_path / "m.db"))
    with patch("core.claude_code_backend.ClaudeCodeBackend.is_available", return_value=True):
        client = make_client(memory=memory)
    assert isinstance(client._backend, ClaudeCodeBackend)


def test_make_client_falls_back_to_api_key(tmp_path, monkeypatch):
    monkeypatch.setenv("BACKEND", "api")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    memory = MemorySystem(db_path=str(tmp_path / "m.db"))
    with patch("anthropic.Anthropic"):
        client = make_client(memory=memory)
    assert not isinstance(client._backend, ClaudeCodeBackend)


def test_chat_saves_interaction_to_memory(tmp_path):
    memory = MemorySystem(db_path=str(tmp_path / "m.db"))
    backend = _mock_backend("resposta salva")
    client = ClaudeClient(backend=backend, memory=memory)
    client.chat("minha pergunta")
    interactions = memory.get_recent_interactions(limit=1)
    assert len(interactions) == 1
    assert "minha pergunta" in interactions[0]["user_message"]
EOF
```

- [ ] **Step 2: Rodar para confirmar falha**

```bash
cd ~/claude-workspace && venv/bin/pytest tests/test_claude_client_backend.py -v 2>&1 | head -20
# Esperado: ImportError ou AttributeError (make_client não existe, ClaudeClient sem backend=)
```

- [ ] **Step 3: Reescrever core/claude_client.py**

```bash
cat > ~/claude-workspace/core/claude_client.py << 'EOF'
import os
from enum import Enum
from typing import Optional, Any
import anthropic
from core.adaptive_thinking import AdaptiveThinkingManager
from core.memory_system import MemorySystem


class TaskType(Enum):
    CODE = "code"
    ANALYSIS = "analysis"
    ARCHITECTURE = "architecture"
    ORCHESTRATION = "orchestration"
    VALIDATION = "validation"
    SUMMARY = "summary"
    CHAT = "chat"


# Mapeamento TaskType → modelo (nome completo para API, alias para CLI)
MODEL_ROUTING = {
    TaskType.CODE:          "claude-opus-4-7",
    TaskType.ANALYSIS:      "claude-opus-4-7",
    TaskType.ARCHITECTURE:  "claude-opus-4-7",
    TaskType.ORCHESTRATION: "claude-opus-4-7",
    TaskType.VALIDATION:    "claude-sonnet-4-6",
    TaskType.SUMMARY:       "claude-sonnet-4-6",
    TaskType.CHAT:          "claude-haiku-4-5",
}

# Mapeamento nome completo → alias CLI
_CLI_ALIAS = {
    "claude-opus-4-7":   "opus",
    "claude-sonnet-4-6": "sonnet",
    "claude-haiku-4-5":  "haiku",
}

CODE_KEYWORDS = ["refator", "implement", "debug", "fix", "código", "função", "classe",
                 "teste", ".py", ".ts", ".js", "error", "bug", "compile"]
ANALYSIS_KEYWORDS = ["analis", "avali", "compar", "expliq", "por que", "performance",
                     "arquitetura", "design", "revi"]


class _AnthropicAPIBackend:
    """Backend direto via SDK Anthropic (exige API key paga)."""

    def __init__(self, api_key: Optional[str] = None, auth_token: Optional[str] = None):
        if auth_token:
            self._client = anthropic.Anthropic(auth_token=auth_token)
        else:
            key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
            self._client = anthropic.Anthropic(api_key=key)

    def complete(self, prompt: str, system: str = "",
                 model: str = "claude-sonnet-4-6", max_tokens: int = 4096) -> dict:
        kwargs: dict[str, Any] = dict(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        if system:
            kwargs["system"] = [{"type": "text", "text": system,
                                  "cache_control": {"type": "ephemeral"}}]
        response = self._client.messages.create(**kwargs)
        text = response.content[0].text if response.content else ""
        return {
            "text": text,
            "model": model,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "cost_usd": 0.0,
        }


class ClaudeClient:
    """
    Cliente principal. Aceita qualquer backend com interface .complete().
    Use make_client() para criação automática com detecção de backend.
    """

    def __init__(self, backend=None, memory: Optional[MemorySystem] = None,
                 # Compat: parâmetros antigos ainda aceitos
                 api_key: Optional[str] = None,
                 oauth_token: Optional[str] = None,
                 oauth_manager=None):
        if backend is not None:
            self._backend = backend
        else:
            # Retrocompatibilidade com código que passa api_key/oauth_token diretamente
            if oauth_manager and not oauth_token:
                oauth_token = oauth_manager.get_valid_token()
            self._backend = _AnthropicAPIBackend(api_key=api_key, auth_token=oauth_token)

        self.thinking_mgr = AdaptiveThinkingManager()
        self.memory = memory or MemorySystem()

    def detect_task_type(self, prompt: str) -> TaskType:
        lower = prompt.lower()
        if any(k in lower for k in CODE_KEYWORDS):
            return TaskType.CODE
        if any(k in lower for k in ANALYSIS_KEYWORDS):
            return TaskType.ANALYSIS
        return TaskType.CHAT

    def select_model(self, task_type: TaskType) -> str:
        return MODEL_ROUTING.get(task_type, "claude-sonnet-4-6")

    def chat(self, prompt: str, system: str = "",
             task_type: Optional[TaskType] = None,
             max_tokens: int = 4096) -> dict:
        if task_type is None:
            task_type = self.detect_task_type(prompt)
        model_full = self.select_model(task_type)

        # Claude Code CLI usa aliases; API usa nome completo.
        # O backend decide o que fazer com o valor.
        from core.claude_code_backend import ClaudeCodeBackend
        if isinstance(self._backend, ClaudeCodeBackend):
            model = _CLI_ALIAS.get(model_full, "sonnet")
        else:
            model = model_full

        recent = self.memory.get_recent_interactions(limit=5)
        sys_prompt = system
        if recent and not sys_prompt:
            sys_prompt = "[Contexto recente disponível no histórico]"

        result = self._backend.complete(
            prompt=prompt,
            system=sys_prompt,
            model=model,
            max_tokens=max_tokens,
        )

        self.memory.save_interaction(
            user_message=prompt,
            assistant_response=result["text"],
            task_type=task_type.value,
            model_used=model_full,
            tokens_used=result["input_tokens"] + result["output_tokens"],
        )

        return {
            "text": result["text"],
            "model": model_full,
            "task_type": task_type.value,
            "input_tokens": result["input_tokens"],
            "output_tokens": result["output_tokens"],
        }


def make_client(memory: Optional[MemorySystem] = None,
                api_key: Optional[str] = None) -> ClaudeClient:
    """
    Factory com detecção automática de backend.

    Prioridade:
      1. BACKEND=claude-code no .env → ClaudeCodeBackend (usa assinatura)
      2. BACKEND=api ou API key presente → AnthropicAPIBackend
      3. claude CLI disponível e sem API key → ClaudeCodeBackend (auto)
    """
    from core.claude_code_backend import ClaudeCodeBackend

    mem = memory or MemorySystem()
    backend_env = os.environ.get("BACKEND", "").lower()
    api_key_env = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    has_real_key = bool(api_key_env) and api_key_env != "sk-ant-..."

    if backend_env == "claude-code":
        cli = ClaudeCodeBackend()
        if not cli.is_available():
            raise RuntimeError("BACKEND=claude-code mas `claude` CLI não encontrado no PATH")
        return ClaudeClient(backend=cli, memory=mem)

    if backend_env == "api" or has_real_key:
        return ClaudeClient(backend=_AnthropicAPIBackend(api_key=api_key_env or None), memory=mem)

    # Auto-detect: preferir CLI se disponível
    cli = ClaudeCodeBackend()
    if cli.is_available():
        return ClaudeClient(backend=cli, memory=mem)

    if has_real_key:
        return ClaudeClient(backend=_AnthropicAPIBackend(api_key=api_key_env), memory=mem)

    raise RuntimeError(
        "Nenhum backend configurado.\n"
        "Opção 1 (assinatura): defina BACKEND=claude-code no .env\n"
        "Opção 2 (API key):    defina ANTHROPIC_API_KEY no .env"
    )
EOF
```

- [ ] **Step 4: Rodar testes do cliente**

```bash
cd ~/claude-workspace && venv/bin/pytest tests/test_claude_client_backend.py -v
# Esperado: 6 passed
```

- [ ] **Step 5: Garantir que os testes antigos ainda passam**

```bash
cd ~/claude-workspace && venv/bin/pytest tests/test_claude_client.py -v
# Esperado: 7 passed (detect_task_type e select_model não mudaram)
```

- [ ] **Step 6: Commit**

```bash
cd ~/claude-workspace && git add core/claude_client.py tests/test_claude_client_backend.py
git commit -m "refactor: add backend abstraction to ClaudeClient + make_client() factory with auto-detect"
```

---

## Task 3: Atualizar BaseAgent para usar backend abstrato

**Files:**
- Modify: `~/claude-workspace/core/agents/base_agent.py`

- [ ] **Step 1: Verificar que os testes de agentes ainda passam antes de mudar**

```bash
cd ~/claude-workspace && venv/bin/pytest tests/test_agents.py tests/test_orchestrator.py -v
# Esperado: 6 passed
```

- [ ] **Step 2: Atualizar base_agent.py para aceitar backend**

O `BaseAgent.__init__` atualmente recebe `api_key` e cria um `anthropic.Anthropic`. Precisamos trocar para aceitar um backend ou um `ClaudeClient`.

```bash
cat > ~/claude-workspace/core/agents/base_agent.py << 'EOF'
from abc import ABC
from typing import Optional, Any
from core.memory_system import MemorySystem
from core.skill_manager import SkillManager
from core.adaptive_thinking import AdaptiveThinkingManager
from core.claude_client import ClaudeClient, TaskType, make_client


class BaseAgent(ABC):
    name: str = "BaseAgent"
    role_description: str = "Assistente genérico."
    model: str = "claude-sonnet-4-6"
    task_type: str = "chat"

    def __init__(self, memory: Optional[MemorySystem] = None,
                 skill_manager: Optional[SkillManager] = None,
                 api_key: Optional[str] = None,
                 client: Optional[ClaudeClient] = None):
        self.memory = memory or MemorySystem()
        self.skill_manager = skill_manager or SkillManager()
        self.thinking_mgr = AdaptiveThinkingManager()
        # Aceita ClaudeClient externo (com qualquer backend) ou cria via make_client
        if client is not None:
            self._client = client
        else:
            self._client = make_client(memory=self.memory, api_key=api_key)

    def build_system_prompt(self, task: str = "") -> str:
        parts = [f"# {self.name}\n\n{self.role_description}"]
        if self.skill_manager and task:
            injection = self.skill_manager.build_skill_injection_text(query=task, top_k=3)
            if injection:
                parts.append(injection)
        recent = self.memory.get_recent_interactions(limit=3)
        if recent:
            parts.append("## Contexto Recente\n" +
                         "\n".join(f"- {r['task_type']}: {r['user_message'][:80]}" for r in recent))
        return "\n\n".join(parts)

    def run(self, task: str, **kwargs) -> dict[str, Any]:
        return self._call_api(task=task)

    def _call_api(self, task: str, extra_context: str = "",
                  max_tokens: int = 4096) -> dict:
        system = self.build_system_prompt(task=task)
        prompt = task
        if extra_context:
            prompt = f"{task}\n\n**Contexto adicional:**\n{extra_context}"

        task_type_map = {
            "code":          TaskType.CODE,
            "analysis":      TaskType.ANALYSIS,
            "architecture":  TaskType.ARCHITECTURE,
            "orchestration": TaskType.ORCHESTRATION,
            "validation":    TaskType.VALIDATION,
            "summary":       TaskType.SUMMARY,
            "chat":          TaskType.CHAT,
            "execution":     TaskType.CHAT,
        }
        tt = task_type_map.get(self.task_type, TaskType.CHAT)

        result = self._client.chat(
            prompt=prompt,
            system=system,
            task_type=tt,
            max_tokens=max_tokens,
        )
        return {
            "text": result["text"],
            "model": result["model"],
            "agent": self.name,
            "input_tokens": result["input_tokens"],
            "output_tokens": result["output_tokens"],
        }
EOF
```

- [ ] **Step 3: Rodar testes de agentes**

```bash
cd ~/claude-workspace && venv/bin/pytest tests/test_agents.py tests/test_orchestrator.py -v
# Esperado: 6 passed
```

- [ ] **Step 4: Rodar testes E2E (usam mock do backend)**

```bash
cd ~/claude-workspace && venv/bin/pytest tests/test_integration_e2e.py -v
# Esperado: 3 passed (os mocks precisam ser ajustados — ver step 5 se falhar)
```

Se test_integration_e2e falhar por causa da mudança de import, corrija o mock:

```python
# Antes (nos testes E2E):
@patch("anthropic.Anthropic")

# Depois (patch no backend interno do ClaudeClient):
@patch("core.claude_client._AnthropicAPIBackend.complete")
```

Se necessário, atualize `tests/test_integration_e2e.py` conforme abaixo:

```bash
cat > ~/claude-workspace/tests/test_integration_e2e.py << 'EOF'
"""
Testes de integração E2E sem chamada real à API ou CLI.
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from unittest.mock import patch, MagicMock
from core.memory_system import MemorySystem
from core.skill_manager import SkillManager, Skill


def _backend_response(text="resultado mock", input_tokens=100, output_tokens=200):
    return {
        "text": text,
        "model": "sonnet",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": 0.0,
    }


def test_full_chat_flow(tmp_path):
    """Fluxo completo: usuário → detecção → backend → memória → resposta."""
    from core.claude_client import ClaudeClient, TaskType

    mock_backend = MagicMock()
    mock_backend.complete.return_value = _backend_response("def hello(): pass")

    memory = MemorySystem(db_path=str(tmp_path / "test.db"))
    client = ClaudeClient(backend=mock_backend, memory=memory)

    result = client.chat("Escreva uma função Python hello world")
    assert result["text"] == "def hello(): pass"
    assert result["task_type"] == "code"

    interactions = memory.get_recent_interactions(limit=1)
    assert len(interactions) == 1
    assert interactions[0]["task_type"] == "code"


def test_skill_injection_flow(tmp_path):
    """Skills relevantes devem ser injetadas no system prompt."""
    from core.agents.coder_agent import CoderAgent
    from core.claude_client import ClaudeClient

    mock_backend = MagicMock()
    mock_backend.complete.return_value = _backend_response("código refatorado")

    memory = MemorySystem(db_path=str(tmp_path / "mem.db"))
    skills = SkillManager(db_path=str(tmp_path / "sk.db"))
    skills.save_skill(Skill("py_refactor", "Refatora Python", "Refatore: {code}", tags=["python"]))

    client = ClaudeClient(backend=mock_backend, memory=memory)
    agent = CoderAgent(memory=memory, skill_manager=skills, client=client)
    result = agent.run(task="refactor this python code", language="python")

    call_kwargs = mock_backend.complete.call_args[1]
    assert "py_refactor" in call_kwargs.get("system", "")
    assert result["text"] == "código refatorado"


def test_error_handler_retry_flow(tmp_path):
    """Deve retentar em RateLimitError e ter sucesso na 2ª tentativa."""
    import anthropic
    from core.error_handler import RobustErrorHandler
    from core.claude_client import ClaudeClient

    call_count = [0]
    mock_backend = MagicMock()

    def backend_side_effect(**kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise anthropic.RateLimitError(
                message="rate", response=MagicMock(status_code=429), body={}
            )
        return _backend_response("resposta após retry")

    mock_backend.complete.side_effect = backend_side_effect

    memory = MemorySystem(db_path=str(tmp_path / "m.db"))
    client = ClaudeClient(backend=mock_backend, memory=memory)
    handler = RobustErrorHandler(max_retries=2, base_delay=0.001)

    result = handler.execute_with_retry(lambda: client.chat("olá"))
    assert result["text"] == "resposta após retry"
    assert call_count[0] == 2
EOF
```

- [ ] **Step 5: Rodar suite completa**

```bash
cd ~/claude-workspace && venv/bin/pytest tests/ -v 2>&1 | tail -15
# Esperado: todos passando (40+ testes)
```

- [ ] **Step 6: Commit**

```bash
cd ~/claude-workspace && git add core/agents/base_agent.py tests/test_integration_e2e.py
git commit -m "refactor: BaseAgent uses ClaudeClient backend abstraction instead of direct anthropic SDK"
```

---

## Task 4: Atualizar cli.py para usar make_client()

**Files:**
- Modify: `~/claude-workspace/cli.py`

- [ ] **Step 1: Substituir _make_client() por make_client() do módulo**

```bash
# Localizar a função _make_client atual no cli.py
grep -n "_make_client\|make_client" ~/claude-workspace/cli.py
```

- [ ] **Step 2: Editar cli.py**

Substituir a função `_make_client` local pela importação de `make_client` do `core.claude_client`:

```python
# REMOVER do cli.py a função _make_client() inteira (linhas com def _make_client...)
# ADICIONAR logo após load_dotenv():

from core.claude_client import make_client as _make_client
```

Execute:
```bash
cd ~/claude-workspace && python3 - << 'EOF'
import re

with open("cli.py") as f:
    content = f.read()

# Remover a função _make_client local (do def até o return ClaudeClient(...))
old_fn = '''

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

'''

new_fn = '''

def _make_client(memory=None):
    """Cria ClaudeClient com auto-detecção de backend (CLI ou API key)."""
    from core.claude_client import make_client
    return make_client(memory=memory)

'''

content = content.replace(old_fn, new_fn)
with open("cli.py", "w") as f:
    f.write(content)
print("OK cli.py atualizado")
EOF
```

- [ ] **Step 3: Verificar que o CLI funciona**

```bash
cd ~/claude-workspace && venv/bin/python3 cli.py --help
venv/bin/python3 cli.py stats
```

Ambos devem executar sem erros.

- [ ] **Step 4: Commit**

```bash
cd ~/claude-workspace && git add cli.py
git commit -m "feat: cli.py uses make_client() for automatic backend selection"
```

---

## Task 5: Configuração, docs e smoke test

**Files:**
- Modify: `~/claude-workspace/.env.example`
- Modify: `~/claude-workspace/.env`
- Modify: `~/claude-workspace/OPERATIONS.md`

- [ ] **Step 1: Atualizar .env.example com BACKEND**

```bash
cd ~/claude-workspace && python3 - << 'EOF'
with open(".env.example") as f:
    content = f.read()

backend_block = """
# ── Seleção de Backend ────────────────────────────────────────────────────────
# BACKEND=claude-code  → usa o Claude Code CLI (assinatura claude.ai, SEM API key)
# BACKEND=api          → usa a API Anthropic direta (exige ANTHROPIC_API_KEY)
# (omitir)             → auto-detect: prefere CLI se disponível
BACKEND=claude-code
# ──────────────────────────────────────────────────────────────────────────────
"""

if "BACKEND=" not in content:
    # Inserir antes da linha DATABASE_URL
    content = content.replace("DATABASE_URL=", backend_block + "DATABASE_URL=")
    with open(".env.example", "w") as f:
        f.write(content)
    print("OK .env.example atualizado")
else:
    print("BACKEND já presente")
EOF
```

- [ ] **Step 2: Adicionar BACKEND=claude-code ao .env ativo**

```bash
cd ~/claude-workspace
if ! grep -q "^BACKEND=" .env; then
    echo "BACKEND=claude-code" >> .env
    echo "OK BACKEND adicionado ao .env"
else
    sed -i 's/^BACKEND=.*/BACKEND=claude-code/' .env
    echo "OK BACKEND atualizado no .env"
fi
```

- [ ] **Step 3: Atualizar OPERATIONS.md**

```bash
cd ~/claude-workspace && python3 - << 'EOF'
addition = """
## Usando com assinatura claude.ai (sem API key)

O workspace detecta automaticamente o Claude Code CLI e usa sua assinatura.
Não é necessário configurar ANTHROPIC_API_KEY.

```bash
# Verificar que o backend está configurado:
grep BACKEND .env
# Deve mostrar: BACKEND=claude-code

# Testar o backend diretamente:
echo "Responda apenas: OK" | claude -p --output-format json --no-session-persistence | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['result'])"

# Usar o workspace normalmente:
python3 cli.py chat "Olá, estou usando minha assinatura!"
```

## Usando com API key (billing por token)

```bash
# No .env:
BACKEND=api
ANTHROPIC_API_KEY=sk-ant-...
```
"""

with open("OPERATIONS.md") as f:
    content = f.read()

if "assinatura claude.ai" not in content:
    content = content + addition
    with open("OPERATIONS.md", "w") as f:
        f.write(content)
    print("OK OPERATIONS.md atualizado")
else:
    print("Seção já presente")
EOF
```

- [ ] **Step 4: Smoke test com Claude Code CLI real**

```bash
cd ~/claude-workspace && venv/bin/python3 << 'EOF'
import os
os.environ["BACKEND"] = "claude-code"

from core.claude_client import make_client
from core.memory_system import MemorySystem

memory = MemorySystem()
client = make_client(memory=memory)
print(f"Backend: {type(client._backend).__name__}")

result = client.chat("Responda apenas: WORKSPACE_CLI_OK", )
assert "WORKSPACE_CLI_OK" in result["text"].upper(), f"Inesperado: {result['text']}"
print(f"OK texto: {result['text']}")
print(f"OK modelo: {result['model']}")
print(f"OK tokens: in={result['input_tokens']} out={result['output_tokens']}")
print("Smoke test PASSOU — usando assinatura claude.ai!")
EOF
```

- [ ] **Step 5: Rodar suite completa final**

```bash
cd ~/claude-workspace && venv/bin/pytest tests/ -v 2>&1 | tail -15
# Esperado: todos os testes passando
```

- [ ] **Step 6: Commit e tag final**

```bash
cd ~/claude-workspace
git add .env.example .env OPERATIONS.md
git commit -m "feat: configure BACKEND=claude-code as default — no API key required"
git tag -a v2.1.0 -m "v2.1.0 — Claude Code CLI backend, uses claude.ai subscription"
```

---

## Self-Review

**Spec coverage:**
- ✅ ClaudeCodeBackend wrapper subprocess → Task 1
- ✅ `--system-prompt`, `--model`, `--output-format json`, `--no-session-persistence` → Task 1
- ✅ Erro tratado com `ClaudeCodeError` → Task 1
- ✅ `make_client()` com auto-detect por env var → Task 2
- ✅ `ClaudeClient` retrocompatível (aceita `api_key`/`oauth_token` antigos) → Task 2
- ✅ `BaseAgent` usa backend abstrato via `ClaudeClient` → Task 3
- ✅ Testes E2E atualizados para novo mock pattern → Task 3
- ✅ `cli.py` usa `make_client()` → Task 4
- ✅ `.env` com `BACKEND=claude-code` por padrão → Task 5
- ✅ Smoke test real com CLI → Task 5
- ✅ `OPERATIONS.md` documentando ambos backends → Task 5

**Gaps aceitos (pós-escopo):**
- Session persistence (histórico de conversa multi-turn via `--continue`) — o CLI é stateless por design aqui
- Streaming output (usaria `--output-format stream-json`) — não necessário para o fluxo atual
