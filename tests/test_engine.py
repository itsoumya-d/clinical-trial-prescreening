import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from trial_prescreen.models import PatientProfile, Trial, Criterion
from trial_prescreen.engine import prescreen

def _trial():
    return Trial(id="NCT001", title="ALS Trial", criteria=[
        Criterion(id="c1", text="Age 18-75", field="age", expected="18-75"),
        Criterion(id="c2", text="ALS diagnosis", field="condition", expected="ALS"),
        Criterion(id="SOD1", text="SOD1 positive", field="biomarker", expected="SOD1=positive"),
        Criterion(id="c4", text="Prior riluzole", field="prior_therapy", expected="riluzole"),
    ])

def test_all_eligible():
    p = PatientProfile(age=44, conditions=["ALS"], biomarkers={"SOD1": "positive"}, prior_therapies=["riluzole"])
    r = prescreen(p, _trial())
    assert r.overall == "eligible"
    assert r.criteria_to_check_manually == 0
    assert r.total_criteria == 4

def test_age_outside_is_ineligible():
    p = PatientProfile(age=82, conditions=["ALS"], biomarkers={"SOD1": "positive"}, prior_therapies=["riluzole"])
    r = prescreen(p, _trial())
    assert r.overall == "ineligible"
    assert any(x.criterion_id == "c1" and x.verdict == "ineligible" for x in r.criteria_results)

def test_missing_prior_therapy_needs_review():
    p = PatientProfile(age=44, conditions=["ALS"], biomarkers={"SOD1": "positive"}, prior_therapies=[])
    r = prescreen(p, _trial())
    assert r.overall == "needs_review"
    assert r.criteria_to_check_manually >= 1

def test_audit_deterministic_and_recall_guard():
    p = PatientProfile(age=44, conditions=["ALS"], biomarkers={"SOD1": "positive"}, prior_therapies=["riluzole"])
    r1, r2 = prescreen(p, _trial()), prescreen(p, _trial())
    assert r1.audit_id == r2.audit_id
    assert "recall 1.0" in r1.recall_guard
