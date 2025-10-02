import json
from pathlib import Path

SNOMED = Path("data/snomed.json")

# Add/ensure these SNOMED concepts exist (idempotent)
ENTRIES = [
    ("29857009", "Chest pain"),
    ("267036007", "Dyspnea"),
    ("25064002", "Headache"),
    ("386661006", "Fever"),
    ("62315008", "Diarrhea"),
]

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

def upsert_list(data_list):
    # data is a list of {code, display, ...}
    code_index = {str(rec.get("code")): rec for rec in data_list if isinstance(rec, dict)}
    for code, display in ENTRIES:
        rec = code_index.get(code)
        if rec is None:
            data_list.append({"code": code, "display": display, "aliases": []})
        else:
            rec["code"] = code
            rec["display"] = display
            if "aliases" not in rec or not isinstance(rec["aliases"], list):
                rec["aliases"] = []
    return data_list

def upsert_dict(data_dict):
    # data is a dict keyed by code
    for code, display in ENTRIES:
        v = data_dict.get(code)
        if v is None:
            data_dict[code] = {"display": display, "aliases": []}
        elif isinstance(v, dict):
            v["display"] = display
            if "aliases" not in v or not isinstance(v["aliases"], list):
                v["aliases"] = []
        elif isinstance(v, str):
            data_dict[code] = {"display": display, "aliases": []}
        else:
            data_dict[code] = {"display": display, "aliases": []}
    return data_dict

if isinstance(data, list):
    data = upsert_list(data)
elif isinstance(data, dict):
    data = upsert_dict(data)
else:
    # Unexpected shape -> reset to minimal valid list with our entries
    data = [{"code": c, "display": d, "aliases": []} for c, d in ENTRIES]

save(data)
print("SNOMED patched for:", ", ".join(c for c, _ in ENTRIES))