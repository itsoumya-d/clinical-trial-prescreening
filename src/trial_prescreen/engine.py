import hashlib
import uuid
from .models import PatientProfile, Trial, CriterionResult, PrescreenResult

def _evaluate_criterion(patient: PatientProfile, criterion) -> CriterionResult:
    field, expected = criterion.field, criterion.expected
    verdict, evidence, confidence, needs = "review", "no direct match — physician review required", 0.5, True

    if field == "age":
        lo, hi = (int(x) for x in expected.split("-")) if "-" in expected else (int(expected), 999)
        if lo <= patient.age <= hi:
            verdict, evidence, confidence, needs = "eligible", f"age {patient.age} within {expected}", 0.97, False
        else:
            verdict, evidence, confidence, needs = "ineligible", f"age {patient.age} outside {expected}", 0.97, False
    elif field == "condition":
        if expected.lower() in {c.lower() for c in patient.conditions}:
            verdict, evidence, confidence, needs = "eligible", f"condition match: {expected}", 0.95, False
        else:
            verdict, evidence, confidence, needs = "ineligible", f"condition not listed (has: {patient.conditions})", 0.90, False
    elif field == "biomarker":
        value = patient.biomarkers.get(criterion.id, patient.biomarkers.get(field, ""))
        # Support "KEY=VALUE" expected strings
        key, _, want = expected.partition("=")
        have = patient.biomarkers.get(key.strip(), value or "")
        if have and have.lower() == want.strip().lower():
            verdict, evidence, confidence, needs = "eligible", f"biomarker {key}={have}", 0.92, False
        elif have:
            verdict, evidence, confidence, needs = "ineligible", f"biomarker {key}={have} != {want}", 0.92, False
    elif field == "prior_therapy":
        if expected.lower() in {t.lower() for t in patient.prior_therapies}:
            verdict, evidence, confidence, needs = "eligible", f"prior therapy match: {expected}", 0.93, False
        else:
            # Absence of prior therapy is not automatically exclusionary
            verdict, evidence, confidence, needs = "review", f"prior therapy '{expected}' not recorded — confirm with physician", 0.60, True

    return CriterionResult(criterion_id=criterion.id, verdict=verdict, evidence=evidence, confidence=confidence, needs_physician=needs)

def prescreen(patient: PatientProfile, trial: Trial) -> PrescreenResult:
    results = [_evaluate_criterion(patient, c) for c in trial.criteria]
    ineligible = any(r.verdict == "ineligible" for r in results)
    review = any(r.verdict == "review" for r in results)
    overall = "ineligible" if ineligible else ("needs_review" if review else "eligible")
    manual = sum(1 for r in results if r.needs_physician)
    audit = hashlib.sha256(f"{trial.id}|{patient.age}|{overall}|{manual}".encode()).hexdigest()[:16]
    guard = "physician-in-the-loop: LLM/system alone recall 0.50 per myTomorrows llm-prescreening paper; with physician recall 1.0, precision 0.71, 90% fewer criteria to check"
    return PrescreenResult(
        trial_id=trial.id,
        overall=overall,
        criteria_results=results,
        criteria_to_check_manually=manual,
        total_criteria=len(results),
        recall_guard=guard,
        audit_id=audit,
    )
