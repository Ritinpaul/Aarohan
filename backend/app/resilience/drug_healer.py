"""
Drug Healer — Aarohan++ Phase 4
Extends Phase 3 DrugCodeMapper with:
  - Brand name → Generic name resolution
  - Multi-drug string splitting (e.g. "Tab Metformin 500mg + Glimepiride 2mg")
  - Dosage information extraction
  - Duration parsing
  - Auto-assign NRCeS drug codes after enrichment

Wraps the existing DrugCodeMapper from Phase 3.
"""

import re
import logging
from typing import Optional
from app.fhir.drug_mapper import get_mapper

logger = logging.getLogger(__name__)

# ─── Brand → Generic (most common Indian brands) ─────────────────────────────
BRAND_GENERIC_MAP: dict[str, str] = {
    # Diabetes
    "glucophage": "metformin",
    "glycomet": "metformin",
    "amaryl": "glimepiride",
    "januvia": "sitagliptin",
    "galvus": "vildagliptin",

    # Cardiovascular
    "norvasc": "amlodipine",
    "amlokind": "amlodipine",
    "metoprolol xl": "metoprolol",
    "betaloc": "metoprolol",
    "ecosprin": "aspirin",
    "loprin": "aspirin",
    "disprin": "aspirin",
    "rosuvas": "rosuvastatin",
    "atocor": "atorvastatin",
    "ator": "atorvastatin",

    # Pain / Fever
    "crocin": "paracetamol",
    "calpol": "paracetamol",
    "dolo": "paracetamol",
    "combiflam": "ibuprofen+paracetamol",
    "brufen": "ibuprofen",
    "nurofen": "ibuprofen",
    "voveran": "diclofenac",
    "ultracet": "tramadol+paracetamol",

    # Gastro
    "pantocid": "pantoprazole",
    "pan": "pantoprazole",
    "omez": "omeprazole",
    "zantac": "ranitidine",

    # Antibiotics
    "taxim": "cefotaxime",
    "augmentin": "amoxicillin+clavulanate",
    "novamox": "amoxicillin",
    "zithromax": "azithromycin",
    "azee": "azithromycin",
    "ciprobay": "ciprofloxacin",
    "ciplox": "ciprofloxacin",
    "norflox": "norfloxacin",

    # Respiratory
    "foracort": "formoterol+budesonide",
    "budecort": "budesonide",
    "salbutamol": "salbutamol",
    "asthalin": "salbutamol",
    "deriphyllin": "theophylline+etofylline",

    # Vitamins / Supplements
    "limcee": "vitamin c",
    "becosules": "vitamin b complex",
    "dexorange": "iron+folic acid",
    "folvite": "folic acid",
}

# ─── Dosage pattern ───────────────────────────────────────────────────────────
_DOSAGE_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml|iu|units?|tab(?:lets?)?|cap(?:sules?)?|vial)",
    re.IGNORECASE,
)

# ─── Duration pattern ─────────────────────────────────────────────────────────
_DURATION_PATTERN = re.compile(
    r"(?:for\s+)?(\d+)\s*(day|week|month|hr|hour)s?",
    re.IGNORECASE,
)

# ─── Separator for multi-drug strings ────────────────────────────────────────
_DRUG_SEPARATOR = re.compile(r"[,+&]|\band\b|\bwith\b|\bplus\b", re.IGNORECASE)


def _resolve_brand(name: str) -> str:
    """Convert brand name to generic if known."""
    lower = name.strip().lower()
    return BRAND_GENERIC_MAP.get(lower, lower)


def _extract_dosage(text: str) -> Optional[str]:
    m = _DOSAGE_PATTERN.search(text)
    if m:
        return f"{m.group(1)} {m.group(2).lower()}"
    return None


def _extract_duration_days(text: str) -> Optional[int]:
    m = _DURATION_PATTERN.search(text)
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2).lower()
    if unit.startswith("day"):
        return n
    if unit.startswith("week"):
        return n * 7
    if unit.startswith("month"):
        return n * 30
    return None


def _clean_drug_name(text: str) -> str:
    """Strip route/form prefixes like Tab., Inj., Syp., Cap. and trailing dosage info."""
    text = re.sub(
        r"^\s*(tab|tablet|inj|injection|syp|syrup|cap|capsule|oint|ointment|drop|sol|solution)\s*\.?\s*",
        "", text, flags=re.IGNORECASE
    ).strip()
    # Remove dosage suffix for name purposes
    text = _DOSAGE_PATTERN.sub("", text).strip()
    return text.strip(".,-/ ")


def split_multi_drug(text: str) -> list[str]:
    """
    Split a multi-drug string like "Metformin 500mg + Glimepiride 2mg" 
    into individual drug strings.
    """
    parts = _DRUG_SEPARATOR.split(text)
    result = [p.strip() for p in parts if p.strip()]
    return result if len(result) > 1 else [text]


def heal_single_medication(med: dict, mapper) -> list[dict]:
    """
    Heal a single medication dict.
    May return multiple dicts if the original was a multi-drug string.
    """
    text = (med.get("text") or med.get("generic_name") or "").strip()
    if not text:
        return [med]

    # Check if multi-drug
    drug_parts = split_multi_drug(text)
    if len(drug_parts) > 1:
        result = []
        for part in drug_parts:
            new_med = {**med, "text": part, "_split_from": text}
            result.extend(heal_single_medication(new_med, mapper))
        return result

    # Extract dosage and duration
    dosage = _extract_dosage(text)
    duration = _extract_duration_days(text)
    clean_name = _clean_drug_name(text)
    generic_name = _resolve_brand(clean_name)

    updated = {**med}
    if dosage and not updated.get("dosage_instruction"):
        updated["dosage_instruction"] = dosage
    if duration and not updated.get("duration_days"):
        updated["duration_days"] = duration
    if generic_name != clean_name.lower():
        updated["generic_name"] = generic_name
        updated["brand_resolved"] = True

    # Enrich with NRCeS drug code
    if not updated.get("code"):
        map_result = mapper.map(generic_name or clean_name)
        if map_result.get("code"):
            updated["code"] = map_result["code"]
            updated["system"] = "https://nrces.in/ndhm/fhir/r4/StructureDefinition/Drug"
            updated["code_confidence"] = map_result.get("confidence", 0)
            updated["code_match_type"] = map_result.get("match_type", "none")

    return [updated]


def heal_medications(medications: list) -> list:
    """
    Heal a list of medication dicts.
    May expand multi-drug entries.
    """
    mapper = get_mapper()
    healed = []
    for med in medications:
        healed.extend(heal_single_medication(med, mapper))
    return healed
