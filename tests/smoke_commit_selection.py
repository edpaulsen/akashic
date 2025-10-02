import json, sys, os
from datetime import datetime, timezone
from pathlib import Path
import urllib.request

BASE_URL = os.environ.get("AKASHIC_BASE_URL", "http://127.0.0.1:8000")
PAYLOAD_PATH = Path("data/payload.json")  # per your rule
LOG_DIR = Path("data/logs/learned")

def post_commit(payload: dict):
    req = urllib.request.Request(
        f"{BASE_URL}/api/commit_selection",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def today_log_path():
    # timezone-aware UTC date
    return LOG_DIR / (datetime.now(timezone.utc).date().isoformat() + ".log.jsonl")

def tail_log_for_term(term: str, max_lines=10):
    p = today_log_path()
    if not p.exists():
        return []
    out = []
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                j = json.loads(line)
                if (j.get("term") or "").strip().lower() == term.strip().lower():
                    out.append(j)
            except json.JSONDecodeError:
                pass
    return out[-max_lines:]

def main():
    if not PAYLOAD_PATH.exists():
        print(f"ERROR: {PAYLOAD_PATH} not found.")
        sys.exit(1)

    payload = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))
    term = (payload.get("term") or "").strip()
    if not term:
        print("ERROR: payload.term is required")
        sys.exit(1)

    # 1) Commit once (expect insert/update depending on current state)
    r1 = post_commit(payload)
    print("Commit #1:", {"ok": r1.get("ok"), "preview": r1.get("preview"), "action": r1.get("action")})

    # 2) Commit same again (expect noop)
    r2 = post_commit(payload)
    print("Commit #2:", {"ok": r2.get("ok"), "preview": r2.get("preview"), "action": r2.get("action")})

    # 3) Optional update with environment override
    alt_code = os.environ.get("ALT_CODE")
    alt_display = os.environ.get("ALT_DISPLAY", "")
    if alt_code:
        alt_payload = dict(payload)
        alt_payload["code"] = str(alt_code)
        if alt_display:
            alt_payload["display"] = alt_display
        r3 = post_commit(alt_payload)
        print("Commit #3 (alt):", {"ok": r3.get("ok"), "preview": r3.get("preview"), "action": r3.get("action")})

    # Show today's log entries for term
    logs = tail_log_for_term(term)
    print(f"Today’s log entries for '{term}': {len(logs)}")
    for j in logs:
        print(f"- {j.get('ts')}  {j.get('action')}  {j.get('snomed_code')}  {j.get('snomed_display')}")

if __name__ == "__main__":
    main()