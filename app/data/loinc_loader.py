from __future__ import annotations
from typing import Dict
import os, json
from functools import lru_cache

def _norm(s: str) -> str:
    return (s or "").strip().lower()

@lru_cache(maxsize=1)
def _load_alias_map() -> Dict[str, str]:
    """Load alias -> canonical-key from data/loinc_aliases.json.
    Accepts UTF-8 with or without BOM; returns {} on problems."""
    path = os.getenv("LOINC_ALIASES_JSON", "data/loinc_aliases.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8-sig") as f:  # <-- handles BOM
            raw = json.load(f)
        if not isinstance(raw, dict):
            return {}
        out: Dict[str, str] = {}
        for k, v in raw.items():
            if isinstance(v, str):
                out[_norm(k)] = _norm(v)
        return out
    except Exception:
        return {}

def normalize_loinc_term(term: str) -> str:
    """Map input term/synonym to canonical key; if no match, return normalized input."""
    alias_map = _load_alias_map()
    t = _norm(term)
    return alias_map.get(t, t)