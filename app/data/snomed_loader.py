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
            if a:
                idx[_norm(a)] = primary
    return idx

def _as_object_map(raw: Any) -> Dict[str, Dict[str, Any]]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, list):
        out: Dict[str, Dict[str, Any]] = {}
        for row in raw:
            if not isinstance(row, dict):
                continue
            term = row.get("term")
            if not term:
                continue
            out[str(term)] = {
                "code": str(row.get("code", "")).strip(),
                "display": str(row.get("display", "")).strip(),
                "aliases": row.get("aliases") or []
            }
        return out
    return {}

@lru_cache(maxsize=1)
def get_snomed_db() -> Tuple[Dict[str, Dict[str, Any]], Dict[str, str]]:
    """Load SNOMED terms from data/snomed.json.
    - Accepts UTF-8 with or without BOM.
    - Accepts object map OR array-of-rows (with .term/.code/.display/.aliases).
    - Never throws; returns ({}, {}) on problems.
    """
    path = os.getenv("SNOMED_JSON", "data/snomed.json")
    if not os.path.exists(path):
        return {}, {}
    try:
        with open(path, "r", encoding="utf-8-sig") as f:  # <-- handles BOM
            raw = json.load(f)
        raw = _as_object_map(raw)
        db: Dict[str, Dict[str, Any]] = {}
        for k, v in raw.items():
            if not isinstance(v, dict):
                continue
            code = v.get("code")
            display = v.get("display")
            if not code or not display:
                continue
            aliases = [str(a).strip().lower() for a in (v.get("aliases") or []) if a]
            db[str(k).strip().lower()] = {"code": str(code), "display": str(display), "aliases": aliases}
        return db, _alias_index(db)
    except Exception:
        return {}, {}