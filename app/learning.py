from __future__ import annotations
import json, os, datetime, threading
from typing import Optional, Dict, Any

_LEARNED_PATH = os.getenv("LEARNED_JSON", "data/layman_learned.json")
_LOG_DIR = os.getenv("LEARNED_LOG_DIR", "data/logs/learned")
_LOCK = threading.RLock()

def _ensure_dirs():
    os.makedirs(os.path.dirname(_LEARNED_PATH) or ".", exist_ok=True)
    os.makedirs(_LOG_DIR, exist_ok=True)

def _load_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def _dump_json(path: str, data: dict):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

def _today_log_path() -> str:
    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    return os.path.join(_LOG_DIR, f"{today}.jsonl")

def _append_jsonl(path: str, row: Dict[str, Any]):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

def _ns_key(context: Optional[str], term: str) -> str:
    ctx = (context or "global").strip().lower()
    return f"{ctx}::{term.strip().lower()}"

def learn_selection(
    term: str,
    snomed_code: Optional[str],
    snomed_display: Optional[str],
    lay_text: Optional[str],
    context: Optional[str] = None,
) -> Dict[str, Any]:
    """Persist a selection into namespaced learned map and JSONL log."""
    assert term, "term required"
    _ensure_dirs()
    with _LOCK:
        data = _load_json(_LEARNED_PATH)
        key = _ns_key(context, term)
        entry = {
            "term": term,
            "context": (context or "global"),
            "snomed_code": snomed_code,
            "snomed_display": snomed_display,
            "lay_text": lay_text or term,
            "updated_utc": datetime.datetime.utcnow().isoformat() + "Z",
        }
        data[key] = entry
        _dump_json(_LEARNED_PATH, data)

        log_row = {
            "ts": datetime.datetime.utcnow().isoformat() + "Z",
            "action": "api_learn",
            "term": term,
            "context": (context or "global"),
            "snomed_code": snomed_code,
            "snomed_display": snomed_display,
            "lay_text": lay_text or term,
        }
        _append_jsonl(_today_log_path(), log_row)

        return {"ok": True, "key": key, "entry": entry}

def get_learned(context: Optional[str], term: str) -> Optional[Dict[str, Any]]:
    key = _ns_key(context, term)
    data = _load_json(_LEARNED_PATH)
    return data.get(key)
