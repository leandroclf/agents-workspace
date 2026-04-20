# Agents Workspace

> **Base reutilizável para novos projetos com agentes** — sistema multi-agente com backend abstrato, memória persistente, servidores MCP, REST API, CLI e workflows declarativos.

---

## Visão Geral

### Contexto

O **Agents Workspace** é um template de fundação para iniciar projetos com agentes. A ideia é separar o que é infraestrutura genérica do que é regra de negócio específica:

- infraestrutura reutilizável: backend, memória, skills, orquestração, CLI, API e workflows;
- exemplos de domínio: agentes prontos para demonstração ou adaptação rápida;
- objetivo: começar um projeto novo sem reconstruir o runtime do zero.

### O que foi construído

| Componente | Descrição |
|---|---|
| **Backend abstraction** | Usa Claude Code CLI, Codex CLI ou API Anthropic direta, com detecção automática |
| **Roteamento de modelos** | Opus 4.7 para código/análise, Sonnet 4.6 para validação, Haiku 4.5 para chat |
| **Sistema multi-agente** | OrchestratorAgent decompõe tarefas e despacha para agentes especializados em paralelo |
| **Memória persistente** | SQLite com histórico de interações, skills aprendidas e contexto de projeto |
| **Skill Manager** | Biblioteca de skills com busca por relevância e rastreamento de taxa de sucesso |
| **MCP Servers** | Servidor git e filesystem via protocolo MCP (TypeScript) |
| **REST API** | Flask com endpoints de chat, skills e histórico |
| **CLI** | Interface Click com comandos `chat`, `orchestrate`, `history`, `stats` |
| **Observabilidade** | OpenTelemetry com exportador OTLP |
| **Workflow Engine** | Motor YAML para automação de fluxos multi-passo |

### Resultado técnico

- **113 testes automatizados** passando (unitários + integração E2E)
- **Zero dependência de API key** quando usando `BACKEND=claude-code`
- **Sem shell injection** — todos os subprocessos usam array de argumentos
- **Retrocompatível** — aceita `api_key=`, `oauth_token=` e o novo `backend=` na mesma interface
- Pronto para ser clonado e adaptado a novos projetos

### Decisão de arquitetura principal

A arquitetura isola a escolha de backend do restante do sistema. Isso permite usar o mesmo runtime com:

- `claude-code` quando houver Claude Code CLI disponível;
- `codex` quando o projeto quiser validar fluxos com o modelo Codex via CLI;
- `api` quando a integração direta com Anthropic fizer sentido;
- fallback automático entre backends quando configurado.

---

## Sumário

- [Pré-requisitos](#pré-requisitos)
- [Instalação](#instalação)
- [Configuração de autenticação](#configuração-de-autenticação)
- [Uso rápido — CLI](#uso-rápido--cli)
- [Arquitetura](#arquitetura)
- [Módulos principais](#módulos-principais)
- [Multi-agentes e Orquestração](#multi-agentes-e-orquestração)
- [REST API](#rest-api)
- [MCP Servers](#mcp-servers)
- [Workflow Engine](#workflow-engine)
- [Testes](#testes)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Referência de comandos](#referência-de-comandos)
- [Tutorial para agentes autônomos](#tutorial-para-agentes-autônomos)

---

## Pré-requisitos

| Dependência | Versão mínima | Uso |
|---|---|---|
| Python | 3.11+ | Runtime principal |
| Claude Code CLI (`claude`) | qualquer | Backend de execução (assinatura) |
| Node.js | 18+ | Compilar MCP servers TypeScript |
| Docker + Compose | qualquer | PostgreSQL + Redis (opcional) |
| Git | qualquer | MCP git server |

### Verificar pré-requisitos

```bash
python3 --version        # >= 3.11
claude --version         # Claude Code CLI instalado
node --version           # >= 18
docker --version         # opcional
```

Instalar Claude Code CLI se ausente:
```bash
npm install -g @anthropic-ai/claude-code
claude login             # autenticar com conta claude.ai
```

---

## Instalação

```bash
# 1. Clonar o repositório
git clone git@github-hotmail:leandroclf/agents-workspace.git
cd agents-workspace

# 2. Criar e ativar o virtualenv
python3 -m venv venv
source venv/bin/activate
# ou: source activate_env.sh

# 3. Instalar dependências Python
pip install -r requirements.txt

# 4. Copiar configuração e ajustar
cp .env.example .env
# Editar .env conforme necessário (ver seção abaixo)

# 5. Compilar MCP servers (TypeScript)
npm install
npx tsc

# 6. Verificar instalação
python3 cli.py --help
python3 cli.py stats
```

---

## Configuração de backend

O workspace suporta três modos principais de backend, com fallback opcional.

### Modo 1: Claude Code CLI

```bash
# No .env:
BACKEND=claude-code

# Verificar que o CLI está disponível:
claude whoami

# Testar o backend diretamente:
echo "Responda: OK" | claude -p --output-format json --no-session-persistence \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['result'])"
```

O workspace detecta automaticamente o `claude` no PATH. Nenhuma chave de API é necessária.

### Modo 2: Codex CLI

```bash
# No .env:
BACKEND=codex
CODEX_MODEL=gpt-5.4-mini
```

### Modo 3: API Anthropic direta

```bash
# No .env:
BACKEND=api
ANTHROPIC_API_KEY=sk-ant-...
```

### Fallback chain automático

Quando `FALLBACK_CHAIN_ENABLED=true`, o workspace tenta backends em cascata ao atingir rate limit:

```
claude-code → codex → api
```

```bash
# No .env:
FALLBACK_CHAIN_ENABLED=true
```

### Detecção automática (sem BACKEND definido)

Se `BACKEND` não está definido no `.env`:
1. Se `claude` CLI estiver no PATH → usa `ClaudeCodeBackend`
2. Se `codex` CLI estiver no PATH → usa `CodexBackend`
3. Se `ANTHROPIC_API_KEY` estiver definida → usa `_AnthropicAPIBackend`
4. Nenhum dos dois → erro com instrução de configuração

---

## Uso rápido — CLI

```bash
# Ativar o ambiente
source venv/bin/activate

# Chat simples (detecção automática de task type)
python3 cli.py chat "Como funciona o asyncio em Python?"

# Forçar task type
python3 cli.py chat "Refatore essa função: def f(x): return x+1" --task-type code
python3 cli.py chat "Analise os prós e contras de SQLite vs PostgreSQL" --task-type analysis

# Orquestrar tarefa complexa com múltiplos agentes
python3 cli.py orchestrate "Crie um módulo de autenticação JWT com testes"

# Ver histórico de interações
python3 cli.py history --limit 20

# Ver estatísticas do workspace
python3 cli.py stats
```

Exemplo de saída do `chat`:

```
╭─────────────── claude-haiku-4-5 ───────────────╮
│ O asyncio é o framework de I/O assíncrono...   │
╰─ task:chat | in:42 out:287 tokens ─────────────╯
```

---

## Arquitetura

```
agents-workspace/
├── core/
│   ├── claude_code_backend.py   # Backend subprocess do claude CLI
│   ├── claude_client.py         # ClaudeClient + make_client() factory + roteamento
│   ├── memory_system.py         # SQLite: interações, skills, preferências, contexto
│   ├── skill_manager.py         # Biblioteca de skills com busca por relevância
│   ├── adaptive_thinking.py     # Adaptação dinâmica de parâmetros de pensamento
│   ├── error_handler.py         # Retry com backoff exponencial
│   ├── rate_limiter.py          # Rate limiting por janela de tempo
│   ├── oauth_manager.py         # OAuth PKCE (uso futuro / API key alternativo)
│   └── agents/
│       ├── base_agent.py        # ABC: build_system_prompt, _call_api, make_client
│       ├── orchestrator_agent.py # Decomposição + despacho paralelo (ThreadPoolExecutor)
│       ├── coder_agent.py       # Especialista em código
│       ├── analysis_agent.py    # Especialista em análise
│       ├── executor_agent.py    # Especialista em execução
│       └── validator_agent.py   # Especialista em validação
├── api/
│   ├── app.py                   # Flask REST API
│   └── mcp_manager.py           # Gerenciador de servidores MCP
├── mcp/servers/
│   ├── git-server.ts            # MCP: git status/log/diff/branches
│   └── filesystem-server.ts     # MCP: leitura de arquivos
├── workflows/
│   └── engine.py                # Motor de workflows YAML
├── observability/
│   └── telemetry.py             # OpenTelemetry (traces + métricas)
├── tests/                       # 113 testes pytest
├── cli.py                       # Entrypoint Click
├── authenticate.py              # Setup OAuth interativo
├── docker-compose.yml           # PostgreSQL + Redis
└── .env.example                 # Template de configuração
```

### Fluxo de uma requisição

```
cli.py chat "prompt"
    ↓
_make_client() → make_client()
    ↓
ClaudeClient.chat()
    ├── detect_task_type(prompt) → TaskType.CODE / ANALYSIS / CHAT / ...
    ├── select_model(task_type) → "claude-opus-4-7" / "claude-sonnet-4-6" / "claude-haiku-4-5"
    ├── backend.complete(prompt, system, model)
    │       ├── ClaudeCodeBackend: subprocess claude CLI → JSON
    │       └── _AnthropicAPIBackend: anthropic.messages.create()
    ├── memory.save_interaction(...)
    └── return {text, model, task_type, input_tokens, output_tokens}
```

---

## Módulos principais

### `core/claude_client.py`

Ponto de entrada para qualquer chamada ao Claude.

```python
from core.claude_client import ClaudeClient, TaskType, make_client
from core.memory_system import MemorySystem

# Criar cliente com auto-detecção de backend
client = make_client()

# Chat com detecção automática de task type
result = client.chat("Explique decorators em Python")
print(result["text"])
print(result["model"])        # claude-haiku-4-5
print(result["input_tokens"]) # tokens consumidos

# Forçar task type e system prompt
result = client.chat(
    prompt="Refatore esse código...",
    system="Você é um engenheiro sênior Python.",
    task_type=TaskType.CODE,
    max_tokens=8192,
)
```

**Roteamento de modelos:**

| TaskType | Modelo | Uso |
|---|---|---|
| CODE, ANALYSIS, ARCHITECTURE, ORCHESTRATION | `claude-opus-4-7` | Tarefas complexas |
| VALIDATION, SUMMARY | `claude-sonnet-4-6` | Tarefas médias |
| CHAT | `claude-haiku-4-5` | Interações rápidas |

### `core/claude_code_backend.py`

Wrapper subprocess em torno do `claude` CLI.

```python
from core.claude_code_backend import ClaudeCodeBackend, ClaudeCodeError

backend = ClaudeCodeBackend()

# Verificar disponibilidade
print(backend.is_available())  # True/False

# Chamada direta
result = backend.complete(
    prompt="Responda apenas: OK",
    system="Você é um assistente de testes.",
    model="haiku",          # opus | sonnet | haiku
    max_tokens=256,
)
print(result["text"])         # "OK"
print(result["cost_usd"])     # custo da chamada (debitado da assinatura)
```

O backend passa o prompt via **stdin** e recebe JSON na stdout. Não usa shell string interpolation — sem risco de injeção.

### `core/memory_system.py`

Memória persistente em SQLite com 4 tabelas.

```python
from core.memory_system import MemorySystem

memory = MemorySystem()  # padrão: memory/workspace.db
# ou: MemorySystem(db_path="/caminho/custom.db")

# Salvar interação
memory.save_interaction(
    user_message="Como implementar singleton?",
    assistant_response="...",
    task_type="code",
    model_used="claude-opus-4-7",
    tokens_used=450,
)

# Recuperar histórico
interactions = memory.get_recent_interactions(limit=10)
for i in interactions:
    print(i["user_message"], i["task_type"], i["tokens_used"])

# Preferências do usuário
memory.save_preference("language", "python")
pref = memory.get_preference("language")  # "python"

# Contexto de projeto
memory.save_project_context("stack", "FastAPI + SQLAlchemy")
```

### `core/skill_manager.py`

Biblioteca de habilidades injetáveis no system prompt.

```python
from core.skill_manager import SkillManager, Skill

skills = SkillManager()

# Registrar skill
skills.save_skill(Skill(
    name="python_refactor",
    description="Refatora código Python para seguir PEP8 e boas práticas",
    template="Refatore o código a seguir: {code}",
    tags=["python", "refactor", "clean-code"],
))

# Buscar skills relevantes para uma tarefa
injection = skills.build_skill_injection_text(
    query="refatore esse código Python",
    top_k=3,
)
# injection → texto pronto para incluir no system prompt

# Listar todas as skills
all_skills = skills.list_skills()
```

---

## Multi-agentes e Orquestração

O `OrchestratorAgent` usa GPT-4-class (Opus 4.7) para decompor tarefas e despacha para agentes especializados em **paralelo** via `ThreadPoolExecutor`.

```python
from core.agents.orchestrator_agent import OrchestratorAgent

agent = OrchestratorAgent()
result = agent.run(
    task="Crie um módulo de autenticação JWT com testes e documentação",
    parallel=True,
)

print(result["consolidated_result"])
print(result["subtasks_count"])   # número de subtarefas
print(result["total_tokens"])     # tokens totais consumidos
```

**Via CLI:**
```bash
python3 cli.py orchestrate "Analise o repositório e gere um relatório de qualidade de código"
```

**Agentes de referência incluídos no template:**

| Agente | `task_type` | Modelo | Especialidade |
|---|---|---|---|
| `CoderAgent` | `code` | Opus 4.7 | Escrita e refatoração de código |
| `AnalysisAgent` | `analysis` | Opus 4.7 | Análise técnica e comparações |
| `ExecutorAgent` | `execution` | Haiku 4.5 | Execução de tarefas operacionais |
| `ValidatorAgent` | `validation` | Sonnet 4.6 | Revisão e validação de resultados |
| `WorldBankRiskAgent` | `analysis` | Opus 4.7 | Dados de risco soberano via World Bank |
| `WikidataEntityAgent` | `analysis` | Opus 4.7 | Resolução de entidades via Wikidata |
| `OpenAlexEnrichmentAgent` | `analysis` | Opus 4.7 | Enriquecimento de leads via OpenAlex |
| `ProposalAgent` | `orchestration` | Opus 4.7 | Geração de propostas comerciais de exemplo |
| `LeadReportAgent` | `analysis` | Opus 4.7 | Relatórios executivos de leads de exemplo |

### Criar um agente customizado

```python
from core.agents.base_agent import BaseAgent
from core.claude_client import ClaudeClient, make_client

class DocumentationAgent(BaseAgent):
    name = "DocumentationAgent"
    role_description = "Você é especialista em documentação técnica. Escreva docs claros e precisos."
    task_type = "analysis"

    def run(self, task: str, **kwargs) -> dict:
        return self._call_api(task=task)

# Usar com backend explícito
client = make_client()
agent = DocumentationAgent(client=client)
result = agent.run(task="Documente essa função: def parse_json(s): ...")
print(result["text"])
```

---

## REST API

```bash
# Iniciar servidor
python3 api/app.py
# Disponível em: http://localhost:5000
```

### Endpoints

#### `GET /health`
```bash
curl http://localhost:5000/health
# {"status": "ok", "version": "2.0"}
```

#### `POST /api/chat`
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "O que é TDD?", "task_type": "analysis"}'

# Resposta:
# {
#   "text": "TDD (Test-Driven Development)...",
#   "model": "claude-opus-4-7",
#   "task_type": "analysis",
#   "input_tokens": 12,
#   "output_tokens": 184
# }
```

#### `POST /api/skills`
```bash
curl -X POST http://localhost:5000/api/skills \
  -H "Content-Type: application/json" \
  -d '{"name": "py_lint", "description": "Analisa lint Python", "template": "Analise: {code}", "tags": ["python"]}'
```

#### `GET /api/skills`
```bash
curl http://localhost:5000/api/skills
```

#### `GET /api/interactions?limit=10`
```bash
curl "http://localhost:5000/api/interactions?limit=5"
```

---

## MCP Servers

O workspace inclui dois servidores MCP (Model Context Protocol) em TypeScript.

### Compilar

```bash
npm install
npx tsc
# Gera: dist/mcp/servers/git-server.js e dist/mcp/servers/filesystem-server.js
```

### `git-server` — Ferramentas git

| Tool | Parâmetros | Descrição |
|---|---|---|
| `git_status` | `repo_path` | Status do repositório |
| `git_log` | `repo_path`, `limit` | Histórico de commits |
| `git_diff` | `repo_path`, `file` | Diff de arquivo específico |
| `git_branches` | `repo_path` | Listar branches |

```bash
# Executar diretamente
node dist/mcp/servers/git-server.js

# Usar via MCPManager
python3 -c "
from api.mcp_manager import MCPManager
mgr = MCPManager()
mgr.start_server('git', 'node dist/mcp/servers/git-server.js')
"
```

**Segurança:** todos os comandos git usam `spawnSync` com array de argumentos — sem interpolação em string de shell, sem risco de injeção via parâmetro `file`.

### `filesystem-server` — Leitura de arquivos

Expõe ferramentas de leitura segura do filesystem via protocolo MCP.

```bash
# Executar diretamente
WORKSPACE_ROOT="$(pwd)" node dist/mcp/servers/filesystem-server.js

# Usar via MCPManager
python3 -c "
from api.mcp_manager import MCPManager
mgr = MCPManager.default_workspace_manager(workspace_root='$(pwd)')
mgr.start_all()
print(mgr.is_running('filesystem'))
print(mgr.is_running('git'))
mgr.stop_all()
"
```

**Segurança:** o servidor bloqueia path traversal fora de `WORKSPACE_ROOT`.

---

## Workflow Engine

Automatize sequências multi-passo com YAML.

### Definição de workflow (YAML)

```yaml
name: daily_standup
trigger: manual
description: "Gera relatório diário de standup"
steps:
  - name: analyze_commits
    task: "Analise os últimos commits e liste as mudanças"
    agent: analysis
    output_var: commits_summary

  - name: generate_report
    task: "Com base nas mudanças, gere o standup de hoje"
    agent: chat
    depends_on: [analyze_commits]
    output_var: standup_text
```

### Executar workflow

```python
from workflows.engine import WorkflowEngine
from core.memory_system import MemorySystem

engine = WorkflowEngine(memory=MemorySystem())
workflow = engine.load("workflows/examples/daily_standup.yaml")
results = engine.run(workflow)

for step_name, output in results.items():
    print(f"[{step_name}]", output.get("text", ""))
```

---

## Testes

```bash
# Todos os testes (113)
venv/bin/pytest tests/ -v

# Por módulo
venv/bin/pytest tests/test_claude_code_backend.py -v   # 7 testes — ClaudeCodeBackend
venv/bin/pytest tests/test_claude_client.py -v         # 7 testes — ClaudeClient
venv/bin/pytest tests/test_claude_client_backend.py -v # 6 testes — make_client + backend
venv/bin/pytest tests/test_memory_system.py -v         # 6 testes — MemorySystem
venv/bin/pytest tests/test_skill_manager.py -v         # 5 testes — SkillManager
venv/bin/pytest tests/test_agents.py -v                # 4 testes — Agentes especializados
venv/bin/pytest tests/test_orchestrator.py -v          # 2 testes — OrchestratorAgent
venv/bin/pytest tests/test_integration_e2e.py -v       # 3 testes — E2E com mock de backend
venv/bin/pytest tests/test_error_handler.py -v         # 4 testes — Retry + backoff
venv/bin/pytest tests/test_oauth_manager.py -v         # 5 testes — OAuthManager
venv/bin/pytest tests/test_mcp_servers.py -v           # 4 testes — MCP servers

# Com cobertura (requer pytest-cov)
pip install pytest-cov
venv/bin/pytest tests/ --cov=core --cov-report=term-missing
```

**Padrão de mock usado nos testes de integração:**

```python
from unittest.mock import MagicMock
from core.claude_client import ClaudeClient

mock_backend = MagicMock()
mock_backend.complete.return_value = {
    "text": "resposta mock",
    "model": "sonnet",
    "input_tokens": 10,
    "output_tokens": 20,
    "cost_usd": 0.0,
}

client = ClaudeClient(backend=mock_backend, memory=memory)
```

Todos os testes são **offline** — nenhum faz chamada real ao Claude. O `ClaudeCodeBackend` é mockado via `@patch("subprocess.run")`.

---

## Variáveis de ambiente

Arquivo: `.env` (copiar de `.env.example`)

| Variável | Padrão | Descrição |
|---|---|---|
| `BACKEND` | _(auto)_ | `claude-code` \| `codex` \| `api` \| _(omitir para auto-detect)_ |
| `FALLBACK_CHAIN_ENABLED` | `true` | Ativa cadeia de fallback entre backends |
| `CODEX_MODEL` | `gpt-5.4-mini` | Modelo Codex quando `BACKEND=codex` |
| `ANTHROPIC_API_KEY` | — | API key Anthropic (necessário se `BACKEND=api`) |
| `ANTHROPIC_CLIENT_ID` | — | OAuth client ID (uso experimental) |
| `ANTHROPIC_CLIENT_SECRET` | — | OAuth client secret (opcional, PKCE público) |
| `DATABASE_URL` | `sqlite:///memory/workspace.db` | URL do banco de dados principal |
| `OAUTH_DB_URL` | `sqlite:///memory/oauth_tokens.db` | URL do banco de tokens OAuth |
| `POSTGRES_HOST` | `localhost` | Host PostgreSQL (Docker) |
| `POSTGRES_PORT` | `5432` | Porta PostgreSQL |
| `POSTGRES_DB` | `workspace` | Nome do banco PostgreSQL |
| `POSTGRES_USER` | `workspace` | Usuário PostgreSQL |
| `POSTGRES_PASSWORD` | `changeme` | Senha PostgreSQL |
| `REDIS_URL` | `redis://localhost:6379` | URL Redis |
| `GITHUB_TOKEN` | — | Token GitHub (integração futura) |
| `DEBUG` | `false` | Modo debug |
| `LOG_LEVEL` | `INFO` | Nível de log |
| `MAX_TOKENS_PER_REQUEST` | `4096` | Limite de tokens por chamada |
| `DAILY_COST_LIMIT_USD` | `50.0` | Limite diário de custo (modo API) |
| `KEEPALIVE_ENDPOINTS` | endpoints internos | JSON array `[{"name":"x","url":"..."}]` |
| `KEEPALIVE_INTERVAL` | `300` | Intervalo keepalive em segundos |
| `PROPOSALS_DIR` | `~/propostas` | Diretório de saída do `ProposalAgent` de exemplo; sobrepor com `PROPOSALS_DIR=/custom/path` |

---

## Referência de comandos

```bash
# CLI
python3 cli.py chat "<prompt>"                          # Chat com roteamento automático
python3 cli.py chat "<prompt>" --task-type code         # Forçar task type
python3 cli.py orchestrate "<tarefa>"                   # Orquestração multi-agente
python3 cli.py orchestrate "<tarefa>" --sequential      # Forçar execução sequencial
python3 cli.py history                                  # Últimas 10 interações
python3 cli.py history --limit 50                       # Últimas N interações
python3 cli.py stats                                    # Estatísticas do workspace

# Agentes especializados
python3 cli.py proposal "Empresa XYZ" "saúde" "acelerar vendas" --orcamento "15k"
python3 cli.py lead-report demo
python3 cli.py lead-report '[{"empresa":"XYZ","pais":"BR","setor":"tech"}]'
python3 cli.py risk "análise" --country BR
python3 cli.py entity "consulta" --entity "Petrobras"
python3 cli.py enrich "análise" --account "USP"

# Ambiente
source activate_env.sh                                  # Ativar venv + carregar .env
source venv/bin/activate                                # Ativar venv apenas

# Testes
venv/bin/pytest tests/ -q                              # Suite completa (rápido)
venv/bin/pytest tests/ -v                              # Suite completa (verbose)

# API
python3 api/app.py                                     # Iniciar Flask na porta 5000

# Infraestrutura (opcional)
docker compose up -d                                   # Subir PostgreSQL + Redis
docker compose down                                    # Parar infraestrutura

# MCP
npx tsc                                                # Compilar TypeScript
node dist/mcp/servers/git-server.js                   # Iniciar MCP git server
```

---

## Tutorial para agentes autônomos

Esta seção descreve como outro agente (Claude Code, GPT, Gemini, etc.) deve interagir com este workspace.

### Bootstrap recomendado

Consulte o checklist em [`docs/bootstrap-checklist.md`](docs/bootstrap-checklist.md).
Ele concentra o fluxo de clone, instalação, configuração, infraestrutura local, validação da API, CLI, MCP e testes.

### Smoke test mínimo

Depois do bootstrap, valide um backend explícito:

```bash
. venv/bin/activate && BACKEND=codex python cli.py chat "Responda apenas OK." --task-type chat
```

Se preferir `claude-code`, use o backend correspondente e confirme que `claude` está autenticado.

### Como extender o sistema

**Adicionar novo agente:**

1. Criar `core/agents/meu_agente.py` herdando de `BaseAgent`
2. Definir `name`, `role_description`, `task_type`
3. Sobrescrever `run()` se precisar de lógica customizada
4. Registrar em `AGENT_MAP` do `orchestrator_agent.py` se quiser disponível via orquestração
5. Escrever testes em `tests/test_agents.py` usando `MagicMock` no backend

**Adicionar nova skill:**

```python
from core.skill_manager import SkillManager, Skill
skills = SkillManager()
skills.save_skill(Skill(
    name="minha_skill",
    description="O que essa skill faz (usado para busca por relevância)",
    template="Template com {variavel} opcional",
    tags=["tag1", "tag2"],
))
```

**Usar o `ClaudeClient` diretamente como backend de outro sistema:**

```python
from core.claude_client import ClaudeClient, make_client, TaskType

client = make_client()  # auto-detect: CLI ou API key

# Passagem de backend explícito para testes
from core.claude_code_backend import ClaudeCodeBackend
backend = ClaudeCodeBackend()
client = ClaudeClient(backend=backend)

# Interface completa
result = client.chat(
    prompt="...",
    system="Contexto do sistema",
    task_type=TaskType.CODE,
    max_tokens=4096,
)
# result: {text, model, task_type, input_tokens, output_tokens}
```

### Trocar de backend em runtime

```python
import os
os.environ["BACKEND"] = "claude-code"   # força CLI
# ou
os.environ["BACKEND"] = "api"           # força API key
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-..."

from core.claude_client import make_client
client = make_client()
```

### Troubleshooting para agentes

| Sintoma | Causa provável | Solução |
|---|---|---|
| `ClaudeCodeError: claude CLI retornou código 1` | CLI não autenticado | `claude login` |
| `RuntimeError: BACKEND=claude-code mas claude CLI não encontrado` | `claude` não está no PATH | `npm install -g @anthropic-ai/claude-code` |
| `RuntimeError: Nenhum backend configurado` | Nem CLI nem API key disponível | Definir `BACKEND=claude-code` no `.env` |
| `ModuleNotFoundError` | venv não ativado | `source venv/bin/activate` |
| `anthropic.RateLimitError` | Rate limit da API | O `RobustErrorHandler` retenta automaticamente |
| `json.JSONDecodeError` no backend | Versão antiga do CLI | Atualizar: `npm update -g @anthropic-ai/claude-code` |

---

## Keepalive (backends remotos)

O script `scripts/keepalive.sh` mantém backends remotos ativos com pings periódicos (útil no Render free tier que hiberna após inatividade).

```bash
# Iniciar em background
./scripts/keepalive.sh
# Log em: /tmp/agents-workspace-keepalive.log

# Acompanhar log
tail -f /tmp/agents-workspace-keepalive.log

# Configurar endpoints personalizados (JSON)
export KEEPALIVE_ENDPOINTS='[{"name":"MyAPI","url":"https://myapi.onrender.com/health"}]'
export KEEPALIVE_INTERVAL=60   # intervalo em segundos (padrão: 300)
```

| Variável | Padrão | Descrição |
|---|---|---|
| `KEEPALIVE_ENDPOINTS` | endpoints internos | JSON array de `{name, url}` a pingar |
| `KEEPALIVE_INTERVAL` | `300` | Intervalo entre pings em segundos |

---

## Histórico de versões

| Versão | Commits | Destaques |
|---|---|---|
| `v2.1.0` | `8a283fd` | Claude Code CLI backend, sem API key obrigatória |
| `v2.0.0` | — | OAuth PKCE, multi-agentes, orquestração paralela |

---

## Licença

Uso interno. Todos os direitos reservados.
