from compuse.protocol import *
from compuse.coordinator import *
def t():
 c=Coordinator();o=Observation(run_id='r',revision=1,captured_at=now(),coordinate_space_id='s');p=ActionProposal(action_id='a',run_id='r',action=Wait(seconds=0),origin=Origin.USER_INTENT,observation_revision=1,policy_revision='x');return c,o,p
def test_flow():
 c,o,p=t();q=c.issue(p,o);c.consume(q.permit_id,p,o);assert c.store.verify('r')
def test_untrusted():
 c,o,p=t();p.origin=Origin.PROVIDER_OUTPUT
 try:c.issue(p,o);assert 0
 except PermitError:pass
