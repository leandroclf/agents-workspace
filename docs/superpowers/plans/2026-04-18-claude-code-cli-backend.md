# Agents Workspace Foundation Notes

> Documento de referência para o template base.  
> O objetivo deste repositório é servir como ponto de partida para novos projetos
> com runtime de agentes, memória persistente, CLI, API, workflows e backend
> abstrato.

## O que este template oferece

- `ClaudeClient` com seleção de backend por `BACKEND`
- fallback entre `claude-code`, `codex` e `api`
- memória persistente em SQLite
- `SkillManager` para injeção de habilidades relevantes
- `OrchestratorAgent` para decompor tarefas em subtarefas
- CLI, REST API e `WorkflowEngine` como pontos de entrada
- keepalive para backends remotos

## Como adaptar para um novo projeto

1. Clone este repositório e crie uma nova branch.
2. Ajuste `.env.example` e crie o `.env` do novo projeto.
3. Remova ou substitua os agentes de exemplo que não fizerem sentido.
4. Atualize `README.md` e `OPERATIONS.md` com o novo domínio.
5. Rode a suíte de testes e confirme os contratos públicos.

## Convenções do template

- Prefira contratos pequenos e testáveis.
- Mantenha a seleção de backend centralizada.
- Documente qualquer agente novo como exemplo ou como parte do domínio real.
- Preserve a separação entre runtime genérico e comportamento específico do projeto.
