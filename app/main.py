from __future__ import annotations
from fastapi import FastAPI, Query, Body
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import orjson

from app.learning import learn_selection, get_learned
from app.extensions.canonical_loinc import choose as choose_loinc

app = FastAPI(title="Akashic Lookup API (Overlay)")

@app.get("/healthz")
@app.get("/api/healthz")
def healthz():
    return {"ok": True}

# --- Tiny in-memory demo dictionaries to make the overlay smokable ---
_SNOMED = {
    "heart attack": {"code": "22298006", "display": "Myocardial infarction"},
    "watery eyes": {"code": "231834007", "display": "Epiphora"},
    "tearing": {"code": "231834007", "display": "Epiphora"},
    "high blood pressure": {"code": "38341003", "display": "Hypertension"},
}

class LookupResult(BaseModel):
    term: str
    aliases: List[str] = []
    loinc: Optional[str] = None
    snomed: Optional[str] = None
    score: int = 100
    patient_view: Optional[str] = None
    practitioner_view: Optional[str] = None
    practitioner_options: Dict[str, Any] = {}
    codeable_concept: Dict[str, Any] = {}

@app.get("/lookup")
def lookup(
    q: str = Query(..., alias="query"),
    domain: str = "auto",
    include_technical: bool = False,
    top_k: int = 5,
    score_cutoff: int = 70,
    tech_top_k: int = 8,
    tech_score_cutoff: int = 60,
):
    term = (q or "").strip().lower()

    # Try SNOMED demo dict
    snomed = _SNOMED.get(term)

    # Canonical LOINC for common labs
    loinc = choose_loinc(term)

    # Build response
    result = LookupResult(term=term)
    if snomed:
        result.snomed = snomed["code"]
        pv = f"{term} ({snomed['display']})"
        pr = f"{snomed['display']} ({term})"
        result.patient_view = pv
        result.practitioner_view = pr
        result.practitioner_options = {
            "snomed": [
                {"code": snomed["code"], "display": snomed["display"], "score": 100, "selected": True}
            ]
        }
        result.codeable_concept = {
            "coding": [
                {"system": "http://snomed.info/sct", "code": snomed["code"], "display": snomed["display"]}
            ],
            "text": term,
        }

    if loinc:
        result.loinc = loinc

    return {
        "ok": True,
        "query": term,
        "domain": domain,
        "count": 1 if (snomed or loinc) else 0,
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

