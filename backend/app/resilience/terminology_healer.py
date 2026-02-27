"""
Terminology Healer — Aarohan++ Phase 4
Enriches diagnosis/observation free-text with ICD-10 / SNOMED CT codes.

Strategy (no external API required — self-contained):
  1. Exact match on normalised English term → ICD-10
  2. Hindi/Hinglish → English → ICD-10 (via csv_parser maps)
  3. Substring match (e.g. "hypertensive heart disease" → I11.9)
  4. SNOMED CT code lookup for common Indian disorders

Confidence scoring:
  exact   → 1.0
  fuzzy   → 0.75
  hindi   → 0.85
  unknown → None
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ─── Comprehensive ICD-10 lookup table ─────────────────────────────────────────
ICD10_MAP: dict[str, str] = {
    # Metabolic / Endocrine
    "diabetes mellitus": "E11.9",
    "type 2 diabetes": "E11.9",
    "type 1 diabetes": "E10.9",
    "gestational diabetes": "O24.4",
    "hypothyroidism": "E03.9",
    "hyperthyroidism": "E05.9",
    "obesity": "E66.9",

    # Cardiovascular
    "hypertension": "I10",
    "essential hypertension": "I10",
    "high blood pressure": "I10",
    "heart failure": "I50.9",
    "congestive heart failure": "I50.0",
    "myocardial infarction": "I21.9",
    "angina": "I20.9",
    "coronary artery disease": "I25.1",
    "atrial fibrillation": "I48",
    "ischemic heart disease": "I25.9",
    "chest pain": "R07.4",

    # Respiratory
    "upper respiratory infection": "J06.9",
    "acute upper respiratory infection": "J06.9",
    "uri": "J06.9",
    "pneumonia": "J18.9",
    "asthma": "J45.9",
    "chronic obstructive pulmonary disease": "J44.9",
    "copd": "J44.9",
    "bronchitis": "J40",
    "influenza": "J11.1",
    "tuberculosis": "A15.9",
    "pulmonary tuberculosis": "A15.0",
    "cough": "R05",
    "dyspnoea": "R06.0",
    "shortness of breath": "R06.0",

    # Gastrointestinal
    "abdominal pain": "R10.4",
    "gastroenteritis": "A09",
    "acute gastroenteritis": "A09",
    "diarrhoea": "A09",
    "diarrhea": "A09",
    "peptic ulcer": "K27.9",
    "gastric ulcer": "K25.9",
    "appendicitis": "K37",
    "cholecystitis": "K81.9",
    "gallbladder stone": "K80.2",
    "cholelithiasis": "K80.2",
    "jaundice": "R17",
    "hepatitis b": "B18.1",
    "hepatitis c": "B18.2",
    "constipation": "K59.0",
    "vomiting": "R11",
    "nausea": "R11",

    # Musculoskeletal
    "rheumatoid arthritis": "M05.9",
    "osteoarthritis": "M19.9",
    "back pain": "M54.5",
    "low back pain": "M54.5",
    "fracture": "S00",
    "knee pain": "M25.361",
    "gout": "M10.9",

    # Neurological
    "headache": "R51",
    "migraine": "G43.9",
    "epilepsy": "G40.9",
    "stroke": "I64",
    "cerebrovascular accident": "I64",
    "parkinson": "G20",
    "vertigo": "R42",
    "dizziness": "R42",

    # Gynaecological / Obstetric
    "normal delivery": "O80",
    "caesarean section": "O82",
    "ectopic pregnancy": "O00.9",
    "pre-eclampsia": "O14.9",
    "anaemia in pregnancy": "O99.0",

    # Blood / Haematology
    "anaemia": "D64.9",
    "anemia": "D64.9",
    "iron deficiency anaemia": "D50.9",
    "sickle cell disease": "D57.1",
    "thalassemia": "D56.9",

    # Infectious
    "malaria": "B54",
    "dengue": "A97.9",
    "dengue fever": "A97.9",
    "typhoid": "A01.0",
    "chickenpox": "B01.9",
    "covid-19": "U07.1",
    "covid19": "U07.1",
    "hiv": "B20",
    "fever": "R50.9",
    "pyrexia": "R50.9",

    # Urological
    "urinary tract infection": "N39.0",
    "uti": "N39.0",
    "burning micturition": "R30.0",
    "kidney stone": "N20.0",
    "nephrolithiasis": "N20.0",
    "chronic kidney disease": "N18.9",
    "renal failure": "N17.9",

    # Dermatology
    "eczema": "L30.9",
    "psoriasis": "L40.9",
    "fungal infection": "B35.9",

    # Ophthalmology
    "cataract": "H26.9",
    "glaucoma": "H40.9",
    "diabetic retinopathy": "H36.0",

    # Mental Health
    "depression": "F32.9",
    "anxiety": "F41.9",
    "schizophrenia": "F20.9",
    "bipolar disorder": "F31.9",

    # General / Symptoms
    "weakness": "R53.1",
    "fatigue": "R53.1",
    "weight loss": "R63.4",
    "generalised weakness": "R53.1",
    "pedal oedema": "R60.0",
    "oedema": "R60.9",

    # Hindi/transliterated terms (direct ICD-10 bypass)
    "sugar ki bimari": "E11.9",
    "madhumeh": "E11.9",
    "bp ki bimari": "I10",
    "ucch raktachaap": "I10",
    "bukhar": "R50.9",
    "khansi": "R05",
    "peyt mein dard": "R10.4",
    "pet dard": "R10.4",
    "sir dard": "R51",
    "chakkar": "R42",
    "khoon ki kami": "D64.9",
}

# ─── SNOMED CT codes for priority disorders ────────────────────────────────────
SNOMED_MAP: dict[str, str] = {
    "diabetes mellitus": "73211009",
    "hypertension": "38341003",
    "asthma": "195967001",
    "tuberculosis": "56717001",
    "malaria": "61462000",
    "dengue fever": "38362002",
    "anaemia": "271737000",
    "rheumatoid arthritis": "69896004",
    "upper respiratory infection": "54150009",
    "gastroenteritis": "4559003",
}


def _normalise_term(text: str) -> str:
    """Lowercase, strip punctuation except hyphens, collapse spaces."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z\-\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def lookup_icd10(
    text: str,
) -> tuple[Optional[str], float, str]:
    """
    Attempt to find an ICD-10 code for a diagnosis text string.

    Returns:
        (code_or_None, confidence_0_to_1, match_type)
    """
    if not text:
        return None, 0.0, "none"

    norm = _normalise_term(text)

    # Exact match
    if norm in ICD10_MAP:
        return ICD10_MAP[norm], 1.0, "exact"

    # Exact with original casing
    lower = text.lower().strip()
    if lower in ICD10_MAP:
        return ICD10_MAP[lower], 1.0, "exact"

    # Substring: check if any known term is contained in the input
    for term, code in ICD10_MAP.items():
        if term in norm or norm in term:
            return code, 0.85, "substring"

    # Word-overlap fuzzy: ≥ 2 words match
    norm_words = set(norm.split())
    for term, code in ICD10_MAP.items():
        term_words = set(term.split())
        overlap = norm_words & term_words
        if len(overlap) >= 2 and len(overlap) / max(len(term_words), 1) >= 0.6:
            return code, 0.75, "fuzzy"

    return None, 0.0, "none"


def lookup_snomed(text: str) -> Optional[str]:
    """Return SNOMED CT code for a known condition, or None."""
    norm = _normalise_term(text)
    return SNOMED_MAP.get(norm)


def heal_diagnoses(diagnoses: list) -> list:
    """
    Enrich a list of diagnosis dicts with ICD-10 codes if missing.
    Returns the (mutated) list.
    """
    for d in diagnoses:
        if not d.get("code"):
            text = d.get("text") or d.get("raw") or ""
            code, conf, mtype = lookup_icd10(text)
            if code:
                d["code"] = code
                d["system"] = "http://hl7.org/fhir/sid/icd-10"
                d["code_confidence"] = conf
                d["code_match_type"] = mtype
                d["snomed"] = lookup_snomed(text)
                logger.debug(
                    f"TerminologyHealer: '{text}' → {code} "
                    f"(conf={conf:.2f}, type={mtype})"
                )
    return diagnoses
