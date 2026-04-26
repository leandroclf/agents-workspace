import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, request, jsonify
from dotenv import load_dotenv
from core.claude_client import make_client, TaskType
from core.memory_system import MemorySystem
from core.skill_manager import SkillManager, Skill
from core.error_handler import RobustErrorHandler

load_dotenv()


def create_app(memory: MemorySystem = None, skills: SkillManager = None,
               client=None, error_handler: RobustErrorHandler = None) -> Flask:
    app = Flask(__name__)
    memory = memory or MemorySystem()
    skills = skills or SkillManager()
    error_handler = error_handler or RobustErrorHandler()
    client_ref = {"client": client}

    def get_client():
        if client_ref["client"] is None:
            client_ref["client"] = make_client(memory=memory)
        return client_ref["client"]

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "version": "2.0"})

    @app.route("/api/chat", methods=["POST"])
    def chat():
        data = request.get_json(silent=True) or {}
        prompt = data.get("prompt", "")
        if not isinstance(prompt, str) or not prompt.strip():
            return jsonify({"error": "prompt is required"}), 400

        task_type = None
        task_type_str = data.get("task_type")
        if task_type_str:
            try:
                task_type = TaskType[str(task_type_str).upper()]
            except KeyError:
                valid = [t.value for t in TaskType]
                return jsonify({"error": "invalid task_type", "valid": valid}), 400

        try:
            result = error_handler.execute_with_retry(
                lambda: get_client().chat(prompt=prompt, task_type=task_type)
            )
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)}), 500


    @app.route("/api/interactions", methods=["GET"])
    def interactions():
        try:
            limit = int(request.args.get("limit", 10))
        except ValueError:
            return jsonify({"error": "limit must be an integer"}), 400
        return jsonify(memory.get_recent_interactions(limit=limit))


    @app.route("/api/skills", methods=["GET"])
    def list_skills():
        return jsonify([
            {"name": s.name, "description": s.description,
             "success_rate": s.success_rate, "usage_count": s.usage_count}
            for s in skills.list_skills()
        ])


    @app.route("/api/skills", methods=["POST"])
    def create_skill():
        data = request.get_json(silent=True) or {}
        if not data.get("name") or not data.get("prompt_template"):
            return jsonify({"error": "name and prompt_template are required"}), 400
        skill = Skill(
            name=data["name"],
            description=data.get("description", ""),
            prompt_template=data["prompt_template"],
            tags=data.get("tags", []),
        )
        skills.save_skill(skill)
        return jsonify({"status": "created", "name": skill.name}), 201


    @app.route("/api/stats", methods=["GET"])
    def stats():
        all_interactions = memory.get_recent_interactions(limit=1000)
        total_tokens = sum(i.get("tokens_used", 0) for i in all_interactions)
        by_model: dict[str, int] = {}
        for i in all_interactions:
            m = i.get("model_used", "unknown")
            by_model[m] = by_model.get(m, 0) + 1
        return jsonify({
            "total_interactions": len(all_interactions),
            "total_tokens": total_tokens,
            "by_model": by_model,
            "skills_count": len(skills.list_skills()),
        })

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("DEBUG", "false").lower() == "true")
