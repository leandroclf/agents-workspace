"""Pings the 3 Render backends every 5 minutes to prevent hibernation."""
import os
import time
import urllib.request
import urllib.error
from datetime import datetime

_DEFAULT_ENDPOINTS = [
    ("WorldBank Risk Pricing", "https://lf-worldbank-risk-pricing.onrender.com/health"),
    ("Wikidata Entity Graph", "https://lf-wikidata-entity-graph.onrender.com/health"),
    ("OpenAlex Enrichment", "https://lf-openalex-enrichment-mvp.onrender.com/health"),
]


def _load_endpoints() -> list[tuple[str, str]]:
    """Load endpoints from KEEPALIVE_ENDPOINTS env var (JSON) or use defaults."""
    raw = os.environ.get("KEEPALIVE_ENDPOINTS")
    if raw:
        import json
        try:
            return [(e["name"], e["url"]) for e in json.loads(raw)]
        except Exception:
            pass
    return _DEFAULT_ENDPOINTS


INTERVAL = int(os.environ.get("KEEPALIVE_INTERVAL", "300"))


def ping(name: str, url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            ok = resp.status == 200
            status = "✓" if ok else f"✗ {resp.status}"
    except urllib.error.URLError as e:
        ok = False
        status = f"✗ {e.reason}"
    except Exception as e:
        ok = False
        status = f"✗ {e}"
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {name}: {status}")
    return ok


def run():
    endpoints = _load_endpoints()
    print(f"Keep-alive iniciado. Pingando a cada {INTERVAL // 60} minutos.")
    print("Ctrl+C para parar.\n")
    while True:
        for name, url in endpoints:
            ping(name, url)
        print()
        time.sleep(INTERVAL)


if __name__ == "__main__":
    run()
