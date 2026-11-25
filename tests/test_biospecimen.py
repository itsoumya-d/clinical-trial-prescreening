"""Unit tests for biospecimen custody tracking and trial suitability evaluation."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from trial_prescreen.biospecimen import BiospecimenRegistry, SpecimenRecord, SpecimenStatus


@pytest.fixture
def registry():
    reg = BiospecimenRegistry()
    sample = SpecimenRecord(
        specimen_id="SP-1001",
        patient_id="PT-501",
        specimen_type="Serum",
        collection_date="2026-11-20T09:00:00Z",
        volume_ml=10.0,
        storage_temp_c=-80.0,
        location="Freezer-1/Shelf-A/Box-01/Slot-01",
    )
    reg.register(sample, operator="dr_smith")
    return reg


def test_register_and_get(registry):
    sp = registry.get("SP-1001")
    assert sp is not None
    assert sp.patient_id == "PT-501"
    assert len(sp.custody_chain) == 1
    assert sp.custody_chain[0].action == "REGISTER"
    assert sp.custody_chain[0].operator == "dr_smith"


def test_transfer_location(registry):
    sp = registry.transfer_location("SP-1001", "Freezer-2/Shelf-C/Box-05/Slot-12", operator="lab_tech_1", notes="Routine audit re-organization")
    assert sp.location == "Freezer-2/Shelf-C/Box-05/Slot-12"
    assert len(sp.custody_chain) == 2
    assert sp.custody_chain[1].action == "TRANSFER"
    assert "Freezer-1" in sp.custody_chain[1].details
    assert "Freezer-2" in sp.custody_chain[1].details


def test_freeze_thaw_tracking(registry):
    sp = registry.record_freeze_thaw("SP-1001", operator="lab_tech_2")
    assert sp.freeze_thaw_cycles == 1
    sp = registry.record_freeze_thaw("SP-1001", operator="lab_tech_2")
    assert sp.freeze_thaw_cycles == 2
    assert len(sp.custody_chain) == 3


def test_aliquot_creation_and_depletion(registry):
    aliquots = registry.aliquot(
        parent_id="SP-1001",
        aliquot_counts=4,
        volume_per_aliquot_ml=2.0,
        operator="lab_tech_3",
        base_location="Freezer-1/Shelf-B/Box-02",
    )
    parent = registry.get("SP-1001")
    assert len(aliquots) == 4
    assert parent.volume_ml == 2.0  # 10.0 - (4 * 2.0)
    assert parent.status == SpecimenStatus.ALIQUOTED

    for i, a in enumerate(aliquots, start=1):
        assert a.specimen_id == f"SP-1001-A{i:02d}"
        assert a.volume_ml == 2.0
        assert a.parent_specimen_id == "SP-1001"
        assert a.status == SpecimenStatus.STORED


def test_aliquot_volume_exceeded_error(registry):
    with pytest.raises(ValueError, match="exceeds available"):
        registry.aliquot(
            parent_id="SP-1001",
            aliquot_counts=6,
            volume_per_aliquot_ml=2.0,
            operator="lab_tech_3",
            base_location="Freezer-1/Box-02",
        )


def test_trial_suitability_eligible(registry):
    res = registry.evaluate_trial_suitability(
        patient_id="PT-501",
        required_type="Serum",
        min_volume_ml=5.0,
        max_freeze_thaw=2,
    )
    assert res["eligible"] is True
    assert res["specimen_id"] == "SP-1001"
    assert res["available_volume_ml"] == 10.0


def test_trial_suitability_insufficient_volume(registry):
    res = registry.evaluate_trial_suitability(
        patient_id="PT-501",
        required_type="Serum",
        min_volume_ml=15.0,  # exceeds 10ml
        max_freeze_thaw=2,
    )
    assert res["eligible"] is False
    assert "volume" in res["reason"]


def test_trial_suitability_excessive_freeze_thaw(registry):
    registry.record_freeze_thaw("SP-1001", operator="tech")
    registry.record_freeze_thaw("SP-1001", operator="tech")
    registry.record_freeze_thaw("SP-1001", operator="tech")  # 3 cycles

    res = registry.evaluate_trial_suitability(
        patient_id="PT-501",
        required_type="Serum",
        min_volume_ml=2.0,
        max_freeze_thaw=2,  # requires <= 2 cycles
    )
    assert res["eligible"] is False
    assert "freeze-thaw" in res["reason"]


def test_trial_suitability_missing_patient_specimen(registry):
    res = registry.evaluate_trial_suitability(
        patient_id="PT-999",  # no specimens
        required_type="Serum",
        min_volume_ml=1.0,
    )
    assert res["eligible"] is False
    assert "No available specimens" in res["reason"]
