import os, io, json

_DEF_PATH = os.environ.get("DOMAIN_PROFILE_PATH", os.path.join(os.getcwd(), "data", "domain_profile.json"))

def load_domain_profile(path: str | None = None) -> dict:
    p = path or _DEF_PATH
    try:
        with io.open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def resolve_allowed_systems(profile: dict, context: str | None, domain: str | None) -> set[str]:
    # If a context is provided and present in profile, honor it
    if context and context in profile:
        return set(s.lower() for s in profile[context])
    # Else honor explicit domain if not 'auto'
    if domain and domain.lower() != "auto":
        return {domain.lower()}
    # Default for 'auto': allow both SNOMED and LOINC
    return {"snomed", "loinc"}