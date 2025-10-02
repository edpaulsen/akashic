# Minimal canonical LOINC chooser for common labs.
# Extend this map freely; prefer most widely used 'gold standard' LOINC codes.
CANONICAL = {
    "hemoglobin": "718-7",
    "creatinine": "2160-0",
    "ldl": "2089-1",
    "ldl cholesterol": "2089-1",
    "total cholesterol": "2093-3",
    "hdl": "2085-9",
}

def choose(term: str) -> str | None:
    key = (term or "").strip().lower()
    return CANONICAL.get(key)
