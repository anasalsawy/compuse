"""Demo and workflow helpers shared by the CLI and GUI applications."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import TypeAdapter

from compuse.protocol import Action, ActionProposal, Observation, Origin, Permit, digest_action
from compuse.coordinator import Coordinator
from compuse.storage import EventStore
from compuse.app.executor import execute


def build_action(payload: dict[str, Any]) -> Action:
    """Validate and construct a typed action from a plain dictionary."""
    return TypeAdapter(Action).validate_python(payload)


def demo(events: list[str]) -> None:
    """Run the full lifecycle demonstration, appending trace lines to ``events``."""
    a = build_action({"kind": "type", "text": "hello from compuse"})
    events.append(f"action        {a.kind} text={a.text!r}")
    o = Observation(
        run_id="demo-run",
        revision=0,
        captured_at=datetime.now(timezone.utc),
        coordinate_space_id="demo-space",
    )
    events.append("observation   bound to demo-run (revision 0)")
    store = EventStore()
    co = Coordinator(store=store)
    p = ActionProposal(
        action_id="demo-action",
        run_id="demo-run",
        action=a,
        origin=Origin.USER_INTENT,
        observation_revision=0,
        coordinate_space_id="demo-space",
        policy_revision="policy-1",
    )
    permit = co.issue(p, o, ttl=30)
    events.append(f"permit        issued {permit.permit_id} (ttl 30s)")
    result = co.consume(permit.permit_id, p, o)
    events.append(f"consume       approved {result.kind!r}; permit spent={permit.consumed}")
    co.release(permit.permit_id)
    events.append("release       mutation boundary released")
    count = len(store.events("demo-run"))
    events.append(f"journal       {count} events, chain verifies={store.verify('demo-run')}")
    events.append("demo          complete")


def run_demo() -> list[str]:
    lines: list[str] = []
    demo(lines)
    return lines


def authorize(action_payload: dict[str, Any], *, run_id: str = "cli-run",
              ttl: float = 30.0, journal_path: str | None = None) -> dict[str, Any]:
    """One-shot propose -> issue -> consume -> release, optionally persisted."""
    action = build_action(action_payload)
    observation = Observation(
        run_id=run_id,
        revision=0,
        captured_at=datetime.now(timezone.utc),
        coordinate_space_id="cli-space",
    )
    store = EventStore(journal_path if journal_path else ":memory:")
    coordinator = Coordinator(store=store)
    proposal = ActionProposal(
        action_id=f"{run_id}-action",
        run_id=run_id,
        action=action,
        origin=Origin.USER_INTENT,
        observation_revision=0,
        coordinate_space_id="cli-space",
        policy_revision=coordinator.policy_revision,
    )
    permit = coordinator.issue(proposal, observation, ttl=ttl)
    approved = coordinator.consume(permit.permit_id, proposal, observation)
    coordinator.release(permit.permit_id)
    return {
        "approved": approved.model_dump(mode="json"),
        "permit_id": str(permit.permit_id),
        "policy_revision": permit.policy_revision,
        "journal_events": len(store.events(run_id)),
        "journal_verifies": store.verify(run_id),
    }


def perform(action_payload: dict[str, Any], *, run_id: str = "cli-run",
            ttl: float = 30.0, journal_path: str | None = None) -> dict[str, Any]:
    """Propose -> issue -> consume -> EXECUTE -> release, journaled as it goes."""
    action = build_action(action_payload)
    observation = Observation(
        run_id=run_id,
        revision=0,
        captured_at=datetime.now(timezone.utc),
        coordinate_space_id="cli-space",
    )
    store = EventStore(journal_path if journal_path else ":memory:")
    coordinator = Coordinator(store=store)
    proposal = ActionProposal(
        action_id=f"{run_id}-action",
        run_id=run_id,
        action=action,
        origin=Origin.USER_INTENT,
        observation_revision=0,
        coordinate_space_id="cli-space",
        policy_revision=coordinator.policy_revision,
    )
    permit = coordinator.issue(proposal, observation, ttl=ttl)
    approved = coordinator.consume(permit.permit_id, proposal, observation)
    try:
        execution = execute(approved)
    finally:
        coordinator.release(permit.permit_id)
    return {
        "approved": approved.model_dump(mode="json"),
        "permit_id": str(permit.permit_id),
        "policy_revision": permit.policy_revision,
        "execution": execution,
        "journal_events": len(store.events(run_id)),
        "journal_verifies": store.verify(run_id),
    }


__all__ = ["build_action", "demo", "run_demo", "authorize", "perform"]