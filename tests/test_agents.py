import pytest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from unittest.mock import patch, MagicMock
from core.agents.base_agent import BaseAgent
from core.memory_system import MemorySystem
from core.skill_manager import SkillManager

@pytest.fixture
def memory(tmp_path):
    return MemorySystem(db_path=str(tmp_path / "mem.db"))

@pytest.fixture
def skills(tmp_path):
    return SkillManager(db_path=str(tmp_path / "skills.db"))

def test_base_agent_has_required_attributes(memory, skills):
    agent = BaseAgent.__new__(BaseAgent)
    agent.name = "TestAgent"
    agent.model = "claude-sonnet-4-6"
    agent.memory = memory
    agent.skill_manager = skills
    assert agent.name == "TestAgent"
    assert agent.model == "claude-sonnet-4-6"

def test_base_agent_build_system_prompt_includes_agent_name(memory, skills):
    agent = BaseAgent.__new__(BaseAgent)
    agent.name = "CoderBot"
    agent.role_description = "Você é um especialista em Python."
    agent.memory = memory
    agent.skill_manager = skills
    prompt = agent.build_system_prompt(task="refactor python code")
    assert "CoderBot" in prompt
    assert "Python" in prompt

def test_base_agent_build_system_prompt_with_skills(memory, skills):
    from core.skill_manager import Skill
    skills.save_skill(Skill("py_tip", "Python tip", "Use list comprehension: {code}", tags=["python"]))
    agent = BaseAgent.__new__(BaseAgent)
    agent.name = "Bot"
    agent.role_description = "Expert"
    agent.memory = memory
    agent.skill_manager = skills
    prompt = agent.build_system_prompt(task="python refactor")
    assert "py_tip" in prompt
