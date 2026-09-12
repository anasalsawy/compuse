# Final Verification Report

**Repository reviewed:** `anasalsawy/compuse`  
**Authoritative document reviewed:** `plan.md` on `main`  
**Review date:** 2026-09-12

## Final verdict

The architecture is fundamentally sound and materially safer than a sequential computer-use loop. Its core rules are:

```text
No permit without current state.
No mutation without a permit.
No success without independent evidence.
No retry after uncertainty without reconciliation.
No environment content can authorize an action.
No partial voice transcript can mutate the desktop.
No local process may bypass the Coordinator.
```

This plan is the authoritative, builder-ready implementation specification for a local-first Windows 11 dual-lobe computer-use agent. It incorporates the required corrections to protocol strictness, DPI handling, coordinate transforms, action state, atomic permits, event integrity, desktop-session locking, browser isolation, IPC security, artifact trust, voice confirmation, and supported-application scope.

## Product contract

The first release supports a published matrix of Windows applications and agent-owned browser sessions using:

- Windows UI Automation;
- Playwright;
- explicit agent-owned Chromium/WebView2 CDP attachment;
- screenshots;
- keyboard and mouse fallback.

The first release does **not** promise universal Windows application support, reliable elevated UI control, UAC/secure-desktop automation, autonomous credential or MFA entry, automatic rollback for irreversible operations, zero-latency sequencing, or complete protection against sensitive screen exposure.

The MVP is:

- local-first Windows 11;
- one interactive desktop session;
- one physical desktop mutation in flight globally;
- same-integrity applications only;
- Coordinator-owned permits and transitions;
- deterministic verification first;
- durable SQLite journaling;
- isolated Playwright profiles;
- push-to-talk voice as optional;
- no arbitrary shell execution.

Every capability is labeled `supported`, `best effort`, `experimental`, `unsupported`, or `requires user intervention`.

## Authority matrix

| Capability | User | Renderer | Electron Main | Coordinator | Strategist | Executor | Verifier |
|---|---:|---:|---:|---:|---:|---:|---:|
| Create run | Yes | Request | Broker | Yes | No | No | No |
| Capture observation | Request | No | No | Yes | Read | Adapter | Read |
| Propose plan | Yes | Request | No | Accept | Yes | No | No |
| Issue permit | Confirm only | No | No | Yes | Propose only | No | No |
| Execute mutation | Confirm | No | No | Dispatch | No | Yes | No |
| Mark verified | No | No | No | Yes | Propose | No | Propose |
| Write ledger | No | No | No | Yes | No | No | No |
| Change policy | User/admin | No | No | Controlled | No | No | No |
| Emergency stop | Yes | Request | Forward | Enforce | No | Cleanup | No |

## Threat model

Controls must cover:

- malicious web/document/clipboard content;
- malicious provider output;
- compromised renderer or unauthorized local IPC;
- stale permit replay;
- artifact substitution and database modification;
- TTS echo and voice replay;
- wrong foreground window, session, or integrity level;
- browser-profile compromise;
- prompt injection.

Environment content is always data, never authority. Redaction status is an enum (`redacted`, `not_redacted`, `redaction_failed`, `redaction_not_attempted`, `unknown`); unknown redaction blocks remote transmission.

## Runtime topology

```text
Electron Renderer
    React task UI, evidence, confirmation, state

Electron Main
    IPC validation, confirmation broker, lifecycle

Python Coordinator
    state machines, permits, scheduler, recovery,
    watchdog, SQLite writer, desktop-session lock

Python Executor Adapter
    screenshots, display metadata, UIA, input,
    application launch, browser control

Verifier
    deterministic UIA/browser/file/process evidence,
    optional model verifier

Optional .NET UIA sidecar
    only when the supported-app matrix proves Python UIA coverage is insufficient
```

The Coordinator is the only authoritative writer. The Executor returns structured results and evidence references; it does not write the ledger.

## Repository structure

```text
compuse/
├── desktop/{main,preload,renderer}
├── packages/
│   ├── protocol/{base.py,envelope.py,actions.py,observations.py,permits.py,evidence.py,confirmations.py,ownership.py,errors.py}
│   ├── coordinator/{runtime.py,state_machine.py,scheduler.py,permit_service.py,confirmation_service.py,watchdog.py,recovery.py,locks.py,capabilities.py,policy.py}
│   ├── windows_executor/{screenshot.py,display.py,dpi.py,uia_adapter.py,uia_locator.py,semantic_actions.py,input_actions.py,window_manager.py,process_manager.py,session.py,clipboard.py,cancellation.py,browser.py,launch_registry.py}
│   ├── verifier/{deterministic.py,uia.py,browser.py,files.py,processes.py,visual.py,policy.py}
│   ├── storage/{db.py,migrations/,events.py,artifacts.py,checkpoints.py,retention.py}
│   └── voice/{capture.py,provider.py,stt.py,tts.py,commands.py,emergency_stop.py}
├── scenarios/
├── tests/
├── installer/
├── pyproject.toml
├── package.json
├── package-lock.json
└── uv.lock
```

## Strict protocol

Use strict Pydantic models:

```python
from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
```

Use typed/discriminated payload models rather than an authoritative `payload: dict`. If a generic envelope remains, dispatch through a schema registry before acceptance. Sequence numbers are allocated only by the Coordinator; producer `message_id` values provide idempotency and `correlation_id` groups request/response messages.

Use explicit content origins:

```text
USER_INTENT
SYSTEM_POLICY
STRATEGIST_INSTRUCTION
EXECUTOR_INSTRUCTION
ENVIRONMENT_CONTENT
PROVIDER_OUTPUT
```

## Action protocol

Supported MVP actions include:

```text
screenshot, mouse_move, click, double_click, drag, scroll,
keypress, key_combo, type, wait,
uia.invoke, uia.set_value, uia.select, uia.expand,
uia.collapse, uia.scroll, uia.focus, uia.close,
window.focus, application.launch
```

The model never supplies arbitrary Python, PowerShell, shell strings, executable code, unrestricted file writes, or unrestricted network requests. Provider batches are split into individual internal actions, each receiving its own permit.

`ApplicationLaunch` binds to `launch_policy_revision`, while state-dependent actions bind to `observation_revision` and `coordinate_space_id`.

## Observation, DPI, and coordinates

Every observation records:

- timestamp and monotonic revision;
- foreground window handle, title, process, integrity, session, and input desktop;
- monitor origin/dimensions and DPI;
- screenshot artifact and SHA-256;
- coordinate-space ID and persisted transform;
- UIA tree hash and browser state reference.

DPI awareness is authoritative in the application manifest. A guarded API fallback may tolerate `ERROR_ACCESS_DENIED` when the manifest already configured awareness; it must not blindly fail or assume success.

Coordinate conversion must use an explicit persisted transform that handles crop, padding, letterboxing, monitor scope, negative virtual-desktop origins, and invalid dimensions. Reject coordinate actions after topology, DPI, screenshot, or coordinate-space changes.

## UI Automation

Define a language-neutral adapter before selecting one primary Python library. Do not let `uiautomation` and `pywinauto` create competing ownership abstractions. The adapter must:

1. verify process/window/session scope;
2. re-resolve immediately before acting;
3. inspect supported patterns;
4. reject ambiguous matches;
5. perform only the requested semantic operation;
6. return the mechanism used;
7. capture post-action state.

Use scored matching across AutomationId, RuntimeId within the captured tree/session, control type, normalized name, class name, ancestry, and rectangle proximity. Reject ambiguity.

`Text` is not treated as a setter pattern. Use `Value` or a documented legacy setter, with concrete method names verified against the selected adapter.

## Window and session safety

Before each focus-dependent mutation:

1. inspect foreground state;
2. verify handle, process, session, and input desktop;
3. verify visibility, enabled state, and non-minimized state;
4. focus target;
5. verify resulting foreground state;
6. abort on mismatch.

Pause for UAC, Windows Hello, MFA, credential dialogs, secure desktop, lock screen, elevated targets, unknown input desktop, or uncertain detection. RDP is unsupported unless separately tested and explicitly enabled.

## Application launch

The Coordinator owns a versioned launch registry. The model chooses a `target_id`, never a path or command string. Validate canonical path, approved location, publisher/hash when configured, registry revision, registry-owned arguments, working directory, expected process, and expected window. Launch via an argument list with `shell=False`; never use model-generated shell text.

## Permits

A permit binds:

```text
run ID, action ID, tool, exact arguments hash,
policy/tool/launch/browser revisions,
executor capability hash, observation revision,
coordinate-space ID, window/process identity,
expiration, one-use state, confirmation record
```

Permit validation and consumption are atomic:

```text
BEGIN IMMEDIATE
    validate all bindings and current state
    increment uses
    append permit_consumed event
COMMIT
dispatch action
```

If dispatch fails after consumption, do not restore the permit; record failure or unknown state.

## State machines

Run states:

```text
IDLE, LISTENING, TASK_ACCEPTED, PLANNING, PLAN_REVIEW,
WAITING_FOR_USER, READY_TO_EXECUTE, ACTION_REVIEW,
WAITING_FOR_CONFIRMATION, ACTION_EXECUTING, VERIFYING,
CHECKPOINTED, RECOVERY, ROLLBACK, COMPLETION_REVIEW,
COMPLETED, CANCELLED, PAUSED, ABORTED
```

Action states:

```text
PROPOSED, PERMIT_PENDING, PERMITTED, DISPATCHING, DISPATCHED,
EXECUTOR_RETURNED, VERIFICATION_PENDING, VERIFIED, FAILED,
UNKNOWN, RECONCILING, RECONCILED_SUCCESS, RECONCILED_FAILURE,
CANCELLED, ABORTED
```

`EXECUTOR_RETURNED` is not success. `VERIFIED` is the only normal success state. Only the Coordinator transitions states.

## Desktop-session lock

Use both an OS-level named mutex and durable SQLite lease. The lease includes device, Windows session, user, input desktop, process/executor IDs, random ownership token, heartbeat, and expiration. Reclaim only after validating the token and stale-lease rules. Only one physical desktop mutation may be in flight globally for the active session.

## Browser isolation

Use Playwright persistent contexts with dedicated profiles, run-specific downloads, exclusive profile locks, known browser process identity, explicit shutdown, permission denial by default, and retention policy. Use DOM/API first, explicit CDP second, UIA/keyboard/coordinates after that.

CDP is disabled by default and may attach only to an agent-owned browser process and profile. Never attach to the user’s daily browser. Validate canonical HTTPS URLs, ports, redirects, downloads, and disallow `javascript:`, `data:`, and `file:` by default.

## Verification

Every mutation produces:

```text
pre-observation
→ action event
→ executor result
→ post-observation
→ verification result
```

Prefer deterministic UIA properties, DOM predicates, process/window identity, file hashes, downloads, and application notifications. Model verification is a fallback only. Record provider/model/prompt/observation dimensions when claiming verifier independence.

## Confirmation and voice

High-risk operations require visible confirmation by default. Generate a random, expiring, one-use token bound to the exact action hash, e.g. `confirm 4827`; do not treat a generic “yes” as sufficient. Voice-only confirmation is disabled by default for consequential actions.

MVP voice is push-to-talk. Partial transcripts never mutate. Emergency stop is outside the model and must work through both voice and a global keyboard shortcut. Select and document a real default STT/TTS provider, including privacy, offline behavior, hardware, latency, languages, and retention. Experimental Windows AI streaming speech remains optional only.

## Persistence and integrity

Use the latest tested SQLite runtime; Python’s `sqlite3.sqlite_version` must be at least 3.51.3. Use WAL, `foreign_keys=ON`, busy timeout, and `synchronous=FULL` for authoritative records. Preserve `-wal` and `-shm` files during backup.

The append-only events table includes:

```sql
previous_event_hash TEXT NOT NULL,
event_hash TEXT NOT NULL,
UNIQUE(run_id, seq)
```

Hash the previous hash, run ID, sequence, event type, payload hash, and timestamp. Verify the chain at startup. Store per-run artifact manifests with canonical root-restricted paths, hashes, origin, capture metadata, redaction state, and retention status. Reject symlinks/reparse points and untrusted externally supplied evidence.

## IPC and Electron

Electron uses context isolation, no Node integration, sandbox where compatible, restrictive CSP, navigation and window-open allowlists, and deny-by-default permission handling. Main-process handlers validate sender frame/origin, webContents, schema, and run ownership.

Local IPC binds only to loopback or a Windows named pipe, uses a random per-launch token, constant-time comparison, origin validation, size limits, rate limits, and lifecycle binding. Public API operations cannot issue or consume permits or dispatch actions; dangerous operations remain private Coordinator operations.

## Operating modes

```text
OBSERVE_ONLY
DRY_RUN
CONFIRM_EVERYTHING
NORMAL
SAFE_MODE
```

Dry-run displays proposals and permits but performs no mutation and cannot claim real-world verification. Safe mode is observation-first with confirmation for every mutation.

## Scenarios and testing

Use declarative scenarios such as:

```yaml
name: notepad-save
steps:
  - observe: foreground_window
  - launch: notepad
  - set_value:
      target: editor
      value: "hello"
  - verify:
      ui:
        value: "hello"
```

Test unit fakes, native Win32/WinForms/WPF/Qt/Electron apps, browsers and WebView2, single/dual/negative-origin monitors, 100/125/150/200% DPI, topology changes, UAC/secure desktop, crash points, prompt injection, malformed providers, stale permits, unauthorized IPC, voice replay, TTS echo, cancellation, and unknown-after-crash side effects.

Publish a supported-application matrix containing application/version, technology, integrity, UIA coverage, semantic actions, coordinate fallback, browser/DOM support, known failures, and verification adapters.

## Implementation order

```text
1. Authority matrix and threat model
2. Runtime/dependency compatibility review
3. Manifest DPI configuration
4. Observation and display metadata
5. Persisted coordinate transforms
6. Primary Python UIA adapter
7. Window/process/session/integrity checks
8. Deterministic UIA actions
9. Cancellation and input cleanup
10. Allowlisted application launch
11. Artifact store/manifests
12. SQLite journal and event hash chain
13. Desktop mutex and durable lease
14. Run/action state machines
15. Atomic permit consumption
16. Deterministic verification
17. Crash recovery
18. Watchdog
19. Dry-run and safe modes
20. Electron/local IPC authentication
21. Strategist integration
22. Provider adapters and contract tests
23. Isolated Playwright sessions
24. Agent-owned CDP attachment
25. Push-to-talk voice
26. Confirmation tokens
27. Supported-application matrix
28. Installer/signing/migrations/privacy
29. Bounded-overlap evaluation
30. Optional FlaUI/.NET sidecar where evidence requires it
```

## Quick start

Use a clean Windows 11 profile or disposable VM; do not use production credentials.

```powershell
git clone https://github.com/anasalsawy/compuse.git
cd compuse
git checkout main
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install uv
uv sync --locked
npm ci
python -c "import sqlite3; print(sqlite3.sqlite_version)"
```

Install Playwright assets only when required by the packaging strategy:

```powershell
python -m playwright install chromium
```

The first vertical slice is model-free:

```text
capture observation
→ acquire desktop-session lock
→ propose one allowlisted action
→ issue permit
→ consume permit atomically
→ execute one same-integrity action
→ capture post-observation
→ verify deterministic evidence
→ append events
```

Initial tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\protocol tests\coordinator tests\fake_executor -q
.\.venv\Scripts\python.exe -m pytest tests\windows -q
```

Acceptance test: launch allowlisted Notepad, capture its window/UIA observation, focus the verified window, set text through a permitted action, capture resulting UIA state, verify the value, and persist the complete event chain.

## Final acceptance criteria

### Executor

- DPI is manifest-configured and verified.
- Screenshots include origin, dimensions, DPI, transform, coordinate-space ID, and hash.
- Coordinate actions reject stale topology or transforms.
- UIA elements are re-resolved and ambiguity rejected.
- Focus actions verify window, process, session, and input desktop.
- Launch uses a versioned allowlist and `shell=False`.
- Cancellation releases keys/buttons.
- Clipboard restoration is tracked honestly.
- Elevated and secure-desktop surfaces pause.

### Coordinator

- Only Coordinator issues permits and writes the authoritative ledger.
- Every mutation has pre/post observations and verification.
- Permits bind exact action, policy, capability, revisions, and expiration.
- Consumption is atomic and single-use.
- One physical desktop mutation is in flight.
- Duplicate requests are idempotent.
- Event hash chain verifies at startup.
- Restart never blindly repeats uncertain side effects.
- Watchdog prevents infinite loops.
- Desktop-session mutex and durable lease prevent concurrent runs.

### Browser, safety, and voice

- Agent profiles are isolated and daily profiles never attached.
- CDP is agent-owned and explicit only.
- URL/redirect/download policies are enforced.
- High-risk actions require visible expiring one-use confirmation tokens.
- Environment content cannot authorize actions.
- Credentials and MFA codes are not model-visible.
- Shell execution is disabled.
- Partial transcripts never mutate.
- Emergency stop works independently of STT.
- Default voice provider and privacy behavior are documented.

### Evaluation

- Baseline and dual-lobe measurements exist.
- False-success and unauthorized-side-effect rates are measured.
- Crash reconciliation is tested.
- Supported-application matrix is published.
- Release thresholds are documented and met.

The architecture is complete when every mutation is traceable through:

```text
user intent
→ observation
→ typed proposal
→ policy review
→ permit
→ atomic permit consumption
→ executor dispatch
→ post-observation
→ independent verification
→ durable event
→ checkpoint or recovery
```
