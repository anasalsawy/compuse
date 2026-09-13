# Deep Findings Report: `anasalsawy/compuse`

**Investigation date:** 2026-09-13  
**Repository:** https://github.com/anasalsawy/compuse  
**Audited branch:** `main`  
**Conclusion:** The repository is a small, well-structured Python safety/coordinator foundation. It is **not yet a Windows computer-use application**, and it cannot honestly be called complete until the Windows executor, desktop UI, durable state machine, verification, recovery, packaging, and Windows-native tests are implemented.

---

# Compuse Windows Computer-Use Application — Definitive Implementation Plan

## Quick Start

This plan converts the existing `anasalsawy/compuse` Python coordination core into a safety-first Windows computer-use application.

The first implementation target is a **model-free Notepad vertical slice**:

```text
start Compuse
→ observe the interactive Windows desktop
→ identify an approved Notepad window
→ inspect its UI Automation tree
→ resolve the text control unambiguously
→ create a typed action proposal
→ issue a durable permit
→ consume the permit atomically
→ set text through UI Automation
→ capture post-action state
→ verify the text
→ persist evidence and events
→ display the result in the desktop UI
```

Do not begin with voice, browser automation, unrestricted mouse control, or model integration. Those capabilities depend on the durable state, Windows identity, executor, verification, and recovery boundaries defined here.

### Required first milestone

The first milestone is complete only when the following succeeds on a real, unlocked, interactive Windows desktop:

```text
approved Notepad launch
→ UIA observation
→ durable permit
→ atomic consume
→ UIA text mutation
→ post-observation
→ deterministic verification
→ durable event history
→ clean cancellation and restart behavior
```

## Requirements

The implementation must initially target Windows 11, interactive desktop sessions, x64 unless ARM64 is explicitly added, a logged-in unlocked user session, compatible integrity levels, and local-only installation.

Before implementation begins, decide the Windows minimum build, architecture, desktop shell, native-helper language, packaging method, browser distribution policy, signing ownership, retention period, supported application matrix, and whether model/voice capabilities are in the first release.

Recommended boundaries:

- Python owns protocol validation, policy, durable state, permits, event storage, orchestration, recovery, browser orchestration, and provider integration.
- A Windows-native helper owns Windows Graphics Capture, UI Automation COM access, display/DPI enumeration, foreground and process integrity checks, session/input-desktop inspection, `SendInput`, OS-level locking, and emergency stop.
- Electron, if selected, owns application lifecycle, desktop UI, secure IPC, confirmation UI, and evidence display.
- The renderer must never directly control the Windows desktop.

## Current State

The current repository is Python-based, requires Python `>=3.11`, uses Pydantic `>=2.7,<3`, and Pytest `>=8`. It has a strict typed action protocol, an in-memory Coordinator, SQLite hash-chained event storage, and no Windows-specific implementation, desktop UI, browser automation, installer, or Windows integration tests.

Current actions include `wait`, `screenshot`, `mouse_move`, `type`, `click`, `double_click`, `drag`, `scroll`, `keypress`, `key_combo`, `window.focus`, and `application.launch`.

The Coordinator currently keeps:

```python
self._permits = {}
self._active_permit = None
```

Therefore permits disappear after restart, concurrent Coordinator processes are not protected, issue/consume is not durable, and `consume()` authorizes but does not execute or verify actions.

The event store provides SQLite, foreign keys, busy timeout, `synchronous=FULL`, WAL, sequence numbers, SHA-256 chaining, canonical JSON, and chain verification. It does not yet provide migrations, durable runs/actions/permits, observations, confirmations, leases, artifacts, checkpoints, or recovery records.

## Implementation Design

### Runtime topology

```text
Electron Renderer
    React/TypeScript UI
    task entry
    run status
    confirmation UI
    evidence viewer
    emergency-stop control

Electron Main
    application lifecycle
    secure IPC
    renderer sender validation
    Coordinator supervision
    confirmation forwarding
    emergency-stop forwarding

Python Coordinator
    authoritative state machine
    policy evaluation
    durable permits
    event journal
    scheduler
    watchdog
    cancellation
    recovery
    executor orchestration

Windows Native Helper
    Windows Graphics Capture
    UI Automation
    SendInput
    display/DPI metadata
    process/session/integrity checks
    foreground-window checks
    input-desktop checks
    OS-level mutation lock
    emergency stop

Verifier
    UIA verification
    process/window verification
    browser/DOM verification
    file/download verification

Browser Subsystem
    Playwright
    run-scoped profiles
    isolated downloads
    process ownership

SQLite Storage
    migrations
    runs
    actions
    permits
    observations
    confirmations
    leases
    artifacts
    checkpoints
    event journal
```

### State machines

Run states:

```python
class RunState(StrEnum):
    IDLE = "IDLE"
    TASK_ACCEPTED = "TASK_ACCEPTED"
    OBSERVING = "OBSERVING"
    PLANNING = "PLANNING"
    WAITING_FOR_CONFIRMATION = "WAITING_FOR_CONFIRMATION"
    READY_TO_EXECUTE = "READY_TO_EXECUTE"
    ACTION_EXECUTING = "ACTION_EXECUTING"
    VERIFYING = "VERIFYING"
    RECOVERY = "RECOVERY"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    ABORTED = "ABORTED"
```

Action states:

```python
class ActionState(StrEnum):
    PROPOSED = "PROPOSED"
    PERMIT_PENDING = "PERMIT_PENDING"
    PERMITTED = "PERMITTED"
    DISPATCHING = "DISPATCHING"
    DISPATCHED = "DISPATCHED"
    EXECUTOR_RETURNED = "EXECUTOR_RETURNED"
    VERIFICATION_PENDING = "VERIFICATION_PENDING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    RECONCILING = "RECONCILING"
    RECONCILED_SUCCESS = "RECONCILED_SUCCESS"
    RECONCILED_FAILURE = "RECONCILED_FAILURE"
    CANCELLED = "CANCELLED"
    ABORTED = "ABORTED"
```

Only the Coordinator may change these states. Invalid transitions must be rejected and recorded.

### Durable storage

Add migrations and tables for runs, actions, permits, observations, confirmations, leases, artifacts, and checkpoints. Permit consumption must use `BEGIN IMMEDIATE`, validate every binding, mark the permit consumed, transition the action to `DISPATCHING`, append events, and commit atomically. A failed validation must leave the permit unconsumed.

Required bindings include action hash, observation revision, coordinate-space ID, policy revision, capability revision, process/window/session identity, input desktop, launch policy, browser revision, and confirmation where applicable.

### Execution and verification

Define structured execution results with `success`, `failure`, `unknown`, and `cancelled` statuses. A successful executor return must not automatically mean the action succeeded; independent post-action verification is required.

When execution is uncertain:

```text
mark action UNKNOWN
→ block further mutations
→ capture a fresh observation
→ reconcile against expected state
→ classify success, failure, or user intervention
```

Never automatically retry a physically dispatched action whose result is uncertain.

### Windows observation and input

Implement a native helper for Windows Graphics Capture, UI Automation, display/DPI metadata, foreground/process/session/input-desktop identity, and `SendInput`.

Use semantic UIA operations first and physical input only as a fallback. Reject ambiguous UIA targets. Require DPI awareness, physical-coordinate transforms, monitor topology metadata, screenshot hashes, and stale-coordinate invalidation.

The `SendInput` wrapper must check the return count, treat partial insertion as unknown, validate the target immediately before dispatch, track pressed inputs, and clean up on cancellation or error.

### Browser and Electron

Browser support is later-phase work. Use Playwright run-scoped profiles and downloads, process ownership, URL policy, and explicit CDP restrictions. Never attach to the user’s daily browser.

If Electron is selected, use `contextIsolation: true`, `nodeIntegration: false`, and `sandbox: true`. Expose narrow preload functions only. Validate every IPC sender, origin, schema, message size, rate limit, and run ownership. Do not expose raw `ipcRenderer`, filesystem APIs, native handles, or arbitrary permit creation.

## File and Change Map

Modify:

- `pyproject.toml` for validated dependencies and entry points.
- `compuse/protocol/models.py` for state, execution, confirmation, identity, coordinate, and artifact models.
- `compuse/coordinator/core.py` for durable permits, atomic consume, bindings, idempotency, and recovery.
- `compuse/storage/events.py` for migrations, UTC timestamp normalization, startup verification, and state integration.
- `tests/test_core.py` for restart, concurrency, binding, confirmation, and transaction tests.
- `.github/workflows/test.yml` while adding a separate Windows workflow.
- `README.md` and `docs/supported-capabilities.md` for status, prerequisites, limitations, and support matrix.

Add packages for artifacts, durable coordination, executor, verifier, recovery, IPC, launch registry, browser management, strategist validation, and runtime lifecycle. Add a versioned native-helper project and, after selecting Electron, a secure desktop project.

## Step-by-Step Build Plan

### Step 0 — Freeze and document the baseline

1. Preserve current protocol and safety tests.
2. Run the current Python suite on a clean environment.
3. Record the actual result.
4. State clearly that Windows functionality is not yet implemented.
5. Decide minimum Windows build, architecture, native-helper language, and desktop shell.

### Step 1 — Introduce storage migrations

Implement schema versions, transactional migrations, backups, unknown-future-schema refusal, migration events, and recovery instructions. Startup must migrate, verify schema, verify event chains, verify state invariants, and fail closed on integrity failure.

### Step 2 — Add durable runs, actions, observations, and permits

Move permits out of memory. Implement atomic consumption with all identity checks, action state transitions, event records, and rollback on failure.

### Step 3 — Add complete binding enforcement

Require conditional window/process/session/input-desktop, coordinate-space/screenshot, launch-policy, browser, confirmation, and UIA element bindings based on action type and risk.

### Step 4 — Add idempotency and restart recovery

Duplicate requests must return existing state and must survive restart. Actions left in dispatch-related states after a crash become `UNKNOWN` unless durable evidence proves completion. Block new mutations until reconciliation completes.

### Step 5 — Implement the native Windows identity layer

Expose interactive session, input desktop, foreground HWND, process ID, integrity level, monitor topology, DPI, process launch metadata, OS-level lock, and emergency stop. Reject locked, secure, incompatible, or unknown desktop states.

### Step 6 — Implement screenshot capture

Use Windows Graphics Capture. Implement support detection, window/display capture, frame lifecycle, device-loss recovery, dimension changes, stale-frame rejection, artifact hashing, and retention.

### Step 7 — Implement DPI and coordinate transforms

Configure DPI awareness, enumerate monitors, record virtual desktop origin and physical dimensions, record per-monitor DPI, and invalidate observations after topology or scale changes. Test 100%, 125%, 150%, 200%, mixed DPI, negative coordinates, monitor movement, attach/detach, resolution, and runtime scale changes.

### Step 8 — Implement UI Automation

Implement window enumeration, tree inspection, stable target resolution, ambiguity rejection, InvokePattern, ValuePattern, SelectionPattern, ExpandCollapsePattern, WindowPattern, ScrollPattern, focus, and post-action tree capture.

### Step 9 — Implement the Notepad vertical slice

Use an approved launch registry. Resolve and verify Notepad, inspect and resolve its text control, issue and atomically consume a permit, set text through UIA, capture post-state, verify exact text, persist evidence/events, and display verified success.

### Step 10 — Implement physical input fallback

Implement `SendInput` with foreground, process, session, integrity, input-desktop, key mapping, coordinate, multi-monitor, pressed-input, cancellation, and uncertain-dispatch safeguards.

### Step 11 — Implement deterministic verification

Prefer UIA state, process/window state, browser DOM, file/download hashes, clipboard state, and deterministic screenshots. Model-based visual judgment is only a lower-confidence fallback.

### Step 12 — Implement cancellation, watchdog, and emergency stop

Detect missing heartbeats, timeouts, held inputs, stale leases, executor death, renderer disconnects, integrity failure, and deadlocks. Emergency stop must be independent of model and speech output.

### Step 13 — Add browser automation

Add Playwright only after desktop execution is reliable. Use run-scoped profiles/downloads, process ownership, URL policy, explicit CDP restrictions, browser crash recovery, and artifact hashes.

### Step 14 — Add Electron desktop UI

Implement Electron Main, secure preload, React renderer, local IPC, run creation, observations, action timeline, confirmation, evidence, cancellation, emergency stop, and recovery screens.

### Step 15 — Add strategist and optional voice

Validate provider output strictly, add step/action budgets, no-progress detection, prompt-injection tests, push-to-talk, confirmation phrases, and replay/echo protection. Voice must use the same permit path.

### Step 16 — Package and release

Bundle Electron, renderer, Python, native helper, migrations, launch registry, policy, and optional browser assets. Build, sign, timestamp, and test clean install, upgrade, uninstall, rollback, migration, crash recovery, and supported application behavior.

## Technical Details

### Canonical timestamps

All events must use timezone-aware UTC timestamps generated and normalized at the event boundary:

```python
from datetime import datetime, timezone

def canonical_timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat()
```

### Minimum storage tables

Create versioned tables for:

```text
runs
actions
permits
observations
confirmations
leases
artifacts
checkpoints
events
```

Use foreign keys, uniqueness constraints, indexes, migration tests, and a schema version table.

### Lease and mutation locking

Use a durable SQLite lease plus a Windows named mutex or equivalent. Include owner token, session ID, input desktop, heartbeat, expiration, stale-owner recovery, release, and audit events. A second Coordinator must fail closed.

### Error codes

Define structured errors for stale observations and coordinates, missing or ambiguous targets, window/process/session/integrity/input-desktop mismatch, no interactive desktop, UIPI and `SendInput` failure, capture problems, missing UIA patterns, browser ownership/profile failures, confirmation and permit failures, unknown execution, event corruption, IPC authorization, launch policy, lease conflict, timeout, and verification failure.

### Launch policy

The provider may reference only a registry ID, never an arbitrary executable path. Resolve canonical path, allowed arguments, working directory, expected process/window patterns, optional hashes/publisher, and launch-policy revision through the Coordinator. Record PID, HWND, session, integrity, command line identity, launch token, and policy revision.

### Artifact handling

Hash screenshots, UIA trees, browser downloads, DOM snapshots, and verification reports. Store artifact ID, hash, timestamp, run/action IDs, source, redaction status, and retention status. Do not put secrets or full sensitive artifacts in ordinary event payloads.

### Resource limits

Enforce limits for action text, screenshots, artifacts, UIA depth, browser downloads, action/run duration, steps, provider responses, and IPC messages.

## Testing and Verification

Run the baseline suite with:

```powershell
python -m pytest -ra
```

Add unit tests for canonical hashing/timestamps, strict validation, stale and mismatched bindings, permit expiry/replay, confirmation replay, transitions, idempotency, transaction rollback, restart, event corruption, startup integrity, leases, watchdog, and emergency stop.

Use a dedicated interactive Windows machine or VM containing Notepad, Win32, WinForms, WPF, WinUI, Electron, Qt, Chromium/Edge, and WebView2 test applications.

Test UIA patterns, screenshot capture, device loss, `SendInput`, cleanup, cancellation, foreground/integrity/session/input-desktop boundaries, multi-monitor and mixed-DPI matrices, secure desktop, locked workstation, RDP, browser profile/download isolation, CDP rejection, Electron IPC security, renderer disconnect, and all crash points.

Required crash invariant:

> An action whose physical outcome may be uncertain must never be automatically replayed.

### First vertical-slice acceptance test

The Notepad test passes only when registry resolution, process/window verification, unambiguous control resolution, observation-bound proposal, durable one-use permit, semantic UIA mutation, post-action observation, exact verification, evidence/event persistence, restart safety, and cancellation cleanup all succeed.

## Security and Reliability

Threats include prompt injection, malicious provider output, hostile clipboard data, renderer compromise, permit replay, database tampering, artifact replacement, browser profile leakage, wrong foreground window, wrong input desktop, voice replay, credential exposure, redirects, and accidental elevated interaction.

Non-negotiable controls:

- environment content is data, never authority;
- provider output is data, never authority;
- no arbitrary shell or code execution;
- no arbitrary model-generated executable paths;
- no user-profile CDP attachment;
- no credential or MFA automation;
- no secure-desktop automation;
- no blind retry after uncertain execution;
- no success without verification;
- no permit reuse;
- no unrestricted IPC;
- no artifact transmission when redaction is unknown;
- emergency stop outside the model loop.

Screenshots and UIA trees may contain credentials, tokens, private messages, financial, medical, and private-document data. Implement local-only default, capture scope, retention, redaction status, encryption where required, upload consent, secret-free logs, clipboard cleanup, and deletion behavior.

Maintain these invariants:

1. A permit is never consumed twice.
2. A stale observation cannot authorize a mutation.
3. A changed target cannot inherit an old permit.
4. Uncertain physical actions are never blindly replayed.
5. Success requires verification.
6. A second Coordinator cannot mutate concurrently.
7. Storage corruption prevents authoritative mutations.
8. Cancellation releases held inputs.
9. Emergency stop does not depend on the provider.
10. Environment content cannot alter policy.

## Deployment and Operations

Package a signed installer containing Electron, renderer, packaged Python, native helper, migrations, launch registry, policy, and optional browser assets. Define installation scope, data/log/artifact directories, migration, upgrade, uninstall, rollback, browser assets, native-helper registration, and IPC behavior.

Use Windows Credential Manager, DPAPI, or an approved secret store rather than plaintext secrets. Separate operational logs, security logs, event history, artifact metadata, and crash diagnostics. Do not log passwords, tokens, full clipboard, full screenshots, or API keys.

Retain Linux CI for portable Python tests and add Windows workflows for package installation, Python tests, native-helper build/tests, interactive integration tests where available, Electron build, installer build, signature verification, and artifact publication. Do not claim interactive Windows coverage from a non-interactive runner.

## Gaps and Unknowns

Unresolved items include Windows build, architecture, Electron/native-helper selection, packaging, signing, browser policy, executor, capture, UIA, `SendInput`, DPI, session/input-desktop inspection, OS lock, native IPC, emergency stop, durable state, migrations, confirmations, leases, artifacts, launch registry, support matrix, browser subsystem, provider and voice interfaces, screenshot privacy, encryption, remote processing, secret storage, IPC transport, update trust, and rollback policy.

Windows execution was not available during research. The following remain unverified: Windows repository execution, Notepad launch, Windows Graphics Capture, UI Automation, `SendInput`, DPI, mixed monitors, Electron build, Playwright installation, installer build, signing, and Windows-native integration tests. Linux documentation is not evidence of Windows functionality.

## Builder Handoff

Implement in this order:

1. Freeze the Python baseline.
2. Add migrations.
3. Add durable runs/actions/observations/permits.
4. Add atomic consumption.
5. Add idempotency and restart recovery.
6. Add durable leases and OS locking.
7. Implement native Windows identity.
8. Implement capture and coordinate metadata.
9. Implement UI Automation.
10. Complete the model-free Notepad slice.
11. Implement `SendInput` fallback.
12. Implement deterministic verification.
13. Implement watchdog, cancellation, emergency stop, and unknown reconciliation.
14. Add approved launching.
15. Add browser isolation.
16. Add Electron UI and secure IPC.
17. Add strategist integration.
18. Add optional voice.
19. Package, sign, and test.

Do not describe the repository as a complete Windows computer-use application until Windows observation, UI Automation, physical fallback, DPI/multi-monitor handling, process/window/session/input-desktop binding, durable permits, atomic state, verification, unknown recovery, watchdog/emergency stop, secured UI, browser isolation if advertised, Windows-native tests, installer/signing, support matrix, and privacy policy all exist and are tested.

The next practical task is the durable, model-free Notepad vertical slice. Do not add broad model or voice functionality until that slice passes on a real interactive Windows 11 environment.
