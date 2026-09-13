"""Deterministic shell proof for the concurrent dual-lobe runtime."""
from __future__ import annotations

import argparse
import threading
import time
from datetime import datetime, timezone
from typing import Callable

from compuse.agent.contracts import (
    BatchPreconditions,
    BatchSpec,
    LobeDecision,
    PredictedState,
    RuntimeObservation,
)
from compuse.agent.runtime import DualLobeRuntime
from compuse.protocol import Wait


def _observation(revision: int, marker: str) -> RuntimeObservation:
    return RuntimeObservation(
        run_id="demo-adapter-run",
        revision=revision,
        captured_at=datetime.now(timezone.utc),
        coordinate_space_id="demo-screen:100x100",
        foreground_window="Compuse Dual-Lobe Demo",
        visible_markers=(marker,),
        screen_sha256=("0" if revision % 2 else "1") * 64,
    )


def _batch(
    batch_id: str,
    source_batch_id: str | None,
    start_marker: str,
    end_marker: str,
    source_lobe: str,
    action_count: int,
    terminal: bool = False,
) -> BatchSpec:
    return BatchSpec(
        batch_id=batch_id,
        actions=tuple(Wait(seconds=0.06) for _ in range(action_count)),
        preconditions=BatchPreconditions(
            coordinate_space_id="demo-screen:100x100",
            foreground_window="Compuse Dual-Lobe Demo",
            required_markers=(start_marker,),
            source_batch_id=source_batch_id,
        ),
        predicted_end=PredictedState(
            summary=f"demo marker becomes {end_marker}",
            coordinate_space_id="demo-screen:100x100",
            foreground_window="Compuse Dual-Lobe Demo",
            required_markers=(end_marker,),
        ),
        confidence=1.0,
        source_lobe=source_lobe,
        terminal=terminal,
    )


class DemoAdapter:
    def __init__(self) -> None:
        self.marker = "home"
        self.revision = 0
        self.actions_in_state = 0
        self.execution_started = threading.Event()

    def observe(self) -> RuntimeObservation:
        self.revision += 1
        return _observation(self.revision, self.marker)

    def execute_action(self, action) -> dict[str, object]:
        self.execution_started.set()
        time.sleep(0.06)
        self.actions_in_state += 1
        if self.marker == "home" and self.actions_in_state == 3:
            self.marker = "mid"
            self.actions_in_state = 0
        elif self.marker == "mid" and self.actions_in_state == 2:
            self.marker = "done"
            self.actions_in_state = 0
        return {"performed": True, "detail": "shell demo action completed"}


class DemoLobeA:
    def __init__(self, adapter: DemoAdapter) -> None:
        self.adapter = adapter
        self.prediction_started_during_execution = False

    def plan_initial(self, task: str, observation: RuntimeObservation) -> BatchSpec | None:
        if "home" in observation.visible_markers:
            return _batch("a0", None, "home", "mid", "A", 3)
        if "mid" in observation.visible_markers:
            return _batch("a-replan", None, "mid", "done", "A", 2, terminal=True)
        return None

    def predict_next(self, task: str, active_batch: BatchSpec, observation: RuntimeObservation) -> BatchSpec | None:
        self.prediction_started_during_execution = self.adapter.execution_started.is_set()
        time.sleep(0.10)
        if active_batch.batch_id == "a0":
            return _batch("a-predicted", active_batch.batch_id, "mid", "done", "A", 2, terminal=True)
        return None


class DemoLobeB:
    def __init__(self, adapter: DemoAdapter) -> None:
        self.adapter = adapter
        self.prepare_started_during_execution = False
        self.saw_predicted_end = False

    def prepare_next(self, task: str, active_batch: BatchSpec, observation: RuntimeObservation) -> LobeDecision:
        self.prepare_started_during_execution = self.adapter.execution_started.is_set()
        self.saw_predicted_end = bool(active_batch.predicted_end.required_markers)
        time.sleep(0.10)
        if active_batch.batch_id == "a0":
            return LobeDecision(
                approved=True,
                reason="B confirmed A's predicted end anchor",
                batch=_batch("b0", active_batch.batch_id, "mid", "done", "B", 2, terminal=True),
            )
        return LobeDecision(approved=False, reason="terminal batch; no next handoff")


def run_demo(trace: Callable[[str], None] | None = None):
    adapter = DemoAdapter()
    lobe_a = DemoLobeA(adapter)
    lobe_b = DemoLobeB(adapter)
    runtime = DualLobeRuntime(
        adapter=adapter,
        lobe_a=lobe_a,
        lobe_b=lobe_b,
        run_id="dual-loop-shell-demo",
        max_actions_per_batch=8,
        trace=trace,
    )
    report = runtime.run("complete the deterministic shell demonstration", max_batches=4)
    return report, adapter, lobe_a, lobe_b


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="compuse-dual-loop-demo",
        description="Show A prediction, B preparation, and execution overlapping in the real runtime.",
    )
    parser.parse_args(argv)
    print("DUAL-LOBE SHELL PROOF: starting", flush=True)
    report, adapter, lobe_a, lobe_b = run_demo(trace=lambda line: print(line, flush=True))
    print("--- proof ---", flush=True)
    print(f"status={report.status}", flush=True)
    print(f"final_marker={adapter.marker}", flush=True)
    print(f"A_prediction_started_during_execution={lobe_a.prediction_started_during_execution}", flush=True)
    print(f"B_preparation_started_during_execution={lobe_b.prepare_started_during_execution}", flush=True)
    print(f"B_saw_A_predicted_end={lobe_b.saw_predicted_end}", flush=True)
    print("CONTINUOUS_HANDOFF=PASS" if report.status == "completed" and lobe_a.prediction_started_during_execution and lobe_b.prepare_started_during_execution else "CONTINUOUS_HANDOFF=FAIL", flush=True)
    return 0 if report.status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
