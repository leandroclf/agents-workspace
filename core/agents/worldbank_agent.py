"""
Agent that integrates with the lf-worldbank-risk-pricing backend.
Exposes risk scoring and pricing calculation as workspace capabilities.
"""
import json
import urllib.request
import urllib.error
from typing import Any, Optional
from core.agents.base_agent import BaseAgent
from core.memory_system import MemorySystem
from core.skill_manager import SkillManager


WORLDBANK_BASE_URL = "https://lf-worldbank-risk-pricing.onrender.com"

STATIC_RISK = {
    "BR": 62, "US": 22, "DE": 18, "IN": 58, "NG": 78,
    "AR": 71, "CN": 45, "FR": 20, "GB": 19, "MX": 55,
}


def _http_get(path: str, base: str = WORLDBANK_BASE_URL) -> dict:
    try:
        with urllib.request.urlopen(f"{base}{path}", timeout=5) as r:
            return json.loads(r.read())
    except Exception:
        return {}


def _http_post(path: str, body: dict, base: str = WORLDBANK_BASE_URL) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{base}{path}", data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read())
    except Exception:
        return {}


def get_risk_score(country_code: str) -> dict:
    """Return risk score for a country, with static fallback."""
    result = _http_get(f"/v1/risk-score?country_code={country_code.upper()}")
    if result:
        return result
    code = country_code.upper()
    score = STATIC_RISK.get(code, 50)
    return {
        "countryCode": code, "riskScore": score,
        "fallback": True, "sourceAttribution": "World Bank (CC BY 4.0)",
    }


def get_pricing_quote(country_code: str, base_price: float,
                      risk_score: Optional[float] = None) -> dict:
    """Calculate risk-adjusted pricing for a country."""
    if risk_score is None:
        risk_score = get_risk_score(country_code).get("riskScore", 50)

    result = _http_post("/v1/pricing/quote", {
        "countryCode": country_code.upper(),
        "riskScore": risk_score,
        "basePrice": base_price,
        "currency": "USD",
    })
    if result:
        return result

    # Local calculation (mirrors backend logic)
    if risk_score >= 75:
        tier, adj = "high", 8
    elif risk_score >= 50:
        tier, adj = "medium", 3
    else:
        tier, adj = "low", 0
    mult = round(1 + adj / 100, 4)
    return {
        "countryCode": country_code.upper(),
        "riskScore": risk_score,
        "tier": tier,
        "adjustment": adj,
        "multiplier": mult,
        "basePrice": base_price,
        "finalPrice": round(base_price * mult, 2),
        "currency": "USD",
        "fallback": True,
    }


def batch_risk_scores(country_codes: list[str]) -> list[dict]:
    """Return risk scores for multiple countries."""
    return [get_risk_score(c) for c in country_codes]


class WorldBankRiskAgent(BaseAgent):
    """
    Workspace agent for country risk analysis and pricing.
    Uses lf-worldbank-risk-pricing backend when available, falls back to static data.
    """
    name = "WorldBankRiskAgent"
    task_type = "analysis"
    role_description = """Você é especialista em risco-país e precificação regional.
Suas capacidades:
- Calcular risk scores por país (dados World Bank)
- Gerar quotes de pricing ajustados por risco
- Comparar múltiplos países em batch
- Explicar fatores de risco e metodologia

Use dados concretos e explique o impacto financeiro das diferenças de risco."""

    def run(self, task: str, country_code: str = "",
            base_price: float = 0, countries: Optional[list] = None,
            **kwargs) -> dict[str, Any]:
        context_parts = []

        if country_code and base_price:
            quote = get_pricing_quote(country_code, base_price)
            context_parts.append(f"Pricing quote:\n{json.dumps(quote, indent=2)}")
        elif country_code:
            risk = get_risk_score(country_code)
            context_parts.append(f"Risk score:\n{json.dumps(risk, indent=2)}")

        if countries:
            batch = batch_risk_scores(countries)
            context_parts.append(f"Batch scores:\n{json.dumps(batch, indent=2)}")

        extra = "\n\n".join(context_parts) if context_parts else ""
        return self._call_api(task=task, extra_context=extra)
