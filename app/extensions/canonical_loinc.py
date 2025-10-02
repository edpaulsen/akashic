from __future__ import annotations
from typing import Optional, Dict
from functools import lru_cache
import os, json

def _norm(s: str) -> str:
    return (s or "").strip().lower()

@lru_cache(maxsize=1)
def _load_canonical() -> Dict[str, str]:
    """Load canonical key -> LOINC code from data/loinc_canonical.json.
    Accepts UTF-8 with or without BOM; returns {} on problems."""
    path = os.getenv("LOINC_CANONICAL_JSON", "data/loinc_canonical.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8-sig") as f:  # <-- handles BOM
            raw = json.load(f)
        if not isinstance(raw, dict):
            return {}
        out: Dict[str, str] = {}
        for k, v in raw.items():
            if isinstance(v, str) and v.strip():
                out[_norm(k)] = v.strip()
        return out
    except Exception:
        return {}

def choose(term: str) -> Optional[str]:
    """Input: canonical key (already normalized). Output: LOINC code or None."""
    return _load_canonical().get(_norm(term))