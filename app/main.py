from __future__ import annotations
from fastapi import FastAPI, Query, Body
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.learning import learn_selection
from app.extensions.canonical_loinc import choose as choose_loinc
from app.data.snomed_loader import get_snomed_db  # reads data/snomed.json
from app.data.loinc_loader import normalize_loinc_term
import os, json



app = FastAPI(title="Akashic Lookup API")

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")

@app.get("/healthz")
@app.get("/api/healthz")
def healthz():
    return {"ok": True}


@app.get("/readyz")
def readyz():
    # counts (never crash)
    try:
        db, _ = get_snomed_db()
        snomed_count = len(db)
    except Exception:
        snomed_count = -1
    try:
        aliases_path = os.getenv("LOINC_ALIASES_JSON", "data/loinc_aliases.json")
        with open(aliases_path, "r", encoding="utf-8-sig") as f:
            loinc_aliases = json.load(f)
        loinc_alias_count = len(loinc_aliases) if isinstance(loinc_aliases, dict) else 0
    except Exception:
        loinc_alias_count = -1
        aliases_path = os.getenv("LOINC_ALIASES_JSON", "data/loinc_aliases.json")
    try:
        canon_path = os.getenv("LOINC_CANONICAL_JSON", "data/loinc_canonical.json")
        with open(canon_path, "r", encoding="utf-8-sig") as f:
            loinc_canon = json.load(f)
        loinc_canon_count = len(loinc_canon) if isinstance(loinc_canon, dict) else 0
    except Exception:
        loinc_canon_count = -1
        canon_path = os.getenv("LOINC_CANONICAL_JSON", "data/loinc_canonical.json")
    return {
        "ok": True,
        "counts": {
            "snomed_entries": snomed_count,
            "loinc_aliases": loinc_alias_count,
            "loinc_canonicals": loinc_canon_count
        },
        "paths": {
            "snomed_json": os.getenv("SNOMED_JSON", "data/snomed.json"),
            "loinc_aliases_json": aliases_path,
            "loinc_canonical_json": canon_path
        }
    }

@app.get("/version")
def version():
    sha = os.getenv("GITHUB_SHA") or os.getenv("COMMIT_SHA") or "local"
    return {"version": sha}


class LookupResult(BaseModel):
    term: str
    aliases: List[str] = []
    loinc: Optional[str] = None
    snomed: Optional[str] = None
    score: int = 0
    patient_view: Optional[str] = None
    practitioner_view: Optional[str] = None
    practitioner_options: Dict[str, Any] = {}
    codeable_concept: Dict[str, Any] = {}

@app.get("/lookup")
def lookup(
    query: str = Query(...),
    domain: str = "auto",
    include_technical: bool = False,
    top_k: int = 5,
    score_cutoff: int = 70,
    tech_top_k: int = 8,
    tech_score_cutoff: int = 60,
):
    term = (query or "").strip().lower()
    result = LookupResult(term=term)

    # Deterministic SNOMED from data/snomed.json (no fuzzy)
    db, alias_index = get_snomed_db()
    pk = alias_index.get(term)
    if pk:
        entry = db[pk]
        snomed_code = entry["code"]
        snomed_display = entry["display"]
        result.snomed = snomed_code
        result.score = 100
        result.patient_view = f"{term} ({snomed_display})"
        result.practitioner_view = f"{snomed_display} ({term})"
        result.practitioner_options = {
            "snomed": [
                {"code": snomed_code, "display": snomed_display, "score": 100, "selected": True}
            ]
        }
        result.codeable_concept = {
            "coding": [
                {"system": "http://snomed.info/sct", "code": snomed_code, "display": snomed_display}
            ],
            "text": term,
        }

    # Canonical LOINC still applies independently (for labs)
    loinc_key = normalize_loinc_term(term)   
    result.loinc = choose_loinc(loinc_key)

    return {
        "ok": True,
        "query": term,
        "domain": domain,
        "count": 1 if (result.snomed or result.loinc) else 0,
        "results": [result.model_dump()],
        "include_technical": include_technical,
    }

class CommitPayload(BaseModel):
    term: str
    code: Optional[str] = None
    display: Optional[str] = None
    lay_text: Optional[str] = None
    dry_run: bool = False
    context: Optional[str] = None

@app.post("/api/commit_selection")
def commit_selection(payload: CommitPayload = Body(...)):
    if payload.dry_run:
        return {"ok": True, "preview": True, "action": "preview", "payload": payload.model_dump()}
    res = learn_selection(
        term=payload.term,
        snomed_code=payload.code,
        snomed_display=payload.display, 
        lay_text=payload.lay_text or payload.term,
        context=payload.context,
    )
    return {"ok": True, "preview": False, "result": res} 