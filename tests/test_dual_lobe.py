from __future__ import annotations

import threading
import time
from datetime import datetime, timezone

from compuse.agent.contracts import (
    BatchPreconditions,
    BatchSpec,
    LobeDecision,
    PredictedState,
    RuntimeObservation,
)
from compuse.agent.runtime import DualLobeRuntime
from compuse.protocol import Wait


def observation(revision: int, markers: tuple[str, ...]) -> RuntimeObservation:
    return RuntimeObservation(
        run_id="adapter-run",
        revision=revision,
        captured_at=datetime(2026, 9, 13, tzinfo=timezone.utc),
        coordinate_space_id="screen:100x100",
        foreground_window="Demo Window",
        visible_markers=markers,
        screen_sha256=("0" if revision % 2 else "1") * 64,
    )


def batch(
    batch_id: str,
    source_batch_id: str | None,
    start_marker: str,
    end_marker: str,
    source_lobe: str,
    terminal: bool = False,
) -> BatchSpec:
    return BatchSpec(
        batch_id=batch_id,
        actions=(Wait(seconds=0.001),),
        preconditions=BatchPreconditions(
            coordinate_space_id="screen:100x100",
            foreground_window="Demo Window",
            required_markers=(start_marker,),
            source_batch_id=source_batch_id,
        ),
        predicted_end=PredictedState(
            summary=f"at {end_marker}",
            coordinate_space_id="screen:100x100",
            foreground_window="Demo Window",
            required_markers=(end_marker,),
        ),
        confidence=0.95,
        source_lobe=source_lobe,
        terminal=terminal,
    )


class FakeAdapter:
    def __init__(self) -> None:
        self.revision = 0
        self.markers = ("home",)
        self.action_started = threading.Event()

    def observe(self) -> RuntimeObservation:
        self.revision += 1
        return observation(self.revision, self.markers)

    def execute_action(self, action) -> dict:
        self.action_started.set()
        time.sleep(0.03)
        self.markers = ("next",) if self.markers == ("home",) else ("done",)
        return {"performed": True, "detail": "fake action"}


class FakeA:
    def __init__(self, adapter: FakeAdapter) -> None:
        self.adapter = adapter
        self.prediction_started_during_execution = False

    def plan_initial(self, task, observation):
        return batch("a0", None, "home", "next", "A")

    def predict_next(self, task, active_batch, observation):
        self.prediction_started_during_execution = self.adapter.action_started.is_set()
        return batch("a-next", active_batch.batch_id, "next", "done", "A", terminal=True)


class FakeB:
    def prepare_next(self, task, active_batch, observation):
        return LobeDecision(
            approved=True,
            reason="predicted end has a matching anchor",
            batch=batch("b-next", active_batch.batch_id, "next", "done", "B", terminal=True),
        )


def test_dual_lobe_overlaps_prediction_with_execution(tmp_path):
    adapter = FakeAdapter()
    lobe_a = FakeA(adapter)
    runtime = DualLobeRuntime(
        adapter=adapter,
        lobe_a=lobe_a,
        lobe_b=FakeB(),
        run_id="overlap-run",
        journal_path=str(tmp_path / "events.db"),
    )

    report = runtime.run("complete the demo", max_batches=4)

    assert report.status == "completed"
    assert report.batches_executed == 2
    assert report.actions_executed == 2
    assert lobe_a.prediction_started_during_execution is True
    assert report.final_observation.visible_markers == ("done",)
    assert runtime.store.verify("overlap-run") is True


def test_mismatched_predicted_end_is_discarded(tmp_path):
    adapter = FakeAdapter()

    class RejectingB:
        def prepare_next(self, task, active_batch, observation):
            return LobeDecision(
                approved=True,
                reason="bad source contract",
                batch=batch("wrong", "not-the-active-batch", "next", "done", "B", terminal=True),
            )

    class RecoveryA(FakeA):
        def __init__(self, adapter):
            super().__init__(adapter)
            self.initial_calls = 0

        def plan_initial(self, task, observation):
            self.initial_calls += 1
            if self.initial_calls == 1:
                return batch("a0", None, "home", "next", "A")
            return None

    lobe_a = RecoveryA(adapter)
    runtime = DualLobeRuntime(
        adapter=adapter,
        lobe_a=lobe_a,
        lobe_b=RejectingB(),
        run_id="reject-run",
        journal_path=str(tmp_path / "events.db"),
    )

    report = runtime.run("complete the demo", max_batches=2)

    assert report.status == "no_next_plan"
    assert report.batches_executed == 1
    assert report.batches_discarded == 1
    assert lobe_a.initial_calls == 2
