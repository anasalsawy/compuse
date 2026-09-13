"""Model-facing computer-use runtime primitives."""

from .contracts import (
    ActionExecution,
    BatchExecution,
    BatchPreconditions,
    BatchSpec,
    LobeDecision,
    PredictedState,
    RiskClass,
    RuntimeObservation,
    RuntimeReport,
    ScreenAssessment,
)
from .runtime import (
    DualLobeRuntime,
    LobeA,
    LobeB,
    DesktopAdapter,
    ScreenAwareDualLobeRuntime,
    ScreenAwareLobeB,
    SingleLoopRuntime,
    StaleBatch,
)

__all__ = [
    "ActionExecution",
    "BatchExecution",
    "BatchPreconditions",
    "BatchSpec",
    "DesktopAdapter",
    "DualLobeRuntime",
    "LobeA",
    "LobeB",
    "LobeDecision",
    "PredictedState",
    "RiskClass",
    "RuntimeObservation",
    "RuntimeReport",
    "ScreenAssessment",
    "ScreenAwareDualLobeRuntime",
    "ScreenAwareLobeB",
    "SingleLoopRuntime",
    "StaleBatch",
]
