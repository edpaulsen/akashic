import os, io, json, hashlib

_DEF_DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.getcwd(), "data"))

class DataCache:
    def __init__(self, data_dir: str | None = None):
        self.data_dir = data_dir or _DEF_DATA_DIR
        self.snomed = []
        self.loinc = []
        self.hash = ""
        self.reload()

    def _sha256_file(self, path: str) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def reload(self):
        snomed_path = os.path.join(self.data_dir, "snomed.json")
        loinc_path = os.path.join(self.data_dir, "loinc.json")

        if os.path.exists(snomed_path):
            with io.open(snomed_path, "r", encoding="utf-8") as f:
                self.snomed = json.load(f)
        else:
            self.snomed = []

        if os.path.exists(loinc_path):
            with io.open(loinc_path, "r", encoding="utf-8") as f:
                self.loinc = json.load(f)
        else:
            self.loinc = []

        h_parts = []
        if os.path.exists(snomed_path):
            h_parts.append(self._sha256_file(snomed_path))
        if os.path.exists(loinc_path):
            h_parts.append(self._sha256_file(loinc_path))
        joined = "|".join(h_parts).encode("utf-8")
        self.hash = hashlib.sha256(joined).hexdigest()

    def get_hash(self) -> str:
        return self.hash

_cache_instance: DataCache | None = None

def get_data_cache(data_dir: str | None = None) -> DataCache:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = DataCache(data_dir=data_dir)
    return _cache_instance
