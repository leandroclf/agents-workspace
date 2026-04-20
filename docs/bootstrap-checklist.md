# Bootstrap Checklist

Use este checklist para colocar um clone novo do `agents-workspace` em funcionamento.

## 1. Preparar o ambiente

```bash
git clone git@github.com:leandroclf/agents-workspace.git
cd agents-workspace
python3 -m venv venv
. venv/bin/activate
```

## 2. Instalar dependências

```bash
pip install -r requirements.txt
npm install
npx tsc --noEmit
```

## 3. Configurar variáveis

```bash
cp .env.example .env
```

Regras práticas:
- usar `BACKEND=codex` quando o `codex` CLI estiver disponível;
- usar `BACKEND=claude-code` quando o `claude` CLI estiver disponível;
- usar `BACKEND=api` somente com `ANTHROPIC_API_KEY` válida.

## 4. Subir infraestrutura local

```bash
docker compose up -d
docker compose ps
```

## 5. Validar a API

```bash
python3 api/app.py
curl http://localhost:5000/health
curl http://localhost:5000/api/stats
```

## 6. Validar a CLI

```bash
python cli.py stats
BACKEND=codex python cli.py chat "Responda apenas OK." --task-type chat
```

## 7. Validar MCP

```bash
npx tsc
WORKSPACE_ROOT="$(pwd)" node dist/mcp/servers/filesystem-server.js
node dist/mcp/servers/git-server.js
```

## 8. Rodar testes

```bash
pytest -q
```

## 9. Conferir Git

```bash
git remote -v
```

Para este repositório, o remoto deve usar o alias SSH `github-hotmail`.
