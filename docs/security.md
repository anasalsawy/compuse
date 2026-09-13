# Security boundary

Compuse provides authorization and audit primitives, not complete desktop security.

## Current guarantees

- Strict typed input models reject unknown fields and bounded-value violations.
- Untrusted content and provider output cannot authorize actions through the Coordinator.
- Permits bind an action to a run, observation revision, coordinate space, policy revision, and deterministic action digest.
- Event records are stored in a SQLite hash chain and can detect tampering, gaps, and reordered records.

## Current limitations

Permit state is process-local, the mutation boundary is process-local, and no executor or Windows identity layer exists. A permit authorizes a typed action but does not execute it or prove success. There is no durable lease, restart recovery, idempotency, native helper, UI Automation, authentication, authorization service, or protection against a separately running process.

Do not treat this prototype as a security boundary for unattended desktop control. Report security issues privately to the repository owner rather than publishing exploit details first.
