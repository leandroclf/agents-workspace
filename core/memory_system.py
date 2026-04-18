import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class MemorySystem:
    def __init__(self, db_path: str = "memory/workspace.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init_schema()

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_message TEXT NOT NULL,
                    assistant_response TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    model_used TEXT NOT NULL,
                    tokens_used INTEGER DEFAULT 0,
                    feedback_score REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    preference_key TEXT UNIQUE NOT NULL,
                    preference_value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS learned_skills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    prompt_template TEXT NOT NULL,
                    success_rate REAL DEFAULT 0.5,
                    usage_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS project_context (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT UNIQUE NOT NULL,
                    project_name TEXT NOT NULL,
                    description TEXT,
                    tech_stack TEXT DEFAULT '[]',
                    recent_files TEXT DEFAULT '[]',
                    last_interaction TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

    def save_interaction(self, user_message: str, assistant_response: str,
                         task_type: str, model_used: str, tokens_used: int = 0,
                         feedback_score: Optional[float] = None):
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO interactions
                   (user_message, assistant_response, task_type, model_used, tokens_used, feedback_score)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user_message, assistant_response, task_type, model_used, tokens_used, feedback_score)
            )

    def get_recent_interactions(self, limit: int = 10) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM interactions ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def set_preference(self, key: str, value: str):
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO user_preferences (preference_key, preference_value, updated_at)
                   VALUES (?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(preference_key) DO UPDATE SET
                   preference_value = excluded.preference_value,
                   updated_at = CURRENT_TIMESTAMP""",
                (key, value)
            )

    def get_preference(self, key: str, default: Any = None) -> Any:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT preference_value FROM user_preferences WHERE preference_key = ?", (key,)
            ).fetchone()
        return row["preference_value"] if row else default

    def save_skill(self, name: str, description: str, prompt_template: str,
                   success_rate: float = 0.5):
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO learned_skills (name, description, prompt_template, success_rate)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(name) DO UPDATE SET
                   description = excluded.description,
                   prompt_template = excluded.prompt_template,
                   success_rate = excluded.success_rate,
                   updated_at = CURRENT_TIMESTAMP""",
                (name, description, prompt_template, success_rate)
            )

    def get_skills(self, min_success_rate: float = 0.0) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM learned_skills WHERE success_rate >= ? ORDER BY success_rate DESC",
                (min_success_rate,)
            ).fetchall()
        return [dict(r) for r in rows]

    def save_project_context(self, project_id: str, project_name: str,
                              description: str = "", tech_stack: list = None,
                              recent_files: list = None):
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO project_context
                   (project_id, project_name, description, tech_stack, recent_files, updated_at)
                   VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(project_id) DO UPDATE SET
                   project_name = excluded.project_name,
                   description = excluded.description,
                   tech_stack = excluded.tech_stack,
                   recent_files = excluded.recent_files,
                   updated_at = CURRENT_TIMESTAMP""",
                (project_id, project_name, description,
                 json.dumps(tech_stack or []), json.dumps(recent_files or []))
            )

    def get_project_context(self, project_id: str) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM project_context WHERE project_id = ?", (project_id,)
            ).fetchone()
        if not row:
            return None
        result = dict(row)
        result["tech_stack"] = json.loads(result["tech_stack"])
        result["recent_files"] = json.loads(result["recent_files"])
        return result
