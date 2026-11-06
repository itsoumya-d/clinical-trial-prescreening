import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastapi.testclient import TestClient
from trial_prescreen.app import app

client = TestClient(app)

def test_health():
    assert client.get("/health").json()["status"] == "ok"

def test_prescreen_endpoint():
    payload = {
        "patient": {"age": 44, "conditions": ["ALS"], "biomarkers": {"SOD1": "positive"}, "prior_therapies": ["riluzole"]},
        "trial": {"id": "NCT001", "title": "ALS Trial", "criteria": [
            {"id": "c1", "text": "Age 18-75", "field": "age", "expected": "18-75"}
        ]},
    }
    r = client.post("/prescreen", json=payload)
    assert r.status_code == 200, r.text
    assert r.json()["overall"] == "eligible"

def test_funnel_endpoint():
    r = client.get("/trials/NCT001/eligibility-funnel")
    assert r.status_code == 200
    assert r.json()["pseudonymized"] is True
