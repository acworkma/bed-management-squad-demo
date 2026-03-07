"""
State store tests — seeding, snapshots, entity retrieval, clearing.

The state store holds the materialized in-memory state (ADR-001, ADR-002).
It's the fast read path; the event store is the audit trail.

Snapshot format: get_snapshot() returns dicts keyed by entity ID.
"""

import json
import pytest

from app.models.enums import BedState, PatientState
from app.models.entities import Bed, Patient
from app.state.store import StateStore


class TestSeedInitialState:
    """seed_initial_state() creates the expected hospital bed layout."""

    def test_seed_creates_beds(self, state_store: StateStore):
        state_store.seed_initial_state()
        beds = state_store.get_beds()
        assert len(beds) > 0, "seed_initial_state should create at least one bed"

    def test_seed_creates_12_beds(self, state_store: StateStore):
        """Default layout has 12 beds (2 units × 3 rooms × 2 beds)."""
        state_store.seed_initial_state()
        beds = state_store.get_beds()
        assert len(beds) == 12

    def test_seed_creates_beds_in_various_states(self, state_store: StateStore):
        state_store.seed_initial_state()
        beds = state_store.get_beds()
        statuses = {b.state for b in beds}
        # Seeded state should include at least OCCUPIED and READY
        assert BedState.OCCUPIED in statuses, "Seeded beds should include OCCUPIED"
        assert BedState.READY in statuses, "Seeded beds should include READY"
        assert BedState.DIRTY in statuses, "Seeded beds should include DIRTY"

    def test_seed_creates_existing_patients(self, state_store: StateStore):
        state_store.seed_initial_state()
        patients = state_store.get_patients()
        assert len(patients) > 0, "seed_initial_state should create existing patients"

    def test_seed_is_idempotent_or_resets(self, state_store: StateStore):
        state_store.seed_initial_state()
        count_1 = len(state_store.get_beds())
        state_store.seed_initial_state()
        count_2 = len(state_store.get_beds())
        assert count_1 == count_2


class TestGetSnapshot:
    """get_snapshot() returns a serializable dict."""

    def test_snapshot_returns_dict(self, seeded_state_store: StateStore):
        snapshot = seeded_state_store.get_snapshot()
        assert isinstance(snapshot, dict)

    def test_snapshot_has_beds_key(self, seeded_state_store: StateStore):
        snapshot = seeded_state_store.get_snapshot()
        assert "beds" in snapshot

    def test_snapshot_has_patients_key(self, seeded_state_store: StateStore):
        snapshot = seeded_state_store.get_snapshot()
        assert "patients" in snapshot

    def test_snapshot_has_tasks_key(self, seeded_state_store: StateStore):
        snapshot = seeded_state_store.get_snapshot()
        assert "tasks" in snapshot

    def test_snapshot_has_transports_key(self, seeded_state_store: StateStore):
        snapshot = seeded_state_store.get_snapshot()
        assert "transports" in snapshot

    def test_snapshot_has_reservations_key(self, seeded_state_store: StateStore):
        snapshot = seeded_state_store.get_snapshot()
        assert "reservations" in snapshot

    def test_snapshot_is_json_serializable(self, seeded_state_store: StateStore):
        snapshot = seeded_state_store.get_snapshot()
        json_str = json.dumps(snapshot, default=str)
        assert isinstance(json_str, str)

    def test_snapshot_beds_count_matches_get_beds(self, seeded_state_store: StateStore):
        snapshot = seeded_state_store.get_snapshot()
        beds = seeded_state_store.get_beds()
        assert len(snapshot["beds"]) == len(beds)

    def test_snapshot_beds_are_dicts_keyed_by_id(self, seeded_state_store: StateStore):
        snapshot = seeded_state_store.get_snapshot()
        beds_dict = snapshot["beds"]
        assert isinstance(beds_dict, dict)
        for key, val in beds_dict.items():
            assert isinstance(key, str)
            assert isinstance(val, dict)
            assert val["id"] == key

    def test_empty_store_snapshot(self, state_store: StateStore):
        snapshot = state_store.get_snapshot()
        assert isinstance(snapshot, dict)
        assert len(snapshot.get("beds", {})) == 0
        assert len(snapshot.get("patients", {})) == 0


class TestClear:
    """clear() resets all state."""

    def test_clear_removes_all_beds(self, seeded_state_store: StateStore):
        assert len(seeded_state_store.get_beds()) > 0
        seeded_state_store.clear()
        assert len(seeded_state_store.get_beds()) == 0

    def test_clear_removes_all_patients(self, state_store: StateStore):
        state_store.seed_initial_state()
        assert len(state_store.get_patients()) > 0
        state_store.clear()
        assert len(state_store.get_patients()) == 0

    def test_clear_removes_all_tasks(self, state_store: StateStore):
        state_store.seed_initial_state()
        state_store.clear()
        assert len(state_store.get_tasks()) == 0

    def test_clear_removes_all_transports(self, state_store: StateStore):
        state_store.clear()
        assert len(state_store.get_transports()) == 0

    def test_clear_removes_all_reservations(self, state_store: StateStore):
        state_store.clear()
        assert len(state_store.get_active_reservations()) == 0


class TestGetBed:
    """get_bed() returns a single bed by ID."""

    def test_get_existing_bed(self, seeded_state_store: StateStore):
        beds = seeded_state_store.get_beds()
        assert len(beds) > 0
        bed = seeded_state_store.get_bed(beds[0].id)
        assert bed is not None
        assert bed.id == beds[0].id

    def test_get_nonexistent_bed_returns_none(self, seeded_state_store: StateStore):
        bed = seeded_state_store.get_bed("nonexistent-bed-999")
        assert bed is None


class TestGetPatient:
    """get_patient() returns a single patient by ID."""

    def test_get_existing_patient(self, seeded_state_store: StateStore):
        patients = seeded_state_store.get_patients()
        if patients:
            patient = seeded_state_store.get_patient(patients[0].id)
            assert patient is not None
            assert patient.id == patients[0].id

    def test_get_nonexistent_patient_returns_none(self, state_store: StateStore):
        patient = state_store.get_patient("nonexistent-pat-999")
        assert patient is None


class TestGetBeds:
    """get_beds() returns a list of all beds."""

    def test_get_beds_returns_list(self, seeded_state_store: StateStore):
        beds = seeded_state_store.get_beds()
        assert isinstance(beds, list)

    def test_get_beds_returns_bed_objects(self, seeded_state_store: StateStore):
        beds = seeded_state_store.get_beds()
        for bed in beds:
            assert isinstance(bed, Bed)

    def test_get_beds_empty_store(self, state_store: StateStore):
        beds = state_store.get_beds()
        assert beds == []

    def test_get_beds_with_filter(self, seeded_state_store: StateStore):
        """get_beds(filter_fn) returns only beds matching the filter."""
        ready_beds = seeded_state_store.get_beds(
            filter_fn=lambda b: b.state == BedState.READY
        )
        assert len(ready_beds) > 0
        for bed in ready_beds:
            assert bed.state == BedState.READY


class TestStateTransitions:
    """StateStore transition methods validate via the state machine."""

    async def test_transition_bed_valid(self, seeded_state_store: StateStore):
        dirty_beds = seeded_state_store.get_beds(
            filter_fn=lambda b: b.state == BedState.DIRTY
        )
        assert len(dirty_beds) > 0
        bed = await seeded_state_store.transition_bed(dirty_beds[0].id, BedState.CLEANING)
        assert bed.state == BedState.CLEANING

    async def test_transition_bed_invalid_raises(self, seeded_state_store: StateStore):
        from app.models.transitions import InvalidTransitionError
        ready_beds = seeded_state_store.get_beds(
            filter_fn=lambda b: b.state == BedState.READY
        )
        assert len(ready_beds) > 0
        with pytest.raises(InvalidTransitionError):
            await seeded_state_store.transition_bed(ready_beds[0].id, BedState.DIRTY)

    async def test_transition_bed_nonexistent_raises(self, state_store: StateStore):
        with pytest.raises(KeyError):
            await state_store.transition_bed("fake-bed-999", BedState.CLEANING)

    async def test_transition_patient_valid(self, seeded_state_store: StateStore):
        arrived_patients = seeded_state_store.get_patients(
            filter_fn=lambda p: p.state == PatientState.ARRIVED
        )
        if arrived_patients:
            patient = await seeded_state_store.transition_patient(
                arrived_patients[0].id, PatientState.DISCHARGED
            )
            assert patient.state == PatientState.DISCHARGED

    async def test_transition_patient_invalid_raises(self, seeded_state_store: StateStore):
        from app.models.transitions import InvalidTransitionError
        arrived_patients = seeded_state_store.get_patients(
            filter_fn=lambda p: p.state == PatientState.ARRIVED
        )
        if arrived_patients:
            with pytest.raises(InvalidTransitionError):
                await seeded_state_store.transition_patient(
                    arrived_patients[0].id, PatientState.AWAITING_BED
                )
