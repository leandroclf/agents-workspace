import pytest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.skill_manager import SkillManager, Skill

@pytest.fixture
def manager(tmp_path):
    return SkillManager(db_path=str(tmp_path / "skills.db"))

def test_save_and_list_skills(manager):
    skill = Skill(
        name="python_refactor",
        description="Refatoração de código Python",
        prompt_template="Refatore o seguinte código Python mantendo a funcionalidade: {code}",
        tags=["python", "refactor", "code"]
    )
    manager.save_skill(skill)
    skills = manager.list_skills()
    assert len(skills) == 1
    assert skills[0].name == "python_refactor"

def test_find_relevant_skills_by_tag(manager):
    s1 = Skill("python_refactor", "Refactoring Python", "Refatore: {code}", tags=["python"])
    s2 = Skill("ts_types", "TypeScript types", "Adicione types: {code}", tags=["typescript"])
    manager.save_skill(s1)
    manager.save_skill(s2)
    results = manager.find_relevant(query="refactor python code", top_k=1)
    assert any(s.name == "python_refactor" for s in results)

def test_update_skill_success_rate(manager):
    skill = Skill("my_skill", "desc", "template", success_rate=0.5)
    manager.save_skill(skill)
    manager.update_success_rate("my_skill", success=True)
    updated = manager.get_skill("my_skill")
    assert updated.success_rate > 0.5

def test_get_nonexistent_skill_returns_none(manager):
    assert manager.get_skill("does_not_exist") is None

def test_build_system_prompt_injection(manager):
    s = Skill("tip", "tip desc", "Use este padrão: {pattern}", tags=["pattern"])
    manager.save_skill(s)
    prompt = manager.build_skill_injection_text(query="pattern", top_k=1)
    assert "tip" in prompt
    assert "tip desc" in prompt
