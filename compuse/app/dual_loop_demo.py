"""Deterministic shell proof and three-way architecture comparison."""
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
from compuse.agent.runtime import DualLobeRuntime, ScreenAwareDualLobeRuntime, SingleLoopRuntime
from compuse.protocol import Wait


_SCENARIOS = {
    "simple": (
        ("home", "mid", 3),
        ("mid", "done", 2),
    ),
    "complex": (
        ("home", "catalog", 4),
        ("catalog", "product", 3),
        ("product", "basket", 3),
        ("basket", "done", 2),
    ),
}


def _task_for(scenario: str) -> str:
    if scenario == "complex":
        return "research the catalog, inspect a product, add it to the basket, and finish the workflow"
    return "complete the deterministic shell demonstration"


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
    def __init__(self, scenario: str = "simple") -> None:
        if scenario not in _SCENARIOS:
            raise ValueError(f"unknown demo scenario: {scenario}")
        self.scenario = scenario
        self.steps = _SCENARIOS[scenario]
        self.marker = "home"
        self.revision = 0
        self.actions_in_state = 0
        self.execution_started = threading.Event()
        self.execution_active = threading.Event()

    def step_for(self, marker: str) -> tuple[str, int] | None:
        for start_marker, end_marker, action_count in self.steps:
            if start_marker == marker:
                return end_marker, action_count
        return None

    def observe(self) -> RuntimeObservation:
        self.revision += 1
        return _observation(self.revision, self.marker)

    def execute_action(self, action) -> dict[str, object]:
        self.execution_started.set()
        self.execution_active.set()
        try:
            time.sleep(0.06)
            self.actions_in_state += 1
            step = self.step_for(self.marker)
            if step is not None and self.actions_in_state == step[1]:
                self.marker = step[0]
                self.actions_in_state = 0
        finally:
            self.execution_active.clear()
        return {"performed": True, "detail": "shell demo action completed"}


class DemoLobeA:
    def __init__(self, adapter: DemoAdapter) -> None:
        self.adapter = adapter
        self.prediction_started_during_execution = False

    def plan_initial(self, task: str, observation: RuntimeObservation) -> BatchSpec | None:
        marker = observation.visible_markers[0] if observation.visible_markers else "unknown"
        step = self.adapter.step_for(marker)
        if step is None:
            return None
        end_marker, action_count = step
        batch_id = "a0" if marker == "home" else f"a-replan-{marker}"
        return _batch(batch_id, None, marker, end_marker, "A", action_count, terminal=end_marker == "done")

    def predict_next(self, task: str, active_batch: BatchSpec, observation: RuntimeObservation) -> BatchSpec | None:
        # Thread scheduling may enter this function just before the executor
        # starts its first action.  Wait for the physical action window so the
        # proof records overlap, while the control group still sees it closed.
        self.adapter.execution_started.wait(timeout=0.25)
        self.prediction_started_during_execution = (
            self.prediction_started_during_execution or self.adapter.execution_active.is_set()
        )
        time.sleep(0.10)
        marker = active_batch.predicted_end.required_markers[0]
        step = self.adapter.step_for(marker)
        if step is None:
            return None
        end_marker, action_count = step
        return _batch(
            f"a-predicted-{marker}",
            active_batch.batch_id,
            marker,
            end_marker,
            "A",
            action_count,
            terminal=end_marker == "done",
        )


class DemoLobeB:
    def __init__(self, adapter: DemoAdapter) -> None:
        self.adapter = adapter
        self.prepare_started_during_execution = False
        self.saw_predicted_end = False

    def prepare_next(self, task: str, active_batch: BatchSpec, observation: RuntimeObservation) -> LobeDecision:
        self.prepare_started_during_execution = (
            self.prepare_started_during_execution or self.adapter.execution_active.is_set()
        )
        self.saw_predicted_end = self.saw_predicted_end or bool(active_batch.predicted_end.required_markers)
        time.sleep(0.10)
        marker = active_batch.predicted_end.required_markers[0]
        step = self.adapter.step_for(marker)
        if step is None:
            return LobeDecision(approved=False, reason="terminal batch; no next handoff")
        end_marker, action_count = step
        return LobeDecision(
            approved=True,
            reason="B confirmed A's predicted end anchor",
            batch=_batch(
                f"b-prepared-{marker}",
                active_batch.batch_id,
                marker,
                end_marker,
                "B",
                action_count,
                terminal=end_marker == "done",
            ),
        )


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


def run_control_demo(trace: Callable[[str], None] | None = None, scenario: str = "simple"):
    adapter = DemoAdapter(scenario)
    lobe_a = DemoLobeA(adapter)
    runtime = SingleLoopRuntime(
        adapter=adapter,
        lobe_a=lobe_a,
        run_id=f"control-shell-demo-{scenario}",
        max_actions_per_batch=8,
        trace=trace,
    )
    report = runtime.run(_task_for(scenario), max_batches=len(adapter.steps) + 2)
    runtime.store.close()
    return report, adapter, lobe_a, None


def run_demo(trace: Callable[[str], None] | None = None, scenario: str = "simple"):
    adapter = DemoAdapter(scenario)
    lobe_a = DemoLobeA(adapter)
    lobe_b = DemoLobeB(adapter)
    runtime = DualLobeRuntime(
        adapter=adapter,
        lobe_a=lobe_a,
        lobe_b=lobe_b,
        run_id=f"dual-loop-shell-demo-{scenario}",
        max_actions_per_batch=8,
        trace=trace,
    )
    report = runtime.run(_task_for(scenario), max_batches=len(adapter.steps) + 2)
    runtime.store.close()
    return report, adapter, lobe_a, lobe_b


def run_screen_aware_demo(trace: Callable[[str], None] | None = None, scenario: str = "simple"):
    adapter = DemoAdapter(scenario)
    lobe_a = DemoLobeA(adapter)
    screen_lobe = ScreenDemoLobeB()
    runtime = ScreenAwareDualLobeRuntime(
        adapter=adapter,
        lobe_a=lobe_a,
        screen_lobe=screen_lobe,
        run_id=f"screen-aware-shell-demo-{scenario}",
        max_actions_per_batch=8,
        screen_poll_interval=0.02,
        trace=trace,
    )
    report = runtime.run(_task_for(scenario), max_batches=len(adapter.steps) + 2)
    runtime.store.close()
    return report, adapter, lobe_a, screen_lobe


def _print_proof(label: str, report, adapter: DemoAdapter, lobe_a: DemoLobeA, lobe_b) -> bool:
    print(f"--- {label} proof ---", flush=True)
    print(f"status={report.status}", flush=True)
    print(f"final_marker={adapter.marker}", flush=True)
    print(f"batches_executed={report.batches_executed}", flush=True)
    print(f"actions_executed={report.actions_executed}", flush=True)
    print(f"A_prediction_started_during_execution={lobe_a.prediction_started_during_execution}", flush=True)
    if lobe_b is None:
        print("control_has_no_prediction_during_execution=True", flush=True)
        passed = report.status == "completed" and not lobe_a.prediction_started_during_execution
        print("CONTROL_BASELINE=PASS" if passed else "CONTROL_BASELINE=FAIL", flush=True)
        return passed
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
        choices=("control", "predictive", "screen-aware", "compare"),
        default="compare",
        help="run one architecture or all three (default: compare)",
    )
    parser.add_argument(
        "--scenario",
        choices=tuple(_SCENARIOS),
        default="complex",
        help="deterministic task length (default: complex)",
    )
    args = parser.parse_args(argv)
    runners = {
        "control": ("control", lambda trace: run_control_demo(trace=trace, scenario=args.scenario)),
        "predictive": ("predictive", lambda trace: run_demo(trace=trace, scenario=args.scenario)),
        "screen-aware": ("screen-aware", lambda trace: run_screen_aware_demo(trace=trace, scenario=args.scenario)),
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
