from core.agents.base_agent import BaseAgent
from core.claude_client import TaskType


class CodeAnalysisAgent(BaseAgent):
    """
    Agente especializado em análise de código.
    Detecta problemas, sugere refactorings, analisa qualidade e segurança.
    """

    name = "CodeAnalysisAgent"
    role_description = """Você é um especialista em análise de código com expertise em:
- Detecção de bugs, problemas de performance e vulnerabilidades
- Refactoring e boas práticas (SOLID, DRY, KISS)
- Análise arquitetural (padrões de design, separação de responsabilidades)
- Qualidade de código (complexidade ciclomática, coverage, maintainability)
- Segurança (injection, XSS, SQL injection, autenticação, criptografia)
- Python, JavaScript/TypeScript, Go, Java, Rust

Ao analisar código:
1. Identifique os problemas principais (severidade: crítica, alta, média, baixa)
2. Explique o impacto de cada problema
3. Sugira soluções concretas com exemplos
4. Priorize por severidade e esforço"""

    task_type = "analysis"
    model = "claude-opus-4-7"  # Melhor para análise profunda

    def run(self, task: str, code: str = "", **kwargs) -> dict:
        """
        Executar análise de código.

        Args:
            task: Descrição do que analisar (ex: "bugs", "performance", "segurança")
            code: Código para analisar (opcional, pode estar no task)

        Returns:
            dict com text, model, agent, tokens
        """
        if code:
            extra = f"\n\n**Código para analisar:**\n```\n{code}\n```"
        else:
            extra = ""

        return self._call_api(task=task, extra_context=extra, max_tokens=8192)


class SecurityAnalysisAgent(BaseAgent):
    """
    Agente especializado em análise de segurança.
    Focado em vulnerabilidades, OWASP Top 10, práticas de segurança.
    """

    name = "SecurityAnalysisAgent"
    role_description = """Você é um especialista em segurança de aplicações com foco em:
- OWASP Top 10 (injection, XSS, CSRF, insecure data exposure, etc)
- Cryptografia e criptografia de dados sensíveis
- Autenticação e autorização
- Segurança de APIs REST/GraphQL
- Segurança de containers e orquestração
- Gerenciamento de secrets e credenciais
- Análise de dependências vulneráveis

Sempre comece com uma visão geral do risco, depois detalhe cada vulnerabilidade encontrada."""

    task_type = "analysis"
    model = "claude-opus-4-7"

    def run(self, task: str, code: str = "", **kwargs) -> dict:
        if code:
            extra = f"\n\n**Código para analisar segurança:**\n```\n{code}\n```"
        else:
            extra = ""

        return self._call_api(task=task, extra_context=extra, max_tokens=8192)


class ArchitectureAnalysisAgent(BaseAgent):
    """
    Agente especializado em análise de arquitetura.
    Avalia design, escalabilidade, manutenibilidade, padrões.
    """

    name = "ArchitectureAnalysisAgent"
    role_description = """Você é um arquiteto de software sênior especializado em:
- Padrões de design (MVC, MVVM, microserviços, serverless, etc)
- Escalabilidade e performance architecture
- Separação de responsabilidades e coesão
- Trade-offs tecnológicos
- Manutenibilidade de longo prazo
- Cloud-native design
- Event-driven vs request-response arquiteture

Ao analisar, contextualize dentro dos objetivos do projeto e constraints."""

    task_type = "architecture"
    model = "claude-opus-4-7"

    def run(self, task: str, context: str = "", **kwargs) -> dict:
        if context:
            extra = f"\n\n**Contexto arquitetural:**\n{context}"
        else:
            extra = ""

        return self._call_api(task=task, extra_context=extra, max_tokens=8192)
