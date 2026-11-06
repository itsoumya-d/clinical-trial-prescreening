from pydantic import BaseModel

class PatientProfile(BaseModel):
    age: int
    conditions: list[str]
    biomarkers: dict[str, str]
    prior_therapies: list[str]

class Criterion(BaseModel):
    id: str
    text: str
    field: str  # age|condition|biomarker|prior_therapy
    expected: str

class Trial(BaseModel):
    id: str
    title: str
    criteria: list[Criterion]

class CriterionResult(BaseModel):
    criterion_id: str
    verdict: str  # eligible|ineligible|review
    evidence: str
    confidence: float
    needs_physician: bool

class PrescreenResult(BaseModel):
    trial_id: str
    overall: str  # eligible|ineligible|needs_review
    criteria_results: list[CriterionResult]
    criteria_to_check_manually: int
    total_criteria: int
    recall_guard: str
    audit_id: str
