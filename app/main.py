from __future__ import annotations

import os
import json
import re
import time
import threading
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from fastapi import FastAPI, Query, Body, HTTPException, Header, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from rapidfuzz import fuzz

# -----------------------------------------------------------------------------
# App
# -----------------------------------------------------------------------------
app = FastAPI(title="Akashic Lookup API")

# -----------------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

LEARNED_JSON = DATA_DIR / "layman_learned.json"
SNOMED_JSON = DATA_DIR / "snomed.json"
LOINC_JSON = DATA_DIR / "loinc.json"

# React build (served if present)
BUILD_DIR = ROOT_DIR / "frontend" / "build"

# -----------------------------------------------------------------------------
# Small utils
# -----------------------------------------------------------------------------
def _read_json(path: Path, default: Any = None) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

_word_re = re.compile(r"[a-z0-9]+")

def _norm(s: Optional[str]) -> str:
    t = (s or "").strip().lower()
    return " ".join(_word_re.findall(t))

def _score(a: str, b: str) -> int:
    return int(fuzz.token_set_ratio((a or ""), (b or "")))

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def _append_learn_log(entry: Dict[str, Any]) -> None:
    """Append a JSON line to data/logs/learned/YYYY-MM-DD.jsonl"""
    logs_dir = DATA_DIR / "logs" / "learned"
    logs_dir.mkdir(parents=True, exist_ok=True)
    file = logs_dir / (datetime.now(timezone.utc).strftime("%Y-%m-%d") + ".jsonl")
    line = json.dumps(entry, ensure_ascii=False)
    with file.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def _data_hash() -> str:
    parts = []
    try:
        if SNOMED_JSON.exists():
            parts.append(_sha256_file(SNOMED_JSON))
        if LOINC_JSON.exists():
            parts.append(_sha256_file(LOINC_JSON))
        # include domain profile in the version hash (same folder as SNOMED/LOINC)
        dp = SNOMED_JSON.parent / "domain_profile.json"
        if dp.exists():
            parts.append(_sha256_file(dp))
    except Exception:
        # keep it resilient; empty parts -> stable hash of empty string
        pass
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()

def pick_best_loinc(loincs: list[dict], query: str) -> dict | None:
    """
    Choose a single LOINC to represent the lab when no SNOMED is present.
    Rules:
      1) Drop 'Deprecated' displays
      2) Prefer 'in Blood' for hemoglobin (718-7 is the canonical one)
      3) Otherwise take the first remaining candidate
    """
    if not loincs:
        return None
    q = (query or "").lower()
    filt = [l for l in loincs if "display" in l and "deprecated" not in l["display"].lower()]
    if not filt:
        filt = loincs[:]  # fall back if every hit is deprecated

    # Special-case hemoglobin: prefer Blood
    if "hemoglobin" in q:
        for l in filt:
            if " in blood" in l["display"].lower():
                return l

    return filt[0]



# -----------------------------------------------------------------------------
# Dataset caches (SNOMED/LOINC)
# -----------------------------------------------------------------------------
_CACHE_TTL_SEC = 300  # 5m
_lock = threading.Lock()
_cache: Dict[str, Dict[str, Any]] = {
    "snomed": {"data": None, "ts": 0.0},
    "loinc":  {"data": None, "ts": 0.0},
}

def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def _get_cached(name: str, path: Path):
    now = time.time()
    with _lock:
        entry = _cache[name]
        if entry["data"] is None or (now - entry["ts"]) > _CACHE_TTL_SEC:
            try:
                print(f"[CACHE] reload {name} from {path}")
            except Exception:
                pass
            entry["data"] = _load_json(path)
            entry["ts"] = now
        return entry["data"]

def get_snomed():
    return _get_cached("snomed", SNOMED_JSON)

def get_loinc():
    return _get_cached("loinc", LOINC_JSON)

# -----------------------------------------------------------------------------
# Auth guard (startup requirement only, endpoints are open to UI)
# -----------------------------------------------------------------------------
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN")
if not ADMIN_TOKEN:
    raise RuntimeError("ADMIN_TOKEN must be set in environment or .env")

# -----------------------------------------------------------------------------
# SNOMED candidates
# -----------------------------------------------------------------------------
def snomed_candidates(q: str, top_k: int = 8, score_cutoff: int = 60) -> List[Dict[str, Any]]:
    q = (q or "").strip().lower()
    snomed = _read_json(SNOMED_JSON, default=[])
    if not isinstance(snomed, list):
        return []
    out: List[Dict[str, Any]] = []
    for rec in snomed:
        if not isinstance(rec, dict):
            continue
        display = (rec.get("display") or "")
        aliases = rec.get("aliases") or rec.get("synonyms") or []
        if not isinstance(aliases, list):
            aliases = []
        best = 0
        for h in [display, *aliases]:
            if not h:
                continue
            s = fuzz.token_set_ratio(q, str(h))
            if s > best:
                best = s
        if best >= int(score_cutoff):
            out.append({"code": rec.get("code"), "display": display, "score": int(best)})
    out.sort(key=lambda x: x["score"], reverse=True)
    return out[: max(1, int(top_k))]

def pick_best_loinc(loincs, query):
    """
    Choose a single LOINC to represent the lab when no SNOMED is present.
    Rules:
      1) Drop 'Deprecated' displays
      2) Prefer 'in Blood' for hemoglobin (718-7 is canonical)
      3) Otherwise take the first remaining candidate
    """
    if not loincs:
        return None
    q = (query or "").lower()
    # remove deprecated
    filt = [l for l in loincs if isinstance(l, dict)
            and str(l.get("display", "")).strip()
            and "deprecated" not in str(l.get("display", "")).lower()]
    if not filt:
        filt = [l for l in loincs if isinstance(l, dict)]

    # special-case hemoglobin
    if "hemoglobin" in q:
        for l in filt:
            disp = str(l.get("display", "")).lower()
            if " in blood" in disp or str(l.get("code")) == "718-7":
                return l

    return filt[0] if filt else None


# -----------------------------------------------------------------------------
# LOINC candidates
# -----------------------------------------------------------------------------
def loinc_candidates(q: str, top_k: int = 8, score_cutoff: int = 60):
    q_raw = (q or "")
    qn = _norm(q_raw)
    q_tokens = set(qn.split())

    loinc = _read_json(LOINC_JSON, default=[]) or []
    # normalize to rows
    if isinstance(loinc, list):
        rows = loinc
    elif isinstance(loinc, dict):
        rows = loinc.get("rows") if isinstance(loinc.get("rows"), list) else [
            {**(v or {}), "code": k} for k, v in loinc.items() if not str(k).startswith("_")
        ]
    else:
        return []

    preferred_codes = {"2089-1", "2093-3", "2085-9", "8480-6", "8462-4"}  # core examples

    out = []
    for rec in rows:
        if not isinstance(rec, dict):
            continue
        code = str(rec.get("code") or rec.get("LOINC_NUM") or rec.get("loinc_num") or rec.get("id") or "").strip()
        display = (
            rec.get("display")
            or rec.get("LONG_COMMON_NAME") or rec.get("LongCommonName") or rec.get("long_common_name")
            or rec.get("SHORTNAME") or rec.get("ShortName") or rec.get("shortname")
            or rec.get("COMPONENT") or rec.get("Component") or rec.get("component")
            or ""
        )
        prop = (rec.get("PROPERTY") or rec.get("property") or "") or ""
        method = (rec.get("METHOD_TYP") or rec.get("METHOD") or rec.get("MethodType") or "") or ""
        loinc_class = (rec.get("CLASS") or rec.get("Class") or rec.get("class") or "") or ""
        aliases = rec.get("aliases") or rec.get("synonyms") or []
        if not isinstance(aliases, list):
            aliases = []

        best = 0
        for h in [display, *aliases]:
            if not h:
                continue
            h_norm = _norm(str(h))
            h_tokens = set(h_norm.split())
            if q_tokens and q_tokens.issubset(h_tokens):
                best = max(best, 98)
            s = fuzz.token_set_ratio(q_raw, str(h))
            if s > best:
                best = s

        L = (str(display) + " " + str(method)).lower()
        bonus = 0
        penalty = 0

        if code in preferred_codes: bonus += 8
        if "serum" in L or "plasma" in L or "ser/plas" in L: bonus += 6
        if prop.upper() in {"MCNC", "MASS CONC"}: bonus += 6
        if "CHEM" in loinc_class.upper(): bonus += 4
        for kw, pts in [
            ("panel", 20), ("question", 20), ("survey", 20),
            ("ratio", 12), ("/hdl", 10), ("ldl/hdl", 12),
            ("presence", 12), ("antibody", 12), (" ab ", 12),
            ("receptor", 10), ("electrophoresis", 12),
            ("little a", 12), ("lp(a)", 12),
            ("by calculation", 6), ("corrected", 6),
        ]:
            if kw in L:
                penalty += pts

        final = max(0, min(100, int(best + bonus - penalty)))
        if final >= int(score_cutoff):
            out.append({"code": code, "display": str(display), "score": final})

    out.sort(key=lambda x: x["score"], reverse=True)
    return out[: max(1, int(top_k))]

# -----------------------------------------------------------------------------
# /lookup
# -----------------------------------------------------------------------------
@app.get("/lookup")
def lookup(
    q: str,
    domain: str = "auto",
    include_technical: bool = False,
    top_k: int = 5,
    score_cutoff: int = 70,
    tech_top_k: int = 8,
    tech_score_cutoff: int = 60,
    select_snomed: str | None = None,
):  
    snomed = get_snomed()
    loinc = get_loinc()
    store = _read_json(LEARNED_JSON, default={}) or {}
    if not isinstance(store, dict):
        store = {}

    qn = _norm(q)
    code2disp: dict[str, str] = {}
    if isinstance(snomed, list):
        for rec in snomed:
            if isinstance(rec, dict) and rec.get("code") and rec.get("display"):
                code2disp[str(rec["code"])] = str(rec["display"])
    elif isinstance(snomed, dict):
        for c, v in snomed.items():
            if isinstance(v, dict) and v.get("display"):
                code2disp[str(c)] = str(v["display"])
            elif isinstance(v, str):
                code2disp[str(c)] = v

    results: List[Dict[str, Any]] = []
    for term, data in store.items():
        if not isinstance(data, dict):
            continue
        term_s = _score(qn, _norm(term))
        best = term_s
        aliases = data.get("aliases") or []
        if isinstance(aliases, list):
            for a in aliases:
                best = max(best, _score(qn, _norm(str(a))))
        if best >= int(score_cutoff):
            learned_code = data.get("snomed")
            learned_display = code2disp.get(str(learned_code)) if learned_code else None
            chosen_code = select_snomed or learned_code
            chosen_display = code2disp.get(str(chosen_code)) if chosen_code else None
            snomed_code = chosen_code
            snomed_display = chosen_display or learned_display
            patient_view = f"{term} ({snomed_display})" if snomed_display else term
            practitioner_view = f"{snomed_display} ({term})" if snomed_display else term
            codeable_concept = None
            if snomed_code and snomed_display:
                codeable_concept = {
                    "coding": [{
                        "system": "http://snomed.info/sct",
                        "code": str(snomed_code),
                        "display": snomed_display,
                    }],
                    "text": term,
                }
            seed_for_options = snomed_display or term
            options = snomed_candidates(seed_for_options, tech_top_k, tech_score_cutoff) or []
            practitioner_list = []
            seen: set[str] = set()
            if snomed_code and snomed_display:
                practitioner_list.append({
                    "code": str(snomed_code),
                    "display": snomed_display,
                    "score": 100,
                    "selected": True,
                })
                seen.add(str(snomed_code))
            for o in options:
                c = str(o.get("code") or "")
                d = o.get("display")
                if not c or c in seen:
                    continue
                seen.add(c)
                practitioner_list.append({"code": c, "display": d, "score": int(o.get("score", 0))})
            entry = {
                "term": term,
                "aliases": aliases if isinstance(aliases, list) else [],
                "loinc": data.get("loinc"),
                "snomed": snomed_code,
                "score": int(best),
                "patient_view": patient_view,
                "practitioner_view": practitioner_view,
                # ✅ Guard rail: labs (LOINC-only) don’t show practitioner options
                "practitioner_options": None if data.get("loinc") and not snomed_code else {
                    "snomed": practitioner_list[: max(1, int(tech_top_k))]
                },
            }
            if codeable_concept:
                entry["codeable_concept"] = codeable_concept
            results.append(entry)

    results.sort(key=lambda r: (-int(r["score"]), str(r["term"])))
    resp: Dict[str, Any] = {
        "query": q,
        "domain": domain,
        "count": min(len(results), int(top_k)),
        "results": results[: int(top_k)],
        "include_technical": include_technical,
    }
    if include_technical:
        resp["technical"] = {
            "snomed": snomed_candidates(q, tech_top_k, tech_score_cutoff),
            "loinc": loinc_candidates(q, tech_top_k, tech_score_cutoff),
        }

    # --- LOINC-only fallback: if we have no results (no SNOMED),
    # surface one sensible LOINC so Patient/Practitioner views aren't blank.
    if not resp["results"]:
        loinc_tech = (resp.get("technical", {}) or {}).get("loinc") if include_technical else \
                    loinc_candidates(q, tech_top_k, tech_score_cutoff)
        best = pick_best_loinc(loinc_tech or [], q)
        if best:
            entry = {
                "term": q,
                "aliases": [],
                # provide both object and flattened fields for UI compatibility
                "loinc": {"code": best.get("code"), "display": best.get("display")},
                "loinc_code": best.get("code"),
                "loinc_display": best.get("display"),
                "snomed": None,
                "score": 100,
                "patient_view": f"{q} ({best.get('display')})",
                "practitioner_view": best.get("display"),
                "practitioner_options": None,  # lab-only: no SNOMED picker
            }
            resp["results"] = [entry]
            resp["count"] = 1

    return resp


# -----------------------------------------------------------------------------
# Learn / Commit / Unlearn
# -----------------------------------------------------------------------------
class LearnPayload(BaseModel):
    term: str
    snomed_code: Optional[str] = None
    snomed_display: Optional[str] = None
    lay_text: str
    dry_run: bool = False

@app.post("/api/learn")
def api_learn(payload: LearnPayload):
    db = _read_json(LEARNED_JSON, default={}) or {}
    entry = db.get(payload.term) or {}
    # preserve existing fields like aliases/loinc if present
    entry["snomed"] = payload.snomed_code
    entry["snomed_display"] = payload.snomed_display
    entry["lay_text"] = payload.lay_text or payload.term
    db[payload.term] = entry
    if not payload.dry_run:
        _write_json(LEARNED_JSON, db)
        _append_learn_log({
            "ts": _now_iso(),
            "action": "api_learn",
            "term": payload.term,
            "snomed_code": payload.snomed_code,
            "snomed_display": payload.snomed_display,
            "lay_text": payload.lay_text,
        })
    # Return fresh lookup for convenience
    return {"ok": True, "result": lookup(q=payload.term, include_technical=False)}

from typing import Any, Dict
from fastapi import Body

@app.post("/api/commit_selection")
def commit_selection(payload: Dict[str, Any] = Body(...)):
    """
    Compatibility handler:
    - Accepts either {term, snomed_code, snomed_display, lay_text?, dry_run?}
      or      {term, code,         display,         lay_text?, dry_run?}
    - Normalizes to LearnPayload and reuses api_learn().
    """
    term = (payload.get("term") or payload.get("lay_text") or "").strip()
    if not term:
        raise HTTPException(status_code=400, detail="Missing term")

    # accept both key styles
    snomed_code = payload.get("snomed_code") or payload.get("code")
    snomed_display = payload.get("snomed_display") or payload.get("display")
    if not snomed_code or not snomed_display:
        raise HTTPException(status_code=400, detail="Missing SNOMED code/display")

    lp = LearnPayload(
        term=term,
        snomed_code=str(snomed_code),
        snomed_display=str(snomed_display),
        lay_text=(payload.get("lay_text") or term),
        dry_run=bool(payload.get("dry_run", False)),
    )
    return api_learn(lp)


class UnlearnPayload(BaseModel):
    term: str
    keep_aliases: bool = True

@app.post("/api/unlearn")
def api_unlearn(payload: UnlearnPayload):
    db = _read_json(LEARNED_JSON, default={}) or {}
    if payload.term in db:
        entry = db.get(payload.term) or {}
        if payload.keep_aliases:
            db[payload.term] = {
                "aliases": entry.get("aliases") or [],
                "lay_text": entry.get("lay_text") or payload.term,
                "snomed": None,
            }
        else:
            db.pop(payload.term, None)
        _write_json(LEARNED_JSON, db)
        _append_learn_log({
            "ts": _now_iso(),
            "action": "api_unlearn",
            "term": payload.term,
            "keep_aliases": payload.keep_aliases,
        })
    return {"ok": True}

# -----------------------------------------------------------------------------
# Health
# -----------------------------------------------------------------------------
@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/api/healthz")
def healthz_alias():
    return {"ok": True}

@app.get("/api/version")
def api_version():
    return {"ok": True, "data_hash": _data_hash()}

# -----------------------------------------------------------------------------
# Serve React build if it exists (SPA fallback)
# -----------------------------------------------------------------------------
if BUILD_DIR.exists():
    app.mount("/static", StaticFiles(directory=BUILD_DIR / "static"), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        index_file = BUILD_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail="Not Found")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        index_file = BUILD_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail="Not Found")