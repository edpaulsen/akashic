import os, io, json, tempfile, time, hashlib
from contextlib import contextmanager

_DEF_DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.getcwd(), "data"))

@contextmanager
def _file_lock(lock_path: str, timeout_s: int = 5):
    # Minimal cross-platform file lock using exclusive lockfile creation
    start = time.time()
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            try:
                yield
            finally:
                try:
                    os.close(fd)
                except Exception:
                    pass
                try:
                    os.remove(lock_path)
                except FileNotFoundError:
                    pass
            break
        except FileExistsError:
            if time.time() - start > timeout_s:
                raise TimeoutError(f"Lock timeout for {lock_path}")
            time.sleep(0.05)

def _ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)

def _read_json(path: str, default):
    if not os.path.exists(path):
        return default
    with io.open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _write_json_atomic(path: str, data):
    d = os.path.dirname(path)
    _ensure_dir(d)
    tmp_fd, tmp_path = tempfile.mkstemp(prefix=".tmp_", dir=d)
    try:
        with io.open(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        backup_path = path + ".bak"
        if os.path.exists(path):
            try:
                if os.path.exists(backup_path):
                    os.remove(backup_path)
            except FileNotFoundError:
                pass
            try:
                os.replace(path, backup_path)
            except FileNotFoundError:
                pass
        os.replace(tmp_path, path)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except FileNotFoundError:
            pass

def _now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def update_learned_mapping(term: str, snomed_code: str, snomed_display: str, lay_text: str,
                           data_dir: str = _DEF_DATA_DIR, keep_aliases: bool = True) -> dict:
    term_norm = (term or "").strip()
    if not term_norm:
        raise ValueError("term is required")
    if not snomed_code:
        raise ValueError("snomed_code is required")

    learned_path = os.path.join(data_dir, "layman_learned.json")
    logs_dir = os.path.join(data_dir, "logs", "learned")
    _ensure_dir(os.path.dirname(learned_path))
    _ensure_dir(logs_dir)

    lock_path = learned_path + ".lock"
    with _file_lock(lock_path):
        store = _read_json(learned_path, default={})
        store[term_norm] = {
            "snomed": str(snomed_code),
            "snomed_display": snomed_display,
            "lay_text": lay_text or term_norm,
        }
        _write_json_atomic(learned_path, store)

        # append JSONL log for the day
        today = time.strftime("%Y-%m-%d")
        log_file = os.path.join(logs_dir, f"{today}.jsonl")
        with io.open(log_file, "a", encoding="utf-8") as lf:
            lf.write(json.dumps({
                "ts": _now_iso(),
                "action": "api_learn",
                "term": term_norm,
                "snomed_code": str(snomed_code),
                "snomed_display": snomed_display,
                "lay_text": lay_text or term_norm,
            }, ensure_ascii=False) + "\n")

    return store[term_norm]

def unlearn_mapping(term: str, data_dir: str = _DEF_DATA_DIR, keep_aliases: bool = True) -> bool:
    term_norm = (term or "").strip()
    learned_path = os.path.join(data_dir, "layman_learned.json")
    if not os.path.exists(learned_path):
        return False

    lock_path = learned_path + ".lock"
    with _file_lock(lock_path):
        store = _read_json(learned_path, default={})
        existed = term_norm in store
        if existed:
            del store[term_norm]
            _write_json_atomic(learned_path, store)
        # log
        logs_dir = os.path.join(data_dir, "logs", "learned")
        _ensure_dir(logs_dir)
        today = time.strftime("%Y-%m-%d")
        log_file = os.path.join(logs_dir, f"{today}.jsonl")
        with io.open(log_file, "a", encoding="utf-8") as lf:
            lf.write(json.dumps({
                "ts": _now_iso(),
                "action": "api_unlearn",
                "term": term_norm,
                "kept_aliases": keep_aliases,
            }) + "\n")
    return existed
