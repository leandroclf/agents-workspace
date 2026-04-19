import yaml
import os
from dataclasses import dataclass, field
from typing import Any
from core.claude_client import make_client, TaskType
from core.memory_system import MemorySystem


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
        self.client = make_client(memory=self.memory, api_key=api_key)

    def load(self, yaml_path: str) -> Workflow:
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        steps = [WorkflowStep(**s) for s in data.get("steps", [])]
        return Workflow(
            name=data["name"],
            trigger=data.get("trigger", "manual"),
            steps=steps,
            description=data.get("description", ""),
        )

    def execute(self, workflow: Workflow) -> dict[str, Any]:
        results: dict[str, str] = {}
        task_type_map = {
            "code": TaskType.CODE,
            "analysis": TaskType.ANALYSIS,
            "chat": TaskType.CHAT,
            "validation": TaskType.VALIDATION,
        }
        for step in workflow.steps:
            tt = task_type_map.get(step.agent, TaskType.CHAT)
            context = "\n".join(results.get(dep, "") for dep in step.depends_on)
            prompt = step.task
            if context:
                prompt += f"\n\nContexto das etapas anteriores:\n{context}"
            result = self.client.chat(prompt=prompt, task_type=tt)
            key = step.output_var or step.name
            results[key] = result["text"]
        return {"workflow": workflow.name, "outputs": results}
