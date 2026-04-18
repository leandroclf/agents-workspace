import pytest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.memory_system import MemorySystem

@pytest.fixture
def memory(tmp_path):
    db_path = str(tmp_path / "test.db")
    m = MemorySystem(db_path=db_path)
    return m

def test_save_and_retrieve_interaction(memory):
    memory.save_interaction(
        user_message="Refatore main.py",
        assistant_response="def main(): ...",
        task_type="code",
        model_used="claude-opus-4-7",
        tokens_used=500
    )
    recent = memory.get_recent_interactions(limit=5)
    assert len(recent) == 1
    assert recent[0]["task_type"] == "code"

def test_get_recent_interactions_limit(memory):
    for i in range(15):
        memory.save_interaction(f"msg {i}", f"resp {i}", "chat", "sonnet", 100)
    recent = memory.get_recent_interactions(limit=10)
    assert len(recent) == 10

def test_save_and_get_preference(memory):
    memory.set_preference("linguagem_principal", "Python")
    assert memory.get_preference("linguagem_principal") == "Python"

def test_get_nonexistent_preference_returns_default(memory):
    assert memory.get_preference("nao_existe", default="fallback") == "fallback"

def test_save_and_get_skill(memory):
    memory.save_skill(
        name="python_refactor",
        description="Refatora código Python",
        prompt_template="Refatore o seguinte código Python: {code}",
        success_rate=0.9
    )
    skills = memory.get_skills()
    assert any(s["name"] == "python_refactor" for s in skills)

def test_save_project_context(memory):
    memory.save_project_context(
        project_id="proj_1",
        project_name="MyApp",
        description="App de testes",
        tech_stack=["Python", "Flask"],
        recent_files=["main.py", "app.py"]
    )
    ctx = memory.get_project_context("proj_1")
    assert ctx["project_name"] == "MyApp"
    assert "Python" in ctx["tech_stack"]
