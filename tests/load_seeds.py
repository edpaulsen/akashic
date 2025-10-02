import json, os, sys
from pathlib import Path
from urllib import request, error

BASE_URL = os.environ.get("AKASHIC_BASE_URL", "http://127.0.0.1:8000")
SEEDS = Path("data/seeds.jsonl")

def post_commit(payload: dict) -> dict:
    req = request.Request(
        f"{BASE_URL}/api/commit_selection",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def main():
    if not SEEDS.exists():
        print(f"ERROR: {SEEDS} not found.", file=sys.stderr)
        sys.exit(1)

    inserted = updated = noops = errors = 0

    with SEEDS.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                item = json.loads(line)
                term = (item.get("term") or "").strip()
                code = str(item.get("code") or "").strip()
                display = (item.get("display") or "").strip()
                lay_text = (item.get("lay_text") or term)

                if not term or not code or not display:
                    print(f"[line {lineno}] SKIP (missing fields): {line}")
                    continue

                payload = {
                    "term": term,
                    "code": code,
                    "display": display,
                    "lay_text": lay_text,
                    "dry_run": False,
                    "include_technical": False,
                }
                res = post_commit(payload)
                action = res.get("action", "unknown")
                if action == "insert":
                    inserted += 1
                elif action == "update":
                    updated += 1
                elif action == "noop":
                    noops += 1
                else:
                    errors += 1
                print(f"[line {lineno}] {term} → {code}  action={action}")

            except error.HTTPError as e:
                body = e.read().decode("utf-8", errors="ignore")
                print(f"[line {lineno}] ERROR HTTP {e.code} for {line}\n{body}")
                errors += 1
            except Exception as e:
                print(f"[line {lineno}] ERROR {e} for {line}")
                errors += 1

    print(f"\nSummary: insert={inserted} update={updated} noop={noops} errors={errors}")

if __name__ == "__main__":
    main()