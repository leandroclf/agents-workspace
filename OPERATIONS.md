# Operações do Workspace

## Inicializar
source ~/claude-workspace/activate_env.sh

## Comandos principais
python3 cli.py chat "sua pergunta"
python3 cli.py chat "refatore main.py" --task-type code
python3 cli.py orchestrate "tarefa complexa"
python3 cli.py history --limit 20
python3 cli.py stats

## Rodar API REST
python3 api/app.py
# Acesso: http://localhost:5000/health

## Rodar infraestrutura (PostgreSQL + Redis)
docker-compose up -d postgres redis

## Rodar testes
pytest tests/ -v

## Configuração
cp .env.example .env
# Editar .env e adicionar ANTHROPIC_API_KEY=sk-ant-...

## Troubleshooting
- API key inválida: verifique .env -> ANTHROPIC_API_KEY
- SQLite lock: reinicie o processo
- RateLimitError: o sistema retenta automaticamente com backoff exponencial
- ModuleNotFoundError: ative o venv -> source venv/bin/activate
