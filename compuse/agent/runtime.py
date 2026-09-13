"""Concurrent dual-lobe runtime for fast but guarded desktop operation."""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from queue import Empty, Full, Queue
from threading import Event, Lock, Thread
from typing import Any, Callable, Protocol

from compuse.coordinator import Coordinator
from compuse.protocol import Action, ActionProposal, Origin
from compuse.storage import EventStore

from .contracts import (
    ActionExecution,
    BCoreReview,
    BatchExecution,
    BatchSpec,
    DeceptionGrade,
    LobeBProfile,
    LobeDecision,
    ParallelBranchReport,
    ParallelBranchSpec,
    ParallelRuntimeReport,
    ParallelSplitPlan,
    RuntimeObservation,
    RuntimeReport,
    ScreenAssessment,
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


class ParallelTaskPlanner(Protocol):
    """The task-receiving planner that decides whether a safe split exists."""

    def plan_split(
        self,
        task: str,
        observation_a: RuntimeObservation,
        observation_b: RuntimeObservation,
    ) -> ParallelSplitPlan | None: ...


class ScreenAwareLobeB(Protocol):
    """Independent B interface for the continuous-awareness architecture."""

    def inspect_screen(
        self,
        task: str,
        active_batch: BatchSpec,
        observation: RuntimeObservation,
    ) -> ScreenAssessment: ...

    def approve_next(
        self,
        task: str,
        active_batch: BatchSpec,
        candidate: BatchSpec,
        observation: RuntimeObservation,
        assessment: ScreenAssessment,
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
        lobe_b: LobeB | None = None,
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
        self._observation_lock = Lock()
        self._b_context_lock = Lock()
        self._b_context_notes: tuple[str, ...] = ()
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
        # Capture calls are serialized, while capture still overlaps planning
        # and physical input.  This protects adapters whose revision counter
        # is not internally thread-safe.
        return self._observe_adapter(self.adapter)

    def _observe_adapter(self, adapter: DesktopAdapter) -> RuntimeObservation:
        """Capture an observation from a selected isolated desktop surface."""
        with self._observation_lock:
            observation = adapter.observe()
        # The adapter owns capture; the runtime owns the durable run identity.
        return observation.model_copy(update={"run_id": self.run_id})

    def _append(self, event_type: str, payload: dict[str, Any]) -> None:
        self.store.append(self.run_id, event_type, payload, datetime.now(timezone.utc).isoformat())

    def _planner_task(self, task: str) -> str:
        """Add B's prior internal notes to A/B without changing user text."""
        with self._b_context_lock:
            notes = self._b_context_notes
        if not notes:
            return task
        joined = "\n".join(f"- {note}" for note in notes)
        return f"{task}\n\n[Internal Lobe B context; do not expose verbatim]\n{joined}"

    def _record_core_review(self, source_batch_id: str, review: BCoreReview | None) -> None:
        if review is None:
            return
        payload = review.model_dump(mode="json")
        payload["source_batch_id"] = source_batch_id
        self._append("b_core_review", payload)
        notes = (
            review.context_notes
            + review.missing_prerequisites
            + review.failure_modes
            + review.unasked_questions
            + review.claim_findings
            + review.proof_required
        )
        if notes:
            with self._b_context_lock:
                self._b_context_notes = tuple((self._b_context_notes + notes)[-16:])
        self._trace(
            "B",
            state="CORE_REVIEW",
            source=source_batch_id,
            profile=review.profile.value,
            grade=review.deception_grade.value,
            context_notes=len(review.context_notes),
            proof_required=len(review.proof_required),
        )

    @staticmethod
    def _enforce_core_policy(decision: LobeDecision) -> LobeDecision:
        """Make the manually selected gatekeeper profile deterministic."""
        review = decision.core_review
        if review is None or review.profile != LobeBProfile.GATEKEEPER:
            return decision
        if review.deception_grade == DeceptionGrade.GREEN and not review.proof_required:
            return decision
        reasons: list[str] = []
        if review.deception_grade != DeceptionGrade.GREEN:
            reasons.append(f"deception grade is {review.deception_grade.value}")
        if review.proof_required:
            reasons.append("proof is required before approval")
        return decision.model_copy(
            update={
                "approved": False,
                "batch": None,
                "reason": "gatekeeper rejected: " + "; ".join(reasons),
            }
        )

    def _execute_batch(
        self,
        batch: BatchSpec,
        starting_observation: RuntimeObservation,
        *,
        adapter: DesktopAdapter | None = None,
        coordinator: Coordinator | None = None,
        lane: str = "main",
        abort_event: Event | None = None,
        abort_reason: Callable[[], str] | None = None,
    ) -> BatchExecution:
        if not batch.preconditions.matches(starting_observation):
            raise StaleBatch(f"batch {batch.batch_id} preconditions do not match observation {starting_observation.revision}")

        dispatch_adapter = adapter or self.adapter
        dispatch_coordinator = coordinator or self.coordinator
        self._trace("EXEC", lane=lane, state="START", batch=batch.batch_id, actions=len(batch.actions))

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
            if abort_event is not None and abort_event.is_set():
                failure_index = index
                uncertain = True
                error = abort_reason() if abort_reason is not None else "screen watchdog interrupted execution"
                self._trace("EXEC", lane=lane, state="INTERRUPTED", batch=batch.batch_id, index=f"{index + 1}/{len(batch.actions)}", reason=error)
                break
            action_started = time.perf_counter()
            self._trace("EXEC", lane=lane, state="ACTION_START", batch=batch.batch_id, index=f"{index + 1}/{len(batch.actions)}", kind=action.kind)
            proposal = ActionProposal(
                action_id=f"{batch.batch_id}-a{index}",
                run_id=self.run_id,
                action=action,
                origin=Origin.STRATEGIST_INSTRUCTION,
                observation_revision=starting_observation.revision + index,
                coordinate_space_id=starting_observation.coordinate_space_id,
                policy_revision=dispatch_coordinator.policy_revision,
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
            permit = dispatch_coordinator.issue(proposal, protocol_observation, ttl=self.ttl)
            consumed = False
            try:
                approved = dispatch_coordinator.consume(permit.permit_id, proposal, protocol_observation)
                consumed = True
                try:
                    result = dispatch_adapter.execute_action(approved)
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
                    lane=lane,
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
                if consumed:
                    dispatch_coordinator.release(permit.permit_id)

        actual = self._observe_adapter(dispatch_adapter)
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
        self._trace("EXEC", lane=lane, state="DONE" if ok else "INVALID", batch=batch.batch_id, verified=ok)
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
        if self.lobe_b is None:
            raise RuntimeError("DualLobeRuntime requires lobe_b")

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
                active = self.lobe_a.plan_initial(self._planner_task(task), observation)
                if active is None:
                    break
            transcript.append(f"execute {active.batch_id}: {len(active.actions)} action(s)")
            self._trace("LOOP", state="ACTIVE", batch=active.batch_id, actions=len(active.actions))
            planner_task = self._planner_task(task)

            def predict_next() -> BatchSpec | None:
                self._trace("A", state="PREDICT_START", source=active.batch_id)
                try:
                    candidate = self.lobe_a.predict_next(planner_task, active, observation)
                except Exception as exc:
                    self._trace("A", state="PREDICT_ERROR", source=active.batch_id, error=type(exc).__name__)
                    raise
                self._trace("A", state="PREDICT_DONE", source=active.batch_id, batch=candidate.batch_id if candidate else "none")
                return candidate

            def prepare_next() -> LobeDecision:
                self._trace("B", state="PREPARE_START", source=active.batch_id, predicted_end=active.predicted_end.summary)
                try:
                    decision = self.lobe_b.prepare_next(planner_task, active, observation)
                except Exception as exc:
                    self._trace("B", state="PREPARE_ERROR", source=active.batch_id, error=type(exc).__name__)
                    raise
                decision = self._enforce_core_policy(decision)
                self._record_core_review(active.batch_id, decision.core_review)
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
                active = self.lobe_a.plan_initial(self._planner_task(task), observation)
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
                active = self.lobe_a.plan_initial(self._planner_task(task), observation)
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
                    active = self.lobe_a.plan_initial(self._planner_task(task), observation)
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


class SingleLoopRuntime(DualLobeRuntime):
    """Control group: one planner observes, plans, then executes serially."""

    def run(self, task: str, *, max_batches: int = 32) -> RuntimeReport:
        if not task.strip():
            raise ValueError("task must not be empty")
        if max_batches < 1:
            raise ValueError("max_batches must be positive")

        transcript: list[str] = []
        discarded = 0
        actions_executed = 0
        observation = self._observe()
        self._trace("RUN", state="START", run_id=self.run_id, architecture="control", task=task)
        self._append("run_started", {"task": task, "architecture": "control", "observation": observation.journal_view()})
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
                transcript=(),
                final_observation=observation,
            )
        if not active.preconditions.matches(observation):
            raise StaleBatch("initial batch does not match the starting observation")

        terminal_executed = False
        for _batch_number in range(max_batches):
            if not active.preconditions.matches(observation):
                discarded += 1
                transcript.append(f"discard {active.batch_id}: actual state no longer matches its preconditions")
                self._append("batch_discarded", {"batch_id": active.batch_id, "reason": "stale_before_execution"})
                active = self.lobe_a.plan_initial(task, observation)
                if active is None:
                    break
                continue

            transcript.append(f"execute {active.batch_id}: {len(active.actions)} action(s)")
            self._trace("LOOP", state="ACTIVE", batch=active.batch_id, actions=len(active.actions))
            execution = self._execute_batch(active, observation)
            actions_executed += len(execution.results)
            observation = execution.actual_observation
            self._trace("BOUNDARY", state="OBSERVED", batch=active.batch_id, revision=observation.revision)

            if not execution.ok or execution.uncertain:
                transcript.append(f"recovery after {active.batch_id}: {execution.error or 'verification failed'}")
                self._append("speculation_invalidated", {"batch_id": active.batch_id, "reason": execution.error or "execution_not_verified"})
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

            # This is the intentional control-group gap: A cannot prepare the
            # next batch until the current batch has finished and been observed.
            self._trace("A", state="PLAN_NEXT_START", source=active.batch_id)
            try:
                candidate = self.lobe_a.predict_next(task, active, observation)
            except Exception as exc:  # noqa: BLE001 - recover from planner failure
                candidate = None
                transcript.append(f"lobe A prediction unavailable: {exc}")
            self._trace("A", state="PLAN_NEXT_DONE", source=active.batch_id, batch=candidate.batch_id if candidate else "none")

            if candidate is None or not self._valid_next_batch(active, candidate) or not candidate.preconditions.matches(observation):
                discarded += 1
                transcript.append(f"discard control next batch after {active.batch_id}: candidate failed contract")
                self._append("batch_discarded", {
                    "batch_id": candidate.batch_id if candidate else None,
                    "source_batch_id": active.batch_id,
                    "reason": "candidate_contract_failed",
                })
                active = self.lobe_a.plan_initial(task, observation)
            else:
                active = candidate
                self._trace("HANDOFF", state="ACCEPTED", batch=active.batch_id, source=active.preconditions.source_batch_id)

            if active is None:
                break

        status = "completed" if terminal_executed else ("no_next_plan" if active is None else "batch_limit")
        batches_executed = len([line for line in transcript if line.startswith("execute ")])
        self._append("run_finished", {
            "status": status,
            "batches_executed": batches_executed,
            "batches_discarded": discarded,
            "actions_executed": actions_executed,
        })
        self._trace("RUN", state=status.upper(), batches=batches_executed, actions=actions_executed)
        return RuntimeReport(
            run_id=self.run_id,
            status=status,
            batches_executed=batches_executed,
            batches_discarded=discarded,
            actions_executed=actions_executed,
            transcript=tuple(transcript),
            final_observation=observation,
        )


class ParallelDualLobeRuntime(DualLobeRuntime):
    """Prototype for safe task splitting across two independent desktop lanes.

    The split planner is a short front-door decision made when the task
    arrives.  If it finds two independent lanes, Loop A and Loop B execute
    their bounded plans concurrently.  A merge batch is eligible only after
    both final observations match their predicted end anchors.

    This architecture requires isolated adapters (for example two windows,
    workspaces, browser profiles, or machines).  It deliberately refuses a
    plan whose lanes share a coordinate space or an exclusive resource.  Two
    workers cannot safely control one ordinary desktop at the same time.
    """

    def __init__(
        self,
        *,
        adapter_a: DesktopAdapter,
        adapter_b: DesktopAdapter,
        split_planner: ParallelTaskPlanner,
        merge_adapter: DesktopAdapter | None = None,
        parallel_execution: bool = True,
        **kwargs: Any,
    ) -> None:
        if adapter_a is adapter_b:
            raise ValueError("parallel lanes require two distinct desktop adapters")
        self.adapter_a = adapter_a
        self.adapter_b = adapter_b
        self.merge_adapter = merge_adapter or adapter_a
        self.split_planner = split_planner
        self.parallel_execution = parallel_execution
        # The inherited coordinator is used for the shared merge surface. Each
        # independent lane receives its own coordinator below, otherwise the
        # single-desktop mutation lock would intentionally serialize both lanes.
        super().__init__(
            adapter=self.merge_adapter,
            lobe_a=split_planner,  # the base planner slot is unused by this loop
            lobe_b=None,
            **kwargs,
        )

    @staticmethod
    def _predicted_end_matches(
        predicted: Any,
        observation: RuntimeObservation,
    ) -> bool:
        if observation.coordinate_space_id != predicted.coordinate_space_id:
            return False
        if predicted.foreground_window is not None and observation.foreground_window != predicted.foreground_window:
            return False
        if predicted.browser_url is not None and observation.browser_url != predicted.browser_url:
            return False
        return set(predicted.required_markers).issubset(set(observation.visible_markers))

    def _run_parallel_branch(
        self,
        branch: ParallelBranchSpec,
        adapter: DesktopAdapter,
        coordinator: Coordinator,
        starting_observation: RuntimeObservation,
        *,
        started_lanes: set[str],
        completed_lanes: set[str],
        overlap_event: Event,
        lane_state_lock: Lock,
        transcript: list[str],
        transcript_lock: Lock,
    ) -> ParallelBranchReport:
        started_at = time.perf_counter()
        observation = starting_observation
        actions_executed = 0
        batches_executed = 0
        uncertain = False
        error: str | None = None
        status = "completed"

        with lane_state_lock:
            started_lanes.add(branch.branch_id)
            if len(started_lanes) == 2 and not completed_lanes:
                overlap_event.set()
        self._trace(
            "LOOP",
            state="BRANCH_START",
            lane=branch.branch_id,
            owner=branch.owner_lobe,
            task=branch.task,
        )
        self._append(
            "parallel_branch_started",
            {
                "split_id": self.run_id,
                "branch_id": branch.branch_id,
                "owner_lobe": branch.owner_lobe,
                "observation": starting_observation.journal_view(),
            },
        )

        try:
            for batch in branch.batches:
                if not batch.preconditions.matches(observation):
                    status = "stale_before_execution"
                    error = f"{batch.batch_id} preconditions do not match branch observation"
                    break
                with transcript_lock:
                    transcript.append(f"execute {branch.branch_id}/{batch.batch_id}: {len(batch.actions)} action(s)")
                execution = self._execute_batch(
                    batch,
                    observation,
                    adapter=adapter,
                    coordinator=coordinator,
                    lane=branch.branch_id,
                )
                batches_executed += 1
                actions_executed += len(execution.results)
                observation = execution.actual_observation
                if not execution.ok or execution.uncertain:
                    status = "execution_failed"
                    uncertain = execution.uncertain
                    error = execution.error or "branch execution was not verified"
                    break

            if status == "completed":
                final_prediction = branch.batches[-1].predicted_end
                if not self._predicted_end_matches(final_prediction, observation):
                    status = "end_anchor_mismatch"
                    error = "branch final observation did not match its predicted end anchor"
        except Exception as exc:  # noqa: BLE001 - one lane must fail closed
            status = "branch_error"
            uncertain = True
            error = str(exc)
        finally:
            with lane_state_lock:
                completed_lanes.add(branch.branch_id)

        elapsed_ms = (time.perf_counter() - started_at) * 1000.0
        with transcript_lock:
            transcript.append(
                f"branch {branch.branch_id} {status}: {actions_executed} action(s) in {elapsed_ms:.1f}ms"
            )
        self._append(
            "parallel_branch_finished",
            {
                "branch_id": branch.branch_id,
                "status": status,
                "batches_executed": batches_executed,
                "actions_executed": actions_executed,
                "uncertain": uncertain,
                "error": error,
                "final_observation": observation.journal_view(),
            },
        )
        self._trace(
            "LOOP",
            state="BRANCH_DONE" if status == "completed" else "BRANCH_INVALID",
            lane=branch.branch_id,
            actions=actions_executed,
            elapsed_ms=f"{elapsed_ms:.1f}",
        )
        return ParallelBranchReport(
            branch_id=branch.branch_id,
            status=status,
            batches_executed=batches_executed,
            actions_executed=actions_executed,
            uncertain=uncertain,
            elapsed_ms=elapsed_ms,
            error=error,
            final_observation=observation,
        )

    def run(self, task: str, *, max_batches: int = 32) -> ParallelRuntimeReport:
        if not task.strip():
            raise ValueError("task must not be empty")
        if max_batches < 1:
            raise ValueError("max_batches must be positive")

        started_at = time.perf_counter()
        transcript: list[str] = []
        transcript_lock = Lock()
        initial_a = self._observe_adapter(self.adapter_a)
        initial_b = self._observe_adapter(self.adapter_b)
        merge_observation = self._observe_adapter(self.merge_adapter)
        self._trace("RUN", state="START", architecture="parallel", run_id=self.run_id, task=task)
        self._append(
            "run_started",
            {
                "task": task,
                "architecture": "parallel",
                "observations": {
                    "A": initial_a.journal_view(),
                    "B": initial_b.journal_view(),
                    "merge": merge_observation.journal_view(),
                },
            },
        )

        self._trace("SPLIT", state="PLAN_START")
        try:
            plan = self.split_planner.plan_split(task, initial_a, initial_b)
        except Exception as exc:  # noqa: BLE001 - split failure is safe refusal
            plan = None
            transcript.append(f"split planner failed: {exc}")
        self._trace("SPLIT", state="PLAN_DONE", split=plan.split_id if plan else "none")

        if plan is None:
            self._append("parallel_split_rejected", {"reason": "no safe split was produced"})
            self._append("run_finished", {"status": "not_parallelizable"})
            return ParallelRuntimeReport(
                run_id=self.run_id,
                status="not_parallelizable",
                batches_executed=0,
                batches_discarded=0,
                actions_executed=0,
                parallel_elapsed_ms=(time.perf_counter() - started_at) * 1000.0,
                serial_estimate_ms=0.0,
                transcript=tuple(transcript),
                final_observation=merge_observation,
            )

        self._record_core_review(plan.split_id, plan.core_review)
        if plan.core_review.profile == LobeBProfile.GATEKEEPER and (
            plan.core_review.deception_grade != DeceptionGrade.GREEN
            or plan.core_review.proof_required
        ):
            reason = "split gatekeeper rejected: proof or non-GREEN review remains"
            transcript.append(reason)
            self._append("parallel_split_rejected", {"split_id": plan.split_id, "reason": reason})
            self._append("run_finished", {"status": "not_parallelizable", "split_id": plan.split_id})
            return ParallelRuntimeReport(
                run_id=self.run_id,
                status="not_parallelizable",
                split_id=plan.split_id,
                batches_executed=0,
                batches_discarded=1,
                actions_executed=0,
                parallel_elapsed_ms=(time.perf_counter() - started_at) * 1000.0,
                serial_estimate_ms=0.0,
                transcript=tuple(transcript),
                final_observation=merge_observation,
            )

        if not plan.branch_a.batches[0].preconditions.matches(initial_a):
            reason = "Loop A branch start does not match its fresh observation"
        elif not plan.branch_b.batches[0].preconditions.matches(initial_b):
            reason = "Loop B branch start does not match its fresh observation"
        elif not plan.merge_batch.preconditions.matches(merge_observation):
            reason = "merge preconditions do not match the shared merge surface"
        else:
            reason = ""
        if reason:
            transcript.append(f"split rejected: {reason}")
            self._append("parallel_split_rejected", {"split_id": plan.split_id, "reason": reason})
            self._append("run_finished", {"status": "not_parallelizable", "split_id": plan.split_id})
            return ParallelRuntimeReport(
                run_id=self.run_id,
                status="not_parallelizable",
                split_id=plan.split_id,
                batches_executed=0,
                batches_discarded=1,
                actions_executed=0,
                parallel_elapsed_ms=(time.perf_counter() - started_at) * 1000.0,
                serial_estimate_ms=0.0,
                transcript=tuple(transcript),
                final_observation=merge_observation,
            )

        started_lanes: set[str] = set()
        completed_lanes: set[str] = set()
        lane_state_lock = Lock()
        overlap_event = Event()
        lane_a_coordinator = Coordinator(store=self.store, policy_revision=self.coordinator.policy_revision)
        lane_b_coordinator = Coordinator(store=self.store, policy_revision=self.coordinator.policy_revision)
        branch_a: ParallelBranchReport
        branch_b: ParallelBranchReport

        self._trace("SPLIT", state="EXECUTE", split=plan.split_id, branches="A+B")
        branch_kwargs = {
            "started_lanes": started_lanes,
            "completed_lanes": completed_lanes,
            "overlap_event": overlap_event,
            "lane_state_lock": lane_state_lock,
            "transcript": transcript,
            "transcript_lock": transcript_lock,
        }
        if self.parallel_execution:
            with ThreadPoolExecutor(max_workers=2, thread_name_prefix="compuse-parallel") as pool:
                future_a = pool.submit(
                    self._run_parallel_branch,
                    plan.branch_a,
                    self.adapter_a,
                    lane_a_coordinator,
                    initial_a,
                    **branch_kwargs,
                )
                future_b = pool.submit(
                    self._run_parallel_branch,
                    plan.branch_b,
                    self.adapter_b,
                    lane_b_coordinator,
                    initial_b,
                    **branch_kwargs,
                )
                branch_a = future_a.result()
                branch_b = future_b.result()
        else:
            branch_a = self._run_parallel_branch(
                plan.branch_a,
                self.adapter_a,
                lane_a_coordinator,
                initial_a,
                **branch_kwargs,
            )
            branch_b = self._run_parallel_branch(
                plan.branch_b,
                self.adapter_b,
                lane_b_coordinator,
                initial_b,
                **branch_kwargs,
            )

        serial_estimate = branch_a.elapsed_ms + branch_b.elapsed_ms
        merge_verified = False
        merge_execution: BatchExecution | None = None
        if branch_a.status == "completed" and branch_b.status == "completed":
            # The join gate runs after both lanes are complete. Only now may a
            # shared adapter be touched, even when it is the lane-A adapter.
            merge_observation = self._observe_adapter(self.merge_adapter)
            join_ok = plan.merge_batch.preconditions.matches(merge_observation)
            join_ok = join_ok and self._predicted_end_matches(
                plan.merge_batch.preconditions, merge_observation
            )
            self._trace("MERGE", state="GATE", split=plan.split_id, ready=join_ok)
            if join_ok:
                with transcript_lock:
                    transcript.append(f"merge {plan.merge_batch.batch_id}: {len(plan.merge_batch.actions)} action(s)")
                merge_execution = self._execute_batch(
                    plan.merge_batch,
                    merge_observation,
                    adapter=self.merge_adapter,
                    coordinator=self.coordinator,
                    lane="MERGE",
                )
                merge_observation = merge_execution.actual_observation
                merge_verified = (
                    merge_execution.ok
                    and not merge_execution.uncertain
                    and self._predicted_end_matches(plan.merge_batch.predicted_end, merge_observation)
                )
                self._trace("MERGE", state="DONE" if merge_verified else "INVALID", verified=merge_verified)
            else:
                transcript.append("merge blocked: shared join surface was not ready")
        else:
            transcript.append("merge blocked: one or both branch endings were not verified")

        merge_elapsed = sum(result.elapsed_ms for result in merge_execution.results) if merge_execution else 0.0
        serial_estimate += merge_elapsed
        actions_executed = branch_a.actions_executed + branch_b.actions_executed + (
            len(merge_execution.results) if merge_execution else 0
        )
        batches_executed = branch_a.batches_executed + branch_b.batches_executed + (
            1 if merge_execution is not None else 0
        )
        status = "completed" if merge_verified else (
            "branches_failed" if branch_a.status != "completed" or branch_b.status != "completed" else "merge_failed"
        )
        parallel_elapsed = (time.perf_counter() - started_at) * 1000.0
        self._append(
            "parallel_join_finished",
            {
                "split_id": plan.split_id,
                "status": status,
                "branch_overlap_observed": overlap_event.is_set(),
                "merge_verified": merge_verified,
                "serial_estimate_ms": serial_estimate,
                "parallel_elapsed_ms": parallel_elapsed,
            },
        )
        self._append(
            "run_finished",
            {
                "status": status,
                "split_id": plan.split_id,
                "batches_executed": batches_executed,
                "batches_discarded": 0 if status == "completed" else 1,
                "actions_executed": actions_executed,
            },
        )
        self._trace(
            "RUN",
            state=status.upper(),
            split=plan.split_id,
            actions=actions_executed,
            parallel_ms=f"{parallel_elapsed:.1f}",
            serial_estimate_ms=f"{serial_estimate:.1f}",
        )
        return ParallelRuntimeReport(
            run_id=self.run_id,
            status=status,
            split_id=plan.split_id,
            batches_executed=batches_executed,
            batches_discarded=0 if status == "completed" else 1,
            actions_executed=actions_executed,
            parallel_elapsed_ms=parallel_elapsed,
            serial_estimate_ms=serial_estimate,
            branch_overlap_observed=overlap_event.is_set(),
            merge_verified=merge_verified,
            branch_a=branch_a,
            branch_b=branch_b,
            transcript=tuple(transcript),
            final_observation=merge_observation,
        )


class _ScreenState:
    def __init__(self) -> None:
        self.lock = Lock()
        self.latest_observation: RuntimeObservation | None = None
        self.latest_assessment: ScreenAssessment | None = None

    def snapshot(self) -> tuple[RuntimeObservation | None, ScreenAssessment | None]:
        with self.lock:
            return self.latest_observation, self.latest_assessment


class ScreenAwareDualLobeRuntime(DualLobeRuntime):
    """Dual-lobe variant with a continuously running B screen watchdog.

    A still prepares the next batch while the current batch executes.  B no
    longer spends its critical path preparing that batch; it continuously
    captures the desktop, assesses the current screen, interrupts unsafe
    execution at the next action boundary, and gates A's handoff.
    """

    def __init__(
        self,
        *,
        screen_lobe: ScreenAwareLobeB,
        screen_poll_interval: float = 0.05,
        **kwargs: Any,
    ) -> None:
        if screen_poll_interval <= 0:
            raise ValueError("screen_poll_interval must be positive")
        # The inherited constructor stores the common adapter/coordinator
        # machinery and expects a B object.  Screen-aware B has a different
        # protocol, but this subclass replaces the inherited run loop, so it
        # is only passed through to satisfy that shared initialization.
        kwargs["lobe_b"] = screen_lobe
        super().__init__(**kwargs)
        self.screen_lobe = screen_lobe
        self.screen_poll_interval = screen_poll_interval

    def _start_screen_watch(
        self,
        *,
        task: str,
        active_ref: list[BatchSpec],
        active_lock: Lock,
        state: _ScreenState,
        stop_event: Event,
        interrupt_event: Event,
        interrupt_reason: list[str],
    ) -> Thread:
        def watch() -> None:
            analysis_queue: Queue[tuple[BatchSpec, RuntimeObservation] | None] = Queue(maxsize=1)
            result_queue: Queue[tuple[int, ScreenAssessment | None, Exception | None]] = Queue(maxsize=1)
            analysis_thread_stop = Event()

            def analyze() -> None:
                while not analysis_thread_stop.is_set():
                    try:
                        item = analysis_queue.get(timeout=0.1)
                    except Empty:
                        continue
                    if item is None:
                        break
                    active_for_analysis, observation_for_analysis = item
                    assessment: ScreenAssessment | None = None
                    error: Exception | None = None
                    try:
                        assessment = self.screen_lobe.inspect_screen(
                            task,
                            active_for_analysis,
                            observation_for_analysis,
                        )
                    except Exception as exc:  # noqa: BLE001 - caller converts B failure to unsafe
                        error = exc
                    result_queue.put((observation_for_analysis.revision, assessment, error))

            analysis_thread = Thread(target=analyze, name="compuse-screen-assessment", daemon=True)
            analysis_thread.start()
            pending = False
            last_key: tuple[str, str] | None = None
            try:
                while not stop_event.is_set():
                    current = self._observe()
                    with state.lock:
                        state.latest_observation = current
                    self._trace("B", state="SCREEN_UPDATE", revision=current.revision)

                    try:
                        result_revision, assessment, error = result_queue.get_nowait()
                    except Empty:
                        pass
                    else:
                        pending = False
                        if error is not None:
                            assessment = ScreenAssessment(
                                observation_revision=result_revision,
                                status="unsafe",
                                reason=f"screen assessment failed: {error}",
                            )
                        if assessment is None:
                            assessment = ScreenAssessment(
                                observation_revision=result_revision,
                                status="unsafe",
                                reason="screen assessment completed without a result",
                            )
                        with state.lock:
                            state.latest_assessment = assessment
                        self._trace(
                            "B",
                            state="SCREEN_ASSESSMENT",
                            status=assessment.status,
                            revision=assessment.observation_revision,
                        )
                        if assessment.status == "unsafe":
                            interrupt_reason[:] = [assessment.reason]
                            interrupt_event.set()

                    with active_lock:
                        active = active_ref[0]
                    current_key = (active.batch_id, current.screen_sha256) if active is not None else None
                    if not pending and active is not None and current_key != last_key:
                        try:
                            analysis_queue.put_nowait((active, current))
                        except Full:
                            pass
                        else:
                            pending = True
                            last_key = current_key
                    stop_event.wait(self.screen_poll_interval)
            finally:
                analysis_thread_stop.set()
                try:
                    analysis_queue.put_nowait(None)
                except Full:
                    pass
                analysis_thread.join(timeout=0.1)

        watcher = Thread(target=watch, name="compuse-screen-watch", daemon=True)
        watcher.start()
        return watcher

    def run(self, task: str, *, max_batches: int = 32) -> RuntimeReport:
        if not task.strip():
            raise ValueError("task must not be empty")
        if max_batches < 1:
            raise ValueError("max_batches must be positive")

        transcript: list[str] = []
        discarded = 0
        actions_executed = 0
        observation = self._observe()
        self._trace("RUN", state="START", run_id=self.run_id, architecture="screen-aware", task=task)
        self._append("run_started", {"task": task, "architecture": "screen-aware", "observation": observation.journal_view()})
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
                transcript=(),
                final_observation=observation,
            )
        if not active.preconditions.matches(observation):
            raise StaleBatch("initial batch does not match the starting observation")

        active_ref = [active]
        active_lock = Lock()
        state = _ScreenState()
        stop_event = Event()
        interrupt_event = Event()
        interrupt_reason = ["screen watchdog interrupted execution"]
        watcher = self._start_screen_watch(
            task=task,
            active_ref=active_ref,
            active_lock=active_lock,
            state=state,
            stop_event=stop_event,
            interrupt_event=interrupt_event,
            interrupt_reason=interrupt_reason,
        )
        terminal_executed = False
        try:
            for _batch_number in range(max_batches):
                with active_lock:
                    active_ref[0] = active
                if not active.preconditions.matches(observation):
                    discarded += 1
                    transcript.append(f"discard {active.batch_id}: actual state no longer matches its preconditions")
                    self._append("batch_discarded", {"batch_id": active.batch_id, "reason": "stale_before_execution"})
                    active = self.lobe_a.plan_initial(self._planner_task(task), observation)
                    if active is None:
                        break
                    continue

                transcript.append(f"execute {active.batch_id}: {len(active.actions)} action(s)")
                self._trace("LOOP", state="ACTIVE", batch=active.batch_id, actions=len(active.actions))
                planner_task = self._planner_task(task)

                def predict_next() -> BatchSpec | None:
                    self._trace("A", state="PREDICT_START", source=active.batch_id)
                    candidate = self.lobe_a.predict_next(planner_task, active, observation)
                    self._trace("A", state="PREDICT_DONE", source=active.batch_id, batch=candidate.batch_id if candidate else "none")
                    return candidate

                with ThreadPoolExecutor(max_workers=2, thread_name_prefix="compuse-action") as pool:
                    execution_future = pool.submit(
                        self._execute_batch,
                        active,
                        observation,
                        abort_event=interrupt_event,
                        abort_reason=lambda: interrupt_reason[0],
                    )
                    a_future = pool.submit(predict_next)
                    execution = execution_future.result()
                    try:
                        a_candidate = a_future.result()
                    except Exception as exc:  # noqa: BLE001 - prediction can be retried from reality
                        a_candidate = None
                        transcript.append(f"lobe A prediction unavailable: {exc}")

                actions_executed += len(execution.results)
                observation = execution.actual_observation
                self._trace("BOUNDARY", state="OBSERVED", batch=active.batch_id, revision=observation.revision)

                if interrupt_event.is_set():
                    reason = interrupt_reason[0]
                    transcript.append(f"screen watchdog interrupted {active.batch_id}: {reason}")
                    self._append("screen_interrupted", {"batch_id": active.batch_id, "reason": reason})
                    self._trace("RUN", state="SCREEN_INTERRUPTED", reason=reason)
                    break
                if not execution.ok or execution.uncertain:
                    transcript.append(f"recovery after {active.batch_id}: {execution.error or 'verification failed'}")
                    self._append("speculation_invalidated", {"batch_id": active.batch_id, "reason": execution.error or "execution_not_verified"})
                    active = self.lobe_a.plan_initial(self._planner_task(task), observation)
                    if active is None:
                        break
                    discarded += 1
                    continue
                if active.terminal:
                    terminal_executed = True
                    transcript.append(f"terminal batch completed: {active.batch_id}")
                    self._trace("RUN", state="TERMINAL", batch=active.batch_id)
                    break

                if a_candidate is None or not self._valid_next_batch(active, a_candidate):
                    discarded += 1
                    transcript.append(f"discard speculative handoff after {active.batch_id}: A candidate failed contract")
                    self._append("batch_discarded", {"batch_id": a_candidate.batch_id if a_candidate else None, "source_batch_id": active.batch_id, "reason": "candidate_contract_failed"})
                    active = self.lobe_a.plan_initial(self._planner_task(task), observation)
                    if active is None:
                        break
                    continue

                _, latest_assessment = state.snapshot()
                assessment = latest_assessment
                if assessment is None or assessment.observation_revision < observation.revision:
                    assessment = self.screen_lobe.inspect_screen(planner_task, active, observation)
                    with state.lock:
                        state.latest_assessment = assessment
                    self._trace(
                        "B",
                        state="SCREEN_ASSESSMENT",
                        status=assessment.status,
                        revision=assessment.observation_revision,
                    )
                self._trace("B", state="HANDOFF_CHECK", status=assessment.status, revision=assessment.observation_revision)
                decision = self.screen_lobe.approve_next(planner_task, active, a_candidate, observation, assessment)
                decision = self._enforce_core_policy(decision)
                self._record_core_review(active.batch_id, decision.core_review)
                if (
                    decision.approved
                    and decision.batch is not None
                    and assessment.status == "stable"
                    and decision.batch == a_candidate
                    and a_candidate.preconditions.matches(observation)
                ):
                    active = a_candidate
                    self._trace("HANDOFF", state="ACCEPTED", batch=active.batch_id, source=active.preconditions.source_batch_id)
                else:
                    discarded += 1
                    transcript.append(f"discard screen-aware handoff after {active.batch_id}: {decision.reason}")
                    self._append("batch_discarded", {"batch_id": a_candidate.batch_id, "source_batch_id": active.batch_id, "reason": decision.reason})
                    active = self.lobe_a.plan_initial(self._planner_task(task), observation)
                    if active is None:
                        break
        finally:
            stop_event.set()
            watcher.join(timeout=max(1.0, self.screen_poll_interval * 4))

        status = "completed" if terminal_executed else ("screen_interrupted" if interrupt_event.is_set() else ("no_next_plan" if active is None else "batch_limit"))
        batches_executed = len([line for line in transcript if line.startswith("execute ")])
        self._append("run_finished", {"status": status, "batches_executed": batches_executed, "batches_discarded": discarded, "actions_executed": actions_executed})
        self._trace("RUN", state=status.upper(), batches=batches_executed, actions=actions_executed)
        return RuntimeReport(
            run_id=self.run_id,
            status=status,
            batches_executed=batches_executed,
            batches_discarded=discarded,
            actions_executed=actions_executed,
            transcript=tuple(transcript),
            final_observation=observation,
        )


__all__ = [
    "DesktopAdapter",
    "DualLobeRuntime",
    "LobeA",
    "LobeB",
    "ParallelDualLobeRuntime",
    "ParallelTaskPlanner",
    "ScreenAwareDualLobeRuntime",
    "ScreenAwareLobeB",
    "SingleLoopRuntime",
    "StaleBatch",
]
