from datetime import timedelta
import pytest
from pydantic import ValidationError
from compuse.coordinator import Coordinator, PermitError
from compuse.protocol import ActionProposal, Click, Observation, Origin, Wait, now
from compuse.storage import EventStore

def fixture():
    observation = Observation(run_id="run", revision=4, captured_at=now(), coordinate_space_id="desktop-a")
    proposal = ActionProposal(action_id="action", run_id="run", action=Wait(seconds=0), origin=Origin.USER_INTENT, observation_revision=4, coordinate_space_id="desktop-a", policy_revision="policy-1")
    return observation, proposal

def test_issue_consume_and_release():
    observation, proposal = fixture(); coordinator = Coordinator(); permit = coordinator.issue(proposal, observation)
    assert coordinator.consume(permit.permit_id, proposal, observation) == proposal.action
    coordinator.release(permit.permit_id)
    assert coordinator.store.verify("run")

def test_untrusted_origins_are_rejected():
    observation, proposal = fixture()
    for origin in (Origin.PROVIDER_OUTPUT, Origin.ENVIRONMENT_CONTENT):
        with pytest.raises(PermitError): coordinator = Coordinator(); coordinator.issue(proposal.model_copy(update={"origin": origin}), observation)

def test_stale_and_mismatched_bindings_are_rejected():
    observation, proposal = fixture(); coordinator = Coordinator()
    with pytest.raises(PermitError): coordinator.issue(proposal.model_copy(update={"observation_revision": 3}), observation)
    permit = coordinator.issue(proposal, observation)
    with pytest.raises(PermitError): coordinator.consume(permit.permit_id, proposal.model_copy(update={"action_id": "other"}), observation)
    with pytest.raises(PermitError): coordinator.consume(permit.permit_id, proposal, observation.model_copy(update={"revision": 5}))

def test_single_mutation_boundary_and_owner_release():
    observation, proposal = fixture(); coordinator = Coordinator(); first = coordinator.issue(proposal, observation); second = coordinator.issue(proposal.model_copy(update={"action_id": "second"}), observation)
    coordinator.consume(first.permit_id, proposal, observation)
    with pytest.raises(PermitError): coordinator.consume(second.permit_id, proposal.model_copy(update={"action_id": "second"}), observation)
    with pytest.raises(PermitError): coordinator.release(second.permit_id)
    coordinator.release(first.permit_id)

def test_ttl_and_models_are_strict():
    observation, proposal = fixture(); coordinator = Coordinator()
    with pytest.raises(PermitError): coordinator.issue(proposal, observation, ttl=0)
    with pytest.raises(ValidationError): Wait(seconds=61)
    with pytest.raises(ValidationError): Observation(run_id="r", revision=0, captured_at=now().replace(tzinfo=None), coordinate_space_id="x")
    with pytest.raises(ValidationError): Click(x=1, y=1, extra="nope")

def test_event_tampering_is_detected(tmp_path):
    store = EventStore(tmp_path / "events.db"); store.append("r", "test", {"value": 1}, now().isoformat()); assert store.verify("r")
    store.db.execute("UPDATE events SET payload=? WHERE run_id=?", ('{"value":2}', "r")); store.db.commit()
    assert not store.verify("r"); store.close()

def test_empty_chain_is_valid():
    assert EventStore().verify("missing")
