from uuid import uuid4
from datetime import timedelta
from compuse.protocol import *
from compuse.storage import EventStore
class PermitError(Exception):pass
class Coordinator:
 def __init__(self,store=None):self.store=store or EventStore();self._permits={};self._busy=False
 def issue(self,p,o,ttl=30):
  if p.origin in (Origin.ENVIRONMENT_CONTENT,Origin.PROVIDER_OUTPUT) or p.run_id!=o.run_id or p.observation_revision!=o.revision:raise PermitError('proposal rejected')
  x=Permit(permit_id=str(uuid4()),run_id=p.run_id,action_id=p.action_id,action_hash=digest_action(p.action),observation_revision=o.revision,policy_revision='policy-1',expires_at=now()+timedelta(seconds=ttl));self._permits[x.permit_id]=(x,p.action);self.store.append(p.run_id,'permit_issued',x.model_dump(mode='json'),now().isoformat());return x
 def consume(self,i,p,o):
  if self._busy or i not in self._permits:raise PermitError('unavailable')
  x,a=self._permits[i]
  if x.consumed or now()>=x.expires_at or digest_action(p.action)!=x.action_hash or o.revision!=x.observation_revision:raise PermitError('binding invalid')
  x.consumed=True;self._busy=True;self.store.append(x.run_id,'permit_consumed',{'permit_id':i},now().isoformat());return a
 def release(self):self._busy=False
