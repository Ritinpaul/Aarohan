"""
Drug Code Mapper — Aarohan++ Phase 3
Maps brand/generic drug names to NRCeS drug codes using:
  1. Exact match in local drugs.json seed
  2. Fuzzy match via rapidfuzz
  3. Falls back to free-text if no match found
"""

import json
import logging
from pathlib import Path
from typing import Optional
from rapidfuzz import fuzz, process

logger = logging.getLogger(__name__)

_SEED_DIR = Path(__file__).parent.parent.parent / "data" / "seed"
_DRUGS_PATH = _SEED_DIR / "drugs.json"

NRCES_DRUG_SYSTEM = "https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-drugcode"
RXNORM_SYSTEM = "http://www.nlm.nih.gov/research/umls/rxnorm"

# Built-in essential drugs (augmented from seed file)
_ESSENTIAL_DRUGS = {
    # Diabetes
    "metformin":       {"code": "MET500",     "system": NRCES_DRUG_SYSTEM, "generic": "Metformin"},
    "insulin":         {"code": "INS001",     "system": NRCES_DRUG_SYSTEM, "generic": "Insulin"},
    "glibenclamide":   {"code": "GLIB300",    "system": NRCES_DRUG_SYSTEM, "generic": "Glibenclamide"},
    # Hypertension
    "amlodipine":      {"code": "AML5",       "system": NRCES_DRUG_SYSTEM, "generic": "Amlodipine"},
    "enalapril":       {"code": "ENAL10",     "system": NRCES_DRUG_SYSTEM, "generic": "Enalapril"},
    "losartan":        {"code": "LOS50",      "system": NRCES_DRUG_SYSTEM, "generic": "Losartan"},
    "telmisartan":     {"code": "TELM40",     "system": NRCES_DRUG_SYSTEM, "generic": "Telmisartan"},
    # Antibiotics
    "amoxicillin":     {"code": "AMOX500",    "system": NRCES_DRUG_SYSTEM, "generic": "Amoxicillin"},
    "ciprofloxacin":   {"code": "CIP500",     "system": NRCES_DRUG_SYSTEM, "generic": "Ciprofloxacin"},
    "azithromycin":    {"code": "AZI500",     "system": NRCES_DRUG_SYSTEM, "generic": "Azithromycin"},
    "doxycycline":     {"code": "DOX100",     "system": NRCES_DRUG_SYSTEM, "generic": "Doxycycline"},
    # Pain/Fever
    "paracetamol":     {"code": "PAR500",     "system": NRCES_DRUG_SYSTEM, "generic": "Paracetamol"},
    "ibuprofen":       {"code": "IBU400",     "system": NRCES_DRUG_SYSTEM, "generic": "Ibuprofen"},
    "diclofenac":      {"code": "DIC50",      "system": NRCES_DRUG_SYSTEM, "generic": "Diclofenac"},
    # Antacids
    "omeprazole":      {"code": "OME20",      "system": NRCES_DRUG_SYSTEM, "generic": "Omeprazole"},
    "pantoprazole":    {"code": "PAN40",      "system": NRCES_DRUG_SYSTEM, "generic": "Pantoprazole"},
    "ranitidine":      {"code": "RAN150",     "system": NRCES_DRUG_SYSTEM, "generic": "Ranitidine"},
    # Bronchodilators
    "salbutamol":      {"code": "SAL2",       "system": NRCES_DRUG_SYSTEM, "generic": "Salbutamol"},
    "theophylline":    {"code": "THEO200",    "system": NRCES_DRUG_SYSTEM, "generic": "Theophylline"},
    # Vitamins
    "folic acid":      {"code": "FOL5",       "system": NRCES_DRUG_SYSTEM, "generic": "Folic Acid"},
    "iron":            {"code": "FE200",      "system": NRCES_DRUG_SYSTEM, "generic": "Ferrous Sulphate"},
    "calcium":         {"code": "CA500",      "system": NRCES_DRUG_SYSTEM, "generic": "Calcium Carbonate"},
    # Antiparasitics
    "albendazole":     {"code": "ALB400",     "system": NRCES_DRUG_SYSTEM, "generic": "Albendazole"},
    "chloroquine":     {"code": "CHLOR150",   "system": NRCES_DRUG_SYSTEM, "generic": "Chloroquine"},
    "artemether":      {"code": "ARTEM20",    "system": NRCES_DRUG_SYSTEM, "generic": "Artemether"},
    # Anticoagulants
    "aspirin":         {"code": "ASP75",      "system": NRCES_DRUG_SYSTEM, "generic": "Aspirin"},
    "warfarin":        {"code": "WAR5",       "system": NRCES_DRUG_SYSTEM, "generic": "Warfarin"},
    "clopidogrel":     {"code": "CLOP75",     "system": NRCES_DRUG_SYSTEM, "generic": "Clopidogrel"},
    # Antidepressants
    "amitriptyline":   {"code": "AMITRI25",   "system": NRCES_DRUG_SYSTEM, "generic": "Amitriptyline"},
    "escitalopram":    {"code": "ESCIT10",    "system": NRCES_DRUG_SYSTEM, "generic": "Escitalopram"},
    # Corticosteroids
    "prednisolone":    {"code": "PRED10",     "system": NRCES_DRUG_SYSTEM, "generic": "Prednisolone"},
    "dexamethasone":   {"code": "DEX4",       "system": NRCES_DRUG_SYSTEM, "generic": "Dexamethasone"},
    "hydrocortisone":  {"code": "HYDRO100",   "system": NRCES_DRUG_SYSTEM, "generic": "Hydrocortisone"},
    # Antiemetics
    "ondansetron":     {"code": "OND4",       "system": NRCES_DRUG_SYSTEM, "generic": "Ondansetron"},
    "metoclopramide":  {"code": "METO10",     "system": NRCES_DRUG_SYSTEM, "generic": "Metoclopramide"},
    # Diuretics
    "furosemide":      {"code": "FUR40",      "system": NRCES_DRUG_SYSTEM, "generic": "Furosemide"},
    "spironolactone":  {"code": "SPIRO25",    "system": NRCES_DRUG_SYSTEM, "generic": "Spironolactone"},
}


class DrugCodeMapper:
    """
    Maps drug names (brand or generic) to NRCeS drug codes.
    Uses: exact match → seed file match → fuzzy match → fallback.
    """

    def __init__(self):
        self.drug_map = dict(_ESSENTIAL_DRUGS)
        self._load_seed()
        self._keywords = list(self.drug_map.keys())

    def _load_seed(self):
        """Load additional drugs from seed/drugs.json if present."""
        if not _DRUGS_PATH.exists():
            return
        try:
            with open(_DRUGS_PATH, encoding="utf-8") as f:
                data = json.load(f)
            for entry in data.get("drugs", []):
                key = entry.get("generic_name", "").lower().strip()
                if key:
                    self.drug_map[key] = {
                        "code": entry.get("code", ""),
                        "system": entry.get("system", NRCES_DRUG_SYSTEM),
                        "generic": entry.get("generic_name", ""),
                    }
            logger.info(f"Loaded {len(data.get('drugs', []))} additional drugs from seed")
        except Exception as e:
            logger.warning(f"Failed to load drugs.json: {e}")

    def map(self, drug_name: str) -> dict:
        """
        Map a drug name to a coding dict.

        Returns:
            dict with 'code', 'system', 'generic', 'confidence', 'match_type'
        """
        if not drug_name:
            return self._fallback("", 0.0, "empty")

        lower = drug_name.strip().lower()

        # 1) Exact match
        if lower in self.drug_map:
            entry = self.drug_map[lower]
            return {**entry, "confidence": 1.0, "match_type": "exact", "input": drug_name}

        # 2) Starts-with match
        for key, entry in self.drug_map.items():
            if lower.startswith(key) or key.startswith(lower):
                return {**entry, "confidence": 0.9, "match_type": "prefix", "input": drug_name}

        # 3) Fuzzy match
        if self._keywords:
            best_match, score, _ = process.extractOne(lower, self._keywords, scorer=fuzz.token_sort_ratio)
            if score >= 75:
                entry = self.drug_map[best_match]
                return {
                    **entry,
                    "confidence": round(score / 100, 2),
                    "match_type": "fuzzy",
                    "input": drug_name,
                    "matched_key": best_match,
                }

        return self._fallback(drug_name, 0.0, "none")

    def _fallback(self, name: str, conf: float, match_type: str) -> dict:
        return {
            "code": None,
            "system": NRCES_DRUG_SYSTEM,
            "generic": name,
            "confidence": conf,
            "match_type": match_type,
            "input": name,
        }

    def enrich_medications(self, medications: list) -> list:
        """
        Enrich a list of medication dicts with NRCeS drug codes.
        Returns the enhanced list (no mutation of originals).
        """
        enriched = []
        for med in medications:
            med_copy = dict(med)
            text = med.get("text") or med.get("generic_name") or ""
            mapping = self.map(text)
            if mapping["code"] and not med_copy.get("code"):
                med_copy["code"] = mapping["code"]
                med_copy["system"] = mapping["system"]
                med_copy["mapping_confidence"] = mapping["confidence"]
                med_copy["mapping_type"] = mapping["match_type"]
            enriched.append(med_copy)
        return enriched


# Singleton
_mapper: Optional[DrugCodeMapper] = None


def get_mapper() -> DrugCodeMapper:
    global _mapper
    if _mapper is None:
        _mapper = DrugCodeMapper()
    return _mapper
