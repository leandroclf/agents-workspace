"""
Agent that integrates with the lf-wikidata-entity-graph backend.
Exposes entity matching and graph enrichment as workspace capabilities.
"""
import json
import urllib.request
from typing import Any, Optional
from core.agents.base_agent import BaseAgent


WIKIDATA_BASE_URL = "http://localhost:8002"


def _http_post(path: str, body: dict, base: str = WIKIDATA_BASE_URL) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{base}{path}", data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception:
        return {}


def _http_get(path: str, base: str = WIKIDATA_BASE_URL) -> dict:
    try:
        with urllib.request.urlopen(f"{base}{path}", timeout=5) as r:
            return json.loads(r.read())
    except Exception:
        return {}


def match_entity(name: str, candidates: list[dict],
                 confidence_threshold: float = 0.7) -> dict:
    """Find the best Wikidata match for a given entity name."""
    result = _http_post("/v1/entities/match", {
        "name": name,
        "candidates": candidates,
        "confidence_threshold": confidence_threshold,
    })
    if result:
        return result

    # Local Jaccard similarity fallback
    def jaccard(a: str, b: str) -> float:
        sa, sb = set(a.lower().split()), set(b.lower().split())
        if not sa and not sb:
            return 1.0
        return len(sa & sb) / len(sa | sb)

    best = max(candidates, key=lambda c: jaccard(name, c.get("label", "")), default=None)
    if not best:
        return {"matched": False, "fallback": True}
    score = jaccard(name, best.get("label", ""))
    return {
        "matched": score >= confidence_threshold,
        "bestMatch": best,
        "score": round(score, 4),
        "fallback": True,
    }


def run_pipeline(records: list[dict], confidence_threshold: float = 0.7) -> dict:
    """Run entity matching pipeline on a batch of records."""
    result = _http_post("/v1/entities/pipeline", {
        "records": records,
        "confidence_threshold": confidence_threshold,
    })
    return result or {"error": "backend unavailable", "records": records}


def get_metrics() -> dict:
    return _http_get("/v1/entities/metrics") or {}


class WikidataEntityAgent(BaseAgent):
    """
    Workspace agent for entity resolution and Wikidata graph enrichment.
    Uses lf-wikidata-entity-graph backend when available.
    """
    name = "WikidataEntityAgent"
    task_type = "analysis"
    role_description = """Você é especialista em resolução de entidades e enriquecimento com Wikidata.
Suas capacidades:
- Fazer match de entidades por nome usando similaridade semântica
- Rodar pipelines de resolução em batch
- Explicar scores de confiança e decisões de match
- Enriquecer registros com dados do grafo Wikidata

Apresente resultados com scores de confiança e explique as decisões."""

    def run(self, task: str, entity_name: str = "",
            candidates: Optional[list] = None,
            records: Optional[list] = None,
            confidence_threshold: float = 0.7,
            **kwargs) -> dict[str, Any]:
        context_parts = []

        if entity_name and candidates:
            match = match_entity(entity_name, candidates, confidence_threshold)
            context_parts.append(f"Entity match result:\n{json.dumps(match, indent=2)}")

        if records:
            pipeline = run_pipeline(records, confidence_threshold)
            context_parts.append(f"Pipeline result:\n{json.dumps(pipeline, indent=2)}")

        metrics = get_metrics()
        if metrics:
            context_parts.append(f"Backend metrics:\n{json.dumps(metrics, indent=2)}")

        extra = "\n\n".join(context_parts) if context_parts else ""
        return self._call_api(task=task, extra_context=extra)
