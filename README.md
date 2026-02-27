# Aarohan : NHCX Compliance Intelligence Platform

> Transform legacy healthcare data into NHCX-compliant FHIR bundles — automatically.

---

## What It Does

Aarohan is a backend microservice that ingests Indian hospital data in any format (HL7v2, CSV, XML, PDF) and outputs NHCX/ABDM-ready FHIR R4 bundles with a quality readiness score.

### Core Capabilities

- **Multi-format Parsing** — HL7v2, CSV, XML, PDF (including scanned documents via OCR)
- **Bharat Context Engine** — auto-detects hospital tier, state, insurance scheme eligibility (PMJAY, CMCHIS, YSR Aarogyasri), and Indic language
- **Quality Assessment Engine** — NHCX Readiness Score (0–100) across 4 dimensions: structural completeness, terminology coverage, profile compliance, consent readiness
- **FHIR Bundle Packager** — generates NRCeS-compliant `ClaimBundle` and `CoverageEligibilityRequestBundle` for both NHCX and OpenHCX networks
- **Drug Code Mapper** — maps brand/generic names to NRCeS drug codes via exact, prefix, and fuzzy matching
- **Snowstorm Terminology Client** — async SNOMED CT / ICD-10 / LOINC lookups with Redis caching

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/convert/` | Parse any format → canonical JSON |
| `POST` | `/api/v1/assess/` | Run quality assessment → Readiness Score |
| `POST` | `/api/v1/transform/` | Full pipeline → FHIR Bundle |
| `GET`  | `/api/v1/health/`   | Service health check |

---

## Stack

- **Runtime**: Python 3.11 + FastAPI
- **FHIR**: NRCeS R4 profiles (HL7 FHIR)
- **Storage**: PostgreSQL + Redis
- **OCR**: PyMuPDF + Tesseract
- **Terminology**: Snowstorm FHIR TS

---

## Quick Start

```bash
# Clone
git clone git@github.com:Ritinpaul/Aarohan.git
cd Aarohan

# Start services
docker compose up -d

# Install backend deps
cd backend
pip install -r requirements.txt

# Run
uvicorn app.main:app --reload

# API docs
open http://localhost:8000/docs
```

---

## Project Structure

```
Aarohan/
├── backend/
│   ├── app/
│   │   ├── api/routes/      # convert, assess, transform, health
│   │   ├── parsers/         # PDF, CSV, HL7v2, XML
│   │   ├── context/         # Bharat Context Engine
│   │   ├── quality/         # Readiness scorers + engine
│   │   ├── fhir/            # Resource builders + bundle packager
│   │   └── models/          # Canonical Pydantic models
│   ├── data/
│   │   └── seed/            # facilities.json, states.json, drugs.json
│   └── tests/
├── docker-compose.yml
└── README.md
```

---

## License

MIT
