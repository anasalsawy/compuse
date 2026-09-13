"""Strict contracts for speculative desktop-action batches.

The important distinction is between a *prediction* and an *observation*.
Predictions may be wrong.  A predicted batch is therefore executable only
when its checkable preconditions match a fresh observation at the boundary.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from compuse.protocol import Action, Observation


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class RiskClass(StrEnum):
    SAFE = "safe"
    CONDITIONAL = "conditional"
    BARRIER = "barrier"


class RuntimeObservation(ContractModel):
    """A model-facing observation; screenshot bytes stay outside the journal."""

    run_id: str = Field(min_length=1, max_length=128)
    revision: int = Field(ge=0)
    captured_at: datetime
    coordinate_space_id: str = Field(min_length=1, max_length=256)
    foreground_window: str | None = Field(default=None, max_length=512)
    browser_url: str | None = Field(default=None, max_length=4096)
    visible_markers: tuple[str, ...] = Field(default=(), max_length=64)
    screen_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    window_id: str | None = Field(default=None, max_length=256)
    process_id: int | None = Field(default=None, ge=0)
    session_id: int | None = Field(default=None, ge=0)
    input_desktop: str | None = Field(default=None, max_length=256)
    screenshot_data_url: str | None = Field(default=None, max_length=30_000_000, repr=False)

    @field_validator("captured_at")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("captured_at must be timezone-aware")
        return value.astimezone(timezone.utc)

    def protocol_observation(self) -> Observation:
        return Observation(
            run_id=self.run_id,
            revision=self.revision,
            captured_at=self.captured_at,
            coordinate_space_id=self.coordinate_space_id,
            foreground_window=self.foreground_window,
            process_id=self.process_id,
            session_id=self.session_id,
            input_desktop=self.input_desktop,
        )

    def journal_view(self) -> dict[str, Any]:
        """Return metadata safe to put in the durable journal.

        The screenshot data URL is intentionally excluded because it can
        contain sensitive screen contents and is not needed for audit links.
        """
        return {
            "run_id": self.run_id,
            "revision": self.revision,
            "captured_at": self.captured_at.isoformat(),
            "coordinate_space_id": self.coordinate_space_id,
            "foreground_window": self.foreground_window,
            "browser_url": self.browser_url,
            "visible_markers": list(self.visible_markers),
            "screen_sha256": self.screen_sha256,
            "window_id": self.window_id,
            "process_id": self.process_id,
            "session_id": self.session_id,
            "input_desktop": self.input_desktop,
        }


class PredictedState(ContractModel):
    """The state the planner believes will exist after a batch."""

    summary: str = Field(min_length=1, max_length=2000)
    coordinate_space_id: str = Field(min_length=1, max_length=256)
    foreground_window: str | None = Field(default=None, max_length=512)
    browser_url: str | None = Field(default=None, max_length=4096)
    required_markers: tuple[str, ...] = Field(default=(), max_length=64)
    strict: bool = True


class BatchPreconditions(ContractModel):
    """Checkable facts required before a speculative batch may run."""

    coordinate_space_id: str = Field(min_length=1, max_length=256)
    foreground_window: str | None = Field(default=None, max_length=512)
    browser_url: str | None = Field(default=None, max_length=4096)
    required_markers: tuple[str, ...] = Field(default=(), max_length=64)
    source_batch_id: str | None = Field(default=None, max_length=128)
    require_anchor: bool = True

    def matches(self, observation: RuntimeObservation) -> bool:
        if observation.coordinate_space_id != self.coordinate_space_id:
            return False
        if self.foreground_window is not None and observation.foreground_window != self.foreground_window:
            return False
        if self.browser_url is not None and observation.browser_url != self.browser_url:
            return False
        if not set(self.required_markers).issubset(set(observation.visible_markers)):
            return False
        if self.require_anchor and not (
            self.foreground_window or self.browser_url or self.required_markers
        ):
            return False
        return True


class BatchSpec(ContractModel):
    """A bounded, typed, speculative sequence of actions."""

    batch_id: str = Field(min_length=1, max_length=128)
    actions: tuple[Action, ...] = Field(min_length=1, max_length=8)
    preconditions: BatchPreconditions
    predicted_end: PredictedState
    confidence: float = Field(ge=0.0, le=1.0)
    risk: RiskClass = RiskClass.CONDITIONAL
    barrier_after: bool = False
    terminal: bool = False
    source_lobe: str = Field(pattern=r"^[ABab]$")

    @model_validator(mode="after")
    def coordinate_spaces_agree(self) -> "BatchSpec":
        if self.predicted_end.coordinate_space_id != self.preconditions.coordinate_space_id:
            raise ValueError("predicted end and preconditions use different coordinate spaces")
        return self


class LobeDecision(ContractModel):
    """Lobe B's compact oversight decision for the next batch."""

    approved: bool
    batch: BatchSpec | None = None
    reason: str = Field(min_length=1, max_length=2000)
    corrections: tuple[str, ...] = Field(default=(), max_length=32)

    @model_validator(mode="after")
    def approved_requires_batch(self) -> "LobeDecision":
        if self.approved and self.batch is None:
            raise ValueError("an approved decision must include a batch")
        return self


class ScreenAssessment(ContractModel):
    """Lobe B's current assessment of the live desktop stream."""

    observation_revision: int = Field(ge=0)
    status: Literal["stable", "changed", "unsafe"]
    reason: str = Field(min_length=1, max_length=2000)


class ActionExecution(ContractModel):
    action_kind: str = Field(min_length=1, max_length=64)
    performed: bool
    uncertain: bool = False
    detail: str = Field(default="", max_length=2000)
    elapsed_ms: float = Field(ge=0.0)


class BatchExecution(ContractModel):
    batch_id: str = Field(min_length=1, max_length=128)
    ok: bool
    uncertain: bool = False
    results: tuple[ActionExecution, ...] = ()
    failure_index: int | None = Field(default=None, ge=0)
    error: str | None = Field(default=None, max_length=2000)
    actual_observation: RuntimeObservation


class RuntimeReport(ContractModel):
    run_id: str
    status: str
    batches_executed: int = Field(ge=0)
    batches_discarded: int = Field(ge=0)
    actions_executed: int = Field(ge=0)
    transcript: tuple[str, ...] = ()
    final_observation: RuntimeObservation
