import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def test_load_rejects_unknown_agent(tmp_path):
    from workflows.engine import WorkflowEngine

    workflow_file = tmp_path / "bad.yaml"
    workflow_file.write_text(
        "name: bad\nsteps:\n  - name: s1\n    task: hi\n    agent: missing\n",
        encoding="utf-8",
    )
    engine = WorkflowEngine.__new__(WorkflowEngine)
    engine.task_type_map = {"chat": object()}

    with pytest.raises(ValueError, match="Unknown workflow agent"):
        WorkflowEngine.load(engine, str(workflow_file))


def test_execute_runs_real_agent_from_agent_map(monkeypatch):
    from workflows.engine import Workflow, WorkflowEngine, WorkflowStep
    import workflows.engine as engine_module

    captured = {}

    class WorkflowAgent:
        def __init__(self, memory=None, skill_manager=None):
            pass

        def run(self, task="", **kwargs):
            captured["task"] = task
            return {"text": "agent-output"}

    monkeypatch.setitem(engine_module.AGENT_MAP, "custom-agent", WorkflowAgent)

    engine = WorkflowEngine.__new__(WorkflowEngine)
    engine.memory = MagicMock()
    engine.skill_manager = MagicMock()
    engine.client = MagicMock()
    engine.task_type_map = {"chat": object()}

    workflow = Workflow(
        name="wf",
        trigger="manual",
        steps=[
            WorkflowStep(name="first", task="base", agent="chat", output_var="base"),
            WorkflowStep(
                name="second",
                task="use base",
                agent="custom-agent",
                depends_on=["base"],
            ),
        ],
    )
    engine.client.chat.return_value = {"text": "chat-output"}

    result = engine.execute(workflow)

    assert result["outputs"]["second"] == "agent-output"
    assert "chat-output" in captured["task"]
