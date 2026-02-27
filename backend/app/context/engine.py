"""
Bharat Context Engine — Aarohan++ Phase 1
Modules:
  1. HospitalTierClassifier — detects facility tier from name using rapidfuzz + facilities.json
  2. StateSchemDetector — maps patient state → eligible insurance schemes using states.json + schemes.json
  3. LanguageDetector — identifies script language (Hindi/Tamil/Telugu/English) from text
  4. ContextEngine — orchestrates all 3 and returns a ContextOutput
"""

import json
import re
import logging
import unicodedata
from pathlib import Path
from typing import Optional

from rapidfuzz import fuzz, process
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ─── Seed data paths ────────────────────────────────────────────────────────
_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "seed"
_FACILITIES_PATH = _DATA_DIR / "facilities.json"
_STATES_PATH = _DATA_DIR / "states.json"
_SCHEMES_PATH = _DATA_DIR / "schemes.json"


def _load_json(path: Path) -> dict:
    if not path.exists():
        logger.warning(f"Seed file not found: {path}")
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ─── Output Schema ───────────────────────────────────────────────────────────

class SchemeInfo(BaseModel):
    name: str
    network: str
    coverage_amount: Optional[int] = None
    claim_types: list = Field(default_factory=list)
    profile_url: Optional[str] = None


class ContextOutput(BaseModel):
    hospital_tier: Optional[str] = None         # e.g. "medical_college", "district_hospital"
    hospital_tier_label: Optional[str] = None   # e.g. "Tier 1 — Medical College"
    hospital_fhir_readiness: Optional[float] = None
    state_code: Optional[str] = None
    state_name: Optional[str] = None
    primary_language: str = "en"
    detected_scripts: list = Field(default_factory=list)
    eligible_schemes: list[SchemeInfo] = Field(default_factory=list)
    network: str = "nhcx"                        # "nhcx" | "openhcx"
    confidence: float = 0.0


# ─── 1. Hospital Tier Classifier ─────────────────────────────────────────────

class HospitalTierClassifier:
    """
    Classifies hospital tier (Tier 1–5) using rapidfuzz keyword matching
    against facilities.json tier definitions.
    """

    def __init__(self):
        data = _load_json(_FACILITIES_PATH)
        # facility_tiers is a list of {tier, name, keywords, ...}
        self.tiers_list = data.get("facility_tiers", [])
        self.nins_prefixes = data.get("nins_code_prefixes", {})
        self._build_keyword_index()

    def _build_keyword_index(self):
        """Pre-compute keyword → tier record mapping for fast lookup."""
        self.keyword_index = {}
        for tier_data in self.tiers_list:
            keywords = tier_data.get("keywords", [])
            for kw in keywords:
                self.keyword_index[kw.lower()] = tier_data

    def classify(self, hospital_name: str) -> dict:
        """
        Returns tier info dict for the given hospital name.
        Tries: exact keyword → fuzzy keyword → NINS prefix → unknown.
        """
        if not hospital_name:
            return {"tier": "unknown", "label": "Unknown", "confidence": 0.0}

        name_lower = hospital_name.strip().lower()

        # 1) Exact keyword match
        for kw, tier_data in self.keyword_index.items():
            if kw in name_lower:
                return {
                    "tier": f"tier_{tier_data.get('tier', 'unknown')}",
                    "label": tier_data.get("name", str(tier_data.get("tier", "unknown"))),
                    "fhir_readiness": tier_data.get("estimated_fhir_readiness", 0.5),
                    "confidence": 0.95,
                    "match_type": "keyword",
                }

        # 2) Fuzzy match against all keywords
        all_keywords = list(self.keyword_index.keys())
        if all_keywords:
            best_match, score, _ = process.extractOne(
                name_lower, all_keywords, scorer=fuzz.partial_ratio
            )
            if score >= 70:
                tier_data = self.keyword_index[best_match]
                return {
                    "tier": f"tier_{tier_data.get('tier', 'unknown')}",
                    "label": tier_data.get("name", str(tier_data.get("tier", "unknown"))),
                    "fhir_readiness": tier_data.get("estimated_fhir_readiness", 0.5),
                    "confidence": round(score / 100, 2),
                    "match_type": "fuzzy",
                    "matched_keyword": best_match,
                }

        return {"tier": "unknown", "label": "Unknown", "confidence": 0.0, "match_type": "none"}


# ─── 2. State Scheme Detector ─────────────────────────────────────────────────

class StateSchemeDetector:
    """
    Maps patient state (from address/name) → eligible insurance schemes.
    Uses states.json for state detection and schemes.json for scheme details.
    """

    def __init__(self):
        states_data = _load_json(_STATES_PATH)
        schemes_data = _load_json(_SCHEMES_PATH)

        self.states = states_data.get("states", [])
        self.schemes = schemes_data.get("schemes", [])

        # Build index: state_code → state record
        self.state_index = {s["code"]: s for s in self.states if "code" in s}
        # Build index: scheme_id_lower → scheme record
        self.scheme_index = {s.get("id", s.get("full_name", "")).lower(): s for s in self.schemes}

    def detect_state(self, text: str) -> Optional[dict]:
        """
        Detect Indian state from free-text (address, city name, etc.)
        Returns state dict or None.
        """
        if not text:
            return None
        text_lower = text.lower()

        # Direct name match
        for state in self.states:
            state_name = state.get("name", "").lower()
            if state_name and state_name in text_lower:
                return state
            # Try state code match
            state_code = state.get("code", "").lower()
            if state_code and re.search(r'\b' + re.escape(state_code) + r'\b', text_lower):
                return state

        return None

    def get_schemes_for_state(self, state_code: str) -> list[SchemeInfo]:
        """Return list of eligible schemes for a given state code."""
        eligible = []
        for scheme in self.schemes:
            # Real JSON uses 'states_active', may also be 'all' for national
            active_states = scheme.get("states_active", scheme.get("active_states", []))
            if not active_states or "all" in active_states or state_code in active_states:
                eligible.append(SchemeInfo(
                    name=scheme.get("full_name", scheme.get("name", scheme.get("id", ""))),
                    network=scheme.get("network", "nhcx"),
                    coverage_amount=scheme.get("coverage_amount"),
                    claim_types=scheme.get("claim_types", []),
                    profile_url=scheme.get("nhcx_profile"),
                ))
        return eligible


# ─── 3. Language Detector ─────────────────────────────────────────────────────

class LanguageDetector:
    """
    Detects primary script/language from text using Unicode block analysis.
    Identifies: Hindi (Devanagari), Tamil, Telugu, Kannada, Malayalam, Bengali, English.
    """

    SCRIPT_RANGES = {
        "hi": (0x0900, 0x097F),   # Devanagari
        "ta": (0x0B80, 0x0BFF),   # Tamil
        "te": (0x0C00, 0x0C7F),   # Telugu
        "kn": (0x0C80, 0x0CFF),   # Kannada
        "ml": (0x0D00, 0x0D7F),   # Malayalam
        "bn": (0x0980, 0x09FF),   # Bengali
        "gu": (0x0A80, 0x0AFF),   # Gujarati
        "pa": (0x0A00, 0x0A7F),   # Gurmukhi / Punjabi
        "or": (0x0B00, 0x0B7F),   # Odia
    }

    LANG_NAMES = {
        "hi": "Hindi", "ta": "Tamil", "te": "Telugu",
        "kn": "Kannada", "ml": "Malayalam", "bn": "Bengali",
        "gu": "Gujarati", "pa": "Punjabi", "or": "Odia", "en": "English",
    }

    def detect(self, text: str) -> dict:
        """
        Returns dict with primary_language code, all detected scripts, and char counts.
        """
        if not text:
            return {"primary_language": "en", "detected_scripts": [], "char_counts": {}}

        char_counts = {lang: 0 for lang in self.SCRIPT_RANGES}
        char_counts["en"] = 0

        for char in text:
            cp = ord(char)
            matched = False
            for lang, (lo, hi) in self.SCRIPT_RANGES.items():
                if lo <= cp <= hi:
                    char_counts[lang] += 1
                    matched = True
                    break
            if not matched and char.isalpha():
                char_counts["en"] += 1

        total_alpha = sum(char_counts.values()) or 1
        proportions = {lang: cnt / total_alpha for lang, cnt in char_counts.items()}

        # Primary = highest non-English proportion, else English
        non_en = {lang: p for lang, p in proportions.items() if lang != "en" and p > 0.02}
        if non_en:
            primary = max(non_en, key=non_en.get)
        else:
            primary = "en"

        detected_scripts = [
            {"code": lang, "name": self.LANG_NAMES.get(lang, lang), "proportion": round(p, 3)}
            for lang, p in proportions.items()
            if p > 0.02
        ]

        return {
            "primary_language": primary,
            "detected_scripts": detected_scripts,
            "char_counts": char_counts,
        }


# ─── 4. Context Engine (Orchestrator) ────────────────────────────────────────

class ContextEngine:
    """
    Orchestrates Tier Classifier + Scheme Detector + Language Detector.
    Accepts parsed data dict and returns a ContextOutput.
    """

    def __init__(self):
        self.tier_classifier = HospitalTierClassifier()
        self.scheme_detector = StateSchemeDetector()
        self.lang_detector = LanguageDetector()

    def detect(
        self,
        hospital_name: str = "",
        address_text: str = "",
        raw_text: str = "",
        state_hint: str = "",
    ) -> ContextOutput:
        """
        Run all context detections and return a ContextOutput object.

        Args:
            hospital_name: Name of facility from parsed record
            address_text: Patient/facility address string
            raw_text: Any free-text block for language detection
            state_hint: Direct state name/code if available
        """
        # 1) Tier classification
        tier_result = self.tier_classifier.classify(hospital_name)

        # 2) State detection
        combined_text = f"{hospital_name} {address_text} {state_hint}"
        state = self.scheme_detector.detect_state(combined_text)

        # 3) Eligible schemes
        schemes = []
        if state:
            schemes = self.scheme_detector.get_schemes_for_state(state.get("code", ""))

        # 4) Language detection
        lang_result = self.lang_detector.detect(raw_text or address_text)

        # 5) Network selection — default NHCX; defer to first scheme's network
        network = schemes[0].network if schemes else "nhcx"

        # 6) Confidence composite
        confidence = round(
            (tier_result.get("confidence", 0) + (1.0 if state else 0)) / 2, 2
        )

        return ContextOutput(
            hospital_tier=tier_result.get("tier"),
            hospital_tier_label=tier_result.get("label"),
            hospital_fhir_readiness=tier_result.get("fhir_readiness"),
            state_code=state.get("code") if state else None,
            state_name=state.get("name") if state else None,
            primary_language=lang_result.get("primary_language", "en"),
            detected_scripts=lang_result.get("detected_scripts", []),
            eligible_schemes=schemes,
            network=network,
            confidence=confidence,
        )
