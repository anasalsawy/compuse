"""Concurrent dual-lobe runtime for fast but guarded desktop operation."""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Callable, Protocol

from compuse.coordinator import Coordinator
from compuse.protocol import Action, ActionProposal, Origin
from compuse.storage import EventStore

from .contracts import (
    ActionExecution,
    BatchExecution,
    BatchSpec,
    LobeDecision,
    RuntimeObservation,
    RuntimeReport,
)


class StaleBatch(RuntimeError):
    """Raised when a speculative batch no longer matches the desktop."""


class DesktopAdapter(Protocol):
    def observe(self) -> RuntimeObservation: ...

    def execute_action(self, action: Action) -> dict[str, Any]: ...


class LobeA(Protocol):
    def plan_initial(self, task: str, observation: RuntimeObservation) -> BatchSpec | None: ...

    def predict_next(
        self,
        task: str,
        active_batch: BatchSpec,
        observation: RuntimeObservation,
    ) -> BatchSpec | None: ...


class LobeB(Protocol):
    def prepare_next(
        self,
        task: str,
        active_batch: BatchSpec,
        observation: RuntimeObservation,
    ) -> LobeDecision: ...


class DualLobeRuntime:
    """Runs A and B beside physical execution.

    At each boundary:

    * the current batch is checked against the fresh observation;
    * A predicts a next batch and B independently prepares/guards one;
    * both predictions run while the current batch executes;
    * only B's approved batch is eligible for the next boundary;
    * any mismatch, failure, or uncertain result invalidates speculation.

    Physical input is still serialized through one Coordinator mutation
    boundary.  Planning may overlap execution; input injection never does.
    """

    def __init__(
        self,
        *,
        adapter: DesktopAdapter,
        lobe_a: LobeA,
        lobe_b: LobeB,
        run_id: str = "dual-lobe-run",
        journal_path: str | None = None,
        ttl: float = 30.0,
        max_actions_per_batch: int = 8,
        trace: Callable[[str], None] | None = None,
    ) -> None:
        if not 1 <= max_actions_per_batch <= 8:
            raise ValueError("max_actions_per_batch must be between 1 and 8")
        self.adapter = adapter
        self.lobe_a = lobe_a
        self.lobe_b = lobe_b
        self.run_id = run_id
        self.ttl = ttl
        self.max_actions_per_batch = max_actions_per_batch
        self.trace = trace
        self._trace_started_at = time.perf_counter()
        self.store = EventStore(journal_path if journal_path else ":memory:")
        self.coordinator = Coordinator(store=self.store)

    def _trace(self, phase: str, **fields: object) -> None:
        if self.trace is None:
            return
        elapsed_ms = (time.perf_counter() - self._trace_started_at) * 1000.0
        details = " ".join(f"{key}={value}" for key, value in fields.items())
        line = f"[{elapsed_ms:9.1f}ms] {phase}"
        if details:
            line += f" {details}"
        self.trace(line)

    def _observe(self) -> RuntimeObservation:
        observation = self.adapter.observe()
        # The adapter owns capture; the runtime owns the durable run identity.
        return observation.model_copy(update={"run_id": self.run_id})

    def _append(self, event_type: str, payload: dict[str, Any]) -> None:
        self.store.append(self.run_id, event_type, payload, datetime.now(timezone.utc).isoformat())

    def _execute_batch(self, batch: BatchSpec, starting_observation: RuntimeObservation) -> BatchExecution:
        if not batch.preconditions.matches(starting_observation):
            raise StaleBatch(f"batch {batch.batch_id} preconditions do not match observation {starting_observation.revision}")

        self._trace("EXEC", state="START", batch=batch.batch_id, actions=len(batch.actions))

        results: list[ActionExecution] = []
        uncertain = False
        failure_index: int | None = None
        error: str | None = None
        self._append("batch_started", {
            "batch_id": batch.batch_id,
            "action_count": len(batch.actions),
            "observation": starting_observation.journal_view(),
            "predicted_end": batch.predicted_end.model_dump(mode="json"),
        })

        for index, action in enumerate(batch.actions):
            action_started = time.perf_counter()
            self._trace("EXEC", state="ACTION_START", batch=batch.batch_id, index=f"{index + 1}/{len(batch.actions)}", kind=action.kind)
            proposal = ActionProposal(
                action_id=f"{batch.batch_id}-a{index}",
                run_id=self.run_id,
                action=action,
                origin=Origin.STRATEGIST_INSTRUCTION,
                observation_revision=starting_observation.revision + index,
                coordinate_space_id=starting_observation.coordinate_space_id,
                policy_revision=self.coordinator.policy_revision,
                tool="desktop",
                window_id=starting_observation.window_id,
                process_id=starting_observation.process_id,
                session_id=starting_observation.session_id,
                input_desktop=starting_observation.input_desktop,
            )
            # The same typed proposal is bound to the observation used for the
            # action slot.  The adapter may observe more frequently, but it
            # cannot inject another mutation concurrently.
            protocol_observation = starting_observation.protocol_observation().model_copy(
                update={"revision": starting_observation.revision + index}
            )
            permit = self.coordinator.issue(proposal, protocol_observation, ttl=self.ttl)
            try:
                approved = self.coordinator.consume(permit.permit_id, proposal, protocol_observation)
                try:
                    result = self.adapter.execute_action(approved)
                    performed = bool(result.get("performed"))
                    action_uncertain = bool(result.get("uncertain", False))
                    detail = str(result.get("detail", ""))
                except Exception as exc:  # noqa: BLE001 - physical dispatch can be interrupted
                    performed = False
                    action_uncertain = True
                    detail = str(exc)
                    error = detail
                elapsed = (time.perf_counter() - action_started) * 1000.0
                action_result = ActionExecution(
                    action_kind=str(approved.kind),
                    performed=performed,
                    uncertain=action_uncertain,
                    detail=detail,
                    elapsed_ms=elapsed,
                )
                results.append(action_result)
                self._trace(
                    "EXEC",
                    state="ACTION_DONE" if performed else "ACTION_FAIL",
                    batch=batch.batch_id,
                    index=f"{index + 1}/{len(batch.actions)}",
                    elapsed_ms=f"{elapsed:.1f}",
                )
                uncertain = uncertain or action_uncertain
                if not performed:
                    failure_index = index
                    if not action_uncertain:
                        error = error or detail or "action was not performed"
                    break
                self._append("action_result", {
                    "batch_id": batch.batch_id,
                    "index": index,
                    "kind": str(approved.kind),
                    "performed": performed,
                    "uncertain": action_uncertain,
                    "detail": detail,
                    "elapsed_ms": elapsed,
                })
            finally:
                self.coordinator.release(permit.permit_id)

        actual = self._observe()
        ok = bool(results) and len(results) == len(batch.actions) and all(r.performed for r in results)
        if uncertain:
            ok = False
        self._append("batch_finished", {
            "batch_id": batch.batch_id,
            "ok": ok,
            "uncertain": uncertain,
            "failure_index": failure_index,
            "actual_observation": actual.journal_view(),
        })
        self._trace("EXEC", state="DONE" if ok else "INVALID", batch=batch.batch_id, verified=ok)
        return BatchExecution(
            batch_id=batch.batch_id,
            ok=ok,
            uncertain=uncertain,
            results=tuple(results),
            failure_index=failure_index,
            error=error,
            actual_observation=actual,
        )

    def _valid_next_batch(self, active: BatchSpec, candidate: BatchSpec | None) -> bool:
        if candidate is None:
            return False
        if len(candidate.actions) > self.max_actions_per_batch:
            return False
        if candidate.preconditions.source_batch_id != active.batch_id:
            return False
        predicted = active.predicted_end
        expected_markers = set(predicted.required_markers)
        candidate_markers = set(candidate.preconditions.required_markers)
        if not expected_markers.issubset(candidate_markers):
            return False
        if predicted.foreground_window is not None and candidate.preconditions.foreground_window != predicted.foreground_window:
            return False
        if predicted.browser_url is not None and candidate.preconditions.browser_url != predicted.browser_url:
            return False
        if predicted.strict and candidate.preconditions.require_anchor is False:
            return False
        return candidate.preconditions.coordinate_space_id == predicted.coordinate_space_id

    def run(self, task: str, *, max_batches: int = 32) -> RuntimeReport:
        if not task.strip():
            raise ValueError("task must not be empty")
        if max_batches < 1:
            raise ValueError("max_batches must be positive")

        transcript: list[str] = []
        discarded = 0
        actions_executed = 0
        observation = self._observe()
        self._trace("RUN", state="START", run_id=self.run_id, task=task)
        self._append("run_started", {"task": task, "observation": observation.journal_view()})
        self._trace("A", state="PLAN_INITIAL_START")
        active = self.lobe_a.plan_initial(task, observation)
        self._trace("A", state="PLAN_INITIAL_DONE", batch=active.batch_id if active else "none")
        if active is None:
            self._append("run_finished", {"status": "no_plan"})
            return RuntimeReport(
                run_id=self.run_id,
                status="no_plan",
                batches_executed=0,
                batches_discarded=0,
                actions_executed=0,
                transcript=tuple(transcript),
                final_observation=observation,
            )
        if not active.preconditions.matches(observation):
            raise StaleBatch("initial batch does not match the starting observation")

        terminal_executed = False
        for batch_number in range(max_batches):
            if not active.preconditions.matches(observation):
                discarded += 1
                transcript.append(f"discard {active.batch_id}: actual state no longer matches its preconditions")
                self._append("batch_discarded", {"batch_id": active.batch_id, "reason": "stale_before_execution"})
                active = self.lobe_a.plan_initial(task, observation)
                if active is None:
                    break
            transcript.append(f"execute {active.batch_id}: {len(active.actions)} action(s)")
            self._trace("LOOP", state="ACTIVE", batch=active.batch_id, actions=len(active.actions))

            def predict_next() -> BatchSpec | None:
                self._trace("A", state="PREDICT_START", source=active.batch_id)
                try:
                    candidate = self.lobe_a.predict_next(task, active, observation)
                except Exception as exc:
                    self._trace("A", state="PREDICT_ERROR", source=active.batch_id, error=type(exc).__name__)
                    raise
                self._trace("A", state="PREDICT_DONE", source=active.batch_id, batch=candidate.batch_id if candidate else "none")
                return candidate

            def prepare_next() -> LobeDecision:
                self._trace("B", state="PREPARE_START", source=active.batch_id, predicted_end=active.predicted_end.summary)
                try:
                    decision = self.lobe_b.prepare_next(task, active, observation)
                except Exception as exc:
                    self._trace("B", state="PREPARE_ERROR", source=active.batch_id, error=type(exc).__name__)
                    raise
                self._trace(
                    "B",
                    state="APPROVED" if decision.approved else "REJECTED",
                    source=active.batch_id,
                    batch=decision.batch.batch_id if decision.batch else "none",
                )
                return decision

            # All three operations are concurrent: the current batch moves the
            # machine while A and B prepare the following handoff.
            with ThreadPoolExecutor(max_workers=3, thread_name_prefix="compuse-lobe") as pool:
                execution_future = pool.submit(self._execute_batch, active, observation)
                a_future = pool.submit(predict_next)
                b_future = pool.submit(prepare_next)
                execution = execution_future.result()
                try:
                    a_candidate = a_future.result()
                except Exception as exc:  # noqa: BLE001 - an unavailable shadow prediction is recoverable
                    a_candidate = None
                    transcript.append(f"lobe A prediction unavailable: {exc}")
                try:
                    b_decision = b_future.result()
                except Exception as exc:  # noqa: BLE001 - B failure must fail closed
                    b_decision = LobeDecision(approved=False, reason=f"lobe B failed: {exc}")

            actions_executed += len(execution.results)
            observation = execution.actual_observation
            self._trace("BOUNDARY", state="OBSERVED", batch=active.batch_id, revision=observation.revision)
            if not execution.ok or execution.uncertain:
                transcript.append(f"recovery after {active.batch_id}: {execution.error or 'verification failed'}")
                self._append("speculation_invalidated", {
                    "batch_id": active.batch_id,
                    "reason": execution.error or "execution_not_verified",
                    "a_candidate": a_candidate.batch_id if a_candidate else None,
                    "b_candidate": b_decision.batch.batch_id if b_decision.batch else None,
                })
                active = self.lobe_a.plan_initial(task, observation)
                if active is None:
                    break
                discarded += 1
                continue

            if active.terminal:
                terminal_executed = True
                transcript.append(f"terminal batch completed: {active.batch_id}")
                self._trace("RUN", state="TERMINAL", batch=active.batch_id)
                break

            b_candidate = b_decision.batch if b_decision.approved else None
            if not b_decision.approved or not self._valid_next_batch(active, b_candidate):
                discarded += 1
                transcript.append(f"discard speculative handoff after {active.batch_id}: {b_decision.reason}")
                self._append("batch_discarded", {
                    "batch_id": b_candidate.batch_id if b_candidate else None,
                    "source_batch_id": active.batch_id,
                    "reason": b_decision.reason,
                })
                active = self.lobe_a.plan_initial(task, observation)
            else:
                # B's batch is planned from the predicted end of A's current
                # batch, but it can run only if the real observation matches.
                if not b_candidate.preconditions.matches(observation):
                    discarded += 1
                    transcript.append(f"discard {b_candidate.batch_id}: predicted end disagreed with actual observation")
                    self._append("batch_discarded", {
                        "batch_id": b_candidate.batch_id,
                        "source_batch_id": active.batch_id,
                        "reason": "predicted_end_mismatch",
                    })
                    active = self.lobe_a.plan_initial(task, observation)
                else:
                    active = b_candidate
                    self._trace("HANDOFF", state="ACCEPTED", batch=active.batch_id, source=b_candidate.preconditions.source_batch_id)

            if active is None:
                break

        status = "completed" if terminal_executed else ("no_next_plan" if active is None else "batch_limit")
        self._append("run_finished", {
            "status": status,
            "batches_executed": len([line for line in transcript if line.startswith("execute ")]),
            "batches_discarded": discarded,
            "actions_executed": actions_executed,
        })
        self._trace("RUN", state=status.upper(), batches=len([line for line in transcript if line.startswith("execute ")]), actions=actions_executed)
        return RuntimeReport(
            run_id=self.run_id,
            status=status,
            batches_executed=len([line for line in transcript if line.startswith("execute ")]),
            batches_discarded=discarded,
            actions_executed=actions_executed,
            transcript=tuple(transcript),
            final_observation=observation,
        )


__all__ = ["DesktopAdapter", "DualLobeRuntime", "LobeA", "LobeB", "StaleBatch"]
