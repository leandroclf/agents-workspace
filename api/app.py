import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, request, jsonify
from dotenv import load_dotenv
from core.claude_client import ClaudeClient, TaskType
from core.memory_system import MemorySystem
from core.skill_manager import SkillManager, Skill
from core.error_handler import RobustErrorHandler

load_dotenv()

app = Flask(__name__)
memory = MemorySystem()
skills = SkillManager()
client = ClaudeClient(memory=memory)
error_handler = RobustErrorHandler()


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "version": "2.0"})


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True)
    prompt = data.get("prompt", "")
    if not prompt:
        return jsonify({"error": "prompt is required"}), 400
    task_type_str = data.get("task_type")
    task_type = TaskType[task_type_str.upper()] if task_type_str else None
    try:
        result = error_handler.execute_with_retry(
            lambda: client.chat(prompt=prompt, task_type=task_type)
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/interactions", methods=["GET"])
def interactions():
    limit = int(request.args.get("limit", 10))
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
    data = request.get_json(force=True)
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("DEBUG", "false").lower() == "true")
