# Protocol

The public boundary is composed of strict Pydantic models in `compuse.protocol.models`.

- Actions are discriminated by `kind` and reject unknown fields.
- Observations carry a run ID, monotonic revision, timezone-aware capture time, coordinate-space ID, and optional Windows identity fields.
- Proposals bind an action to a run, observation revision, coordinate space, policy revision, and origin.
- Permits carry a deterministic SHA-256 action hash, expiry, and one-use state.
- `Coordinator.consume()` validates and consumes authorization; it does not dispatch input or verify a postcondition.

The event journal stores canonical JSON payloads and a per-run SHA-256 chain. A future executor protocol must add request correlation, helper/capability versions, cancellation, and explicit unknown-result handling.
