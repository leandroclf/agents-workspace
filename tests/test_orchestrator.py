import pytest
import sys
import os
from unittest.mock import MagicMock
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.agents.orchestrator_agent import OrchestratorAgent, TaskPlan, SubTask

def test_task_plan_has_subtasks():
    plan = TaskPlan(
        goal="Refatorar e testar main.py",
        subtasks=[
            SubTask(id="1", description="Analisar código atual", agent_type="analysis"),
            SubTask(id="2", description="Refatorar funções", agent_type="coder"),
            SubTask(id="3", description="Escrever testes", agent_type="coder"),
            SubTask(id="4", description="Validar resultado", agent_type="validator"),
        ]
    )
    assert len(plan.subtasks) == 4
    assert plan.subtasks[0].agent_type == "analysis"

def test_subtask_default_status():
    st = SubTask(id="1", description="task", agent_type="coder")
    assert st.status == "pending"
    assert st.result is None

def test_orchestrator_class_attributes():
    orch = OrchestratorAgent.__new__(OrchestratorAgent)
    assert orch.__class__.name == "OrchestratorAgent"
    assert orch.__class__.model == "claude-opus-4-7"
    assert orch.__class__.task_type == "orchestration"


def test_execute_subtask_passes_dependency_context(monkeypatch):
    captured = {}

    class RecorderAgent:
        def __init__(self, memory=None, skill_manager=None):
            pass

        def run(self, task="", **kwargs):
            captured["task"] = task
            return {"text": "ok", "input_tokens": 0, "output_tokens": 0}

    monkeypatch.setitem(
        __import__("core.agents.orchestrator_agent", fromlist=["AGENT_MAP"]).AGENT_MAP,
        "recorder",
        RecorderAgent,
    )
    orch = OrchestratorAgent.__new__(OrchestratorAgent)
    orch.memory = MagicMock()
    orch.skill_manager = MagicMock()

    result = orch._execute_subtask(
        SubTask(id="2", description="usar resultado anterior", agent_type="recorder"),
        context="resultado da etapa 1",
    )

    assert result["text"] == "ok"
    assert "resultado da etapa 1" in captured["task"]
