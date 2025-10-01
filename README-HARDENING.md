# Hardening Notes

## Atomic writes & learned log
- `json_store.update_learned_mapping()` writes `data/layman_learned.json` atomically, creates a `.bak`, and appends a per‑day JSONL audit under `data/logs/learned/`.
- `json_store.unlearn_mapping()` safely removes a term with the same guarantees.

## Data cache & version hash
- `data_cache.get_data_cache()` loads `snomed.json/loinc.json` once and computes a hash; expose it via `/api/version` for demos and bug reports.

## JSON logs
- `JSONLogMiddleware` emits one JSON line per request: `ts, request_id, method, path, query, status, duration_ms`.

## Smoke test
- Run `./smoke.ps1` on Windows PowerShell to verify MI + Epiphora flows end‑to‑end.
