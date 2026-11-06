from fastapi import FastAPI
from .models import PatientProfile, Trial, PrescreenResult
from .engine import prescreen
from pydantic import BaseModel

class PrescreenRequest(BaseModel):
    patient: PatientProfile
    trial: Trial

app = FastAPI(title="Clinical Trial Pre-screening")

@app.get("/health")
def health():
    return {"status": "ok", "service": "clinical-trial-prescreening"}

@app.post("/prescreen", response_model=PrescreenResult)
def run_prescreen(req: PrescreenRequest):
    return prescreen(req.patient, req.trial)

@app.get("/trials/{trial_id}/eligibility-funnel")
def funnel(trial_id: str):
    return {"trial_id": trial_id, "stages": ["search", "pre-screen", "navigator-consult", "site-referral"], "pseudonymized": True, "iso27001": True}
