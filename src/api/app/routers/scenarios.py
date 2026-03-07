"""Scenario trigger endpoints — start demo workflows."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["scenarios"])


@router.post("/scenario/happy-path")
async def run_happy_path():
    """Trigger the happy-path scenario (ADR-007).

    Clears state, seeds initial conditions, kicks off orchestration.
    Returns 202 immediately — scenario runs asynchronously.
    """
    # TODO: clear state, seed beds/patients, start orchestration loop
    return JSONResponse(status_code=202, content={"status": "started", "scenario": "happy-path"})


@router.post("/scenario/disruption-replan")
async def run_disruption_replan():
    """Trigger the disruption + re-plan scenario.

    Same as happy-path but injects a mid-flow disruption event.
    Returns 202 immediately — scenario runs asynchronously.
    """
    # TODO: clear state, seed, start orchestration, inject disruption mid-way
    return JSONResponse(status_code=202, content={"status": "started", "scenario": "disruption-replan"})
