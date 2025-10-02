import json, re
from pathlib import Path

def norm(s): 
    import re
    return " ".join(re.findall(r"[a-z0-9]+", (s or "").lower()))

need = {
    "watery eyes": "231834007",
    "high blood pressure": "38341003",
    "chest pain": "29857009",
    "shortness of breath": "267036007",
    "headache": "25064002",
    "fever": "386661006",
    "cough": "49727002",
    "diarrhea": "62315008",
}

p = Path("data/layman_learned.json")
d = json.loads(p.read_text(encoding="utf-8"))

ok, missing, wrong = [], [], []
for term, code in need.items():
    tn = norm(term)
    e = d.get(tn) or {}
    got = str(e.get("snomed") or "")
    if got == code:
        ok.append(term)
    elif tn not in d:
        missing.append(term)
    else:
        wrong.append((term, got))

print("OK:", len(ok), "Missing:", len(missing), "Wrong:", len(wrong))
if missing: print("Missing ->", ", ".join(missing))
if wrong: print("Wrong ->", ", ".join(f"{t} (has {g or 'none'})" for t,g in wrong))
