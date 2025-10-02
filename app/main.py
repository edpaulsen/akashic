from __future__ import annotations
from fastapi import FastAPI, Query, Body
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from fastapi.responses import RedirectResponse
from app.learning import learn_selection
from app.extensions.canonical_loinc import choose as choose_loinc
from difflib import SequenceMatcher

app = FastAPI(title="Akashic Lookup API (Overlay)")

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.get("/healthz")
@app.get("/api/healthz")
def healthz():
    return {"ok": True}

# --- Deterministic SNOMED dictionary with aliases only (no fuzzy yet) ---
_SNOMED: Dict[str, Dict[str, Any]] = {
    # primary_term: {code, display, aliases}
    "heart attack": {
        "code": "22298006",
        "display": "Myocardial infarction",
        "aliases": ["myocardial infarction", "mi"],  # 'mi' will NOT resolve until fuzzy is added; kept here for later
    },
    "watery eyes": {
        "code": "231834007",
        "display": "Epiphora",
        "aliases": ["tearing", "tears", "watering eyes"],
    },
    "high blood pressure": {
        "code": "38341003",
        "display": "Hypertension",
        "aliases": ["htn", "high bp", "elevated blood pressure"],
    },
}

# Build deterministic alias index -> primary key
_ALIAS_INDEX: Dict[str, str] = {}
for pk, v in _SNOMED.items():
    _ALIAS_INDEX[pk.lower()] = pk
    for a in v.get("aliases", []) or []:
        _ALIAS_INDEX[a.strip().lower()] = pk

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

def _best_fuzzy(term: str, choices: list[str]) -> tuple[str | None, int]:
    """
    Returns (best_choice, score0to100) using difflib.
    """
    best = None
    best_score = 0
    for c in choices:
        s = int(round(SequenceMatcher(None, term, c).ratio() * 100))
        if s > best_score:
            best, best_score = c, s
    return best, best_score

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

    # 1) Deterministic SNOMED (primary or alias exact)
    snomed_code = None
    snomed_display = None

    pk = _ALIAS_INDEX.get(term)
    if not pk:
        # 2) Fuzzy fallback ONLY if no deterministic hit
        #    Accept if score >= 85 (policy)
        FUZZY_ACCEPT = 85
        best, score = _best_fuzzy(term, list(_ALIAS_INDEX.keys()))
        if best and score >= FUZZY_ACCEPT:
            pk = _ALIAS_INDEX[best]

    if pk:
        entry = _SNOMED[pk]
        snomed_code = entry["code"]
        snomed_display = entry["display"]
        result.snomed = snomed_code
        result.score = 100 if term == pk else 90  # 100 for exact, ~90 for accepted fuzzy
        result.patient_view = f"{term} ({snomed_display})"
        result.practitioner_view = f"{snomed_display} ({term})"
        result.practitioner_options = {
            "snomed": [
                {"code": snomed_code, "display": snomed_display, "score": result.score, "selected": True}
            ]
        }
        result.codeable_concept = {
            "coding": [{"system": "http://snomed.info/sct", "code": snomed_code, "display": snomed_display}],
            "text": term,
        }

    # LOINC canonical still applies independently
    result.loinc = choose_loinc(term)

    return {
        "ok": True,
        "query": term,
        "domain": domain,
        "count": 1 if (result.snomed or result.loinc) else 0,
        "results": [result.model_dump()],
        "include_technical": include_technical,
    }
        def _best_fuzzy(term: str, choices: list[str]) -> tuple[str | None, int]:
    """
    Returns (best_choice, score0to100) using difflib.
    """
    best = None
    best_score = 0
    for c in choices:
        s = int(round(SequenceMatcher(None, term, c).ratio() * 100))
        if s > best_score:
            best, best_score = c, s
    return best, best_score

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

        # 1) Deterministic SNOMED (primary or alias exact)
        snomed_code = None
        snomed_display = None

        pk = _ALIAS_INDEX.get(term)
        if not pk:
            # 2) Fuzzy fallback ONLY if no deterministic hit
            #    Accept if score >= 85 (policy)
            FUZZY_ACCEPT = 85
            best, score = _best_fuzzy(term, list(_ALIAS_INDEX.keys()))
            if best and score >= FUZZY_ACCEPT:
                pk = _ALIAS_INDEX[best]

        if pk:
            entry = _SNOMED[pk]
            snomed_code = entry["code"]
            snomed_display = entry["display"]
            result.snomed = snomed_code
            result.score = 100 if term == pk else 90  # 100 for exact, ~90 for accepted fuzzy
            result.patient_view = f"{term} ({snomed_display})"
            result.practitioner_view = f"{snomed_display} ({term})"
            result.practitioner_options = {
                "snomed": [
                    {"code": snomed_code, "display": snomed_display, "score": result.score, "selected": True}
                ]
            }
            result.codeable_concept = {
                "coding": [{"system": "http://snomed.info/sct", "code": snomed_code, "display": snomed_display}],
                "text": term,
            }

        # LOINC canonical still applies independently
        result.loinc = choose_loinc(term)

        return {
            "ok": True,
            "query": term,
            "domain": domain,
            "count": 1 if (result.snomed or result.loinc) else 0,
            "results": [result.model_dump()],
            "include_technical": include_technical,
        }
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

    # Deterministic SNOMED resolution (exact primary or alias only)
    snomed_code = None
    snomed_display = None

    pk = _ALIAS_INDEX.get(term)
    if pk:
        entry = _SNOMED[pk]
        snomed_code = entry["code"]
        snomed_display = entry["display"]
        result.snomed = snomed_code
        result.score = 100  # deterministic match
        result.patient_view = f"{term} ({snomed_display})"
        result.practitioner_view = f"{snomed_display} ({term})"
        result.practitioner_options = {
            "snomed": [
                {"code": snomed_code, "display": snomed_display, "score": 100, "selected": True}
            ]
        }
        result.codeable_concept = {
            "coding": [{"system": "http://snomed.info/sct", "code": snomed_code, "display": snomed_display}],
            "text": term,
        }

    # Canonical LOINC chooser still applies independently (e.g., for labs)
    result.loinc = choose_loinc(term)

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