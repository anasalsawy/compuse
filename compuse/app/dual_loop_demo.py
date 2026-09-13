"""Deterministic shell proof and comparison for both dual-lobe runtimes."""
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
    ScreenAssessment,
)
from compuse.agent.runtime import DualLobeRuntime, ScreenAwareDualLobeRuntime
from compuse.protocol import Wait


def _observation(revision: int, marker: str) -> RuntimeObservation:
    return RuntimeObservation(
        run_id="demo-adapter-run",
        revision=revision,
        captured_at=datetime.now(timezone.utc),
        coordinate_space_id="demo-screen:100x100",
        foreground_window="Compuse Dual-Lobe Demo",
        visible_markers=(marker,),
        screen_sha256=("0" if marker == "home" else "1") * 64,
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


class ScreenDemoLobeB:
    """Deterministic screen watchdog used to prove the second architecture."""

    def __init__(self) -> None:
        self.screen_updates = 0
        self.screen_assessments = 0
        self.handoff_checks = 0
        self.saw_expected_transition = False

    def inspect_screen(
        self,
        task: str,
        active_batch: BatchSpec,
        observation: RuntimeObservation,
    ) -> ScreenAssessment:
        self.screen_updates += 1
        marker = observation.visible_markers[0] if observation.visible_markers else "unknown"
        expected = set(active_batch.preconditions.required_markers) | set(active_batch.predicted_end.required_markers)
        stable = marker in expected
        if marker in active_batch.predicted_end.required_markers:
            self.saw_expected_transition = True
        self.screen_assessments += 1
        return ScreenAssessment(
            observation_revision=observation.revision,
            status="stable" if stable else "unsafe",
            reason=(
                f"demo screen marker {marker!r} is an expected active/terminal anchor"
                if stable
                else f"unexpected demo screen marker {marker!r}"
            ),
        )

    def approve_next(
        self,
        task: str,
        active_batch: BatchSpec,
        candidate: BatchSpec,
        observation: RuntimeObservation,
        assessment: ScreenAssessment,
    ) -> LobeDecision:
        self.handoff_checks += 1
        if assessment.status == "stable" and candidate.preconditions.matches(observation):
            return LobeDecision(
                approved=True,
                reason="screen state is stable and A's candidate matches the fresh observation",
                batch=candidate,
            )
        return LobeDecision(
            approved=False,
            reason="screen-aware gate rejected an unstable or stale candidate",
        )


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
    runtime.store.close()
    return report, adapter, lobe_a, lobe_b


def run_screen_aware_demo(trace: Callable[[str], None] | None = None):
    adapter = DemoAdapter()
    lobe_a = DemoLobeA(adapter)
    screen_lobe = ScreenDemoLobeB()
    runtime = ScreenAwareDualLobeRuntime(
        adapter=adapter,
        lobe_a=lobe_a,
        screen_lobe=screen_lobe,
        run_id="screen-aware-shell-demo",
        max_actions_per_batch=8,
        screen_poll_interval=0.02,
        trace=trace,
    )
    report = runtime.run("complete the deterministic shell demonstration", max_batches=4)
    runtime.store.close()
    return report, adapter, lobe_a, screen_lobe


def _print_proof(label: str, report, adapter: DemoAdapter, lobe_a: DemoLobeA, lobe_b) -> bool:
    print(f"--- {label} proof ---", flush=True)
    print(f"status={report.status}", flush=True)
    print(f"final_marker={adapter.marker}", flush=True)
    print(f"batches_executed={report.batches_executed}", flush=True)
    print(f"actions_executed={report.actions_executed}", flush=True)
    print(f"A_prediction_started_during_execution={lobe_a.prediction_started_during_execution}", flush=True)
    if isinstance(lobe_b, DemoLobeB):
        print(f"B_preparation_started_during_execution={lobe_b.prepare_started_during_execution}", flush=True)
        print(f"B_saw_A_predicted_end={lobe_b.saw_predicted_end}", flush=True)
        passed = (
            report.status == "completed"
            and lobe_a.prediction_started_during_execution
            and lobe_b.prepare_started_during_execution
            and lobe_b.saw_predicted_end
        )
    else:
        print(f"B_screen_updates={lobe_b.screen_updates}", flush=True)
        print(f"B_screen_assessments={lobe_b.screen_assessments}", flush=True)
        print(f"B_handoff_checks={lobe_b.handoff_checks}", flush=True)
        print(f"B_saw_expected_transition={lobe_b.saw_expected_transition}", flush=True)
        passed = (
            report.status == "completed"
            and lobe_a.prediction_started_during_execution
            and lobe_b.screen_updates > 0
            and lobe_b.screen_assessments > 0
            and lobe_b.handoff_checks > 0
            and lobe_b.saw_expected_transition
        )
    print("CONTINUOUS_HANDOFF=PASS" if passed else "CONTINUOUS_HANDOFF=FAIL", flush=True)
    return passed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="compuse-dual-loop-demo",
        description="Compare predictive handoff and continuous screen-aware dual-lobe execution.",
    )
    parser.add_argument(
        "--architecture",
        choices=("predictive", "screen-aware", "compare"),
        default="compare",
        help="run one architecture or both (default: compare)",
    )
    args = parser.parse_args(argv)
    runners = {
        "predictive": ("predictive", run_demo),
        "screen-aware": ("screen-aware", run_screen_aware_demo),
    }
    selected = list(runners) if args.architecture == "compare" else [args.architecture]
    passed_all = True
    timings: dict[str, float] = {}
    for name in selected:
        label, runner = runners[name]
        print(f"DUAL-LOBE SHELL PROOF: {label} starting", flush=True)
        started = time.perf_counter()
        report, adapter, lobe_a, lobe_b = runner(trace=lambda line: print(line, flush=True))
        timings[name] = (time.perf_counter() - started) * 1000.0
        passed_all = _print_proof(label, report, adapter, lobe_a, lobe_b) and passed_all

    if args.architecture == "compare":
        print("--- comparison ---", flush=True)
        for name in selected:
            print(f"{name}_elapsed_ms={timings[name]:.1f}", flush=True)
        print("COMPARISON=PASS" if passed_all else "COMPARISON=FAIL", flush=True)
    return 0 if passed_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
