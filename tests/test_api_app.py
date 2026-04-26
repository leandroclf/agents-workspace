import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def test_health_does_not_require_backend(tmp_path):
    from api.app import create_app
    from core.memory_system import MemorySystem
    from core.skill_manager import SkillManager

    app = create_app(
        memory=MemorySystem(db_path=str(tmp_path / "m.db")),
        skills=SkillManager(db_path=str(tmp_path / "s.db")),
        client=MagicMock(),
    )
    response = app.test_client().get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_chat_rejects_empty_prompt(tmp_path):
    from api.app import create_app
    from core.memory_system import MemorySystem
    from core.skill_manager import SkillManager

    app = create_app(
        memory=MemorySystem(db_path=str(tmp_path / "m.db")),
        skills=SkillManager(db_path=str(tmp_path / "s.db")),
        client=MagicMock(),
    )
    response = app.test_client().post("/api/chat", json={"prompt": ""})
    assert response.status_code == 400


def test_chat_rejects_invalid_task_type(tmp_path):
    from api.app import create_app
    from core.memory_system import MemorySystem
    from core.skill_manager import SkillManager

    app = create_app(
        memory=MemorySystem(db_path=str(tmp_path / "m.db")),
        skills=SkillManager(db_path=str(tmp_path / "s.db")),
        client=MagicMock(),
    )
    response = app.test_client().post(
        "/api/chat",
        json={"prompt": "oi", "task_type": "not-a-task"},
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid task_type"


def test_chat_uses_injected_client(tmp_path):
    from api.app import create_app
    from core.memory_system import MemorySystem
    from core.skill_manager import SkillManager

    client = MagicMock()
    client.chat.return_value = {
        "text": "ok",
        "model": "test",
        "task_type": "chat",
        "input_tokens": 1,
        "output_tokens": 1,
    }
    app = create_app(
        memory=MemorySystem(db_path=str(tmp_path / "m.db")),
        skills=SkillManager(db_path=str(tmp_path / "s.db")),
        client=client,
    )
    response = app.test_client().post("/api/chat", json={"prompt": "oi"})
    assert response.status_code == 200
    assert response.get_json()["text"] == "ok"
