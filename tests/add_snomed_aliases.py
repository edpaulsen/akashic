import json
from pathlib import Path

SNOMED = Path("data/snomed.json")

ALIASES = {
    "29857009": ["chest pain", "cp", "chest discomfort"],
    "267036007": ["shortness of breath", "sob", "breathlessness"],
    "25064002": ["headache", "head pain"],
    "386661006": ["fever", "pyrexia", "elevated temperature"],
    "62315008": ["diarrhea", "diarrhoea", "loose stools"],
    "231834007": ["watery eyes", "epiphora"],
    "38341003": ["high blood pressure", "hypertension", "htn"],
    "49727002": ["cough"],
}

def ensure_list(v):
    return v if isinstance(v, list) else ([] if v is None else [v])

def dedupe_keep_order(seq):
    seen = set(); out = []
    for s in seq:
        s = str(s).strip()
        key = s.lower()
        if s and key not in seen:
            seen.add(key); out.append(s)
    return out

def load():
    if not SNOMED.exists():
        return []
    try:
        return json.loads(SNOMED.read_text(encoding="utf-8"))
    except Exception:
        return []

def save(obj):
    SNOMED.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

data = load()

if isinstance(data, list):
    by_code = {str(rec.get("code")): rec for rec in data if isinstance(rec, dict)}
    for code, adds in ALIASES.items():
        rec = by_code.get(code)
        if not rec:
            rec = {"code": code, "display": "", "aliases": []}
            data.append(rec)
        rec["aliases"] = dedupe_keep_order(ensure_list(rec.get("aliases")) + list(adds))
elif isinstance(data, dict):
    for code, adds in ALIASES.items():
        v = data.get(code)
        if v is None:
            data[code] = {"display": "", "aliases": list(adds)}
        elif isinstance(v, dict):
            v["aliases"] = dedupe_keep_order(ensure_list(v.get("aliases")) + list(adds))
        elif isinstance(v, str):
            data[code] = {"display": v, "aliases": list(adds)}
        else:
            data[code] = {"display": "", "aliases": list(adds)}
else:
    # reset to minimal if shape unknown
    data = [{"code": c, "display": "", "aliases": list(a)} for c, a in ALIASES.items()]

save(data)
print("SNOMED aliases updated for:", ", ".join(sorted(ALIASES.keys())))
