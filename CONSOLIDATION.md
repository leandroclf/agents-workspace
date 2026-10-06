# Consolidation disposition

Status: **REFERENCE / archive candidate**, not a canonical runtime.

Canonical destinations:
- generic engineering orchestration -> ai-engineering-team
- reusable skill content -> ai-kit
- proposal generation boundary -> OmniCLI

## Capabilities reviewed

| Legacy capability | Disposition |
|---|---|
| coder/validator/orchestrator runtime | superseded by isolated Plan/Implement/Validate/Review stages in ai-engineering-team |
| generic skill content | ai-kit owns reusable skills |
| model/backend fallback routing | intentionally not migrated; current architecture uses fixed stage responsibilities rather than dynamic routing |
| YAML workflow engine | retain as reference; migrate only if a measured ai-engineering-team workload needs declarative DAG execution |
| SQLite SkillManager success-rate ranking | retain as reference; current canonical approach uses explicit skill evaluation/benchmarks rather than runtime self-ranking |
| WorldBank/Wikidata/OpenAlex agents | domain examples, not Engineering Harness core |
| REST/CLI/MCP template | reference only; no need for another runtime/control plane |

## Archive gate

Do not add new features here. Archive only after confirming no external runtime depends on this repository and after any specifically approved unique capability has been migrated with tests.
