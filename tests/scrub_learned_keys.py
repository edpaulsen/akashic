import json, re
from pathlib import Path

LEARNED = Path("data/layman_learned.json")

def norm(s: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", (s or "").lower()))

def as_str(x):
    return None if x is None else str(x)

def dedupe_keep_order(seq):
    seen = set(); out = []
    for s in seq or []:
        s = str(s)
        if s and s.lower() not in seen:
            seen.add(s.lower()); out.append(s)
    return out

def clean_entry(k, e):
    changed = False
    # drop UI/log-only fields
    for rm in ("lay_text", "raw_term", "display", "snomed_display"):
        if rm in e:
            e.pop(rm, None); changed = True
    # normalize loinc -> {"code": "<str>"} or remove
    if "loinc" in e:
        lo = e["loinc"]; code = None
        if isinstance(lo, dict):
            code = lo.get("code") or lo.get("LOINC_NUM") or lo.get("loinc_num") or lo.get("id")
        elif isinstance(lo, str):
            code = lo
        if code:
            e["loinc"] = {"code": as_str(code)}
        else:
            e.pop("loinc", None); changed = True
    # snomed -> string if present
    if "snomed" in e and e["snomed"] is not None:
        e["snomed"] = as_str(e["snomed"])
    # aliases -> list, include original key
    aliases = e.get("aliases") if isinstance(e.get("aliases"), list) else []
    if k not in aliases:
        aliases.append(k)
    e["aliases"] = dedupe_keep_order(aliases)
    return changed

def main():
    if not LEARNED.exists():
        print("No learned store found."); return
    data = json.loads(LEARNED.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        print("Unexpected JSON shape; aborting."); return

    out = {}
    moved = removed_fields = conflicts = 0

    for k, v in data.items():
        tn = norm(k)
        e = v.copy() if isinstance(v, dict) else {"snomed": as_str(v), "aliases": []}
        if clean_entry(k, e):
            removed_fields += 1
        if tn not in out:
            out[tn] = e
            if tn != k:
                moved += 1
        else:
            # merge into existing
            tgt = out[tn]
            if not tgt.get("snomed") and e.get("snomed"):
                tgt["snomed"] = e["snomed"]
            elif tgt.get("snomed") and e.get("snomed") and tgt["snomed"] != e["snomed"]:
                conflicts += 1  # keep existing code
            # merge aliases
            tgt["aliases"] = dedupe_keep_order((tgt.get("aliases") or []) + (e.get("aliases") or []))
            # merge loinc (only if missing)
            if not tgt.get("loinc") and e.get("loinc"):
                tgt["loinc"] = e["loinc"]

    LEARNED.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Scrubbed. moved_keys={moved}, removed_fields={removed_fields}, code_conflicts_kept={conflicts}, total_terms={len(out)}")

if __name__ == "__main__":
    main()
