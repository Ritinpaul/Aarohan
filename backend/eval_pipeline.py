"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          AAROHAN++ — NHCX PIPELINE EVALUATION FRAMEWORK                    ║
║          All 5 metric categories evaluated against real sample data         ║
╚══════════════════════════════════════════════════════════════════════════════╝

Re-runnable: python eval_pipeline.py
Produces live terminal output + saves JSON report to data/eval_reports/

Metrics Covered
───────────────
  M1  Information Extraction (Precision / Recall / F1)
  M2  Terminology Mapping Accuracy (Top-1 / Top-3)
  M3  FHIR Bundle Structural Validity (pass-rate)
  M4  Readiness Score Fidelity (correlation with expected outcome)
  M5  Auto-Healer Lift (ΔScore before → after heal)
"""

import sys, os, json, math, time, pathlib, textwrap, copy
from datetime import datetime

# ── Project root on sys.path ──────────────────────────────────────────────────
ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT))

# ── Colours (ANSI) ────────────────────────────────────────────────────────────
R = "\033[91m"; G = "\033[92m"; Y = "\033[93m"; B = "\033[94m"
C = "\033[96m"; W = "\033[97m"; DIM = "\033[2m"; BOLD = "\033[1m"; RST = "\033[0m"

PASS = f"{G}✔{RST}"; WARN = f"{Y}▲{RST}"; FAIL = f"{R}✘{RST}"

SAMPLES = ROOT / "data" / "samples"
REPORT_DIR = ROOT / "data" / "eval_reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# GOLDEN DATASET  (hand-annotated from real sample files)
# ─────────────────────────────────────────────────────────────────────────────

GOLDEN = {
    "csv": {
        "file": "district_hospital_bihar.csv",
        "expected_records": 8,
        "expected_patients": [
            {"name": "Rajesh Kumar",       "gender": "male",   "age": "45"},
            {"name": "Sunita Devi",        "gender": "female", "age": "32"},
            {"name": "Mohammed Irfan",     "gender": "male",   "age": "67"},
            {"name": "Priya Kumari",       "gender": "female", "age": "28"},
            {"name": "Ram Bahadur Yadav",  "gender": "male",   "age": "55"},
            {"name": "Asha Kumari",        "gender": "female", "age": "40"},
            {"name": "Karan Singh",        "gender": "male",   "age": "12"},
            {"name": "Meena Jha",          "gender": "unknown","age": "50"},  # gender blank in file
        ],
        "expected_diagnoses": [
            "sugar ki bimari",   # Hindi — row 1
            "E11.9",             # ICD-10 — row 2
            "High BP and chest pain",    # row 3 free-text
            "O80",               # row 4
            "peyt mein dard",    # Hindi row 5
            "J06.9",             # row 6
            "bukhar aur khansi", # Hindi row 7
            "K80.2",             # row 8
        ],
        "expected_medications": [
            "Metformin", "Glimepiride", "Amlodipine",
            "Aspirin", "Pantoprazole", "Amoxicillin",
            "Combiflam",
        ],
        "expected_schemes": ["PMJAY"],
        "expected_facilities": ["Patna Medical College and Hospital", "Sadar Hospital Hajipur",
                                  "District Hospital Patna", "PHC Begusarai",
                                  "Anugrah Narayan Magadh Medical College"],
    },
    "hl7": {
        "file": "medical_college_chennai.hl7",
        "expected_patient": {"gender": "female"},
        "expected_facility": "CMCH",
        "expected_diagnoses": [],   # DG1 segment present but may be empty in sample
    },
    "xml": {
        "file": "phc_rajasthan_pharmacy.xml",
        "expected_records": 2,
        "expected_patients": [
            {"name": "Geeta Bai",    "gender": "female", "age": "62"},
            {"name": "Bhanwar Lal",  "gender": "male",   "age": "8"},
        ],
        "expected_diagnoses": ["Rheumatoid Arthritis", "Acute Gastroenteritis"],
        "expected_medications": [
            "Ibuprofen", "Folic Acid", "Methotrexate",  # Rx 1
            "ORS", "Paracetamol", "Norfloxacin",         # Rx 2
        ],
        "expected_facility": "Primary Health Centre, Kishangarh",
    },
}

# Drug term expected → NRCeS code mappings
TERM_GOLDEN = [
    # (input_text, expected_top1_code, expected_in_top3_codes)
    ("metformin",       "MET500",   ["MET500"]),
    ("Metformin 500mg", "MET500",   ["MET500"]),
    ("PARACETAMOL",     "PAR500",   ["PAR500"]),
    ("paracetamol",     "PAR500",   ["PAR500"]),
    ("Amlodipine 5mg",  "AML5",     ["AML5"]),
    ("aspirin 75",      "ASP75",    ["ASP75"]),
    ("AMOXICILLIN",     "AMOX500",  ["AMOX500"]),
    ("Glimepiride",     None,       []),         # not in mapper — should gracefully fail
    ("Ibuprofen",       "IBU400",   ["IBU400"]),
    ("Folic Acid",      "FOL5",     ["FOL5"]),
    ("omeprazole",      "OME20",    ["OME20"]),
    ("pantoprazole",    "PAN40",    ["PAN40"]),
    ("amoxicil",        "AMOX500",  ["AMOX500"]),  # fuzzy
    ("metforminn",      "MET500",   ["MET500"]),   # typo fuzzy
    ("xyz_unknown_333", None,       []),           # true unknown
]

# Readiness expected risk bands vs score + blocking + critical combinations
READINESS_GOLDEN = [
    # (overall_score, blocking, critical, expected_risk)
    (95.0, 0, 0, "low"),
    (80.0, 0, 0, "low"),         # < 90 but > 75, 0 blocking/critical → low
    (65.0, 0, 1, "medium"),     # 1 critical, score < 75 → medium
    (45.0, 0, 3, "high"),       # > 2 critical → high
    (30.0, 1, 0, "very_high"),  # any blocking → very_high
    (25.0, 1, 2, "very_high"),  # blocking + low score → very_high
]


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _banner(title: str):
    w = 74
    print(f"\n{BOLD}{B}{'═' * w}{RST}")
    print(f"{BOLD}{B}  {title}{RST}")
    print(f"{BOLD}{B}{'═' * w}{RST}")


def _section(title: str):
    print(f"\n{C}{BOLD}  ── {title} ─{'─' * (60 - len(title))}{RST}")


def _metric_row(label: str, value, threshold_ok=None, width=40):
    if isinstance(value, float):
        vs = f"{value:.3f}"
    else:
        vs = str(value)

    if threshold_ok is None:
        icon = "  "
    elif threshold_ok:
        icon = PASS
    else:
        icon = WARN

    label_str = label.ljust(width)
    print(f"    {icon}  {label_str}  {BOLD}{vs}{RST}")


def _prf(tp, fp, fn):
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f1


def _name_in(extracted_name: str, expected_name: str) -> bool:
    en = extracted_name.lower() if extracted_name else ""
    xn = expected_name.lower()
    # Match if any word from expected is in extracted (handles trailing family name)
    return any(part in en for part in xn.split())


# ─────────────────────────────────────────────────────────────────────────────
# M1: INFORMATION EXTRACTION  Precision / Recall / F1
# ─────────────────────────────────────────────────────────────────────────────

def _eval_csv_parser(report: dict):
    _section("M1-A: CSV Parser — District Hospital Bihar")
    from app.parsers.csv_parser import CSVParser
    parser = CSVParser()
    fp = str(SAMPLES / GOLDEN["csv"]["file"])
    parsed = parser.parse(fp)
    records = parsed.get("records", [])

    # Patient extraction
    exp_pts = GOLDEN["csv"]["expected_patients"]
    tp_name = fp_name = fn_name = 0
    tp_gender = fp_gender = fn_gender = 0
    name_hits = []

    for exp in exp_pts:
        found = False
        for rec in records:
            pat = rec.get("patient", {})
            extracted_name = pat.get("name", "") or ""
            if _name_in(extracted_name, exp["name"]):
                tp_name += 1
                found = True
                name_hits.append(exp["name"])
                # Gender check
                ext_g = (pat.get("gender") or "").lower()
                if exp["gender"] in ext_g or ext_g.startswith(exp["gender"][0]):
                    tp_gender += 1
                else:
                    fn_gender += 1
                break
        if not found:
            fn_name += 1

    all_extracted_names = [r.get("patient", {}).get("name", "") for r in records]
    fp_name = sum(1 for en in all_extracted_names if en and not any(_name_in(en, ep["name"]) for ep in exp_pts))

    pn, rn, f1n = _prf(tp_name, fp_name, fn_name)
    pg, rg, f1g = _prf(tp_gender, fp_gender, fn_gender)

    _metric_row("Name Recall",      rn, rn >= 0.85)
    _metric_row("Name Precision",   pn, pn >= 0.85)
    _metric_row("Name F1",          f1n, f1n >= 0.85)
    _metric_row("Gender F1",        f1g, f1g >= 0.80)

    # Diagnosis
    exp_diag = GOLDEN["csv"]["expected_diagnoses"]
    all_diag_text = []
    for rec in records:
        for d in rec.get("diagnoses", []):
            tx = f"{d.get('text', '')} {d.get('code', '')}".lower()
            all_diag_text.append(tx)

    tp_d = sum(1 for ed in exp_diag if any(part.lower() in dt for dt in all_diag_text for part in ed.lower().split()))
    fn_d = len(exp_diag) - tp_d
    fp_d = max(0, len(all_diag_text) - tp_d)
    pd, rd, f1d = _prf(tp_d, fp_d, fn_d)
    _metric_row("Diagnosis Recall",  rd, rd >= 0.75)
    _metric_row("Diagnosis F1",      f1d, f1d >= 0.70)

    # Medication
    exp_meds = GOLDEN["csv"]["expected_medications"]
    all_med_text = []
    for rec in records:
        for m in rec.get("medications", []):
            all_med_text.append((m.get("text") or "").lower())

    tp_m = sum(1 for em in exp_meds if any(em.lower() in mt for mt in all_med_text))
    fn_m = len(exp_meds) - tp_m
    fp_m = max(0, len(all_med_text) - tp_m)
    pm, rm, f1m = _prf(tp_m, fp_m, fn_m)
    _metric_row("Medication Recall", rm, rm >= 0.75)
    _metric_row("Medication F1",     f1m, f1m >= 0.70)

    report["M1_csv"] = {
        "name_recall": rn, "name_precision": pn, "name_f1": f1n,
        "gender_f1": f1g, "diagnosis_recall": rd, "diagnosis_f1": f1d,
        "medication_recall": rm, "medication_f1": f1m,
    }
    return records


def _eval_xml_parser(report: dict):
    _section("M1-B: XML Parser — PHC Rajasthan")
    from app.parsers.xml_parser import XMLParser
    parser = XMLParser()
    fp = str(SAMPLES / GOLDEN["xml"]["file"])
    parsed = parser.parse(fp)
    records = parsed.get("records", [])

    exp_pts = GOLDEN["xml"]["expected_patients"]
    tp_n = fn_n = fp_n = 0
    all_extracted = [r.get("patient", {}).get("name", "") or "" for r in records]

    for ep in exp_pts:
        if any(_name_in(en, ep["name"]) for en in all_extracted):
            tp_n += 1
        else:
            fn_n += 1
    fp_n = sum(1 for en in all_extracted if en and not any(_name_in(en, ep["name"]) for ep in exp_pts))

    exp_diag = GOLDEN["xml"]["expected_diagnoses"]
    all_diag = []
    for rec in records:
        for d in rec.get("diagnoses", []):
            all_diag.append((d.get("text") or "").lower())
    tp_d = sum(1 for ed in exp_diag if any(ed.lower() in dt for dt in all_diag))
    fn_d = len(exp_diag) - tp_d
    fp_d = max(0, len(all_diag) - tp_d)

    exp_meds = GOLDEN["xml"]["expected_medications"]
    all_meds = []
    for rec in records:
        for m in rec.get("medications", []):
            all_meds.append((m.get("text") or m.get("generic_name") or "").lower())
    tp_m = sum(1 for em in exp_meds if any(em.lower() in mt or mt in em.lower() for mt in all_meds))
    fn_m = len(exp_meds) - tp_m
    fp_m = max(0, len(all_meds) - tp_m)

    pn, rn, f1n = _prf(tp_n, fp_n, fn_n)
    pd, rd, f1d = _prf(tp_d, fp_d, fn_d)
    pm, rm, f1m = _prf(tp_m, fp_m, fn_m)

    _metric_row("Name Recall",       rn, rn >= 0.85)
    _metric_row("Name F1",           f1n, f1n >= 0.85)
    _metric_row("Diagnosis Recall",  rd, rd >= 0.85)
    _metric_row("Diagnosis F1",      f1d, f1d >= 0.85)
    _metric_row("Medication Recall", rm, rm >= 0.75)
    _metric_row("Medication F1",     f1m, f1m >= 0.70)

    report["M1_xml"] = {
        "name_recall": rn, "name_f1": f1n,
        "diagnosis_recall": rd, "diagnosis_f1": f1d,
        "medication_recall": rm, "medication_f1": f1m,
    }


def _eval_hl7_parser(report: dict):
    _section("M1-C: HL7v2 Parser — Medical College Chennai")
    from app.parsers.hl7_parser import HL7Parser
    parser = HL7Parser()
    fp = str(SAMPLES / GOLDEN["hl7"]["file"])
    parsed = parser.parse(fp)

    got_gender = (parsed.get("patient") or {}).get("gender") or ""
    exp_gender = GOLDEN["hl7"]["expected_patient"]["gender"]
    gender_ok = exp_gender in got_gender.lower()

    _metric_row("Gender extracted",  got_gender or "(none)", gender_ok)
    _metric_row("Parse errors",      len(parsed.get("errors", [])), len(parsed.get("errors", [])) == 0)

    report["M1_hl7"] = {
        "gender_correct": gender_ok,
        "parse_errors": len(parsed.get("errors", [])),
    }


# ─────────────────────────────────────────────────────────────────────────────
# M2: TERMINOLOGY MAPPING ACCURACY
# ─────────────────────────────────────────────────────────────────────────────

def _eval_terminology(report: dict):
    _section("M2: Terminology Mapping — Drug Code Top-1 / Top-3")
    from app.fhir.drug_mapper import DrugCodeMapper
    mapper = DrugCodeMapper()

    top1_hit = top3_hit = total = graceful_fail = 0
    rows = []

    for (inp, exp_top1, exp_top3) in TERM_GOLDEN:
        total += 1
        result = mapper.map(inp)
        got_code = result.get("code")
        conf = result.get("confidence", 0)
        mtype = result.get("match_type", "none")

        # Top-1
        t1 = (got_code == exp_top1) if exp_top1 else (got_code is None)
        # Top-3: for now top-1 == top-3 unless we implement multi-candidate
        t3 = (got_code in exp_top3) if exp_top3 else (got_code is None)

        if t1: top1_hit += 1
        if t3: top3_hit += 1
        if not exp_top1 and got_code is None: graceful_fail += 1

        icon = PASS if t1 else (WARN if t3 else FAIL)
        print(f"    {icon}  {inp[:25]:<26}  →  "
              f"{(got_code or 'None'):<12}  conf={conf:.2f}  [{mtype}]")
        rows.append({"input": inp, "expected": exp_top1, "got": got_code,
                     "top1": t1, "top3": t3, "confidence": conf, "type": mtype})

    top1_acc = top1_hit / total
    top3_acc = top3_hit / total
    print()
    _metric_row("Top-1 Accuracy",         top1_acc, top1_acc >= 0.75)
    _metric_row("Top-3 Accuracy",         top3_acc, top3_acc >= 0.85)
    _metric_row("Graceful unknown fail",  graceful_fail, True)

    # Identify gaps
    gaps = [(r["input"], r["expected"], r["got"]) for r in rows if not r["top1"]]
    if gaps:
        print(f"\n    {Y}  Unmapped drugs:{RST}")
        for inp, exp, got in gaps:
            print(f"    {DIM}    {inp:<25}  expected:{str(exp):<10}  got:{str(got)}{RST}")

    report["M2"] = {
        "top1_accuracy": top1_acc, "top3_accuracy": top3_acc,
        "total_probes": total, "top1_hits": top1_hit, "top3_hits": top3_hit,
        "gaps": gaps,
    }


# ─────────────────────────────────────────────────────────────────────────────
# M3: FHIR BUNDLE STRUCTURAL VALIDITY
# ─────────────────────────────────────────────────────────────────────────────

REQUIRED_RESOURCE_TYPES = {"Claim", "Patient", "Condition", "Coverage", "Organization"}
REQUIRED_PROFILES_SUBSTR = "nrces.in"


def _validate_bundle_structure(bundle: dict) -> dict:
    """Local structural validator (subset of HAPI FHIR rules)."""
    errors = []
    warnings = []
    entries = bundle.get("entry", [])

    # Profile
    profiles = bundle.get("meta", {}).get("profile", [])
    if not any(REQUIRED_PROFILES_SUBSTR in p for p in profiles):
        errors.append("Bundle.meta.profile missing NRCeS URL")

    # Required resource types
    types_present = {e["resource"]["resourceType"] for e in entries}
    for rt in REQUIRED_RESOURCE_TYPES:
        if rt not in types_present:
            errors.append(f"Missing required resource type: {rt}")

    # Patient must have gender
    for e in entries:
        r = e["resource"]
        if r["resourceType"] == "Patient":
            if not r.get("gender"):
                warnings.append("Patient.gender missing")
            if not r.get("identifier"):
                warnings.append("Patient.identifier (ABHA) missing")
            if not r.get("name"):
                errors.append("Patient.name missing")

    # Each entry must have fullUrl
    no_url = sum(1 for e in entries if not e.get("fullUrl"))
    if no_url:
        errors.append(f"{no_url} entries missing fullUrl")

    return {"errors": errors, "warnings": warnings, "valid": len(errors) == 0}


def _eval_fhir_validity(report: dict, csv_records: list):
    _section("M3: FHIR Bundle Structural Validity")
    from app.parsers.csv_parser import CSVParser
    from app.parsers.xml_parser import XMLParser
    from app.parsers.hl7_parser import HL7Parser
    from app.fhir.bundle_packager import BundlePackager

    test_cases = [
        ("CSV Bihar",     str(SAMPLES / "district_hospital_bihar.csv"),   "csv"),
        ("XML Rajasthan", str(SAMPLES / "phc_rajasthan_pharmacy.xml"),    "xml"),
        ("HL7 Chennai",   str(SAMPLES / "medical_college_chennai.hl7"),   "hl7v2"),
    ]
    parsers = {"csv": CSVParser(), "xml": XMLParser(), "hl7v2": HL7Parser()}
    packager = BundlePackager(network="nhcx")

    total = passed = warned = failed = 0
    details = []

    for label, fp, fmt in test_cases:
        total += 1
        parsed = parsers[fmt].parse(fp)
        bundle = packager.pack_claim_bundle(parsed, {})
        result = _validate_bundle_structure(bundle)
        err_count = len(result["errors"])
        warn_count = len(result["warnings"])

        if result["valid"] and warn_count == 0:
            passed += 1
            icon = PASS
            status = "PASS"
        elif result["valid"]:
            warned += 1
            icon = WARN
            status = "WARN"
        else:
            failed += 1
            icon = FAIL
            status = "FAIL"

        n_entries = len(bundle.get("entry", []))
        types = sorted({e["resource"]["resourceType"] for e in bundle.get("entry", [])})
        print(f"    {icon}  {label:<20}  entries={n_entries:<3}  errors={err_count}  warns={warn_count}")
        if result["errors"]:
            for e in result["errors"]:
                print(f"    {DIM}        ERROR: {e}{RST}")
        details.append({"label": label, "status": status, "errors": result["errors"],
                        "warnings": result["warnings"], "entry_count": n_entries, "resource_types": types})

    pass_rate = (passed + warned) / total if total else 0
    print()
    _metric_row("Bundle Pass Rate (0 errors)",  pass_rate,      pass_rate >= 0.80)
    _metric_row("Bundles with warnings",        warned,         warned <= 1)
    _metric_row("Bundles with errors",          failed,         failed == 0)
    report["M3"] = {"pass_rate": pass_rate, "passed": passed, "warned": warned,
                    "failed": failed, "details": details}


# ─────────────────────────────────────────────────────────────────────────────
# M4: READINESS SCORE FIDELITY
# ─────────────────────────────────────────────────────────────────────────────

def _eval_readiness_fidelity(report: dict):
    _section("M4: Readiness Score Fidelity")
    from app.quality.readiness_engine import compute_readiness_score, _rejection_risk

    # Test expected risk bands match
    correct = 0
    total = 0
    rows = []

    print(f"    {'Score':<8} {'Blocking':<10} {'Critical':<10} {'Expected Risk':<14} {'Got Risk':<14} {'Match'}")
    print(f"    {'─'*8} {'─'*10} {'─'*10} {'─'*14} {'─'*14} {'─'*6}")

    for score, blocking, critical, exp_risk in READINESS_GOLDEN:
        total += 1
        got_risk, _ = _rejection_risk(score, blocking, critical)
        match = got_risk == exp_risk
        if match: correct += 1
        icon = PASS if match else FAIL
        print(f"    {score:<8.1f} {blocking:<10} {critical:<10} {exp_risk:<14} {got_risk:<14} {icon}")
        rows.append({"score": score, "expected": exp_risk, "got": got_risk, "match": match})

    # Also test on real files
    print()
    from app.parsers.csv_parser import CSVParser
    parsed_csv = CSVParser().parse(str(SAMPLES / "district_hospital_bihar.csv"))
    result = compute_readiness_score(parsed_csv)
    print(f"    {DIM}  Real CSV score: {result.overall_score}/100  grade={result.grade}  "
          f"risk={result.rejection_risk}  gaps={len(result.gaps)}{RST}")

    from app.parsers.xml_parser import XMLParser
    parsed_xml = XMLParser().parse(str(SAMPLES / "phc_rajasthan_pharmacy.xml"))
    result_xml = compute_readiness_score(parsed_xml)
    print(f"    {DIM}  Real XML score: {result_xml.overall_score}/100  grade={result_xml.grade}  "
          f"risk={result_xml.rejection_risk}  gaps={len(result_xml.gaps)}{RST}")

    fidelity = correct / total
    print()
    _metric_row("Risk Band Fidelity",    fidelity,          fidelity >= 0.90)
    _metric_row("CSV Real Score",        result.overall_score, result.overall_score >= 30)
    _metric_row("XML Real Score",        result_xml.overall_score, result_xml.overall_score >= 30)

    report["M4"] = {"fidelity": fidelity, "band_tests": rows,
                    "csv_real_score": result.overall_score,
                    "xml_real_score": result_xml.overall_score}


# ─────────────────────────────────────────────────────────────────────────────
# M5: AUTO-HEALER LIFT  (simulated — Phase 4 not yet built, so simulate)
# ─────────────────────────────────────────────────────────────────────────────

def _simulate_heal(parsed: dict) -> dict:
    """
    Simulate Phase 4 healing on a parsed record:
    - Add ABHA placeholder
    - Normalize gender
    - Normalize date formats
    - Enrich drug codes
    Returns a healed copy of parsed.
    """
    import re
    from app.fhir.drug_mapper import get_mapper
    healed = copy.deepcopy(parsed)
    mapper = get_mapper()

    # Fix patient fields
    pat = healed.get("patient", {})
    if not pat and healed.get("records"):
        pat = healed["records"][0].get("patient", {})

    if pat:
        # 1) ABHA placeholder
        if not pat.get("abha_id"):
            pat["abha_id"] = "99-0000-0000-0001"

        # 2) Gender normalization
        g = str(pat.get("gender") or "").lower().strip()
        pat["gender"] = {"m": "male", "f": "female", "male": "male",
                         "female": "female"}.get(g, "unknown")

        # 3) Date normalization (DD/MM/YYYY → YYYY-MM-DD)
        for date_field in ("birth_date", "dob"):
            raw = pat.get(date_field, "")
            if raw and re.match(r"\d{2}/\d{2}/\d{4}", str(raw)):
                parts = raw.split("/")
                pat[date_field] = f"{parts[2]}-{parts[1]}-{parts[0]}"

    # 4) Drug code enrichment
    meds = list(healed.get("medications", []))
    for rec in healed.get("records", []):
        meds.extend(rec.get("medications", []))

    enriched = mapper.enrich_medications(meds)

    if "medications" in healed:
        healed["medications"] = enriched[:len(healed.get("medications", []))]
    if healed.get("records"):
        for rec in healed["records"]:
            if "medications" in rec:
                rec["medications"] = mapper.enrich_medications(rec["medications"])

    # 5) Add consent mode
    healed["consent_mode"] = "EXPLICIT"
    healed["consent_purpose"] = "HPAYMT"
    healed["meta_profile"] = "https://nrces.in/ndhm/fhir/r4/StructureDefinition/ClaimBundle"

    return healed


def _eval_healer_lift(report: dict):
    _section("M5: Auto-Healer Lift  (simulated Phase 4)")
    from app.parsers.csv_parser import CSVParser
    from app.parsers.xml_parser import XMLParser
    from app.quality.readiness_engine import compute_readiness_score

    test_cases = [
        ("CSV Bihar",     str(SAMPLES / "district_hospital_bihar.csv"),   CSVParser()),
        ("XML Rajasthan", str(SAMPLES / "phc_rajasthan_pharmacy.xml"),    XMLParser()),
    ]

    lifts = []
    print(f"    {'Source':<20} {'Pre-Score':>10} {'Post-Score':>11} {'Lift':>8} {'Risk Before':<12} {'Risk After'}")
    print(f"    {'─'*20} {'─'*10} {'─'*11} {'─'*8} {'─'*12} {'─'*10}")

    for label, fp, parser in test_cases:
        raw = parser.parse(fp)
        healed = _simulate_heal(raw)

        pre = compute_readiness_score(raw)
        post = compute_readiness_score(healed)
        delta = post.overall_score - pre.overall_score
        lifts.append(delta)

        icon = PASS if delta > 0 else WARN
        print(f"    {icon}  {label:<18} {pre.overall_score:>10.1f} {post.overall_score:>11.1f} "
              f"{delta:>+8.1f} {pre.rejection_risk:<12} {post.rejection_risk}")

    avg_lift = sum(lifts) / len(lifts) if lifts else 0
    print()
    _metric_row("Average Lift (ΔScore)",   avg_lift, avg_lift >= 10.0)
    print(f"\n    {DIM}  Note: Phase 4 (Resilience Healer) not yet built. "
          f"These are simulated healing steps.{RST}")
    report["M5"] = {"avg_lift": avg_lift, "lifts": lifts}


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY TABLE
# ─────────────────────────────────────────────────────────────────────────────

def _print_summary(report: dict):
    _banner("EVALUATION SUMMARY")

    def _status(val, ok_thresh):
        if val is None: return f"{DIM}N/A{RST}"
        ok = val >= ok_thresh
        color = G if ok else (Y if val >= ok_thresh * 0.7 else R)
        return f"{color}{val:.3f}{RST}"

    rows = [
        ("M1-A", "CSV Name F1",          report.get("M1_csv", {}).get("name_f1"),      0.85),
        ("M1-A", "CSV Diagnosis Recall", report.get("M1_csv", {}).get("diagnosis_recall"),0.75),
        ("M1-A", "CSV Medication F1",    report.get("M1_csv", {}).get("medication_f1"), 0.70),
        ("M1-B", "XML Name F1",          report.get("M1_xml", {}).get("name_f1"),       0.85),
        ("M1-B", "XML Diagnosis F1",     report.get("M1_xml", {}).get("diagnosis_f1"),  0.85),
        ("M1-B", "XML Medication F1",    report.get("M1_xml", {}).get("medication_f1"), 0.70),
        ("M1-C", "HL7 Parse Errors",     None,                                           None),
        ("M2",   "Drug Top-1 Accuracy",  report.get("M2", {}).get("top1_accuracy"),     0.75),
        ("M2",   "Drug Top-3 Accuracy",  report.get("M2", {}).get("top3_accuracy"),     0.85),
        ("M3",   "Bundle Pass Rate",     report.get("M3", {}).get("pass_rate"),          0.80),
        ("M4",   "Risk Band Fidelity",   report.get("M4", {}).get("fidelity"),          0.90),
        ("M5",   "Avg Healer Lift",      report.get("M5", {}).get("avg_lift"),          10.0),
    ]

    print(f"\n  {'Metric':<6} {'Description':<30} {'Value':>10}  {'Threshold':>10}  Status")
    print(f"  {'─'*6} {'─'*30} {'─'*10}  {'─'*10}  {'─'*8}")

    for metric, desc, val, thresh in rows:
        if val is None:
            val_str = f"{DIM}—{RST}"
            thresh_str = f"{DIM}—{RST}"
            status = f"{DIM}—{RST}"
        else:
            ok = val >= thresh
            color = G if ok else (Y if val >= thresh * 0.7 else R)
            val_str = f"{color}{val:>10.3f}{RST}"
            thresh_str = f"≥ {thresh:<9.3f}"
            status = f"{G}PASS{RST}" if ok else f"{Y}NEEDS WORK{RST}"
        print(f"  {B}{metric:<6}{RST}  {desc:<30} {val_str}  {thresh_str}  {status}")


def _print_recommendations(report: dict):
    _section("Recommendations & Optimization Paths")
    recs = []

    m1 = report.get("M1_csv", {})
    if m1.get("diagnosis_recall", 1) < 0.80:
        recs.append((Y, "M1",
            "Diagnosis recall < 80%. Add Hindi medical term mapping for: "
            "'peyt mein dard', 'bukhar', 'sir dard'. "
            "Also map colloquial English: 'High BP', 'chest pain' → ICD-10 directly."))

    if m1.get("medication_f1", 1) < 0.80:
        recs.append((Y, "M1",
            "Medication F1 < 80%. Improve multi-drug string splitting for "
            "'Amlodipine 5mg, Aspirin 75mg' (currently parsed as one item)."))

    m2 = report.get("M2", {})
    if m2.get("top1_accuracy", 1) < 0.80:
        recs.append((Y, "M2",
            "Drug Top-1 accuracy < 80%. Add: Glimepiride, Cetirizine, Norfloxacin, "
            "Combiflam (brand→generic map) to drug_mapper.py. "
            "Consider adding a brand-name alias table."))

    if m2.get("gaps"):
        missing = ", ".join([g[0] for g in m2["gaps"][:3]])
        recs.append((R, "M2",
            f"Unmapped drugs found: {missing}. "
            "These will produce MedicationRequest resources with no code — "
            "NHCX submission will warn."))

    m3 = report.get("M3", {})
    if m3.get("pass_rate", 1.0) < 1.0:
        recs.append((R, "M3",
            "Some bundles have structural errors. Common fix: ensure Patient.name "
            "is always populated and meta.profile URL matches the target profile."))

    m4 = report.get("M4", {})
    if m4.get("csv_real_score", 100) < 50:
        recs.append((R, "M4",
            "CSV real score < 50. Key driver: ABHA identifiers are missing in all "
            "Bihar CSV records. Phase 4 healer should inject placeholder ABHA for demo."))

    m5 = report.get("M5", {})
    if m5.get("avg_lift", 0) < 20:
        recs.append((Y, "M5",
            "Healer lift < 20 pts. Building Phase 4 (Resilience Healer) will increase "
            "this significantly by: adding ABHA, normalizing dates, mapping drug codes."))

    if not recs:
        print(f"    {G}All metrics at or above threshold. Pipeline is performing well!{RST}")
    else:
        for i, (color, metric, text) in enumerate(recs, 1):
            wrapped = textwrap.fill(text, width=68, subsequent_indent="             ")
            print(f"\n    {color}[{metric}] {BOLD}Action {i}:{RST}\n             {wrapped}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    _banner("AAROHAN++ — NHCX Pipeline Evaluation  v1.0")
    print(f"  {DIM}Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  |  "
          f"Samples: {SAMPLES}{RST}")

    report = {}
    t0 = time.time()

    # ── M1: Information Extraction ────────────────────────────────────────────
    _banner("M1: Information Extraction — Precision / Recall / F1")
    csv_records = _eval_csv_parser(report)
    _eval_xml_parser(report)
    _eval_hl7_parser(report)

    # ── M2: Terminology Mapping ───────────────────────────────────────────────
    _banner("M2: Terminology Mapping Accuracy")
    _eval_terminology(report)

    # ── M3: FHIR Bundle Validity ──────────────────────────────────────────────
    _banner("M3: FHIR Bundle Structural Validity")
    _eval_fhir_validity(report, csv_records)

    # ── M4: Readiness Score Fidelity ──────────────────────────────────────────
    _banner("M4: Readiness Score Fidelity")
    _eval_readiness_fidelity(report)

    # ── M5: Auto-Healer Lift ──────────────────────────────────────────────────
    _banner("M5: Auto-Healer Lift")
    _eval_healer_lift(report)

    # ── Summary ───────────────────────────────────────────────────────────────
    _print_summary(report)

    # ── Recommendations ───────────────────────────────────────────────────────
    _banner("OPTIMIZATION RECOMMENDATIONS")
    _print_recommendations(report)

    elapsed = round(time.time() - t0, 2)
    print(f"\n  {DIM}Evaluation complete in {elapsed}s{RST}")

    # ── Save JSON report ──────────────────────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = REPORT_DIR / f"eval_{ts}.json"
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"  {G}Report saved: {out_path}{RST}\n")


if __name__ == "__main__":
    main()
