import pytest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from unittest.mock import patch, MagicMock
from core.adaptive_thinking import AdaptiveThinkingManager
from core.claude_client import ClaudeClient, TaskType

def test_detect_task_type_code():
    client = ClaudeClient.__new__(ClaudeClient)
    assert client.detect_task_type("Refatore o arquivo main.py") == TaskType.CODE

def test_detect_task_type_analysis():
    client = ClaudeClient.__new__(ClaudeClient)
    assert client.detect_task_type("Analise a performance deste algoritmo") == TaskType.ANALYSIS

def test_detect_task_type_chat():
    client = ClaudeClient.__new__(ClaudeClient)
    assert client.detect_task_type("Qual é a capital do Brasil?") == TaskType.CHAT

def test_select_model_for_code():
    client = ClaudeClient.__new__(ClaudeClient)
    model = client.select_model(TaskType.CODE)
    assert model == "claude-opus-4-7"

def test_select_model_for_chat():
    client = ClaudeClient.__new__(ClaudeClient)
    model = client.select_model(TaskType.CHAT)
    assert model == "claude-haiku-4-5"

def test_adaptive_thinking_effort_by_task():
    mgr = AdaptiveThinkingManager()
    assert mgr.get_effort(TaskType.CODE) == "high"
    assert mgr.get_effort(TaskType.ANALYSIS) == "high"
    assert mgr.get_effort(TaskType.CHAT) == "low"

def test_adaptive_thinking_orchestration():
    mgr = AdaptiveThinkingManager()
    assert mgr.get_effort("orchestration") == "xhigh"
