# app/extensions/canonical_loinc.py
from __future__ import annotations
from typing import Optional, Dict
from functools import lru_cache
import os, json

def _norm(s: str) -> str:
    return (s or "").strip().lower()

@lru_cache(maxsize=1)
def _load_canonical() -> Dict[str, str]:
    """
    Load canonical key -> LOINC code from data/loinc_canonical.json.
    Returns {} if the file is missing or invalid.
    """
    path = os.getenv("LOINC_CANONICAL_JSON", "data/loinc_canonical.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, dict):
            return {}
        out: Dict[str, str] = {}
        for k, v in raw.items():
            if isinstance(v, str):
                out[_norm(k)] = v.strip()
        return out
    except Exception:
        return {}

def choose(term: str) -> Optional[str]:
    """
    Input: canonical key (already normalized by the alias layer).
    Output: canonical LOINC code, or None.
    """
    return _load_canonical().get(_norm(term))