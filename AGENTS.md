# AGENTS.md

## Propósito

Este repositório é um workspace reutilizável para agentes, com backend abstrato, memória persistente, CLI, API Flask, servidores MCP e workflows YAML. As instruções abaixo servem para manter consistência ao editar, testar e operar o projeto.

## Precedência Local

1. Este arquivo tem precedência sobre instruções globais quando houver conflito.
2. Se houver divergência entre documentação e comportamento observado, priorize o comportamento validado por testes.
3. Não alterar arquivos gerados ou dependências sem necessidade clara.

## Stack do Projeto

- Runtime principal: Python 3.11+
- Dependências de CLI/servidores MCP: Node.js 18+
- Serviços locais: PostgreSQL e Redis via Docker Compose
- Backend de execução: Claude Code CLI, Codex CLI ou Anthropic API

## Estrutura Relevante

- `cli.py`: interface principal da linha de comando
- `core/`: clientes, backends, memória, agentes e lógica de orquestração
- `api/`: Flask API e integração MCP
- `mcp/`: servidores TypeScript para filesystem e git
- `workflows/`: engine e exemplos YAML
- `tests/`: suíte automatizada

## Configuração Local

1. Copiar `.env.example` para `.env`.
2. Definir apenas um backend primário por vez, preferencialmente via variável `BACKEND`.
3. Usar `BACKEND=codex` quando houver `codex` instalado e autenticado no ambiente.
4. Usar `BACKEND=claude-code` quando houver `claude` disponível.
5. Usar `BACKEND=api` somente quando houver `ANTHROPIC_API_KEY` válida.

## Comandos Básicos

```bash
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
npm install
npx tsc --noEmit
python cli.py --help
python cli.py stats
pytest -q
docker compose up -d
docker compose ps
```

## Validação

- Rodar testes relevantes antes de concluir mudanças.
- Para ajustes em backend, executar testes específicos do módulo afetado e depois `pytest -q`.
- Para mudanças em CLI, validar pelo menos `python cli.py --help` e um comando funcional com backend definido.
- Para mudanças em Docker Compose, verificar `docker compose ps` e, se necessário, logs dos serviços.

## Regras de Edição

- Não commitar `.env`, credenciais ou tokens.
- Manter compatibilidade com o fluxo de fallback de backends.
- Preferir mudanças pequenas e verificáveis.
- Se um teste falhar por ambiente, documentar o motivo e isolar o problema antes de alterar lógica de negócio.

## Observações Operacionais

- O projeto já usa portas padrão `5432` e `6379` para Postgres e Redis.
- Se `5432` estiver ocupada, ajustar o ambiente local antes de alterar o Compose.
- O backend Codex lê `CODEX_MODEL` por execução, então mudanças em ambiente devem ser refletidas sem reiniciar o processo Python.
- A suíte de testes deve permanecer verde após qualquer ajuste funcional.

## Git E SSH

- Este repositório deve usar o alias SSH `github-hotmail` para `origin`.
- A URL esperada é `git@github-hotmail:leandroclf/agents-workspace.git`.
- A identidade SSH correspondente é `~/.ssh/id_ed25519_hotmail`.
- Antes de fazer push, confirmar `git remote -v` se houver qualquer dúvida sobre a conta usada.
