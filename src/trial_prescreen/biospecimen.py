"""Biospecimen custody tracking and trial biospecimen eligibility verification."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict


class SpecimenStatus(str, Enum):
    COLLECTED = "COLLECTED"
    STORED = "STORED"
    ALIQUOTED = "ALIQUOTED"
    DEPLETED = "DEPLETED"
    DISPOSED = "DISPOSED"


@dataclass
class CustodyEvent:
    timestamp: str
    operator: str
    action: str
    details: str


@dataclass
class SpecimenRecord:
    specimen_id: str
    patient_id: str
    specimen_type: str
    collection_date: str
    volume_ml: float
    storage_temp_c: float
    location: str
    freeze_thaw_cycles: int = 0
    status: SpecimenStatus = SpecimenStatus.COLLECTED
    parent_specimen_id: Optional[str] = None
    custody_chain: List[CustodyEvent] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "specimen_id": self.specimen_id,
            "patient_id": self.patient_id,
            "specimen_type": self.specimen_type,
            "collection_date": self.collection_date,
            "volume_ml": self.volume_ml,
            "storage_temp_c": self.storage_temp_c,
            "location": self.location,
            "freeze_thaw_cycles": self.freeze_thaw_cycles,
            "status": self.status.value,
            "parent_specimen_id": self.parent_specimen_id,
            "custody_chain": [
                {"timestamp": c.timestamp, "operator": c.operator, "action": c.action, "details": c.details}
                for c in self.custody_chain
            ],
        }


class BiospecimenRegistry:
    """In-memory biobank registry tracking specimen inventory, chain of custody, and trial biospecimen suitability."""

    def __init__(self):
        self._inventory: Dict[str, SpecimenRecord] = {}

    def register(self, specimen: SpecimenRecord, operator: str = "system") -> SpecimenRecord:
        now = datetime.now(timezone.utc).isoformat()
        specimen.custody_chain.append(
            CustodyEvent(timestamp=now, operator=operator, action="REGISTER", details=f"Initial intake at {specimen.location}")
        )
        self._inventory[specimen.specimen_id] = specimen
        return specimen

    def get(self, specimen_id: str) -> Optional[SpecimenRecord]:
        return self._inventory.get(specimen_id)

    def transfer_location(self, specimen_id: str, new_location: str, operator: str, notes: str = "") -> SpecimenRecord:
        specimen = self._inventory.get(specimen_id)
        if not specimen:
            raise KeyError(f"Specimen {specimen_id} not found")
        old_loc = specimen.location
        specimen.location = new_location
        now = datetime.now(timezone.utc).isoformat()
        specimen.custody_chain.append(
            CustodyEvent(
                timestamp=now,
                operator=operator,
                action="TRANSFER",
                details=f"Transferred from {old_loc} to {new_location}. {notes}".strip(),
            )
        )
        return specimen

    def record_freeze_thaw(self, specimen_id: str, operator: str, notes: str = "") -> SpecimenRecord:
        specimen = self._inventory.get(specimen_id)
        if not specimen:
            raise KeyError(f"Specimen {specimen_id} not found")
        specimen.freeze_thaw_cycles += 1
        now = datetime.now(timezone.utc).isoformat()
        specimen.custody_chain.append(
            CustodyEvent(
                timestamp=now,
                operator=operator,
                action="FREEZE_THAW",
                details=f"Cycle count incremented to {specimen.freeze_thaw_cycles}. {notes}".strip(),
            )
        )
        return specimen

    def aliquot(
        self,
        parent_id: str,
        aliquot_counts: int,
        volume_per_aliquot_ml: float,
        operator: str,
        base_location: str,
    ) -> List[SpecimenRecord]:
        parent = self._inventory.get(parent_id)
        if not parent:
            raise KeyError(f"Specimen {parent_id} not found")
        total_requested = aliquot_counts * volume_per_aliquot_ml
        if total_requested > parent.volume_ml:
            raise ValueError(
                f"Requested aliquot volume {total_requested}ml exceeds available parent volume {parent.volume_ml}ml"
            )

        parent.volume_ml -= total_requested
        if parent.volume_ml == 0:
            parent.status = SpecimenStatus.DEPLETED
        else:
            parent.status = SpecimenStatus.ALIQUOTED

        now = datetime.now(timezone.utc).isoformat()
        parent.custody_chain.append(
            CustodyEvent(
                timestamp=now,
                operator=operator,
                action="ALIQUOT_CHILDREN_CREATED",
                details=f"Created {aliquot_counts} aliquots of {volume_per_aliquot_ml}ml each. Remaining: {parent.volume_ml}ml",
            )
        )

        aliquots = []
        for i in range(1, aliquot_counts + 1):
            child_id = f"{parent.specimen_id}-A{i:02d}"
            child_loc = f"{base_location}/Slot-{i:02d}"
            child = SpecimenRecord(
                specimen_id=child_id,
                patient_id=parent.patient_id,
                specimen_type=parent.specimen_type,
                collection_date=parent.collection_date,
                volume_ml=volume_per_aliquot_ml,
                storage_temp_c=parent.storage_temp_c,
                location=child_loc,
                freeze_thaw_cycles=parent.freeze_thaw_cycles,
                status=SpecimenStatus.STORED,
                parent_specimen_id=parent.specimen_id,
            )
            child.custody_chain.append(
                CustodyEvent(
                    timestamp=now,
                    operator=operator,
                    action="DERIVED_FROM_PARENT",
                    details=f"Aliquoted from {parent.specimen_id}",
                )
            )
            self._inventory[child_id] = child
            aliquots.append(child)

        return aliquots

    def evaluate_trial_suitability(
        self,
        patient_id: str,
        required_type: str,
        min_volume_ml: float,
        max_freeze_thaw: int = 2,
    ) -> Dict:
        matching = [
            s
            for s in self._inventory.values()
            if s.patient_id == patient_id
            and s.specimen_type.lower() == required_type.lower()
            and s.status in (SpecimenStatus.COLLECTED, SpecimenStatus.STORED, SpecimenStatus.ALIQUOTED)
        ]

        if not matching:
            return {
                "eligible": False,
                "reason": f"No available specimens of type '{required_type}' for patient {patient_id}",
                "specimen_id": None,
                "available_volume_ml": 0.0,
            }

        viable = [s for s in matching if s.volume_ml >= min_volume_ml and s.freeze_thaw_cycles <= max_freeze_thaw]

        if viable:
            best = max(viable, key=lambda s: s.volume_ml)
            return {
                "eligible": True,
                "reason": f"Specimen {best.specimen_id} meets criteria: {best.volume_ml}ml >= {min_volume_ml}ml, freeze-thaw {best.freeze_thaw_cycles} <= {max_freeze_thaw}",
                "specimen_id": best.specimen_id,
                "available_volume_ml": best.volume_ml,
            }

        # Check why none qualified
        reasons = []
        for s in matching:
            if s.volume_ml < min_volume_ml:
                reasons.append(f"{s.specimen_id}: volume {s.volume_ml}ml < {min_volume_ml}ml")
            if s.freeze_thaw_cycles > max_freeze_thaw:
                reasons.append(f"{s.specimen_id}: freeze-thaw cycles {s.freeze_thaw_cycles} > {max_freeze_thaw}")

        return {
            "eligible": False,
            "reason": f"Found {len(matching)} specimen(s) but none qualified: {'; '.join(reasons)}",
            "specimen_id": None,
            "available_volume_ml": sum(s.volume_ml for s in matching),
        }
