import sqlite3
import json
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class Skill:
    name: str
    description: str
    prompt_template: str
    tags: list[str] = field(default_factory=list)
    success_rate: float = 0.5
    usage_count: int = 0
    created_at: str = ""
    updated_at: str = ""

    def format(self, **kwargs) -> str:
        try:
            return self.prompt_template.format(**kwargs)
        except KeyError:
            return self.prompt_template


class SkillManager:
    def __init__(self, db_path: str = "memory/workspace.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._write_lock = threading.RLock()
        self._init_schema()

    def _conn(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 30000")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _init_schema(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS skills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    prompt_template TEXT NOT NULL,
                    tags TEXT DEFAULT '[]',
                    success_rate REAL DEFAULT 0.5,
                    usage_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def _row_to_skill(self, row) -> Skill:
        return Skill(
            name=row["name"],
            description=row["description"] or "",
            prompt_template=row["prompt_template"],
            tags=json.loads(row["tags"]),
            success_rate=row["success_rate"],
            usage_count=row["usage_count"],
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def save_skill(self, skill: Skill):
        with self._write_lock:
            with self._conn() as conn:
                conn.execute(
                    """INSERT INTO skills (name, description, prompt_template, tags, success_rate)
                       VALUES (?, ?, ?, ?, ?)
                       ON CONFLICT(name) DO UPDATE SET
                       description = excluded.description,
                       prompt_template = excluded.prompt_template,
                       tags = excluded.tags,
                       success_rate = excluded.success_rate,
                       updated_at = CURRENT_TIMESTAMP""",
                    (skill.name, skill.description, skill.prompt_template,
                     json.dumps(skill.tags), skill.success_rate)
                )

    def get_skill(self, name: str) -> Optional[Skill]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM skills WHERE name = ?", (name,)).fetchone()
        return self._row_to_skill(row) if row else None

    def list_skills(self) -> list[Skill]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM skills ORDER BY success_rate DESC").fetchall()
        return [self._row_to_skill(r) for r in rows]

    def find_relevant(self, query: str, top_k: int = 3) -> list[Skill]:
        query_lower = query.lower()
        all_skills = self.list_skills()
        def score(skill: Skill) -> float:
            name_match = any(w in skill.name.lower() for w in query_lower.split())
            tag_match = any(t.lower() in query_lower for t in skill.tags)
            desc_match = any(w in (skill.description or "").lower() for w in query_lower.split())
            return (name_match * 2 + tag_match * 3 + desc_match * 1) * skill.success_rate
        ranked = sorted(all_skills, key=score, reverse=True)
        return [s for s in ranked if score(s) > 0][:top_k]

    def update_success_rate(self, name: str, success: bool, alpha: float = 0.1):
        skill = self.get_skill(name)
        if not skill:
            return
        new_rate = skill.success_rate + alpha * (1.0 if success else -1.0)
        new_rate = max(0.0, min(1.0, new_rate))
        with self._write_lock:
            with self._conn() as conn:
                conn.execute(
                    """UPDATE skills SET success_rate = ?, usage_count = usage_count + 1,
                       updated_at = CURRENT_TIMESTAMP WHERE name = ?""",
                    (new_rate, name)
                )

    def build_skill_injection_text(self, query: str, top_k: int = 3) -> str:
        skills = self.find_relevant(query=query, top_k=top_k)
        if not skills:
            return ""
        lines = ["## Habilidades Aprendidas Relevantes\n"]
        for s in skills:
            lines.append(f"### {s.name}")
            lines.append(f"_{s.description}_")
            lines.append(f"Template: `{s.prompt_template}`\n")
        return "\n".join(lines)
