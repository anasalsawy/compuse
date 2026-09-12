"""Coordinator-owned permit lifecycle for the model-free safety core."""
from __future__ import annotations
from datetime import timedelta
from threading import RLock
from uuid import UUID, uuid4
from compuse.protocol import ActionProposal, Observation, Origin, Permit, digest_action, now
from compuse.storage import EventStore
class PermitError(RuntimeError): pass
class Coordinator:
    def __init__(self, store=None, policy_revision="policy-1"):
        self.store=store or EventStore(); self.policy_revision=policy_revision; self._permits={}; self._active_permit=None; self._lock=RLock()
    def issue(self, proposal:ActionProposal, observation:Observation, ttl:float=30)->Permit:
        if not 0<ttl<=300: raise PermitError("ttl must be greater than 0 and no more than 300 seconds")
        if proposal.origin in (Origin.ENVIRONMENT_CONTENT, Origin.PROVIDER_OUTPUT): raise PermitError("untrusted content cannot authorize an action")
        if proposal.run_id!=observation.run_id or proposal.observation_revision!=observation.revision: raise PermitError("proposal is stale")
        if proposal.coordinate_space_id!=observation.coordinate_space_id: raise PermitError("coordinate space differs")
        if proposal.policy_revision!=self.policy_revision: raise PermitError("policy revision is not current")
        permit=Permit(permit_id=uuid4(),run_id=proposal.run_id,action_id=proposal.action_id,action_hash=digest_action(proposal.action),observation_revision=observation.revision,coordinate_space_id=observation.coordinate_space_id,policy_revision=self.policy_revision,expires_at=now()+timedelta(seconds=ttl))
        with self._lock:
            self._permits[permit.permit_id]=(permit,proposal); self.store.append(proposal.run_id,"permit_issued",permit.model_dump(mode="json"),now().isoformat())
        return permit
    def consume(self, permit_id, proposal:ActionProposal, observation:Observation):
        pid=UUID(str(permit_id))
        with self._lock:
            if self._active_permit is not None: raise PermitError("another mutation is in flight")
            item=self._permits.get(pid)
            if item is None: raise PermitError("permit is unavailable")
            permit,original=item
            if permit.consumed or now()>=permit.expires_at: raise PermitError("permit is expired or already consumed")
            if proposal.action_id!=permit.action_id or proposal.run_id!=permit.run_id: raise PermitError("proposal identity does not match permit")
            if proposal.origin in (Origin.ENVIRONMENT_CONTENT,Origin.PROVIDER_OUTPUT): raise PermitError("untrusted content cannot authorize an action")
            if proposal.policy_revision!=permit.policy_revision or proposal.coordinate_space_id!=permit.coordinate_space_id: raise PermitError("proposal binding differs")
            if observation.run_id!=permit.run_id or observation.revision!=permit.observation_revision or observation.coordinate_space_id!=permit.coordinate_space_id: raise PermitError("observation binding is stale")
            if digest_action(proposal.action)!=permit.action_hash or digest_action(original.action)!=permit.action_hash: raise PermitError("action binding is invalid")
            permit.consumed=True; self._active_permit=pid; self.store.append(permit.run_id,"permit_consumed",{"permit_id":str(pid)},now().isoformat()); return proposal.action
    def release(self, permit_id):
        with self._lock:
            if self._active_permit!=UUID(str(permit_id)): raise PermitError("permit does not own mutation boundary")
            self._active_permit=None
    def cleanup(self):
        with self._lock: self._permits={k:v for k,v in self._permits.items() if not v[0].consumed and v[0].expires_at>now()}
