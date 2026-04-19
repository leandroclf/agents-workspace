"""Pings the 3 Render backends every 5 minutes to prevent hibernation."""
import time
import urllib.request
import urllib.error
from datetime import datetime

ENDPOINTS = [
    ("WorldBank Risk Pricing", "https://lf-worldbank-risk-pricing.onrender.com/health"),
    ("Wikidata Entity Graph", "https://lf-wikidata-entity-graph.onrender.com/health"),
    ("OpenAlex Enrichment", "https://lf-openalex-enrichment-mvp.onrender.com/health"),
]

INTERVAL = 300  # 5 minutes


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
    print(f"Keep-alive iniciado. Pingando a cada {INTERVAL // 60} minutos.")
    print("Ctrl+C para parar.\n")
    while True:
        for name, url in ENDPOINTS:
            ping(name, url)
        print()
        time.sleep(INTERVAL)


if __name__ == "__main__":
    run()
