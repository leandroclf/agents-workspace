# 🚀 Quick Start — Agents Workspace para Análise de Código

Você configurou um workspace com **3 agentes especializados em análise**:

## ✅ O que você tem

- **CodeAnalysisAgent**: Análise geral de código, bugs, refactoring, qualidade
- **SecurityAnalysisAgent**: Análise de segurança, vulnerabilidades, OWASP Top 10
- **ArchitectureAnalysisAgent**: Análise arquitetural, padrões, escalabilidade
- **Backend**: Claude Code CLI (assinatura claude.ai, sem custos de API)
- **Memória persistente**: SQLite com histórico de análises
- **124 testes passando**: Confiança no código

---

## 🎯 Próximos Passos

### 1️⃣ Ativar o ambiente

```bash
cd /tmp/agents-workspace
source venv/bin/activate
```

### 2️⃣ Analisar um arquivo

```bash
# Analisar um arquivo Python
python3 analyze_code.py --file core/claude_client.py --type code

# Analisar para vulnerabilidades de segurança
python3 analyze_code.py --file api/app.py --type security

# Analisar arquitetura
python3 analyze_code.py --file core/agents/base_agent.py --type architecture
```

### 3️⃣ Analisar código inline

```bash
python3 analyze_code.py --code "
def process_data(x):
    return x.split(',')[0] if x else None
" --type code --task "Encontre bugs e sugira refactoring"
```

### 4️⃣ Ver histórico de análises

```bash
source venv/bin/activate
python3 -c "
from core.memory_system import MemorySystem
mem = MemorySystem()
for i in mem.get_recent_interactions(limit=5):
    print(f\"[{i['task_type']}] {i['user_message'][:60]}...\")
"
```

---

## 📊 Exemplos de Casos de Uso

### Análise de Código Legacy

```bash
python3 analyze_code.py --file my_project/legacy_module.py --type code \
  --task "Este módulo tem 10 anos. Há padrões desatualizados ou boas práticas não seguidas?"
```

### Revisão de Segurança

```bash
python3 analyze_code.py --file src/auth.py --type security \
  --task "Revise este código de autenticação. Há vulnerabilidades?"
```

### Avaliação de Design

```bash
python3 analyze_code.py --file src/domain/ --type architecture \
  --task "Analise a arquitetura da camada de domínio. Está bem estruturada?"
```

---

## 🔧 Uso Programático (em seu código)

```python
from core.agents.code_analysis_agent import CodeAnalysisAgent, SecurityAnalysisAgent
from core.memory_system import MemorySystem

# Setup
memory = MemorySystem()
analyst = CodeAnalysisAgent(memory=memory)
security_expert = SecurityAnalysisAgent(memory=memory)

# Análise de código
code = open("my_file.py").read()
result = analyst.run(task="Detecte problemas", code=code)
print(result["text"])

# Análise de segurança
vuln_result = security_expert.run(task="Revise segurança", code=code)
print(vuln_result["text"])
```

---

## 🎓 Aprender Mais

- **Arquitetura**: Leia `README.md` (seção "Arquitetura")
- **Agentes**: Veja `AGENTS.md` (regras de edição e stack)
- **CLI**: `python3 cli.py --help`
- **Testes**: `pytest -v` (124 testes cobrindo todo o sistema)

---

## ⚡ Dicas Rápidas

| Tarefa | Comando |
|--------|---------|
| Ativar venv | `source venv/bin/activate` |
| Rodar testes | `pytest -q` |
| Ver histórico | `python3 cli.py history` |
| Ver stats | `python3 cli.py stats` |
| API REST | `python3 api/app.py` (porta 5000) |
| MCP Git Server | `node dist/mcp/servers/git-server.js` |

---

## 🐛 Troubleshooting

**Erro: `claude CLI não encontrado`**
```bash
npm install -g @anthropic-ai/claude-code
claude login
```

**Erro: `ModuleNotFoundError`**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

**Erro: `JSON decode error`**
→ Atualize o CLI: `npm update -g @anthropic-ai/claude-code`

---

**Pronto para começar? Execute:**
```bash
source venv/bin/activate
python3 analyze_code.py --code "def hello(name): return f'Hello {name}!'" --type code
```

Happy analyzing! 🎉
