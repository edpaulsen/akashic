import csv, json, sys, argparse, pathlib

def pick_display(row):
    # Try common LOINC columns in order of preference
    for k in ("LONG_COMMON_NAME", "SHORTNAME", "COMPONENT", "EXTERNAL_COPYRIGHT_NOTICE"):
        if k in row and row[k].strip():
            return row[k].strip()
    # Fallback: join some key attributes if no names
    parts = [row.get("COMPONENT","").strip(), row.get("PROPERTY","").strip(), row.get("SYSTEM","").strip()]
    disp = " ".join([p for p in parts if p])
    return disp or row.get("LOINC_NUM","").strip()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-i","--input", required=True, help="Path to LOINC CSV")
    ap.add_argument("-o","--output", default="data/loinc.json", help="Output JSON path")
    args = ap.parse_args()

    inp = pathlib.Path(args.input)
    out = pathlib.Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    with inp.open("r", encoding="utf-8-sig", newline="") as f:
        rdr = csv.DictReader(f)
        if "LOINC_NUM" not in rdr.fieldnames:
            sys.exit("CSV is missing LOINC_NUM column.")
        seen = set()
        rows = []
        for row in rdr:
            code = (row.get("LOINC_NUM") or "").strip()
            if not code or code in seen:
                continue
            seen.add(code)
            display = pick_display(row)
            rows.append({"code": code, "display": display})

    with out.open("w", encoding="utf-8") as wf:
        json.dump(rows, wf, ensure_ascii=False, indent=2)
    print(f"Wrote {len(rows)} records to {out}")

if __name__ == "__main__":
    main()
    