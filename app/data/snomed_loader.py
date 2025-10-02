from __future__ import annotations
from typing import Dict, Any, Tuple
import os, json
from functools import lru_cache

def _norm(s: str) -> str:
    return (s or "").strip().lower()

def _alias_index(db: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
    idx: Dict[str, str] = {}
    for primary, v in db.items():
        idx[_norm(primary)] = primary
        for a in (v.get("aliases") or []):
            idx[_norm(a)] = primary
    return idx

@lru_cache(maxsize=1)
def get_snomed_db() -> Tuple[Dict[str, Dict[str, Any]], Dict[str, str]]:
    """Load SNOMED terms from data/snomed.json. Returns (db, alias_index)."""
    path = os.getenv("SNOMED_JSON", "data/snomed.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing {path}. Add your SNOMED JSON.")
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, dict):
        raise ValueError("snomed.json must be an object mapping term -> {code, display, aliases}")
    db: Dict[str, Dict[str, Any]] = {}
    for k, v in raw.items():
        if not isinstance(v, dict):
            continue
        code = v.get("code"); display = v.get("display")
        if not code or not display:
            continue
        aliases = v.get("aliases") or []
        db[k] = {"code": str(code), "display": str(display), "aliases": aliases}
    return db, _alias_index(db)
