import json
from dataclasses import dataclass, field
from typing import Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.agents.base_agent import BaseAgent
from core.agents.coder_agent import CoderAgent
from core.agents.analysis_agent import AnalysisAgent
from core.agents.executor_agent import ExecutorAgent
from core.agents.validator_agent import ValidatorAgent
from core.agents.worldbank_agent import WorldBankRiskAgent
from core.agents.wikidata_agent import WikidataEntityAgent
from core.agents.openalex_agent import OpenAlexEnrichmentAgent
from core.agents.proposal_agent import ProposalAgent
from core.agents.lead_report_agent import LeadReportAgent
from core.memory_system import MemorySystem
from core.skill_manager import SkillManager


@dataclass
class SubTask:
    id: str
    description: str
    agent_type: str
    dependencies: list[str] = field(default_factory=list)
    status: str = "pending"
    result: Optional[dict] = None


@dataclass
class TaskPlan:
    goal: str
    subtasks: list[SubTask]


AGENT_MAP = {
    "coder":     CoderAgent,
    "analysis":  AnalysisAgent,
    "executor":  ExecutorAgent,
    "validator": ValidatorAgent,
    "worldbank": WorldBankRiskAgent,
    "wikidata":  WikidataEntityAgent,
    "openalex":  OpenAlexEnrichmentAgent,
    "proposal":  ProposalAgent,
    "lead-report": LeadReportAgent,
}


AGENT_DESCRIPTIONS = {
    "coder":       "Escreve, refatora e revisa código. Input: descrição da tarefa de código. Output: código gerado.",
    "analysis":    "Analisa dados, textos ou resultados e produz insights. Input: dados/texto. Output: análise.",
    "executor":    "Executa comandos, scripts e tarefas genéricas. Input: comando ou tarefa. Output: resultado.",
    "validator":   "Valida resultados, testes e qualidade de código. Input: artefato a validar. Output: relatório.",
    "worldbank":   "Consulta indicadores de risco econômico do Banco Mundial por país. Input: país. Output: indicadores.",
    "wikidata":    "Enriquece entidades com dados do Wikidata (empresas, pessoas, lugares). Input: nome da entidade. Output: dados estruturados.",
    "openalex":    "Busca e enriquece dados acadêmicos via OpenAlex. Input: tema ou DOI. Output: publicações/autores.",
    "proposal":    "Gera proposta comercial personalizada em markdown para um prospect B2B. Input: cliente, segmento, objetivo, orçamento. Output: {text, file, cliente}",
    "lead-report": "Gera relatório executivo de leads com ranking de prioridade, risco por país e recomendações. Input: JSON list de leads [{empresa, pais, setor}] ou 'demo'. Output: relatório em texto",
}

_AGENT_LIST = "\n".join(f"  - {k}: {v}" for k, v in AGENT_DESCRIPTIONS.items())


class OrchestratorAgent(BaseAgent):
    name = "OrchestratorAgent"
    model = "claude-opus-4-7"
    task_type = "orchestration"
    role_description = f"""Você é um orquestrador de tarefas de alto nível.
Dada uma tarefa complexa, decomponha-a em subtarefas e delegue para agentes especializados.

Agentes disponíveis:
{_AGENT_LIST}

Quando solicitado a decompor, responda em JSON:
{{
  "goal": "...",
  "subtasks": [
    {{"id": "1", "description": "...", "agent_type": "<um dos agentes acima>", "dependencies": []}}
  ]
}}"""

    def decompose(self, task: str) -> TaskPlan:
        result = self._call_api(
            task=f"Decomponha esta tarefa em subtarefas JSON: {task}",
            max_tokens=2000
        )
        text = result["text"]
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            data = json.loads(text[start:end])
            subtasks = [SubTask(**st) for st in data.get("subtasks", [])]
            return TaskPlan(goal=data.get("goal", task), subtasks=subtasks)
        except Exception:
            return TaskPlan(goal=task, subtasks=[
                SubTask(id="1", description=task, agent_type="executor")
            ])

    def _execute_subtask(self, subtask: SubTask, context: str = "") -> dict:
        agent_class = AGENT_MAP.get(subtask.agent_type, ExecutorAgent)
        agent = agent_class(memory=self.memory, skill_manager=self.skill_manager)
        result = agent.run(args=[subtask.description])
        # Normalise: some agents return str, others return dict
        if isinstance(result, str):
            return {"text": result, "agent": subtask.agent_type,
                    "input_tokens": 0, "output_tokens": 0}
        return result

    def run(self, task: str, parallel: bool = True, **kwargs) -> dict[str, Any]:
        plan = self.decompose(task)
        completed: dict[str, dict] = {}

        if parallel:
            independent = [st for st in plan.subtasks if not st.dependencies]
            with ThreadPoolExecutor(max_workers=4) as pool:
                futures = {pool.submit(self._execute_subtask, st): st for st in independent}
                for future in as_completed(futures):
                    st = futures[future]
                    st.result = future.result()
                    st.status = "done"
                    completed[st.id] = st.result

            dependent = [st for st in plan.subtasks if st.dependencies]
            for st in dependent:
                ctx = "\n".join(completed.get(dep, {}).get("text", "") for dep in st.dependencies)
                st.result = self._execute_subtask(st, context=ctx)
                st.status = "done"
                completed[st.id] = st.result
        else:
            for st in plan.subtasks:
                ctx = "\n".join(completed.get(dep, {}).get("text", "") for dep in st.dependencies)
                st.result = self._execute_subtask(st, context=ctx)
                st.status = "done"
                completed[st.id] = st.result

        consolidation = self._call_api(
            task=f"Consolide os resultados das subtarefas do objetivo: {plan.goal}",
            extra_context="\n\n".join(
                f"### {st.description}\n{st.result.get('text', '')[:500]}"
                for st in plan.subtasks
            ),
            max_tokens=4096
        )
        return {
            "goal": plan.goal,
            "subtasks_count": len(plan.subtasks),
            "subtasks": [
                {"id": st.id, "description": st.description, "agent": st.agent_type,
                 "status": st.status}
                for st in plan.subtasks
            ],
            "consolidated_result": consolidation["text"],
            "total_tokens": sum(
                (st.result or {}).get("input_tokens", 0) +
                (st.result or {}).get("output_tokens", 0)
                for st in plan.subtasks
            ) + consolidation["input_tokens"] + consolidation["output_tokens"],
        }
