# Protocol notes

The portable protocol uses strict Pydantic models with forbidden extra fields. Actions are discriminated by `kind` and include waits, screenshots, mouse movement, text, clicks, dragging, scrolling, keypresses, key combinations, focus, and logical application launch.

`Observation` binds a run to a revision and coordinate-space identity. `ActionProposal` binds an action to an observation revision, coordinate space, policy revision, origin, and optional capability metadata. `digest_action()` produces deterministic SHA-256 JSON digests. `Permit` binds the resulting action hash to the observation and policy and is single-use and expiring.

This protocol is intentionally portable. It does not yet define a durable run state machine, native-helper request/response envelopes, leases, executor results, or verification artifacts. Those additions must preserve strict validation and fail closed on mismatches.