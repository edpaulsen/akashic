import json
from pathlib import Path

LEARNED = Path("data/layman_learned.json")

def as_str(x):
    return None if x is None else str(x)

def clean_entry(e: dict) -> bool:
    changed = False

    # Remove any display-like fields
    for k in list(e.keys()):
        if k in {"display", "snomed_display"}:
            del e[k]
            changed = True

    # Migrate old key names
    if "snomed_code" in e and "snomed" not in e:
        e["snomed"] = as_str(e.pop("snomed_code"))
        changed = True

    # Normalize loinc to code-only (if present)
    if "loinc" in e:
        lo = e["loinc"]
        code = None
        if isinstance(lo, dict):
            code = lo.get("code") or lo.get("LOINC_NUM") or lo.get("loinc_num") or lo.get("id")
        elif isinstance(lo, str):
            code = lo
        if code:
            e["loinc"] = {"code": as_str(code)}
        else:
            del e["loinc"]
        changed = True

    # Ensure aliases is a de-duplicated list of strings
    aliases = e.get("aliases")
    if not isinstance(aliases, list):
        aliases = []
    # de-dupe while preserving order
    seen = set()
    deduped = []
    for a in aliases:
        s = str(a)
        if s and s not in seen:
            deduped.append(s)
            seen.add(s)
    if e.get("aliases") != deduped:
        e["aliases"] = deduped
        changed = True

    # Ensure snomed is a string if present
    if "snomed" in e and e["snomed"] is not None:
        e["snomed"] = as_str(e["snomed"])

    return changed

def main():
    if not LEARNED.exists():
        print(f"{LEARNED} not found; nothing to clean.")
        return

    try:
        data = json.loads(LEARNED.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print("JSON decode error; aborting to avoid data loss.")
        return

    if not isinstance(data, dict):
        print("Unexpected JSON shape (expected object at top level). Aborting.")
        return

    changed_any = False
    for term, entry in list(data.items()):
        if isinstance(entry, dict):
            changed_any |= clean_entry(entry)
        else:
            # If an old format stored just a code string/number
            data[term] = {"snomed": as_str(entry), "aliases": []}
            changed_any = True

    if changed_any:
        LEARNED.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print("Cleaned learned store: removed display fields & normalized entries.")
    else:
        print("No changes needed; store already code-only.")

if __name__ == "__main__":
    main()