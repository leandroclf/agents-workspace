# Operations Guide

## Running the CLI

```bash
source venv/bin/activate

# Chat
python cli.py chat "pergunta"

# Agents
python cli.py proposal "Empresa XYZ" "saúde" "acelerar vendas" --orcamento "15k"
python cli.py lead-report demo
python cli.py lead-report '[{"empresa":"XYZ","pais":"BR","setor":"tech"}]'
python cli.py risk "análise" --country BR
python cli.py entity "consulta" --entity "Petrobras"
python cli.py enrich "análise" --account "USP"
```

## Backend Selection

| Env Var | Value | Behavior |
|---|---|---|
| BACKEND | claude-code | Claude CLI (primary) |
| BACKEND | codex | Codex CLI |
| BACKEND | api | Anthropic API key |
| (unset) | — | Auto-detect: claude → codex → api |
| FALLBACK_CHAIN_ENABLED | true | Enable fallback chain |

## Keepalive (Render backends)

```bash
# Start in background
./scripts/keepalive.sh

# Check log
tail -f /tmp/lf-keepalive.log

# Custom endpoints
export KEEPALIVE_ENDPOINTS='[{"name":"MyAPI","url":"https://myapi/health"}]'
export KEEPALIVE_INTERVAL=60  # seconds
```

## Running Tests

```bash
./venv/bin/pytest tests/ -q          # all tests
./venv/bin/pytest tests/ -v -k codex # specific
```

## API Server

```bash
BACKEND=claude-code uvicorn api.app:app --reload
```

## Workflow Engine

```bash
python -c "from workflows.engine import WorkflowEngine; e = WorkflowEngine(); print(e)"
```

## Deferred Features

### `observability/telemetry.py` — OpenTelemetry

# DEFERRED: not in production path

`telemetry.py` define `setup_telemetry()` com TracerProvider e MeterProvider via OpenTelemetry,
mas **não é importado em nenhum módulo do projeto** (cli.py, api/app.py, core/*). A função
`setup_telemetry()` é chamada apenas dentro do próprio arquivo em um bloco `if __name__ == "__main__"`
(para testes manuais). Decisão: manter o arquivo para uso futuro, sem ativação automática.

Para ativar:
```python
# Em cli.py ou api/app.py:
from observability.telemetry import setup_telemetry
setup_telemetry("claude-workspace")
```

### `core/rate_limiter.py` — RateLimiter

# DEFERRED: not in production path

`RateLimiter` é definido em `core/rate_limiter.py` com controle de janela deslizante e limite
diário de custo, mas **não é importado nem instanciado em nenhum módulo de produção**. A proteção
contra rate limit é feita pelo `RobustErrorHandler` (retry com backoff exponencial). Decisão:
manter o arquivo para uso futuro, sem ativação automática.

Para ativar:
```python
# Em core/claude_client.py ou core/claude_code_backend.py:
from core.rate_limiter import RateLimiter
limiter = RateLimiter(max_requests=60, window_seconds=60)
if not limiter.check_and_consume():
    raise RuntimeError("Rate limit exceeded")
```
