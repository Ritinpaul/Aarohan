"""
Date Healer — Aarohan++ Phase 4
Converts all Indian/HMIS date format variants to ISO 8601 (YYYY-MM-DD).

Handles:
  - DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
  - YYYY-MM-DD (passthrough)
  - D/M/YY (2-digit year)
  - DD Mon YYYY (e.g. 12 Jan 2023)
  - YYYYMMDD (compact)
  - HL7 DTM: YYYYMMDDHHMMSS
  - Relative terms: "today", "yesterday" (for demo use only)
"""

import re
import logging
from datetime import date, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


# Month name → number map (English + Hindi-English transliteration)
MONTH_MAP = {
    "jan": 1, "january": 1, "jan.": 1,
    "feb": 2, "february": 2, "feb.": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

DATE_FIELD_NAMES = {
    "birth_date", "dob", "date", "visit_date", "admission_date",
    "discharge_date", "recorded_date", "issued_date", "start_date",
    "end_date", "encounter_date",
}


def _two_digit_year(y: int) -> int:
    """Convert 2-digit year to 4-digit. Pivot: 00–30 → 2000s, 31–99 → 1900s."""
    if y < 0:
        return y
    if y <= 30:
        return 2000 + y
    if y <= 99:
        return 1900 + y
    return y


def _clamp(val: int, lo: int, hi: int) -> bool:
    return lo <= val <= hi


def _safe_date(y: int, m: int, d: int) -> Optional[date]:
    if not (_clamp(y, 1900, 2099) and _clamp(m, 1, 12) and _clamp(d, 1, 31)):
        return None
    try:
        return date(y, m, d)
    except ValueError:
        return None


def parse_date_string(raw: str) -> Optional[date]:
    """
    Attempt to parse any common date string into a date object.
    Returns None if cannot parse.
    """
    if not raw:
        return None

    raw = str(raw).strip()

    # Already a date object or date-like string
    if isinstance(raw, date):
        return raw

    # Relative
    lower = raw.lower()
    if lower == "today":
        return date.today()
    if lower in ("yesterday", "prev day"):
        return date.today() - timedelta(days=1)

    # ISO 8601 passthrough: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", raw)
    if m:
        return _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # Compact YYYYMMDD or HL7 YYYYMMDDHHMMSS
    m = re.match(r"^(\d{4})(\d{2})(\d{2})(\d{0,6})$", raw)
    if m:
        return _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
    m = re.match(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})$", raw)
    if m:
        d_, mo, y = int(m.group(1)), int(m.group(2)), _two_digit_year(int(m.group(3)))
        result = _safe_date(y, mo, d_)
        if result:
            return result

    # Month-name formats: "12 Jan 2023", "12-Jan-23", "Jan 12 2023"
    m = re.match(
        r"^(\d{1,2})[/\- ]([a-zA-Z]+)[/\- ](\d{2,4})$", raw
    )
    if m:
        d_, mon_str, y = int(m.group(1)), m.group(2).lower(), _two_digit_year(int(m.group(3)))
        mo = MONTH_MAP.get(mon_str)
        if mo:
            return _safe_date(y, mo, d_)

    m = re.match(
        r"^([a-zA-Z]+)[/\- ](\d{1,2})[/\-, ](\d{2,4})$", raw
    )
    if m:
        mon_str, d_, y = m.group(1).lower(), int(m.group(2)), _two_digit_year(int(m.group(3)))
        mo = MONTH_MAP.get(mon_str)
        if mo:
            return _safe_date(y, mo, d_)

    logger.debug(f"DateHealer: Could not parse '{raw}'")
    return None


def to_iso(raw) -> Optional[str]:
    """Parse a raw date value and return ISO 8601 string, or None."""
    if isinstance(raw, date):
        return raw.isoformat()
    parsed = parse_date_string(str(raw))
    if parsed:
        return parsed.isoformat()
    return None


def heal_dates(obj: dict) -> dict:
    """
    Walk a parsed dict and normalise all known date fields to ISO 8601.
    Returns mutated dict.
    """
    for key in list(obj.keys()):
        val = obj[key]
        if key.lower() in DATE_FIELD_NAMES and val:
            iso = to_iso(val)
            if iso and iso != str(val):
                logger.debug(f"DateHealer: {key} '{val}' → '{iso}'")
                obj[key] = iso

    # Recurse into nested dicts and lists
    for key, val in obj.items():
        if isinstance(val, dict):
            heal_dates(val)
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    heal_dates(item)

    return obj
