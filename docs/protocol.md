# Protocol

The portable boundary uses strict Pydantic models and discriminated actions. Unknown fields are rejected; provider/environment content cannot authorize mutations. `Coordinator.consume()` authorizes dispatch only and never asserts execution success.

## Lifecycle states

`compuse.coordinator.states` defines explicit `RunState` and `ActionState` transitions. Terminal states cannot re-enter an active state. An executor outcome may be `UNKNOWN`; it must enter reconciliation and may not jump directly to `VERIFIED`.

## Audit integrity

`EventStore` canonicalizes JSON payloads and links events with SHA-256 hashes per run. `verify()` checks sequence continuity and every link. This is tamper-evident, not an external authenticity guarantee: an actor able to rewrite the database can recompute the chain.

## Compatibility

The action discriminator and action digest are part of the portable contract. Additive protocol changes require tests for serialization and digest stability.
