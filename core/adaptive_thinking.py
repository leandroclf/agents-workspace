from enum import Enum


class AdaptiveThinkingManager:
    EFFORT_MAP = {
        "code":          "high",
        "analysis":      "high",
        "architecture":  "xhigh",
        "orchestration": "xhigh",
        "validation":    "medium",
        "summary":       "medium",
        "chat":          "low",
        "faq":           "low",
    }

    def get_effort(self, task_type) -> str:
        key = task_type.value if hasattr(task_type, "value") else str(task_type)
        return self.EFFORT_MAP.get(key, "medium")

    def build_thinking_config(self, task_type) -> dict:
        effort = self.get_effort(task_type)
        return {"type": "adaptive", "display": "omitted", "effort": effort}
