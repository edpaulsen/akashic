# app/extensions/canonical_loinc.py
"""
Canonical LOINC chooser for common labs.
- Keep this opinionated and small; prefer the most widely used 'gold standard' codes.
- Add synonyms in ALIASES so end-user phrasing resolves to the same key.
"""

from typing import Optional

# Primary canonical keys (lowercase). Keep names short & generic.
CANONICAL: dict[str, str] = {
    # CBC / hematology
    "hemoglobin": "718-7",
    "hematocrit": "4544-3",
    "wbc": "6690-2",
    "rbc": "789-8",
    "platelets": "777-3",
    "mcv": "787-2",
    "mch": "785-6",
    "mchc": "786-4",
    "rdw": "788-0",
    "neutrophils absolute": "751-8",
    "lymphocytes absolute": "731-0",
    "monocytes absolute": "742-7",
    "eosinophils absolute": "711-2",
    "basophils absolute": "704-7",

    # BMP/CMP
    "sodium": "2951-2",
    "potassium": "2823-3",
    "chloride": "2075-0",
    "co2 (bicarbonate)": "2028-9",
    "bun": "3094-0",
    "creatinine": "2160-0",
    "glucose": "2345-7",
    "calcium": "17861-6",
    "total protein": "2885-2",
    "albumin": "1751-7",
    "bilirubin total": "1975-2",
    "alkaline phosphatase": "6768-6",
    "ast": "1920-8",
    "alt": "1742-6",

    # Lipids
    "cholesterol total": "2093-3",
    "hdl cholesterol": "2085-9",
    "ldl cholesterol": "2089-1",       # mass/volume, commonly used
    "ldl cholesterol (direct)": "18262-6",
    "triglycerides": "2571-8",
    "chol/hdl ratio": "9830-1",
    "non-hdl cholesterol": "43396-1",

    # Endocrine
    "hba1c": "4548-4",
    "tsh": "3016-3",
    "free t4": "3024-7",

    # Others commonly ordered
    "psa": "2857-1",
    "vitamin d 25-oh": "1989-3",
    "urine albumin/creatinine ratio": "9318-7",
}

# Common user phrases → canonical key
ALIASES: dict[str, str] = {
    # CBC
    "hgb": "hemoglobin",
    "hematocrit (hct)": "hematocrit",
    "white blood cell count": "wbc",
    "platelet count": "platelets",
    "neutrophils abs": "neutrophils absolute",
    "lymphocytes abs": "lymphocytes absolute",
    "monocytes abs": "monocytes absolute",
    "eosinophils abs": "eosinophils absolute",
    "basophils abs": "basophils absolute",

    # BMP/CMP
    "bicarbonate": "co2 (bicarbonate)",
    "co2": "co2 (bicarbonate)",
    "urea nitrogen": "bun",
    "serum creatinine": "creatinine",
    "blood glucose": "glucose",
    "total bilirubin": "bilirubin total",
    "alk phos": "alkaline phosphatase",
    "sgot": "ast",
    "sgpt": "alt",

    # Lipids
    "cholesterol": "cholesterol total",
    "hdl": "hdl cholesterol",
    "ldl": "ldl cholesterol",
    "ldl direct": "ldl cholesterol (direct)",
    "tg": "triglycerides",
    "cholesterol/hdl ratio": "chol/hdl ratio",
    "non-hdl": "non-hdl cholesterol",

    # Endocrine
    "a1c": "hba1c",
    "hemoglobin a1c": "hba1c",
    "thyroid stimulating hormone": "tsh",
    "ft4": "free t4",

    # Others
    "prostate specific antigen": "psa",
    "vit d": "vitamin d 25-oh",
    "25-oh vitamin d": "vitamin d 25-oh",
    "microalbumin/creatinine ratio": "urine albumin/creatinine ratio",
    "uacr": "urine albumin/creatinine ratio",
}

def _norm(s: Optional[str]) -> str:
    return (s or "").strip().lower()

def _canonical_key(term: str) -> Optional[str]:
    t = _norm(term)
    if t in CANONICAL:
        return t
    return ALIASES.get(t)

def choose(term: str) -> Optional[str]:
    """
    Return the canonical LOINC code for a given term/synonym, or None if unknown.
    """
    key = _canonical_key(term)
    if not key:
        return None
    return CANONICAL.get(key)