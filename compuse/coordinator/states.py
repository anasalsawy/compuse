"""Explicit, fail-closed lifecycle state machines."""
from __future__ import annotations
from enum import StrEnum

class RunState(StrEnum):
    IDLE = "IDLE"
    TASK_ACCEPTED = "TASK_ACCEPTED"
    OBSERVING = "OBSERVING"
    PLANNING = "PLANNING"
    WAITING_FOR_CONFIRMATION = "WAITING_FOR_CONFIRMATION"
    READY_TO_EXECUTE = "READY_TO_EXECUTE"
    ACTION_EXECUTING = "ACTION_EXECUTING"
    VERIFYING = "VERIFYING"
    RECOVERY = "RECOVERY"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    ABORTED = "ABORTED"

class ActionState(StrEnum):
    PROPOSED = "PROPOSED"
    PERMIT_PENDING = "PERMIT_PENDING"
    PERMITTED = "PERMITTED"
    DISPATCHING = "DISPATCHING"
    DISPATCHED = "DISPATCHED"
    EXECUTOR_RETURNED = "EXECUTOR_RETURNED"
    VERIFICATION_PENDING = "VERIFICATION_PENDING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    RECONCILING = "RECONCILING"
    RECONCILED_SUCCESS = "RECONCILED_SUCCESS"
    RECONCILED_FAILURE = "RECONCILED_FAILURE"
    CANCELLED = "CANCELLED"
    ABORTED = "ABORTED"

_RUN_TRANSITIONS = {
    RunState.IDLE: {RunState.TASK_ACCEPTED},
    RunState.TASK_ACCEPTED: {RunState.OBSERVING, RunState.CANCELLED, RunState.ABORTED},
    RunState.OBSERVING: {RunState.PLANNING, RunState.RECOVERY, RunState.CANCELLED, RunState.ABORTED},
    RunState.PLANNING: {RunState.WAITING_FOR_CONFIRMATION, RunState.READY_TO_EXECUTE, RunState.CANCELLED, RunState.ABORTED},
    RunState.WAITING_FOR_CONFIRMATION: {RunState.READY_TO_EXECUTE, RunState.CANCELLED, RunState.ABORTED},
    RunState.READY_TO_EXECUTE: {RunState.ACTION_EXECUTING, RunState.CANCELLED, RunState.ABORTED},
    RunState.ACTION_EXECUTING: {RunState.VERIFYING, RunState.RECOVERY, RunState.CANCELLED, RunState.ABORTED},
    RunState.VERIFYING: {RunState.COMPLETED, RunState.RECOVERY, RunState.CANCELLED, RunState.ABORTED},
    RunState.RECOVERY: {RunState.OBSERVING, RunState.PAUSED, RunState.COMPLETED, RunState.CANCELLED, RunState.ABORTED},
    RunState.PAUSED: {RunState.OBSERVING, RunState.CANCELLED, RunState.ABORTED},
    RunState.COMPLETED: set(), RunState.CANCELLED: set(), RunState.ABORTED: set(),
}
_ACTION_TRANSITIONS = {
    ActionState.PROPOSED: {ActionState.PERMIT_PENDING, ActionState.CANCELLED, ActionState.ABORTED},
    ActionState.PERMIT_PENDING: {ActionState.PERMITTED, ActionState.CANCELLED, ActionState.ABORTED},
    ActionState.PERMITTED: {ActionState.DISPATCHING, ActionState.CANCELLED, ActionState.ABORTED},
    ActionState.DISPATCHING: {ActionState.DISPATCHED, ActionState.UNKNOWN, ActionState.CANCELLED, ActionState.ABORTED},
    ActionState.DISPATCHED: {ActionState.EXECUTOR_RETURNED, ActionState.UNKNOWN},
    ActionState.EXECUTOR_RETURNED: {ActionState.VERIFICATION_PENDING, ActionState.FAILED, ActionState.UNKNOWN},
    ActionState.VERIFICATION_PENDING: {ActionState.VERIFIED, ActionState.FAILED, ActionState.UNKNOWN},
    ActionState.VERIFIED: set(), ActionState.FAILED: set(),
    ActionState.UNKNOWN: {ActionState.RECONCILING, ActionState.CANCELLED, ActionState.ABORTED},
    ActionState.RECONCILING: {ActionState.RECONCILED_SUCCESS, ActionState.RECONCILED_FAILURE, ActionState.UNKNOWN, ActionState.CANCELLED, ActionState.ABORTED},
    ActionState.RECONCILED_SUCCESS: set(), ActionState.RECONCILED_FAILURE: set(),
    ActionState.CANCELLED: set(), ActionState.ABORTED: set(),
}

def can_transition(current: RunState | ActionState, target: RunState | ActionState) -> bool:
    table = _RUN_TRANSITIONS if isinstance(current, RunState) else _ACTION_TRANSITIONS
    return target in table[current]

def transition(current, target):
    if not can_transition(current, target):
        raise ValueError(f"invalid transition: {current} -> {target}")
    return target

__all__ = ["RunState", "ActionState", "can_transition", "transition"]
