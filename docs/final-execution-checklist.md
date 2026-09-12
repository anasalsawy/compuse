# Final execution checklist

**Audit date:** 2026-09-12  
**Audited ref:** `main` at `aa7d4757d5d0389e2c51285d68f8e506b80709d2`  
**Authoritative design:** `plan.md`, committed as `52b775a4b694d03cf68c76cc63cfa016b95dbbb0`

This checklist is deliberately evidence-based. The repository currently contains a small, portable Python coordination core; it is not the complete Windows 11 product described by `plan.md`. No claim below upgrades a planned capability into an implemented one.

## Verification performed

- [x] Inspected the complete tracked tree: 19 files.
- [x] Read the implementation, tests, packaging metadata, README, and CI workflow.
- [x] Cloned `main` into a clean sandbox.
- [x] Installed the project with `pip install -e '.[test]'`.
- [x] Ran the test suite: **7 passed**.
- [x] Ran coverage: **98.32%**, exceeding the CI threshold of 80%.
- [x] Built both wheel and sdist successfully: `compuse-0.2.0-py3-none-any.whl` and `compuse-0.2.0.tar.gz`.
- [ ] Windows-native execution was not performed in this Linux audit; UI Automation, DPI, desktop-session, Electron, browser, voice, and installer claims remain unverified.
- [ ] The remote GitHub Actions run was not independently inspected; local execution confirms the current test command and package build only.

## Already excellent — keep

### Safety boundary and scope

- Keep the explicit README statement that this is a **model-free foundation**, not the complete Windows product.
- Keep the rule that `consume` authorizes a typed action but is not execution and never proves success.
- Keep the explicit rejection of `ENVIRONMENT_CONTENT` and `PROVIDER_OUTPUT` as action authority.
- Keep same-observation and coordinate-space binding for state-dependent permits.
- Keep short, bounded permit TTLs and single-use consumption.
- Keep the one-active-mutation boundary in the Coordinator.

### Protocol

- Keep strict Pydantic models with forbidden extra fields.
- Keep discriminated action unions rather than an untyped authoritative payload.
- Keep timezone-aware observation timestamps.
- Keep canonical action hashing for permit binding.
- Keep bounded input fields and explicit enum origins.

### Event journal

- Keep SQLite-backed event storage, WAL for file databases, `foreign_keys=ON`, busy timeout, and `synchronous=FULL`.
- Keep per-run sequence numbers and SHA-256 chaining with a zero-hash genesis value.
- Keep startup/on-demand chain verification and tamper detection.
- Keep canonical JSON payload encoding.

### Quality gates

- Keep the seven invariant-focused tests.
- Keep the Python 3.11–3.13 CI matrix.
- Keep the 80% coverage gate.
- Keep the minimal workflow permission `contents: read`.
- Keep the package metadata, editable-install path, and successful wheel/sdist build.

## Fix before calling the foundation production-ready

These are concrete issues found by source review, not speculative plan items.

### 1. Make permit consumption durable and atomic

Current permits are held in an in-memory dictionary and `consumed` is mutated on a Pydantic object. The event append is durable, but the permit state itself is lost on restart. Implement a Coordinator-owned persistent permit table or transactionally derive permit state from durable records. The check, consume marker, and `permit_consumed` event must be one SQLite transaction (`BEGIN IMMEDIATE`). Never restore a consumed permit after dispatch uncertainty.

### 2. Add an explicit dispatch lifecycle

The current API returns the action after `consume`; it does not represent `DISPATCHING`, `EXECUTOR_RETURNED`, `VERIFICATION_PENDING`, `VERIFIED`, `FAILED`, or `UNKNOWN`. Add Coordinator-only action transitions and reject illegal transitions. Executor results must be structured and must not directly write authoritative state.

### 3. Bind every permit field required by `plan.md`

Extend proposal/observation/permit models and validation for tool, exact arguments hash, capability hash, launch/browser/policy revisions, window/process/session identity, expiration, confirmation record, and relevant input-desktop identity. The current core binds only a subset: run/action, action hash, observation revision, coordinate space, policy revision, and expiry.

### 4. Make idempotency explicit

`action_id` is an identity field but duplicate requests are not defined as idempotent. Add a durable request/message identity and deterministic duplicate response behavior. Test retries across process restart.

### 5. Tighten event-journal durability and API

- Use a documented, UTC-normalized timestamp policy.
- Make event payloads immutable/canonical at the boundary.
- Define behavior for duplicate requests and sequence conflicts.
- Add startup verification that fails closed for authoritative operation on corruption.
- Add backup guidance preserving SQLite `-wal` and `-shm` files.
- Add retention/size policy before long-running deployment.

### 6. Correct protocol coverage gaps

The plan’s MVP action list includes mouse move, drag, keypress, UIA actions, application launch, and browser-related bindings. The current portable union contains only wait, screenshot, type, click, double-click, scroll, key-combo, and focus-window. Either implement the remaining typed models in the portable layer or state clearly in the capability matrix that they are intentionally absent from this foundation.

### 7. Add malformed-input and concurrency tests

Add tests for invalid UUIDs, malformed hashes, naive/offset timestamps, oversized strings, expired permits, replay, mismatched original proposals, store failures, concurrent issue/consume, database reopen/recovery, corrupted chains, and duplicate action IDs. Include a test proving no second mutation is admitted while the first is unreleased.

### 8. Fix packaging and dependency reproducibility

The repository has no visible lock file despite the plan’s `uv.lock` target. Add and maintain a lock strategy, or explicitly document why this library intentionally does not commit one. Pin CI dependency installation sufficiently for reproducibility. Test installation from the built wheel in a clean environment, not only editable mode.

### 9. Improve CI quality gates

The current workflow runs tests and coverage but does not visibly run formatting, linting, typing, package-build verification, or an installed-wheel test. Add only tools the project commits to maintaining, and make every gate reproducible. Upload coverage/build artifacts when useful.

### 10. Establish repository governance

Protect `main`, require the CI check and review, enable dependency update automation, and document the trust model for unsigned commits. Add `SECURITY.md` with vulnerability reporting and supported versions. Use a recognized SPDX license or document the custom license unambiguously; GitHub currently reports `NOASSERTION`.

## Still missing from the definitive Windows product

The following are **not present in the current 19-file tree** and must not be described as implemented:

- Electron main/preload/renderer application.
- Python Coordinator runtime, scheduler, watchdog, recovery, policy, capabilities, and durable desktop-session lock modules beyond the small in-process core.
- Windows executor: screenshots, display/DPI metadata, persisted coordinate transforms, UIA adapter/locator, semantic/input actions, window/process/session management, clipboard, cancellation, launch registry.
- Deterministic verifier and evidence/artifact store.
- SQLite migrations, checkpoints, artifact manifests, retention, and integrity tooling beyond the small event table.
- Browser isolation, Playwright profiles, downloads policy, and explicit agent-owned CDP attachment.
- Confirmation broker and expiring visible confirmation tokens.
- Push-to-talk STT/TTS provider, privacy/retention documentation, and independent emergency stop.
- Declarative scenarios, fake executor, Windows-native integration tests, crash-point tests, prompt-injection tests, and supported-application matrix with tested versions.
- Installer, signing, migrations, privacy notice, release process, and bounded-overlap evaluation.

These items are the implementation backlog dictated by `plan.md`; they are not defects that can honestly be marked complete without building and testing them.

## Delivery approach

1. Freeze the portable-core contract and add regression tests before expanding scope.
2. Introduce SQLite migrations and durable Coordinator state first; preserve the current safety boundary.
3. Implement observations, display metadata, coordinate transforms, session checks, and cancellation before any real input adapter.
4. Add allowlisted launch and deterministic UIA actions with fake adapters and Windows-native tests.
5. Add evidence/artifact manifests and verification before claiming successful mutations.
6. Add recovery, watchdog, desktop mutex/lease, dry-run, safe mode, and atomic permits.
7. Add authenticated local IPC and Electron only after Coordinator authority is complete.
8. Add isolated Playwright/CDP and voice as separately gated capabilities.
9. Publish the supported-application matrix and capability labels (`supported`, `best effort`, `experimental`, `unsupported`, `requires user intervention`).
10. Run the full acceptance suite on clean Windows 11 profiles at every supported DPI/topology, then package, sign, document, and release only what the evidence supports.

## Final release gate

Do not call the product complete until every mutation has the trace:

```text
user intent
→ current observation
→ typed proposal
→ policy review
→ exact permit
→ atomic consumption
→ executor dispatch
→ post-observation
→ independent verification
→ durable event
→ checkpoint or recovery
```

Until the Windows-specific modules and tests exist, the honest release label is: **Compuse 0.2.0 portable safety-first coordination core; Windows computer-use agent not yet implemented.**
