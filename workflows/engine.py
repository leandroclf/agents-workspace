import yaml
from dataclasses import dataclass, field
from typing import Any
from core.claude_client import make_client, TaskType
from core.memory_system import MemorySystem
from core.skill_manager import SkillManager
from core.agents.orchestrator_agent import AGENT_MAP


@dataclass
class WorkflowStep:
    name: str
    task: str
    agent: str = "chat"
    depends_on: list[str] = field(default_factory=list)
    output_var: str = ""


@dataclass
class Workflow:
    name: str
    trigger: str
    steps: list[WorkflowStep]
    description: str = ""


class WorkflowEngine:
    def __init__(self, memory: MemorySystem = None, api_key: str = None):
        self.memory = memory or MemorySystem()
        self.skill_manager = SkillManager()
        self.client = make_client(memory=self.memory, api_key=api_key)
        self.task_type_map = {
            "code": TaskType.CODE,
            "analysis": TaskType.ANALYSIS,
            "chat": TaskType.CHAT,
            "validation": TaskType.VALIDATION,
            "architecture": TaskType.ARCHITECTURE,
            "orchestration": TaskType.ORCHESTRATION,
            "summary": TaskType.SUMMARY,
        }

    def load(self, yaml_path: str) -> Workflow:
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        steps = [WorkflowStep(**s) for s in data.get("steps", [])]
        valid_agents = set(self.task_type_map) | set(AGENT_MAP)
        for step in steps:
            if step.agent not in valid_agents:
                raise ValueError(
                    f"Unknown workflow agent '{step.agent}'. "
                    f"Valid agents: {', '.join(sorted(valid_agents))}"
                )
        return Workflow(
            name=data["name"],
            trigger=data.get("trigger", "manual"),
            steps=steps,
            description=data.get("description", ""),
        )

    def execute(self, workflow: Workflow) -> dict[str, Any]:
        results: dict[str, str] = {}
        for step in workflow.steps:
            context = "\n".join(results.get(dep, "") for dep in step.depends_on)
            prompt = step.task
            if context:
                prompt += f"\n\nContexto das etapas anteriores:\n{context}"
            if step.agent in self.task_type_map:
                result = self.client.chat(prompt=prompt, task_type=self.task_type_map[step.agent])
                text = result["text"]
            else:
                agent_cls = AGENT_MAP[step.agent]
                agent = agent_cls(memory=self.memory, skill_manager=self.skill_manager)
                if step.agent in {"proposal", "lead-report"}:
                    result = agent.run(args=[prompt])
                else:
                    result = agent.run(task=prompt)
                text = result.get("text", result) if isinstance(result, dict) else str(result)
            key = step.output_var or step.name
            results[key] = text
        return {"workflow": workflow.name, "outputs": results}
