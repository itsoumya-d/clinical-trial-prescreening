# Clinical Trial Pre-screening

Explainable, physician-in-the-loop pre-screening for clinical trials — built in myTomorrows' exact JD stack (Python FastAPI / Pydantic / SQLAlchemy backend + Angular 17 / TypeScript frontend).

## Stack

- **Backend:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2 (models ready for MySQL/Neo4j knowledge-graph join)
- **Frontend:** Angular 17 standalone (`frontend/`, traveler checklist pattern reused for eligibility checklist)
- **Infra:** Dockerfile-ready, GitHub Actions CI (backend-test + frontend-build)

## The `rea` fix — physician survey pain → production fix

myTomorrows' July-2025 physician report: 60% say pre-screening tools are too complicated/insufficient, 53% need more precise search filters, 43% find referral communication unclear, 41% need multiple tools for one referral. Their `llm-prescreening` repo shows LLM-only recall 0.50, physician-in-loop recall 1.0 / precision 0.71 with ~90% fewer criteria to check.

This repo implements that properly:

- **Criterion-level evidence:** every rule returns `eligible | ineligible | review` with plain-language evidence, confidence and `needs_physician` flag — never a black-box score.
- **Recall guard:** any `ineligible` excludes, any `review` forces `needs_review` (no silent False negatives); prior-therapy absence is review, not exclusion.
- **Audit trail:** deterministic `audit_id` hash per (trial, patient, outcome).
- **Funnel endpoints:** search → pre-screen → navigator-consult → site-referral with pseudonymised profiles (ISO-27001/GDPR/HIPAA posture from myTomorrows FAQ).

## Run

```bash
pip install -e .[dev]
pytest -q
uvicorn trial_prescreen.app:app --reload
cd frontend && npm ci && npm run build
```

## Truthfulness boundary

Deterministic reference logic with synthetic profiles only; it does not access EHRs, does not file referrals, and is not medical advice. Production use requires clinical validation, privacy review and physician oversight.
