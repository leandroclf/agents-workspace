"""
Agent that integrates with the lf-openalex-enrichment-mvp backend.
Exposes lead enrichment and value scoring as workspace capabilities.
"""
import json
import urllib.request
from typing import Any, Optional
from core.agents.base_agent import BaseAgent


OPENALEX_BASE_URL = "http://localhost:8003"


def _http_post(path: str, body: dict, base: str = OPENALEX_BASE_URL) -> dict:
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


def _http_get(path: str, base: str = OPENALEX_BASE_URL) -> dict:
    try:
        with urllib.request.urlopen(f"{base}{path}", timeout=5) as r:
            return json.loads(r.read())
    except Exception:
        return {}


def enrich_leads(leads: list[dict], config: Optional[dict] = None) -> dict:
    """Enrich a list of leads with OpenAlex data."""
    body = {"leads": leads}
    if config:
        body["config"] = config
    return _http_post("/enrich", body) or {"error": "backend unavailable", "leads": leads}


def get_value_score(account_id: str, score: float) -> dict:
    """Build a value signal summary for an account."""
    result = _http_post("/v1/value-score", {"accountId": account_id, "score": score})
    return result or {"accountId": account_id, "score": score, "fallback": True}


def prioritize_leads(leads: list[dict], weights: Optional[dict] = None) -> dict:
    """Prioritize leads by enrichment gap score."""
    body = {"leads": leads}
    if weights:
        body["weights"] = weights
    return _http_post("/v1/leads/prioritize", body) or {
        "error": "backend unavailable", "leads": leads
    }


def get_sample() -> dict:
    return _http_get("/sample") or {}


class OpenAlexEnrichmentAgent(BaseAgent):
    """
    Workspace agent for lead enrichment and academic signal scoring via OpenAlex.
    Uses lf-openalex-enrichment-mvp backend when available.
    """
    name = "OpenAlexEnrichmentAgent"
    task_type = "analysis"
    role_description = """Você é especialista em enriquecimento de leads com dados acadêmicos e científicos.
Suas capacidades:
- Enriquecer listas de leads com dados do OpenAlex (publicações, citações, afiliações)
- Calcular value scores para priorização de contas
- Identificar gaps de enriquecimento e priorizar leads
- Explicar sinais de valor e metodologia de scoring

Apresente análises de cobertura, gaps e recomendações de prioridade."""

    def run(self, task: str, leads: Optional[list] = None,
            account_id: str = "", score: float = 0,
            weights: Optional[dict] = None,
            **kwargs) -> dict[str, Any]:
        context_parts = []

        if leads and account_id:
            # Prioritize first, then enrich
            priority_result = prioritize_leads(leads, weights)
            context_parts.append(f"Lead prioritization:\n{json.dumps(priority_result, indent=2)}")
            enrich_result = enrich_leads(leads)
            context_parts.append(f"Enrichment result:\n{json.dumps(enrich_result, indent=2)}")
        elif leads:
            enrich_result = enrich_leads(leads)
            context_parts.append(f"Enrichment result:\n{json.dumps(enrich_result, indent=2)}")

        if account_id and score:
            vs = get_value_score(account_id, score)
            context_parts.append(f"Value score:\n{json.dumps(vs, indent=2)}")

        extra = "\n\n".join(context_parts) if context_parts else ""
        return self._call_api(task=task, extra_context=extra)
