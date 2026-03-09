"""Multi-agent orchestration engine — supervisor pattern (ADR-004).

Provides both a live Azure AI Foundry mode (using the Responses API with
named agents) and a simulated mode that walks through scripted tool calls
for demo without Azure provisioning.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, TypedDict

from ..config import settings
from ..events.event_store import EventStore
from ..messages.message_store import MessageStore
from ..models.enums import BedState, IntentTag, PatientState, TaskState
from ..state.store import StateStore
from ..tools import tool_functions

logger = logging.getLogger(__name__)


class AgentMetrics(TypedDict):
    agent_name: str
    model: str
    input_tokens: int
    output_tokens: int
    max_output_tokens: int
    rounds: int
    latency_seconds: float


class ScenarioMetrics(TypedDict):
    total_latency_seconds: float
    total_input_tokens: int
    total_output_tokens: int
    agents: list[AgentMetrics]


# ── Tool dispatch table (ADR-003a) ──────────────────────────────────

TOOL_DISPATCH: dict[str, Any] = {
    "get_patient": tool_functions.get_patient,
    "get_beds": tool_functions.get_beds,
    "get_tasks": tool_functions.get_tasks,
    "reserve_bed": tool_functions.reserve_bed,
    "release_bed_reservation": tool_functions.release_bed_reservation,
    "create_task": tool_functions.create_task,
    "update_task": tool_functions.update_task,
    "schedule_transport": tool_functions.schedule_transport,
    "publish_event": tool_functions.publish_event,
    "escalate": tool_functions.escalate,
}

# ── Agent prompt loader (ADR-008) ───────────────────────────────────

_PROMPT_DIR = Path(__file__).parent / "prompts"


def _load_prompt(agent_name: str) -> str:
    path = _PROMPT_DIR / f"{agent_name}.txt"
    return path.read_text(encoding="utf-8")


# ── Helpers ─────────────────────────────────────────────────────────

STEP_DELAY = 0.35  # seconds between simulated steps for realistic SSE pacing


async def _call_tool(
    name: str,
    arguments: dict[str, Any],
    *,
    state_store: StateStore,
    event_store: EventStore,
    message_store: MessageStore,
) -> dict:
    """Dispatch a tool call to the matching function in tool_functions.py."""
    fn = TOOL_DISPATCH.get(name)
    if fn is None:
        return {"ok": False, "error": f"Unknown tool: {name}"}
    return await fn(
        **arguments,
        state_store=state_store,
        event_store=event_store,
        message_store=message_store,
    )


def _use_live_agents() -> bool:
    """Return True if a Foundry project endpoint is configured."""
    return bool(settings.PROJECT_ENDPOINT or settings.PROJECT_CONNECTION_STRING)


# ── Agent name ↔ display role mapping ───────────────────────────────

_AGENT_ROLES: dict[str, str] = {
    "flow-coordinator": "Flow Coordinator",
    "predictive-capacity": "Predictive Capacity Agent",
    "bed-allocation": "Bed Allocation Agent",
    "evs-tasking": "EVS Tasking Agent",
    "transport-ops": "Transport Operations Agent",
    "policy-safety": "Policy & Safety Agent",
}


# ── Live Azure Foundry orchestration (v2 — Responses API) ──────────

async def _run_live(
    scenario_type: str,
    state_store: StateStore,
    event_store: EventStore,
    message_store: MessageStore,
) -> dict:
    """Run orchestration using the Responses API with per-agent instructions.

    Each agent is defined by its system prompt and tool set.  All calls use
    the same model deployment (e.g. ``gpt-5.2``) with the ``instructions``
    and ``tools`` parameters customised per agent.
    """
    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential
    from openai.types.responses import ResponseFunctionToolCall, ResponseOutputMessage

    from ..tools.tool_schemas import AGENT_TOOLS

    credential = DefaultAzureCredential()
    if settings.PROJECT_ENDPOINT:
        project_client = AIProjectClient(
            endpoint=settings.PROJECT_ENDPOINT,
            credential=credential,
        )
    else:
        parts = settings.PROJECT_CONNECTION_STRING.split(";")
        host, sub_id, rg, project = parts
        endpoint = f"https://{host}/api/projects/{project}"
        project_client = AIProjectClient(endpoint=endpoint, credential=credential)

    openai_client = project_client.get_openai_client()
    default_deployment = settings.MODEL_DEPLOYMENT_NAME or "gpt-5.2"

    # Parse per-agent model overrides once
    try:
        _model_overrides: dict[str, str] = json.loads(settings.AGENT_MODEL_OVERRIDES)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Invalid AGENT_MODEL_OVERRIDES, using defaults")
        _model_overrides = {}

    # Parse per-agent max_output_tokens overrides once
    try:
        _token_overrides: dict[str, int] = json.loads(settings.AGENT_MAX_TOKENS_OVERRIDES)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Invalid AGENT_MAX_TOKENS_OVERRIDES, using defaults")
        _token_overrides = {}

    async def _invoke_agent(agent_name: str, user_message: str) -> dict:
        """Invoke an agent via the Responses API with its prompt and tools.

        Returns a dict with ``text`` (the agent's reply) and ``metrics``.
        """
        import openai as _openai_mod

        start = time.monotonic()
        total_input_tokens = 0
        total_output_tokens = 0
        rounds = 0

        deployment = _model_overrides.get(agent_name) or default_deployment
        resolved_max_tokens = _token_overrides.get(agent_name) or settings.MAX_OUTPUT_TOKENS

        agent_instructions = _load_prompt(agent_name)
        # Convert Chat Completions tool format to Responses API format
        agent_tools = [
            {"type": "function", **t["function"]}
            for t in AGENT_TOOLS.get(agent_name, [])
        ]

        async def _create_with_retry(**kwargs: Any) -> Any:
            """Call responses.create with exponential backoff on 429."""
            max_retries = 5
            base_delay = 2.0
            for attempt in range(max_retries + 1):
                try:
                    return await asyncio.to_thread(
                        openai_client.responses.create, **kwargs
                    )
                except _openai_mod.RateLimitError:
                    if attempt == max_retries:
                        raise
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        "Rate limited on %s (attempt %d/%d), retrying in %.1fs",
                        agent_name, attempt + 1, max_retries, delay,
                    )
                    await asyncio.sleep(delay)
            raise RuntimeError("unreachable")  # pragma: no cover

        response = await _create_with_retry(
            model=deployment,
            instructions=agent_instructions,
            input=user_message,
            tools=agent_tools,
            max_output_tokens=resolved_max_tokens,
        )
        rounds = 1
        if getattr(response, "usage", None):
            total_input_tokens += response.usage.input_tokens
            total_output_tokens += response.usage.output_tokens

        # Handle truncation on initial response
        if getattr(response, "status", None) == "incomplete":
            logger.warning(
                "agent=%s response truncated at %d max_output_tokens on initial call",
                agent_name, resolved_max_tokens,
            )

        max_rounds = 15
        for _ in range(max_rounds):
            # Collect any tool calls from the response output
            tool_calls = [
                item for item in response.output
                if isinstance(item, ResponseFunctionToolCall)
            ]
            if not tool_calls:
                break  # No tool calls → agent is done

            # Execute each tool call locally and build result items
            tool_results: list[dict] = []
            for tc in tool_calls:
                fn_args = json.loads(tc.arguments)
                result = await _call_tool(
                    tc.name,
                    fn_args,
                    state_store=state_store,
                    event_store=event_store,
                    message_store=message_store,
                )
                tool_results.append({
                    "type": "function_call_output",
                    "call_id": tc.call_id,
                    "output": json.dumps(result),
                })

            # Send tool results back to the agent
            response = await _create_with_retry(
                model=deployment,
                instructions=agent_instructions,
                input=tool_results,
                tools=agent_tools,
                previous_response_id=response.id,
                max_output_tokens=resolved_max_tokens,
            )
            rounds += 1
            if getattr(response, "usage", None):
                total_input_tokens += response.usage.input_tokens
                total_output_tokens += response.usage.output_tokens

            # Handle truncation — log warning and break out with what we have
            if getattr(response, "status", None) == "incomplete":
                logger.warning(
                    "agent=%s response truncated at %d max_output_tokens (round %d)",
                    agent_name, resolved_max_tokens, rounds,
                )
                break

        # Extract the final text from output items
        text_parts: list[str] = []
        for item in response.output:
            if isinstance(item, ResponseOutputMessage):
                for content in item.content:
                    if hasattr(content, "text"):
                        text_parts.append(content.text)
        text = " ".join(text_parts) if text_parts else ""

        latency = time.monotonic() - start
        metrics: AgentMetrics = {
            "agent_name": agent_name,
            "model": deployment,
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
            "max_output_tokens": resolved_max_tokens,
            "rounds": rounds,
            "latency_seconds": round(latency, 3),
        }
        logger.info(
            "agent=%s model=%s input_tokens=%d output_tokens=%d rounds=%d latency_s=%.2f",
            agent_name, deployment, total_input_tokens, total_output_tokens,
            rounds, latency,
        )
        return {"text": text, "metrics": metrics}

    # ── Supervisor loop: flow-coordinator delegates to specialists ───

    patients = state_store.get_patients(
        filter_fn=lambda p: p.state == PatientState.AWAITING_BED,
    )
    if not patients:
        return {"ok": False, "error": "No patient awaiting bed"}
    patient = patients[0]

    # Build the initial message for flow-coordinator
    state_snapshot = json.dumps(
        {
            "patient": patient.model_dump(mode="json"),
            "ready_beds": [
                b.model_dump(mode="json")
                for b in state_store.get_beds(
                    filter_fn=lambda b: b.state == BedState.READY
                )
            ],
        },
        indent=2,
    )
    initial_msg = (
        f"Patient {patient.name} ({patient.id}) needs a bed. "
        f"Location: {patient.current_location}, Acuity: {patient.acuity_level}, "
        f"Diagnosis: {patient.diagnosis}. "
        f"Scenario type: {scenario_type}.\n\n"
        f"Current state:\n{state_snapshot}\n\n"
        f"Coordinate the full placement workflow. For each step, describe "
        f"what you are doing and use the tools available to you. "
        f"After your initial assessment, I will invoke the specialist agents "
        f"(predictive-capacity, bed-allocation, evs-tasking, transport-ops, "
        f"policy-safety) on your behalf. Tell me which agent to invoke next "
        f"and what to ask them."
    )

    # Step 1: Flow Coordinator starts
    coordinator_result = await _invoke_agent("flow-coordinator", initial_msg)
    coordinator_reply = coordinator_result["text"]
    agent_metrics_list: list[AgentMetrics] = [coordinator_result["metrics"]]
    await message_store.publish(
        agent_name="flow-coordinator",
        agent_role="Flow Coordinator",
        content=coordinator_reply,
        intent_tag=IntentTag.PROPOSE,
    )

    # Step 2: Invoke specialist agents in sequence as directed
    specialist_sequence = [
        ("predictive-capacity", IntentTag.PROPOSE),
        ("policy-safety", IntentTag.VALIDATE),
        ("bed-allocation", IntentTag.EXECUTE),
        ("evs-tasking", IntentTag.EXECUTE),
        ("transport-ops", IntentTag.EXECUTE),
    ]

    context = (
        f"Patient: {patient.name} ({patient.id}), "
        f"Acuity: {patient.acuity_level}, "
        f"Location: {patient.current_location}, "
        f"Diagnosis: {patient.diagnosis}. "
        f"Scenario: {scenario_type}."
    )

    for agent_name, intent_tag in specialist_sequence:
        role = _AGENT_ROLES[agent_name]
        await asyncio.sleep(STEP_DELAY)

        # Announce delegation
        await message_store.publish(
            agent_name="flow-coordinator",
            agent_role="Flow Coordinator",
            content=f"Delegating to {role} ({agent_name}).",
            intent_tag=IntentTag.PROPOSE,
        )

        specialist_msg = (
            f"{context}\n\n"
            f"Flow Coordinator says: {coordinator_reply}\n\n"
            f"Execute your role. Use your tools to take action."
        )

        specialist_result = await _invoke_agent(agent_name, specialist_msg)
        reply = specialist_result["text"]
        agent_metrics_list.append(specialist_result["metrics"])
        await message_store.publish(
            agent_name=agent_name,
            agent_role=role,
            content=reply,
            intent_tag=intent_tag,
        )

        # Feed specialist reply back for context
        context += f"\n\n{role} responded: {reply}"

    # Final wrap-up from coordinator
    await asyncio.sleep(STEP_DELAY)
    wrapup_msg = (
        f"All specialist agents have completed their work.\n\n{context}\n\n"
        f"Summarize the outcome of this placement workflow."
    )
    final_result = await _invoke_agent("flow-coordinator", wrapup_msg)
    final_reply = final_result["text"]
    agent_metrics_list.append(final_result["metrics"])
    await message_store.publish(
        agent_name="flow-coordinator",
        agent_role="Flow Coordinator",
        content=final_reply,
        intent_tag=IntentTag.EXECUTE,
    )

    scenario_metrics: ScenarioMetrics = {
        "total_latency_seconds": round(
            sum(m["latency_seconds"] for m in agent_metrics_list), 3
        ),
        "total_input_tokens": sum(m["input_tokens"] for m in agent_metrics_list),
        "total_output_tokens": sum(m["output_tokens"] for m in agent_metrics_list),
        "agents": agent_metrics_list,
    }

    return {"ok": True, "scenario": scenario_type, "mode": "live", "metrics": scenario_metrics}


# ── Simulated orchestration (no Azure) ──────────────────────────────

async def _simulate_happy_path(
    state_store: StateStore,
    event_store: EventStore,
    message_store: MessageStore,
) -> dict:
    """Walk through the happy-path scenario with scripted tool calls."""
    sim_start = time.monotonic()
    patients = state_store.get_patients(
        filter_fn=lambda p: p.state == PatientState.AWAITING_BED,
    )
    if not patients:
        return {"ok": False, "error": "No patient awaiting bed"}
    patient = patients[0]

    # ── Step 1: Predictive Capacity ranks beds ──────────────────────
    await asyncio.sleep(STEP_DELAY)
    await message_store.publish(
        agent_name="flow-coordinator",
        agent_role="Flow Coordinator",
        content=(
            f"Initiating bed placement for {patient.name} ({patient.id}). "
            f"Requesting Predictive Capacity to rank available beds."
        ),
        intent_tag=IntentTag.PROPOSE,
    )

    await asyncio.sleep(STEP_DELAY)
    beds_result = await _call_tool(
        "get_beds", {"state": "READY"},
        state_store=state_store, event_store=event_store, message_store=message_store,
    )
    ready_beds = beds_result.get("beds", [])

    # Simulated scoring (ADR-010)
    ranked = sorted(ready_beds, key=lambda b: b.get("unit", ""))
    top_beds = ranked[:3]
    ranking_text = "\n".join(
        f"  {i+1}. {b['id']} ({b['unit']} {b['room_number']}{b['bed_letter']}) — "
        f"Score: {95 - i*5}%, Ready now"
        for i, b in enumerate(top_beds)
    )

    await message_store.publish(
        agent_name="predictive-capacity",
        agent_role="Predictive Capacity Agent",
        content=f"Bed ranking for patient {patient.id}:\n{ranking_text}",
        intent_tag=IntentTag.PROPOSE,
    )

    if not top_beds:
        await message_store.publish(
            agent_name="flow-coordinator",
            agent_role="Flow Coordinator",
            content="No READY beds available. Escalating.",
            intent_tag=IntentTag.ESCALATE,
        )
        return {"ok": False, "error": "No READY beds available"}

    # ── Step 2: Policy & Safety validates ───────────────────────────
    await asyncio.sleep(STEP_DELAY)
    best_bed = top_beds[0]
    await message_store.publish(
        agent_name="flow-coordinator",
        agent_role="Flow Coordinator",
        content=(
            f"Top candidate: {best_bed['id']}. "
            f"Forwarding to Policy & Safety for validation."
        ),
        intent_tag=IntentTag.PROPOSE,
    )

    await asyncio.sleep(STEP_DELAY)
    # Determine acuity suitability description
    acuity = patient.acuity_level
    if acuity <= 2:
        acuity_assessment = f"Acuity {acuity} (low) — Med-Surg unit is appropriate"
    elif acuity == 3:
        acuity_assessment = f"Acuity {acuity} (moderate) — Med-Surg acceptable, monitoring capability confirmed"
    elif acuity == 4:
        acuity_assessment = f"Acuity {acuity} (high) — step-down/telemetry preferred, nurse staffing ratio verified"
    else:
        acuity_assessment = f"Acuity {acuity} (critical) — ICU required"

    await message_store.publish(
        agent_name="policy-safety",
        agent_role="Policy & Safety Agent",
        content=(
            f"APPROVED — Bed {best_bed['id']} for patient {patient.id}.\n"
            f"  ✓ Acuity check: {acuity_assessment}. "
            f"Unit {best_bed['unit']} meets placement criteria.\n"
            f"  ✓ Infection control: No active isolation flags on patient record. "
            f"Standard precautions apply.\n"
            f"  ✓ Isolation: No isolation requirement identified for dx '{patient.diagnosis}'.\n"
            f"  ✓ Fall risk: Standard protocol — room is within acceptable distance of nursing station.\n"
            f"  Confidence: 97%. Proceed with reservation."
        ),
        intent_tag=IntentTag.VALIDATE,
    )

    # ── Step 3: Bed Allocation reserves the bed ─────────────────────
    await asyncio.sleep(STEP_DELAY)
    await message_store.publish(
        agent_name="flow-coordinator",
        agent_role="Flow Coordinator",
        content=f"Directing Bed Allocation to reserve {best_bed['id']} for {patient.id}.",
        intent_tag=IntentTag.EXECUTE,
    )

    reserve_result = await _call_tool(
        "reserve_bed",
        {"bed_id": best_bed["id"], "patient_id": patient.id},
        state_store=state_store, event_store=event_store, message_store=message_store,
    )
    if not reserve_result.get("ok"):
        return {"ok": False, "error": reserve_result.get("error", "reserve_bed failed")}

    # Patient → BED_ASSIGNED
    await state_store.transition_patient(patient.id, PatientState.BED_ASSIGNED)
    patient.assigned_bed_id = best_bed["id"]

    await asyncio.sleep(STEP_DELAY)
    await message_store.publish(
        agent_name="bed-allocation",
        agent_role="Bed Allocation Agent",
        content=(
            f"Bed {best_bed['id']} is already READY — no cleaning required. "
            f"Patient {patient.id} assigned."
        ),
        intent_tag=IntentTag.VALIDATE,
    )

    # ── Step 4: EVS Tasking (bed is already READY, just confirmation) ─
    await asyncio.sleep(STEP_DELAY)
    await message_store.publish(
        agent_name="flow-coordinator",
        agent_role="Flow Coordinator",
        content=(
            f"Bed {best_bed['id']} is READY — skipping EVS cleaning. "
            f"Proceeding to schedule transport."
        ),
        intent_tag=IntentTag.EXECUTE,
    )

    # ── Step 5: Transport Ops ───────────────────────────────────────
    await asyncio.sleep(STEP_DELAY)
    bed_obj = state_store.get_bed(best_bed["id"])
    to_location = f"{bed_obj.unit} {bed_obj.room_number}{bed_obj.bed_letter}"

    transport_result = await _call_tool(
        "schedule_transport",
        {
            "patient_id": patient.id,
            "from_location": patient.current_location,
            "to_location": to_location,
            "priority": "ROUTINE",
        },
        state_store=state_store, event_store=event_store, message_store=message_store,
    )

    # Patient → TRANSPORT_READY → IN_TRANSIT
    await asyncio.sleep(STEP_DELAY)
    await state_store.transition_patient(patient.id, PatientState.TRANSPORT_READY)
    await message_store.publish(
        agent_name="transport-ops",
        agent_role="Transport Operations Agent",
        content=(
            f"Transport {transport_result.get('transport_id')} dispatched. "
            f"Patient {patient.id} is transport-ready."
        ),
        intent_tag=IntentTag.EXECUTE,
    )

    await asyncio.sleep(STEP_DELAY)
    await state_store.transition_patient(patient.id, PatientState.IN_TRANSIT)
    await message_store.publish(
        agent_name="transport-ops",
        agent_role="Transport Operations Agent",
        content=f"Patient {patient.id} picked up from {patient.current_location}. In transit to {to_location}.",
        intent_tag=IntentTag.EXECUTE,
    )

    # ── Step 6: Arrival ─────────────────────────────────────────────
    await asyncio.sleep(STEP_DELAY)
    await state_store.transition_patient(patient.id, PatientState.ARRIVED)
    patient.current_location = to_location

    # Bed → OCCUPIED
    await state_store.transition_bed(best_bed["id"], BedState.OCCUPIED)
    bed_obj.patient_id = patient.id
    bed_obj.reserved_for_patient_id = None
    bed_obj.reserved_until = None

    await message_store.publish(
        agent_name="flow-coordinator",
        agent_role="Flow Coordinator",
        content=(
            f"Patient {patient.name} ({patient.id}) has ARRIVED at {to_location}. "
            f"Bed {best_bed['id']} is now OCCUPIED. Placement workflow complete."
        ),
        intent_tag=IntentTag.EXECUTE,
    )

    await event_store.publish(
        event_type="PlacementComplete",
        entity_id=patient.id,
        payload={"patient_id": patient.id, "bed_id": best_bed["id"], "scenario": "happy-path"},
    )

    sim_latency = time.monotonic() - sim_start
    return {
        "ok": True,
        "scenario": "happy-path",
        "mode": "simulated",
        "patient_id": patient.id,
        "bed_id": best_bed["id"],
        "final_patient_state": str(patient.state),
        "final_bed_state": str(bed_obj.state),
        "metrics": {
            "total_latency_seconds": round(sim_latency, 3),
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "agents": [
                {"agent_name": n, "model": "simulated", "input_tokens": 0,
                 "output_tokens": 0, "rounds": 0, "latency_seconds": 0.0}
                for n in [
                    "flow-coordinator", "predictive-capacity", "policy-safety",
                    "bed-allocation", "transport-ops",
                ]
            ],
        },
    }


async def _simulate_disruption_replan(
    state_store: StateStore,
    event_store: EventStore,
    message_store: MessageStore,
) -> dict:
    """Walk through the disruption + re-plan scenario with scripted steps."""
    sim_start = time.monotonic()
    patients = state_store.get_patients(
        filter_fn=lambda p: p.state == PatientState.AWAITING_BED,
    )
    if not patients:
        return {"ok": False, "error": "No patient awaiting bed"}
    patient = patients[0]

    # ── Step 1: Predictive Capacity ranks beds ──────────────────────
    await asyncio.sleep(STEP_DELAY)
    await message_store.publish(
        agent_name="flow-coordinator",
        agent_role="Flow Coordinator",
        content=(
            f"URGENT bed placement for {patient.name} ({patient.id}), acuity {patient.acuity_level}. "
            f"Requesting Predictive Capacity to rank available beds."
        ),
        intent_tag=IntentTag.PROPOSE,
    )

    await asyncio.sleep(STEP_DELAY)
    beds_result = await _call_tool(
        "get_beds", {"state": "READY"},
        state_store=state_store, event_store=event_store, message_store=message_store,
    )
    ready_beds = beds_result.get("beds", [])
    ranked = sorted(ready_beds, key=lambda b: b.get("unit", ""))
    top_beds = ranked[:3]

    ranking_text = "\n".join(
        f"  {i+1}. {b['id']} ({b['unit']} {b['room_number']}{b['bed_letter']}) — "
        f"Score: {95 - i*5}%, Ready now"
        for i, b in enumerate(top_beds)
    )
    await message_store.publish(
        agent_name="predictive-capacity",
        agent_role="Predictive Capacity Agent",
        content=f"Bed ranking for URGENT patient {patient.id}:\n{ranking_text}",
        intent_tag=IntentTag.PROPOSE,
    )

    if not top_beds:
        await message_store.publish(
            agent_name="flow-coordinator",
            agent_role="Flow Coordinator",
            content="No READY beds available. Escalating — critical capacity shortage.",
            intent_tag=IntentTag.ESCALATE,
        )
        return {"ok": False, "error": "No READY beds for disruption scenario"}

    # ── Step 2: Policy validates first choice ───────────────────────
    first_bed = top_beds[0]
    await asyncio.sleep(STEP_DELAY)
    acuity = patient.acuity_level
    if acuity <= 2:
        acuity_assessment = f"Acuity {acuity} (low) — Med-Surg unit is appropriate"
    elif acuity == 3:
        acuity_assessment = f"Acuity {acuity} (moderate) — Med-Surg acceptable, monitoring capability confirmed"
    elif acuity == 4:
        acuity_assessment = f"Acuity {acuity} (high) — step-down/telemetry preferred, nurse staffing ratio verified"
    else:
        acuity_assessment = f"Acuity {acuity} (critical) — ICU required"

    await message_store.publish(
        agent_name="policy-safety",
        agent_role="Policy & Safety Agent",
        content=(
            f"APPROVED — Bed {first_bed['id']} for patient {patient.id}.\n"
            f"  ✓ Acuity check: {acuity_assessment}. "
            f"Unit {first_bed['unit']} meets placement criteria.\n"
            f"  ✓ Infection control: No active isolation flags. "
            f"Standard precautions apply.\n"
            f"  ✓ Isolation: No isolation requirement for dx '{patient.diagnosis}'.\n"
            f"  Confidence: 95%. Proceed with reservation."
        ),
        intent_tag=IntentTag.VALIDATE,
    )

    # ── Step 3: Bed Allocation reserves the first bed ───────────────
    await asyncio.sleep(STEP_DELAY)
    await message_store.publish(
        agent_name="flow-coordinator",
        agent_role="Flow Coordinator",
        content=f"Directing Bed Allocation to reserve {first_bed['id']} for {patient.id}.",
        intent_tag=IntentTag.EXECUTE,
    )

    reserve_result = await _call_tool(
        "reserve_bed",
        {"bed_id": first_bed["id"], "patient_id": patient.id},
        state_store=state_store, event_store=event_store, message_store=message_store,
    )
    if not reserve_result.get("ok"):
        return {"ok": False, "error": reserve_result.get("error", "reserve_bed failed")}

    await state_store.transition_patient(patient.id, PatientState.BED_ASSIGNED)
    patient.assigned_bed_id = first_bed["id"]

    # ── Step 4: EVS Tasking starts cleaning ─────────────────────────
    await asyncio.sleep(STEP_DELAY)
    await message_store.publish(
        agent_name="flow-coordinator",
        agent_role="Flow Coordinator",
        content=f"Bed {first_bed['id']} reserved. Triggering EVS cleaning task.",
        intent_tag=IntentTag.EXECUTE,
    )

    task_result = await _call_tool(
        "create_task",
        {"task_type": "EVS_CLEANING", "subject_id": first_bed["id"], "priority": "URGENT"},
        state_store=state_store, event_store=event_store, message_store=message_store,
    )
    task_id = task_result.get("task_id")

    await _call_tool(
        "update_task", {"task_id": task_id, "new_status": "ACCEPTED", "eta_minutes": 15},
        state_store=state_store, event_store=event_store, message_store=message_store,
    )

    # ── Step 5: DISRUPTION — bed goes BLOCKED ───────────────────────
    await asyncio.sleep(STEP_DELAY)
    # Simulate an infrastructure disruption blocking the reserved bed
    bed_obj = state_store.get_bed(first_bed["id"])
    await state_store.transition_bed(first_bed["id"], BedState.BLOCKED)

    await event_store.publish(
        event_type="BedStateChanged",
        entity_id=first_bed["id"],
        payload={"bed_id": first_bed["id"], "reason": "Water leak reported in room"},
        state_diff={"from_state": "RESERVED", "to_state": "BLOCKED"},
    )

    await message_store.publish(
        agent_name="evs-tasking",
        agent_role="EVS Tasking Agent",
        content=(
            f"⚠ DISRUPTION: Bed {first_bed['id']} is now BLOCKED (water leak reported). "
            f"Cannot proceed with cleaning. Escalating to Flow Coordinator."
        ),
        intent_tag=IntentTag.ESCALATE,
    )

    # Policy & Safety flags the blocked bed as a safety concern
    await asyncio.sleep(STEP_DELAY)
    await message_store.publish(
        agent_name="policy-safety",
        agent_role="Policy & Safety Agent",
        content=(
            f"⚠ SAFETY CONCERN — Bed {first_bed['id']} blocked during active placement.\n"
            f"  Patient {patient.id} (acuity {patient.acuity_level}) is currently assigned to this bed.\n"
            f"  Policy ref: All bed disruptions during active placement require immediate re-routing.\n"
            f"  Risk: SLA breach — ED-to-bed timer is running. Escalation level: HIGH.\n"
            f"  Action required: Release reservation, identify fallback bed, document incident."
        ),
        intent_tag=IntentTag.ESCALATE,
    )

    # ── Step 6: EVS escalates SLA risk ──────────────────────────────
    await asyncio.sleep(STEP_DELAY)
    await _call_tool(
        "escalate",
        {
            "issue_type": "sla_breach",
            "entity_id": first_bed["id"],
            "severity": "HIGH",
            "message": f"Bed {first_bed['id']} blocked — patient {patient.id} placement at risk.",
        },
        state_store=state_store, event_store=event_store, message_store=message_store,
    )

    # Cancel the cleaning task
    await _call_tool(
        "update_task", {"task_id": task_id, "new_status": "IN_PROGRESS"},
        state_store=state_store, event_store=event_store, message_store=message_store,
    )
    await _call_tool(
        "update_task", {"task_id": task_id, "new_status": "ESCALATED"},
        state_store=state_store, event_store=event_store, message_store=message_store,
    )

    # ── Step 7: Policy & Safety recommends fallback ─────────────────
    await asyncio.sleep(STEP_DELAY)

    # Find a fallback bed
    fallback_beds_result = await _call_tool(
        "get_beds", {"state": "READY"},
        state_store=state_store, event_store=event_store, message_store=message_store,
    )
    fallback_beds = fallback_beds_result.get("beds", [])
    if not fallback_beds:
        await message_store.publish(
            agent_name="policy-safety",
            agent_role="Policy & Safety Agent",
            content="CRITICAL: No fallback beds available. Manual intervention required.",
            intent_tag=IntentTag.ESCALATE,
        )
        return {"ok": False, "error": "No fallback beds available"}

    fallback_bed = fallback_beds[0]
    await message_store.publish(
        agent_name="policy-safety",
        agent_role="Policy & Safety Agent",
        content=(
            f"APPROVED — Fallback bed {fallback_bed['id']} for patient {patient.id}.\n"
            f"  Comparison to original placement:\n"
            f"    Original: {first_bed['id']} ({first_bed['unit']}) — now BLOCKED (unsafe)\n"
            f"    Fallback: {fallback_bed['id']} ({fallback_bed['unit']}) — READY, clinically equivalent\n"
            f"  ✓ Acuity check: Patient acuity {patient.acuity_level} compatible with {fallback_bed['unit']}.\n"
            f"  ✓ Infection control: Cleared — no change in isolation status.\n"
            f"  ✓ Safety: Fallback bed meets all original placement criteria.\n"
            f"  Confidence: 93% (minor score reduction due to unit change).\n"
            f"  ⚠ Incident report required: Bed disruption during active placement must be documented "
            f"per safety protocol. Filing SafetyIncident event."
        ),
        intent_tag=IntentTag.VALIDATE,
    )

    # Publish safety incident event for the bed disruption
    await event_store.publish(
        event_type="SafetyIncident",
        entity_id=first_bed["id"],
        payload={
            "incident_category": "bed_disruption",
            "severity": "HIGH",
            "affected_bed": first_bed["id"],
            "affected_patient": patient.id,
            "description": f"Bed {first_bed['id']} blocked (water leak) during active placement for patient {patient.id}. Fallback to {fallback_bed['id']}.",
            "fallback_bed": fallback_bed["id"],
            "original_validation_confidence": 95,
            "fallback_validation_confidence": 93,
            "requires_post_incident_review": True,
        },
    )

    # ── Step 8: Release old reservation, reserve fallback ───────────
    await asyncio.sleep(STEP_DELAY)
    await message_store.publish(
        agent_name="flow-coordinator",
        agent_role="Flow Coordinator",
        content=(
            f"Accepted fallback. Releasing blocked bed {first_bed['id']} "
            f"and reserving {fallback_bed['id']}."
        ),
        intent_tag=IntentTag.EXECUTE,
    )

    # Patient back to AWAITING_BED so we can re-assign
    await state_store.transition_patient(patient.id, PatientState.AWAITING_BED)
    patient.assigned_bed_id = None

    # Release old reservation (bed is BLOCKED → DIRTY is the valid transition)
    # Deactivate reservation records manually since bed is BLOCKED
    active_reservations = [
        r for r in state_store.reservations.values()
        if r.bed_id == first_bed["id"] and r.is_active
    ]
    for r in active_reservations:
        r.is_active = False
    bed_obj.reserved_for_patient_id = None
    bed_obj.reserved_until = None

    # Reserve fallback bed
    reserve2_result = await _call_tool(
        "reserve_bed",
        {"bed_id": fallback_bed["id"], "patient_id": patient.id},
        state_store=state_store, event_store=event_store, message_store=message_store,
    )
    if not reserve2_result.get("ok"):
        return {"ok": False, "error": reserve2_result.get("error", "fallback reserve failed")}

    await state_store.transition_patient(patient.id, PatientState.BED_ASSIGNED)
    patient.assigned_bed_id = fallback_bed["id"]

    await message_store.publish(
        agent_name="bed-allocation",
        agent_role="Bed Allocation Agent",
        content=(
            f"Fallback bed {fallback_bed['id']} reserved for patient {patient.id}. "
            f"Bed is already READY — no cleaning needed."
        ),
        intent_tag=IntentTag.EXECUTE,
    )

    # ── Step 9: Transport Ops reschedules ───────────────────────────
    await asyncio.sleep(STEP_DELAY)
    fb_bed_obj = state_store.get_bed(fallback_bed["id"])
    to_location = f"{fb_bed_obj.unit} {fb_bed_obj.room_number}{fb_bed_obj.bed_letter}"

    await message_store.publish(
        agent_name="flow-coordinator",
        agent_role="Flow Coordinator",
        content=f"Scheduling transport to fallback bed {fallback_bed['id']} at {to_location}.",
        intent_tag=IntentTag.EXECUTE,
    )

    transport_result = await _call_tool(
        "schedule_transport",
        {
            "patient_id": patient.id,
            "from_location": patient.current_location,
            "to_location": to_location,
            "priority": "URGENT",
        },
        state_store=state_store, event_store=event_store, message_store=message_store,
    )

    # Patient → TRANSPORT_READY → IN_TRANSIT → ARRIVED
    await asyncio.sleep(STEP_DELAY)
    await state_store.transition_patient(patient.id, PatientState.TRANSPORT_READY)
    await message_store.publish(
        agent_name="transport-ops",
        agent_role="Transport Operations Agent",
        content=(
            f"URGENT transport {transport_result.get('transport_id')} dispatched. "
            f"Patient {patient.id} ready for pickup."
        ),
        intent_tag=IntentTag.EXECUTE,
    )

    await asyncio.sleep(STEP_DELAY)
    await state_store.transition_patient(patient.id, PatientState.IN_TRANSIT)
    await message_store.publish(
        agent_name="transport-ops",
        agent_role="Transport Operations Agent",
        content=f"Patient {patient.id} in transit to {to_location}.",
        intent_tag=IntentTag.EXECUTE,
    )

    # ── Step 10: Arrival ────────────────────────────────────────────
    await asyncio.sleep(STEP_DELAY)
    await state_store.transition_patient(patient.id, PatientState.ARRIVED)
    patient.current_location = to_location

    # Bed → OCCUPIED
    await state_store.transition_bed(fallback_bed["id"], BedState.OCCUPIED)
    fb_bed_obj.patient_id = patient.id
    fb_bed_obj.reserved_for_patient_id = None
    fb_bed_obj.reserved_until = None

    await message_store.publish(
        agent_name="flow-coordinator",
        agent_role="Flow Coordinator",
        content=(
            f"Patient {patient.name} ({patient.id}) has ARRIVED at {to_location} "
            f"(fallback bed {fallback_bed['id']}). Disruption resolved. "
            f"Original bed {first_bed['id']} remains BLOCKED for maintenance."
        ),
        intent_tag=IntentTag.EXECUTE,
    )

    await event_store.publish(
        event_type="PlacementComplete",
        entity_id=patient.id,
        payload={
            "patient_id": patient.id,
            "bed_id": fallback_bed["id"],
            "original_bed_id": first_bed["id"],
            "scenario": "disruption-replan",
            "disruption": "bed_blocked",
        },
    )

    sim_latency = time.monotonic() - sim_start
    return {
        "ok": True,
        "scenario": "disruption-replan",
        "mode": "simulated",
        "patient_id": patient.id,
        "original_bed_id": first_bed["id"],
        "fallback_bed_id": fallback_bed["id"],
        "final_patient_state": str(patient.state),
        "final_bed_state": str(fb_bed_obj.state),
        "metrics": {
            "total_latency_seconds": round(sim_latency, 3),
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "agents": [
                {"agent_name": n, "model": "simulated", "input_tokens": 0,
                 "output_tokens": 0, "rounds": 0, "latency_seconds": 0.0}
                for n in [
                    "flow-coordinator", "predictive-capacity", "policy-safety",
                    "bed-allocation", "evs-tasking", "transport-ops",
                ]
            ],
        },
    }


# ── Public entry point ──────────────────────────────────────────────

async def run_scenario(
    scenario_type: str,
    state_store: StateStore,
    event_store: EventStore,
    message_store: MessageStore,
) -> dict:
    """Run an orchestration scenario (live or simulated).

    Args:
        scenario_type: ``"happy-path"`` or ``"disruption-replan"``
        state_store: Singleton state store.
        event_store: Singleton event store.
        message_store: Singleton message store.

    Returns:
        Result dict with ``ok`` bool and scenario details.
    """
    if _use_live_agents():
        logger.info("Running %s with live Foundry agents", scenario_type)
        return await _run_live(scenario_type, state_store, event_store, message_store)

    logger.info("Running %s in simulated mode (no Foundry agents)", scenario_type)
    if scenario_type == "happy-path":
        return await _simulate_happy_path(state_store, event_store, message_store)
    elif scenario_type == "disruption-replan":
        return await _simulate_disruption_replan(state_store, event_store, message_store)
    else:
        return {"ok": False, "error": f"Unknown scenario: {scenario_type}"}
