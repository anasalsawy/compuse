import pytest
from compuse.coordinator.states import ActionState, RunState, can_transition, transition

def test_valid_and_terminal_run_transitions():
    assert can_transition(RunState.IDLE, RunState.TASK_ACCEPTED)
    assert transition(RunState.IDLE, RunState.TASK_ACCEPTED) is RunState.TASK_ACCEPTED
    assert not can_transition(RunState.COMPLETED, RunState.OBSERVING)

def test_invalid_transition_fails_closed():
    with pytest.raises(ValueError):
        transition(RunState.IDLE, RunState.COMPLETED)

def test_unknown_requires_reconciliation():
    assert can_transition(ActionState.DISPATCHING, ActionState.UNKNOWN)
    assert can_transition(ActionState.UNKNOWN, ActionState.RECONCILING)
    assert not can_transition(ActionState.UNKNOWN, ActionState.VERIFIED)

def test_verified_is_terminal():
    assert not can_transition(ActionState.VERIFIED, ActionState.DISPATCHING)
