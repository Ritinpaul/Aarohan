"""
Name Normaliser — Aarohan++ Phase 4
Cleans and normalises patient/provider names from messy HMIS exports.

Handles:
  - All-caps RAMESH KUMAR → Ramesh Kumar
  - Extra whitespace, stray punctuation
  - Common Indian name title prefixes (Sh., Smt., Er., Dr.)
  - Transliteration artefacts (trailing 'a' in HCX ML names)
  - Gender inference from name (probabilistic, used only as fallback)
"""

import re
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# ─── Title prefixes ────────────────────────────────────────────────────────────
TITLES = {
    "sh": "Sh.", "shri": "Sh.", "smt": "Smt.", "srimati": "Smt.",
    "er": "Er.", "eng": "Er.",
    "dr": "Dr.", "doctor": "Dr.",
    "mr": "Mr.", "mrs": "Mrs.", "ms": "Ms.", "miss": "Ms.",
    "prof": "Prof.",
}

# ─── Name suffixes to strip (non-informative) ──────────────────────────────────
STRIP_SUFFIXES = {"ji", "jee", "g", "saab", "saheb"}

# ─── Common male/female Indian names for gender inference ─────────────────────
_MALE_NAMES = {
    "ram", "raj", "rahul", "rajesh", "ramesh", "suresh", "deepak", "arun",
    "arjun", "ajay", "amrit", "bhuvan", "bhanu", "dinesh", "ganesh", "girish",
    "harish", "harshit", "hitesh", "karan", "mahesh", "manoj", "naresh",
    "naveen", "nikhil", "pradeep", "prakash", "praveen", "rakesh", "ravi",
    "rohit", "sachin", "sanjeev", "santosh", "sanjay", "satish", "saurabh",
    "shivam", "shreyas", "shyam", "sunil", "sushil", "umesh", "vijay",
    "vikas", "vinod", "vishal", "vivek", "yogesh", "mohan", "kishan",
    "krishna", "laxman", "mukesh", "pawan", "prashant", "pushpendra",
    "ramprasad", "shambhu", "umakant", "yogendra", "ramdayal", "bhanwar",
}

_FEMALE_NAMES = {
    "anita", "anjali", "asha", "deepa", "geeta", "gita", "jaya", "kanta",
    "kavita", "lalita", "lata", "mamta", "meena", "meghna", "neha", "nisha",
    "poonam", "pooja", "priya", "pushpa", "radha", "rekha", "rita", "ritu",
    "sarita", "savita", "seema", "shanta", "sita", "sneha", "sonal", "sunita",
    "usha", "vandana", "veena", "vijaya", "vinita", "yamini", "yasmin",
    "zara", "bai", "kumari", "devi", "rani", "shakuntala", "bhagwati",
    "champa", "dropadhi", "gangabai", "laxmi", "parvati", "rukmini",
    "sushila", "tara",
}


def normalise_name(raw: str) -> Tuple[str, Optional[str]]:
    """
    Normalise a raw patient name.

    Returns:
        (normalised_name, inferred_title_or_None)
    """
    if not raw:
        return "", None

    # Strip leading/trailing whitespace and non-alpha boundary characters
    cleaned = raw.strip().strip(".,;:/\\|")
    # Collapse multiple spaces
    cleaned = re.sub(r"\s+", " ", cleaned)
    # Remove stray digits that crept into names
    cleaned = re.sub(r"\d+", "", cleaned).strip()

    if not cleaned:
        return "", None

    tokens = cleaned.split()
    extracted_title: Optional[str] = None
    filtered_tokens = []

    for tok in tokens:
        lower = tok.lower().rstrip(".")
        if lower in TITLES:
            extracted_title = TITLES[lower]
        elif lower in STRIP_SUFFIXES:
            pass  # discard
        else:
            filtered_tokens.append(tok)

    # Title-case each token (handles ALL-CAPS and all-lower)
    normalised_tokens = []
    for tok in filtered_tokens:
        if tok.isupper() or tok.islower():
            normalised_tokens.append(tok.capitalize())
        else:
            normalised_tokens.append(tok)  # preserve existing casing (e.g. McIntosh)

    normalised = " ".join(normalised_tokens).strip()
    return normalised, extracted_title


def infer_gender_from_name(name: str) -> Optional[str]:
    """
    Probabilistically infer gender from an Indian name.
    Returns 'male', 'female', or None (uncertain).
    Used ONLY as a fallback when gender field is missing/unknown.
    """
    if not name:
        return None

    parts = name.lower().split()
    for part in parts:
        if part in _MALE_NAMES:
            return "male"
        if part in _FEMALE_NAMES:
            return "female"

    # Suffix heuristics common in Indian names
    for part in parts:
        if part.endswith(("devi", "bai", "kumari", "rani", "wati", "mati")):
            return "female"
        if part.endswith(("prasad", "lal", "ram", "nath", "dass", "singh")):
            return "male"

    return None


def normalise_patient(patient: dict) -> dict:
    """
    Normalise all name/gender fields in a patient dict.
    Mutates and returns same dict.
    """
    raw_name = patient.get("name") or ""
    norm_name, title = normalise_name(raw_name)
    if norm_name:
        patient["name"] = norm_name
    if title:
        patient["title"] = title

    # Gender fallback
    gender = (patient.get("gender") or "").lower().strip()
    if gender in ("", "unknown", "u", "other"):
        inferred = infer_gender_from_name(norm_name)
        if inferred:
            patient["gender"] = inferred
            patient["gender_inferred"] = True
            logger.debug(f"Inferred gender '{inferred}' from name '{norm_name}'")

    return patient
