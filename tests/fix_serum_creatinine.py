import json, re
from pathlib import Path

def norm(s): return " ".join(re.findall(r"[a-z0-9]+", (s or "").lower()))
p = Path("data/layman_learned.json")
d = json.loads(p.read_text(encoding="utf-8"))

tn = norm("serum creatinine")
e = d.get(tn) or {}
# remove any SNOMED mapping
e.pop("snomed", None)
# ensure aliases include both lay forms
aliases = e.get("aliases", [])
for a in ["creatinine", "serum creatinine"]:
    if a not in aliases:
        aliases.append(a)
e["aliases"] = aliases
# set correct LOINC code (Serum/Plasma creatinine mass concentration)
e["loinc"] = {"code": "2160-0"}
d[tn] = e

p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
print("fixed:", tn)
