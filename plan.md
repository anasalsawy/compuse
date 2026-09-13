# Plan

- [ ] Add support for importing course data
- [ ] Improve the course scheduling interface
- [ ] Add conflict detection
- [ ] Implement calendar export
- [ ] Write documentation and tests

----------

# Final Verification Report: `anasalsawy/compuse`

**Investigation date:** 2026-09-13  
**Repository:** `https://github.com/anasalsawy/compuse`  
**Audited branch:** `main`  
**Conclusion:** The repository is not currently a Windows computer-use application. It is a small Python safety/coordinator foundation. The existing plan correctly identifies the major gap, but its course-import, scheduling, conflict-detection, and calendar-export tasks do not match the repository’s current purpose or implementation.

No code was changed. No Windows application was run. The requested `winmcp-7e6c6443#run_powershell` connection was not available as a tool in this session, so Windows-native behavior, packaging, UI Automation, and interactive tests could not be verified.

---

## 1. Task interpretation and exact requirements

The stated task asks to:

1. Inspect the repository.
2. Determine what is missing for it to become a complete Windows computer-use application.
3. Implement the missing parts.
4. Run and thoroughly test the application.
5. Use a Windows PowerShell/MCP connection if available.
6. Validate the existing plan and identify technical errors or omissions.

The repository’s `plan.md` defines a much larger target than the short task checklist. It proposes:

- A safety-first Windows desktop agent.
- Durable coordinator state.
- Windows observation and input.
- UI Automation.
- Screenshot capture.
- Physical input fallback.
- Verification and recovery.
- Browser isolation.
- Electron UI.
- Packaging and signing.
- Optional model and voice integrations.

The short plan shown in the task:

- Import course data.
- Improve course scheduling UI.
- Add conflict detection.
- Add calendar export.
- Write documentation and tests.

is inconsistent with the repository’s actual domain. There is no course, schedule, calendar, or event-planning implementation in the repository.

### Correct interpretation

The actual near-term goal should be:

> Convert the existing Python coordination core into a narrowly scoped, safety-first Windows desktop automation prototype, beginning with a model-free Notepad vertical slice.

The repository should not be expanded into course scheduling unless the product requirement has changed and a separate domain model is intended.

---

## 2. Evidence-based repository state

### Repository tree

The inspected `main` branch contains:

```text
.github/
LICENSE
README.md
compuse/
  __init__.py
  coordinator/
    __init__.py
    core.py
  protocol/
    __init__.py
    models.py
  storage/
    __init__.py
    events.py
docs/
  final-execution-checklist.md
  supported-capabilities.md
plan.md
pyproject.toml
tests/
  test_core.py
```

The GitHub code search returned no indexed results for course, calendar, or TODO-related implementation. GitHub reported incomplete search metadata, so absence from search is not absolute proof; however, direct repository tree inspection confirms there are no course or calendar modules.

### Current package configuration

`pyproject.toml` confirms:

```toml
requires-python = ">=3.11"
dependencies = ["pydantic>=2.7,<3"]
```

Test dependency:

```toml
[project.optional-dependencies]
test = ["pytest>=8"]
```

The project uses Hatchling for packaging and Pytest for tests. There is no application entry point, GUI dependency, Windows native-helper project, browser dependency, or installer configuration.

### README-confirmed scope

The README describes the project as:

- A safety-first local-first coordination core.
- A portable model-free foundation.
- A protocol and permit system.
- Not the complete Windows product described by `plan.md`.

It explicitly states that the coordinator does not currently:

- Inject input.
- Launch programs.
- Browse.
- Use Electron.
- Process voice.
- Claim verification.

That description is consistent with the source code.

---

## 3. Existing implementation

### 3.1 Protocol models

`compuse/protocol/models.py` defines:

- Strict Pydantic models using `extra="forbid"` and `strict=True`.
- Origins such as `USER_INTENT`, `SYSTEM_POLICY`, `ENVIRONMENT_CONTENT`, and `PROVIDER_OUTPUT`.
- Action kinds:
  - `wait`
  - `screenshot`
  - `mouse_move`
  - `type`
  - `click`
  - `double_click`
  - `drag`
  - `scroll`
  - `keypress`
  - `key_combo`
  - `window.focus`
  - `application.launch`
- `Observation`
- `ActionProposal`
- `Permit`
- SHA-256 action hashing.

Important verified behavior:

```python
def digest_action(action: Action) -> str:
    return sha256(
        json.dumps(
            action.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
```

This is a reasonable deterministic hash for the current Pydantic models. It is not sufficient by itself for physical desktop safety because the action hash does not include target identity, process identity, window identity, UI Automation element identity, or screenshot/coordinate metadata. Those must be added to the proposal or to a separate binding hash.

### 3.2 Coordinator

`compuse/coordinator/core.py` provides:

- Permit issuance.
- Permit validation.
- One-use consumption.
- A process-local mutation boundary.
- Event recording.

The current state is held in memory:

```python
self._permits = {}
self._active_permit = None
```

Therefore:

- Permits disappear on restart.
- Multiple Coordinator processes can mutate concurrently.
- Issue/consume is not durable.
- No post-action verification occurs.
- No run/action state machine exists.
- No recovery exists for crashes after dispatch.

The existing validations are useful but incomplete for Windows:

- Run ID must match.
- Observation revision must match.
- Coordinate-space ID must match.
- Policy revision must match.
- Untrusted origins are rejected.
- Action hash must match.
- A permit cannot be consumed twice.
- Only one process-local mutation can be active.

Missing checks include:

- Foreground HWND.
- Process ID and process start identity.
- Session ID.
- Input desktop.
- Integrity level/UIPI.
- UI Automation element identity.
- Screenshot/frame identity.
- Launch-policy revision.
- Confirmation identity.
- Browser profile/process identity.
- Capability revision.
- Native helper version.
- Durable lease ownership.

### 3.3 Event storage

`compuse/storage/events.py` provides:

- SQLite storage.
- Foreign keys enabled.
- `busy_timeout`.
- `synchronous=FULL`.
- WAL for file-backed databases.
- Per-run sequence numbers.
- SHA-256 hash chaining.
- Canonical JSON payload serialization.
- Chain verification.

The hash-chain implementation is valuable as an audit mechanism, but it is not a complete state store. It lacks:

- Schema versioning.
- Migrations.
- Runs.
- Actions.
- Observations.
- Durable permits.
- Confirmations.
- Leases.
- Artifacts.
- Checkpoints.
- Recovery records.
- State transition constraints.
- Startup invariant checks.

#### Technical issue in `EventStore.append`

The method uses:

```python
with self.db:
    self.db.execute("BEGIN IMMEDIATE")
```

Python’s SQLite connection context manager commits or rolls back transactions, but it does not itself start a transaction before the explicit `BEGIN IMMEDIATE`. In normal operation this can work because the connection is usually not already inside a transaction. However, callers must not invoke `append()` while another transaction is active on the same connection. A more robust storage layer should own transaction boundaries explicitly and expose transaction-safe methods.

The store also has no synchronization around access to the same SQLite connection. `check_same_thread=False` permits cross-thread use but does not make arbitrary concurrent operations safe. The coordinator’s `RLock` currently protects some access, but a future multi-process implementation requires database-level coordination and a durable lease.

### 3.4 Tests

`tests/test_core.py` covers:

- Basic issue/consume/release.
- Rejection of untrusted origins.
- Stale observation rejection.
- Mismatched action ID rejection.
- Single process-local mutation boundary.
- TTL validation.
- Strict Pydantic validation.
- Event tampering detection.
- Empty event-chain validity.

The tests are useful baseline tests, but they do not test:

- Restart behavior.
- Durable permits.
- Concurrent Coordinator processes.
- SQLite transaction rollback.
- Idempotency.
- State transitions.
- Confirmation replay.
- Action expiry after restart.
- Recovery from uncertain execution.
- Native Windows behavior.
- UI Automation.
- DPI.
- Screenshot capture.
- `SendInput`.
- Foreground-window and session checks.
- Packaging.
- Installer behavior.
- GUI security.

### Baseline execution status

The test suite was inspected but not executed in this environment. Therefore:

- **NO DATA: repository test execution returned no result because no repository execution environment was available through the provided tools.**
- The report cannot claim that `pytest` passes.
- The plan’s suggested command remains:

```powershell
python -m pytest -ra
```

---

## 4. Plan verification and corrected priorities

The existing `plan.md` is substantially more accurate than the short course-scheduling checklist. It correctly says the repository is not yet a Windows computer-use app.

The plan’s main architectural direction is sound:

- Python coordinator as authority.
- Native Windows helper for Windows APIs.
- Semantic UI Automation before physical input.
- Durable permits.
- Post-action verification.
- Unknown-result reconciliation.
- Browser isolation.
- Secure desktop UI.
- No arbitrary model-generated executable paths.
- No blind retries after uncertain physical actions.

However, several corrections are required.

### 4.1 The plan is too broad for the first implementation

The plan includes:

- Windows Graphics Capture.
- UI Automation.
- `SendInput`.
- Browser automation.
- Electron.
- Voice.
- Model integration.
- Packaging.
- Signing.
- Credential storage.
- Recovery.
- Multiple test application matrices.

All are reasonable eventual concerns, but implementing them simultaneously would create an untestable system. The first milestone must be narrower:

1. Durable storage.
2. Durable permits.
3. Basic state machine.
4. Windows identity checks.
5. UI Automation only.
6. Approved Notepad launch.
7. Deterministic text mutation.
8. Post-action verification.
9. Restart and cancellation tests.

Do not implement browser, voice, Electron, or physical mouse fallback before this vertical slice is reliable.

### 4.2 Electron is not required for the first desktop application

The plan treats Electron as an optional selected shell, which is correct. But it risks making Electron appear mandatory. For this Python-first repository, PySide6 is a reasonable alternative for the first local desktop UI:

- It keeps UI and coordinator in the same Python ecosystem.
- Qt provides native Windows desktop widgets.
- Qt for Python documents `pyside6-deploy` as a Windows deployment tool.
- A native helper can still be isolated behind a local RPC boundary.

Electron may be preferable later for a web-style UI or a TypeScript-heavy team, but it introduces:

- A second runtime.
- Node dependency management.
- Renderer/main/preload security boundaries.
- More packaging complexity.
- IPC authorization requirements.

Recommendation: implement the first UI with PySide6 or a CLI/test harness, and defer Electron until the coordinator and executor APIs are stable.

### 4.3 A native helper is still recommended for Windows APIs

UI Automation can be accessed from .NET or language bindings, but the plan’s recommendation to isolate Windows-native behavior is sound. A native helper should own:

- COM initialization.
- UI Automation.
- Window and process identity.
- Session/input-desktop inspection.
- DPI and monitor information.
- Windows Graphics Capture.
- `SendInput`.
- Emergency-stop implementation.
- Native mutex/lock if required.

C++/WinRT or C# are viable. Microsoft’s UI Automation documentation confirms that the Windows client API is COM-based and that clients should initialize COM and create `CUIAutomation`/`IUIAutomation`.

A practical choice is:

- C# for faster implementation and managed Windows APIs.
- C++/WinRT for lower-level control and a native ABI.
- Python only for orchestration and protocol/state logic.

The choice remains unresolved because the repository does not specify a native language or IPC protocol.

---

## 5. Recommended architecture

### 5.1 Runtime topology

Recommended first-stage topology:

```text
PySide6 or CLI test harness
        |
        | local authenticated IPC or in-process adapter
        v
Python Coordinator
  - protocol validation
  - policy
  - durable state
  - permits
  - state machine
  - recovery
  - event journal
        |
        | narrow typed RPC
        v
Windows Native Helper
  - UI Automation
  - process/window identity
  - session/input desktop
  - DPI/monitor metadata
  - optional screenshot capture
  - optional SendInput
  - emergency stop
```

Later:

```text
Browser subsystem: Playwright, isolated profiles
Desktop UI: Electron or PySide6
Provider/strategist: strict data-only adapter
Voice: same action/permit path
```

### 5.2 Ownership boundaries

Python Coordinator owns:

- All state transitions.
- Policy decisions.
- Permit creation and consumption.
- Run/action lifecycle.
- Confirmation state.
- Durable event recording.
- Recovery.
- Idempotency.
- Verification orchestration.
- Native-helper request authorization.

Native helper owns:

- OS observation.
- UI Automation calls.
- Foreground and process identity.
- Input desktop identity.
- DPI/monitor state.
- Physical input.
- Emergency stop.
- Native process and window handles.

The native helper must not independently decide that an action is authorized. It should execute only typed requests containing a Coordinator-issued action token or permit binding.

The UI must never directly invoke native input or arbitrary process launch.

---

## 6. Required data model changes

### 6.1 Run state

```python
from enum import StrEnum

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

### 6.2 Action state

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

Transitions must be explicit and validated. The Coordinator must be the only component that changes them.

### 6.3 Observation identity

Add a structured identity model rather than keeping all fields as unrelated optional strings:

```python
class DesktopIdentity(StrictModel):
    session_id: int
    input_desktop: str
    foreground_hwnd: int | None = None
    foreground_process_id: int | None = None
    foreground_process_start: datetime | None = None
    integrity_level: str | None = None
```

```python
class CoordinateSpace(StrictModel):
    space_id: str
    virtual_left: int
    virtual_top: int
    virtual_width: int
    virtual_height: int
    dpi_scale: float
    monitor_fingerprint: str
```

The monitor fingerprint should change when monitor topology, resolution, orientation, or DPI changes. Any coordinate-based permit bound to the previous fingerprint must be rejected.

### 6.4 Permit binding

The permit should bind at minimum:

```text
run_id
action_id
action_hash
observation_revision
coordinate_space_id
desktop identity
target process/window identity
policy revision
capability revision
native-helper revision
confirmation ID, when required
launch-policy revision, when applicable
browser revision/profile ID, when applicable
expiry
consumed state
lease owner
```

Do not place sensitive screenshots or UI trees directly into ordinary event payloads. Store artifact IDs and hashes.

---

## 7. Durable storage requirements

Add versioned migrations and tables:

```text
schema_version
runs
actions
observations
permits
confirmations
leases
artifacts
checkpoints
events
```

Minimum constraints:

- Foreign keys.
- Unique action IDs.
- Unique permit IDs.
- Unique idempotency keys.
- Indexed run/action lookup.
- Explicit state transition records.
- UTC-aware timestamps.
- Event-chain verification.
- Startup refusal on corrupted authoritative state.
- Backup before migration.
- Refusal of unknown future schema versions.

### Atomic permit consumption

The intended transaction should be conceptually:

```text
BEGIN IMMEDIATE

validate:
  permit exists
  permit not consumed
  permit not expired
  action identity matches
  action hash matches
  observation revision matches
  target identity matches
  policy revision matches
  lease owner matches
  confirmation valid
  run/action state allows dispatch

UPDATE permits SET consumed = true
UPDATE actions SET state = 'DISPATCHING'
INSERT event permit_consumed
INSERT event action_dispatching

COMMIT
```

If validation fails, no state changes may be committed.

Important distinction:

> Atomic permit consumption does not make physical execution atomic.

A crash after commit but before physical dispatch produces a permitted/dispatching action that must be reconciled, not blindly retried.

---

## 8. Windows API and native implementation requirements

### 8.1 UI Automation

Microsoft’s documentation confirms:

- UI Automation exposes desktop UI as automation elements.
- Elements form a tree.
- Control patterns represent behavior.
- Clients should use the COM-based UI Automation client API.
- `IUIAutomation` provides root access, conditions, property access, patterns, and event registration.

The helper should implement:

- COM initialization per worker thread.
- Desktop/window enumeration.
- HWND-to-element lookup.
- Window/process identity.
- UIA tree snapshots.
- Stable property extraction.
- Target resolution.
- Ambiguity rejection.
- Pattern support detection.
- `ValuePattern` for text.
- `InvokePattern` for buttons.
- `SelectionPattern`.
- `ExpandCollapsePattern`.
- `WindowPattern`.
- `ScrollPattern`.
- Focus.
- Post-action UIA snapshot.

A target is invalid if:

- No match exists.
- More than one match exists.
- The element is stale.
- The owning HWND changed.
- The owning process changed.
- The expected pattern is not present.
- The element’s bounding rectangle or identity changed unexpectedly.

### 8.2 Notepad vertical slice

The first real feature should be:

```text
Resolve approved Notepad launch policy
→ launch only by registry ID
→ identify process and HWND
→ inspect UIA tree
→ resolve exactly one text control
→ capture observation
→ create typed proposal
→ issue durable permit
→ consume permit
→ set text through UIA ValuePattern
→ capture post-observation
→ verify exact text
→ persist event and artifact metadata
```

The launch registry must contain an approved ID such as:

```json
{
  "notepad": {
    "display_name": "Windows Notepad",
    "executable": "C:\\Windows\\System32\\notepad.exe",
    "allowed_arguments": [],
    "expected_process_name": "notepad.exe",
    "expected_window_patterns": ["Notepad"],
    "policy_revision": "notepad-v1"
  }
}
```

This is an illustrative schema, not a verified path for every Windows installation. The implementation must resolve and verify the actual executable path on the target Windows system.

Do not allow a provider to pass arbitrary executable paths or command lines.

### 8.3 `SendInput`

The `SendInput` fallback should not be part of the first vertical slice. When implemented, it must:

- Check the return count.
- Treat partial insertion as `UNKNOWN`.
- Validate foreground window immediately before dispatch.
- Validate session and input desktop.
- Validate integrity/UIPI assumptions.
- Track pressed keys/buttons.
- Release held input during cancellation and error.
- Refuse secure desktop and locked workstation.
- Never automatically retry uncertain dispatch.
- Require post-action verification.

`SendInput` is not a substitute for semantic UI Automation. It should be a fallback only for controls that cannot be manipulated semantically.

### 8.4 Screenshot capture

Windows Graphics Capture is a later requirement. It should include:

- Window capture.
- Display capture.
- Frame lifecycle management.
- Device-loss recovery.
- Dimension-change handling.
- Artifact hashing.
- Stale-frame rejection.
- Privacy/redaction policy.
- Retention and deletion.

No current repository code implements it.

---

## 9. Browser automation decision

Playwright’s official documentation confirms:

- Browser contexts are isolated sessions.
- Contexts do not share cookies or cache.
- Downloads can be scoped and persisted.
- Persistent contexts should use a separate automation profile.
- Attaching to the user’s normal browser profile is not supported as a safe default.
- CDP attachment can connect to an existing browser and therefore requires explicit policy restrictions.

Recommended later design:

```text
one automation profile per run
one downloads directory per run
browser process owned by the Coordinator
no attachment to the user’s daily profile
explicit URL policy
download size/type limits
hash downloaded artifacts
close context/browser on completion
```

Browser automation should not be added until the desktop execution and recovery model works.

---

## 10. Desktop UI and packaging

### 10.1 UI choice

The plan’s Electron security requirements are technically sound:

```text
contextIsolation: true
nodeIntegration: false
sandbox: true
```

The renderer must not receive:

- Raw `ipcRenderer`.
- Arbitrary filesystem APIs.
- Native handles.
- Permit-creation primitives.
- Arbitrary shell execution.
- Unvalidated action objects.

However, Electron is not required for the initial milestone. A PySide6 UI is a simpler first option for this Python repository. Qt for Python documents `pyside6-deploy` for Windows deployment, using Nuitka-backed packaging.

Recommended sequence:

1. CLI and automated tests.
2. Optional PySide6 control/evidence UI.
3. Electron only if there is a strong product reason for a TypeScript/web renderer.

### 10.2 Windows packaging

Microsoft’s Windows app deployment documentation confirms that packaging decisions depend on:

- MSIX versus unpackaged deployment.
- Framework-dependent versus self-contained runtime.
- Store, enterprise, direct-download, or internal distribution.
- Signing and update requirements.

The repository currently has no packaging implementation.

Required eventual deliverables:

- Windows installer.
- Native helper packaging.
- Python runtime packaging.
- Database migration behavior.
- Data/log/artifact directory policy.
- Clean install.
- Upgrade.
- Rollback.
- Uninstall.
- Signature verification.
- Crash recovery.
- Version compatibility checks.

Do not claim deployment readiness before a signed or explicitly unsigned test installer has been exercised on a clean Windows machine.

---

## 11. Testing and validation plan

### 11.1 Baseline Python tests

Run:

```powershell
python -m pytest -ra
```

Expected baseline acceptance should include the existing tests plus:

- Canonical timestamp tests.
- Action-hash stability tests.
- Permit expiry tests.
- Permit replay tests.
- Restart tests.
- SQLite rollback tests.
- Concurrent Coordinator tests.
- Idempotency tests.
- State transition tests.
- Confirmation replay tests.
- Event corruption tests.
- Startup integrity failure tests.
- Lease ownership tests.
- Unknown-execution recovery tests.

### 11.2 Windows-native tests

Use a dedicated interactive Windows 11 VM or machine. A normal non-interactive CI runner cannot validate interactive desktop behavior.

Test applications should include, where supported:

- Notepad.
- Win32 controls.
- WinForms.
- WPF.
- WinUI.
- Electron.
- Qt.
- Chromium/Edge.
- WebView2.

Test conditions:

- Unlocked interactive desktop.
- Locked workstation.
- Secure desktop.
- UAC/elevated process mismatch.
- RDP.
- Multiple sessions.
- Foreground-window change.
- Process restart.
- Window replacement.
- UIA element replacement.
- Input desktop change.
- DPI at 100%, 125%, 150%, and 200%.
- Mixed-DPI monitors.
- Negative virtual-screen coordinates.
- Monitor attach/detach.
- Resolution changes.
- Device loss.
- Screenshot dimension changes.
- Native helper crash.
- Coordinator crash.
- Renderer disconnect.
- Cancellation during text input.
- Cancellation while mouse button/key is held.
- Partial/uncertain dispatch.
- Event database corruption.
- Upgrade migration.

### 11.3 Required acceptance test

The first acceptance test must prove:

1. Approved Notepad launch only.
2. Process/window identity captured.
3. UIA tree observed.
4. Exactly one text control resolved.
5. Durable permit issued.
6. Permit consumed once.
7. Text set semantically through UIA.
8. Post-action observation captured.
9. Exact text verified.
10. Event history persisted.
11. Restart does not permit replay.
12. Cancellation releases resources.
13. Uncertain execution blocks blind retry.

---

## 12. Security requirements

The following controls are mandatory:

- Environment content is data, never policy authority.
- Provider/model output is data, never authorization.
- No arbitrary shell or code execution.
- No arbitrary provider-generated executable paths.
- No user-profile browser CDP attachment.
- No credential or MFA automation.
- No secure-desktop automation.
- No blind retry after uncertain physical execution.
- No success without independent verification.
- No permit reuse.
- No unrestricted IPC.
- Emergency stop independent of provider/model/voice.
- Database corruption fails closed.
- Native helper cannot self-authorize.
- UI cannot directly mutate the desktop.
- Sensitive screenshots and UIA trees require retention/redaction policy.
- Passwords, tokens, clipboard contents, and API keys must not be logged.
- Secrets must use Windows Credential Manager, DPAPI, or another approved secret store.

Potentially sensitive artifacts include:

- Screenshots.
- UI Automation text.
- Clipboard content.
- Browser DOM.
- Browser downloads.
- Verification reports.
- Window titles.
- Process command lines.

The product needs an explicit privacy policy before capture or provider upload is enabled.

---

## 13. Errors and gaps found in the existing plan

### Confirmed errors or weaknesses

1. **The short course-scheduling checklist is unrelated to the repository.**  
   No course or calendar implementation exists.

2. **The repository has no runnable application entry point.**  
   It is a library plus tests, not a desktop app.

3. **`Coordinator.consume()` does not execute actions.**  
   It only validates and returns an action.

4. **Permit state is in memory.**  
   Restart safety is absent.

5. **The mutation lock is process-local.**  
   It does not protect against another Coordinator process.

6. **No Windows implementation exists.**  
   No UIA, capture, `SendInput`, process inspection, desktop identity, DPI, or native helper exists.

7. **No verification exists.**  
   Executor success is not modeled because no executor exists.

8. **No unknown-result recovery exists.**

9. **No application UI exists.**

10. **No installer, package, signing, or release workflow exists.**

11. **No Windows workflow exists.**  
    The repository contains `.github/workflows` as a directory, but no workflow file was returned by the inspected tree.

12. **The current event journal is not a complete durable state machine.**

13. **The plan includes many unresolved product decisions.**  
    Windows minimum build, native-helper language, UI shell, IPC, browser scope, signing, privacy, retention, and support matrix remain undefined.

### Recommendations that should be adjusted

- Defer browser, voice, and model integration.
- Treat Electron as optional, not mandatory.
- Use UI Automation before `SendInput`.
- Build a small end-to-end Notepad slice before broad capability work.
- Add an explicit idempotency key and durable lease model.
- Separate authoritative state tables from the append-only audit journal.
- Add native Windows test infrastructure before claiming functionality.

---

## 14. Missing information and unresolved questions

These cannot be resolved from the repository:

1. What Windows versions are supported?
2. Is Windows 11 x64 the only target?
3. Is ARM64 required?
4. Which native-helper language is preferred?
5. Is Electron required, or is PySide6 acceptable?
6. Is browser automation in the first release?
7. Is model/provider integration in the first release?
8. Is voice in the first release?
9. What applications must be supported beyond Notepad?
10. What is the allowed automation-risk policy?
11. What data may leave the machine?
12. How long are screenshots and UIA artifacts retained?
13. Is encryption at rest required?
14. Who owns code-signing certificates?
15. Is Microsoft Store, MSIX, MSI, or direct download required?
16. What IPC transport is acceptable?
17. What is the emergency-stop UX?
18. Which elevated/UIPI scenarios are supported?
19. What is the update and rollback policy?
20. Is a real interactive Windows test machine available?

### Explicit verification limitation

The requested Windows PowerShell/MCP connection was not available in the tool list. Consequently, the following remain unverified:

- Windows dependency installation.
- `pytest` execution on Windows.
- Notepad launch.
- UI Automation behavior.
- `SendInput`.
- Windows Graphics Capture.
- DPI and monitor handling.
- Native helper build.
- Desktop UI execution.
- Installer build.
- Code signing.
- Crash recovery on Windows.

**NO DATA: Windows execution source was unavailable and returned no test result.**

---

## 15. Practical implementation sequence

### Phase 0 — Baseline

1. Run and record:
   ```powershell
   python -m pytest -ra
   ```
2. Add CI for Python 3.11–3.14 as appropriate.
3. Add formatting, linting, and type-checking policy.
4. Preserve the current protocol tests.
5. Correct the README and status documents to state that this is not yet a Windows app.

### Phase 1 — Durable coordinator

1. Add schema versioning.
2. Add migrations.
3. Add durable runs, actions, observations, permits, confirmations, leases, and artifacts.
4. Add state transition validation.
5. Add idempotency.
6. Add atomic permit consumption.
7. Add restart recovery.
8. Add event-chain startup verification.
9. Add fail-closed behavior on corruption.

### Phase 2 — Native Windows identity

1. Choose C# or C++/WinRT.
2. Define a narrow typed RPC interface.
3. Implement COM/UIA initialization.
4. Implement foreground window and process identity.
5. Implement session and input-desktop checks.
6. Implement integrity/UIPI checks.
7. Implement native mutation lock.
8. Implement emergency stop.

### Phase 3 — UI Automation

1. Enumerate top-level windows.
2. Inspect UIA trees.
3. Resolve stable targets.
4. Reject ambiguous targets.
5. Implement `ValuePattern`, `InvokePattern`, `SelectionPattern`, `WindowPattern`, and `ScrollPattern`.
6. Capture post-action UIA state.

### Phase 4 — Notepad vertical slice

1. Add approved launch registry.
2. Launch Notepad through registry ID only.
3. Resolve process/window.
4. Resolve text control.
5. Issue durable permit.
6. Consume it atomically.
7. Set text with UIA.
8. Verify exact text.
9. Persist evidence and event records.
10. Test restart, cancellation, and failure paths.

### Phase 5 — Capture and physical fallback

1. Add screenshot capture.
2. Add coordinate-space fingerprints.
3. Add DPI/multi-monitor handling.
4. Add `SendInput` only as a fallback.
5. Add uncertain-dispatch state and reconciliation.
6. Test cancellation and held-input cleanup.

### Phase 6 — User interface

1. Build a minimal local UI.
2. Display run state, action state, observations, confirmations, and evidence.
3. Add emergency stop.
4. Keep UI authorization narrow.
5. Add Electron only if required.

### Phase 7 — Browser and provider integrations

1. Add Playwright run-scoped profiles.
2. Add URL policy.
3. Add download isolation and hashing.
4. Add provider schema validation.
5. Add action and time budgets.
6. Add prompt-injection tests.
7. Ensure all provider/voice actions use the same Coordinator permit path.

### Phase 8 — Packaging and release

1. Package Python and native helper.
2. Add installer.
3. Add signing.
4. Test clean installation.
5. Test migration and upgrade.
6. Test rollback and uninstall.
7. Publish a support matrix and privacy policy.

---

## Final determination

The repository is a valid starting point for a safety-oriented coordination core, but it is missing nearly every component required for a complete Windows computer-use application:

- No Windows desktop UI.
- No native Windows helper.
- No executor.
- No UI Automation.
- No screenshot capture.
- No physical input implementation.
- No durable permit/state machine.
- No restart recovery.
- No independent verification.
- No unknown-result reconciliation.
- No process/window/session/input-desktop binding.
- No DPI/multi-monitor implementation.
- No browser subsystem.
- No secure IPC.
- No packaging or installer.
- No Windows-native tests.
- No release or privacy policy.

The existing large plan is directionally sound but should be executed incrementally. The first deliverable should not be course scheduling or calendar export. It should be a durable, model-free Notepad vertical slice on a real interactive Windows 11 machine.

Until that slice and its Windows-native tests pass, the project must not be described as a complete Windows computer-use application.

----------

## Quick Start

### 1. Confirm the repository and baseline

From a clean checkout of `anasalsawy/compuse`:

```powershell
git clone https://github.com/anasalsawy/compuse.git
Set-Location compuse

python --version
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
python -m pytest -ra
```

The repository requires Python `>=3.11`, uses Pydantic `>=2.7,<3`, Hatchling, and Pytest `>=8`.

Record the actual results of each command. Do not report tests as passing unless they were executed and the output was retained.

### 2. Confirm the current scope before changing code

The repository is currently a Python coordination library, not a Windows desktop application. The course-import, scheduling, conflict-detection, and calendar-export checklist does not match the repository contents. There are no course, calendar, or scheduling modules in the inspected tree.

The first implementation target is therefore:

> A model-free, safety-first Windows Notepad vertical slice using the existing Python coordinator as the authority, durable local state, Windows UI Automation, post-action verification, and fail-closed recovery.

Do not begin with browser automation, voice, arbitrary model integration, Electron, or physical mouse/keyboard fallback.

### 3. Preserve the existing baseline

Before modifying the implementation:

```powershell
git checkout -b feature/windows-notepad-vertical-slice
git status --short
```

Preserve these existing components and tests:

```text
compuse/protocol/models.py
compuse/coordinator/core.py
compuse/storage/events.py
tests/test_core.py
README.md
plan.md
docs/final-execution-checklist.md
docs/supported-capabilities.md
pyproject.toml
```

### 4. Establish Windows execution access

The requested `winmcp-7e6c6443#run_powershell` connection was unavailable during research. A builder with access to an interactive Windows machine must first verify:

```powershell
$PSVersionTable
Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, OsBuildNumber, OsArchitecture
python --version
```

The machine must have an unlocked interactive desktop for UI Automation and Notepad tests. A non-interactive CI runner cannot validate foreground-window behavior, UI Automation, input desktop identity, DPI, or physical input.

### 5. Implement in this order

1. Run and record the baseline Python test suite.
2. Add durable schema-backed coordinator state.
3. Add explicit run/action state machines.
4. Add durable permit consumption, leases, idempotency, and restart recovery.
5. Define a typed native-helper boundary.
6. Implement Windows identity and UI Automation observation.
7. Implement approved Notepad launch.
8. Implement semantic text editing through UI Automation.
9. Verify the exact resulting text.
10. Add Windows integration tests and failure tests.
11. Add a minimal local UI only after the vertical slice works.
12. Defer browser, voice, models, screenshots, and `SendInput` until the core slice is reliable.

---

## Requirements

### Functional requirements

#### R1. Coordinator authority

The Python Coordinator must be the sole authority for:

- Run creation and cancellation.
- Action proposal validation.
- Policy evaluation.
- Permit issuance.
- Permit consumption.
- State transitions.
- Confirmation requirements.
- Native-helper authorization.
- Verification decisions.
- Recovery decisions.
- Event and artifact recording.

The native helper, UI, provider, or voice layer must never authorize itself.

#### R2. Durable state

The following must survive process restart:

- Runs.
- Actions.
- Observations.
- Permits.
- Confirmations.
- Leases.
- Artifacts.
- State transitions.
- Audit events.

An in-memory dictionary is not sufficient for authoritative state.

#### R3. Explicit lifecycle state

Run and action states must be explicit, persisted, and transition-validated.

A state transition must:

- Identify the run and action.
- Record the previous state.
- Record the next state.
- Record the reason.
- Record a UTC timestamp.
- Be part of the same transaction as the authoritative state update.

Invalid transitions must fail without modifying state.

#### R4. Safe permit behavior

A permit must:

- Be bound to one run.
- Be bound to one action.
- Include a deterministic action hash.
- Include the observation revision used to plan the action.
- Include target process/window identity where applicable.
- Include coordinate-space identity for coordinate actions.
- Include policy and capability revisions.
- Include a bounded expiry.
- Be consumed at most once.
- Be rejected after expiry.
- Be rejected after restart if already consumed.
- Be rejected if the target or observation has changed.
- Be rejected if the Coordinator lease is not held.

#### R5. Notepad vertical slice

The first supported operation must be:

1. Resolve an approved Notepad launch policy.
2. Launch Notepad only through that registry entry.
3. Identify the created process and top-level window.
4. Observe the UI Automation tree.
5. Resolve exactly one text control.
6. Capture desktop, process, window, and UI Automation identity.
7. Create a typed action proposal.
8. Issue and durably persist a permit.
9. Consume the permit atomically.
10. Set text through UI Automation `ValuePattern`.
11. Capture a post-action observation.
12. Verify the resulting text exactly.
13. Persist evidence and audit events.
14. Mark the action and run complete only after successful verification.

#### R6. Ambiguity rejection

The executor must fail closed when:

- No target matches.
- Multiple targets match.
- The target is stale.
- The target belongs to a different process or window.
- The expected UI Automation pattern is unavailable.
- The foreground window changed unexpectedly.
- The input desktop or session changed.
- The monitor/DPI identity changed for coordinate-bound actions.
- The native helper returns an incomplete or uncertain result.

#### R7. No blind retry

An action with uncertain physical or native execution must enter an unknown/reconciliation state. It must not be automatically retried.

The Coordinator must first observe the target again and determine whether the requested postcondition already holds.

#### R8. Cancellation and emergency stop

Cancellation must:

- Stop new dispatch.
- Invalidate unconsumed permits for the run.
- Request native-helper cancellation.
- Release held native input if physical input exists.
- Persist the cancellation result.
- Leave uncertain actions in a reconciliation-required state rather than claiming failure or success without evidence.

The emergency stop must not depend on a model, provider, voice service, or renderer.

### Technical requirements

- Python `>=3.11`.
- Existing Pydantic major version constraint: `>=2.7,<3`.
- Existing Pytest dependency: `>=8`.
- SQLite must remain the local authoritative database for the first milestone.
- All timestamps must be timezone-aware UTC values.
- Existing strict Pydantic models and event hash-chain behavior must be preserved unless a compatibility migration is added.
- Windows-specific functionality must be isolated behind a typed adapter or RPC boundary.
- UI Automation must be preferred over coordinate input.
- No arbitrary executable path may originate from model/provider output.
- No application may receive raw permit-creation capability.
- No application may directly call native input APIs.

### Operational requirements

- The application must run on an unlocked interactive Windows desktop for the first integration milestone.
- A dedicated Windows test machine or VM must be available.
- The native helper and Python coordinator must report compatible versions.
- Database corruption must cause a fail-closed startup rather than silent repair.
- Logs must exclude secrets and sensitive text unless explicitly configured for test mode.
- Installation, upgrade, rollback, signing, and supported Windows versions must be documented before release claims are made.

### Acceptance requirements

The first milestone is accepted only when all of the following are demonstrated on Windows:

- Approved Notepad launch succeeds.
- Arbitrary executable launch is rejected.
- The correct process and window are identified.
- Exactly one text control is resolved.
- Text is written through UI Automation.
- Exact postcondition verification succeeds.
- Permit replay is rejected.
- Stale observation is rejected.
- Foreground-window change is rejected.
- Coordinator restart does not permit replay.
- Database/event corruption fails closed.
- Cancellation leaves no held input.
- An uncertain execution is not blindly retried.
- The entire event and state history can be inspected after completion.

---

## Current State

### Repository contents

The inspected repository contains:

```text
.github/
LICENSE
README.md
compuse/
  __init__.py
  coordinator/
    __init__.py
    core.py
  protocol/
    __init__.py
    models.py
  storage/
    __init__.py
    events.py
docs/
  final-execution-checklist.md
  supported-capabilities.md
plan.md
pyproject.toml
tests/
  test_core.py
```

### Existing protocol implementation

`compuse/protocol/models.py` already provides:

- Strict Pydantic models.
- `extra="forbid"`.
- Strict validation.
- Origin classification.
- Action kinds including:
  - `wait`
  - `screenshot`
  - `mouse_move`
  - `type`
  - `click`
  - `double_click`
  - `drag`
  - `scroll`
  - `keypress`
  - `key_combo`
  - `window.focus`
  - `application.launch`
- `Observation`.
- `ActionProposal`.
- `Permit`.
- Deterministic SHA-256 action hashing through `digest_action()`.

Preserve the current deterministic serialization behavior:

```python
from hashlib import sha256
import json

def digest_action(action: Action) -> str:
    return sha256(
        json.dumps(
            action.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
```

The current action hash is not sufficient for physical desktop authorization by itself. It must be combined with target identity, observation identity, policy revision, capability revision, and native-helper revision.

### Existing Coordinator

`compuse/coordinator/core.py` currently provides:

- Permit issuance.
- Permit validation.
- One-use permit consumption.
- An in-process mutation boundary.
- Event recording.

Current authoritative state is process-local:

```python
self._permits = {}
self._active_permit = None
```

This means:

- Permits disappear after restart.
- Multiple Coordinator processes are not coordinated.
- Permit consumption is not durable.
- No executor is invoked.
- No post-action verification occurs.
- No recovery exists for a crash after dispatch.
- The process-local lock is not a multi-process lease.

Preserve the current validation behavior while moving authoritative permit and action state into SQLite.

### Existing event store

`compuse/storage/events.py` already provides:

- SQLite storage.
- Foreign keys.
- Busy timeout.
- `synchronous=FULL`.
- WAL for file-backed databases.
- Per-run sequence numbers.
- SHA-256 hash chaining.
- Canonical JSON payload serialization.
- Chain verification.

Preserve the event-chain mechanism as the audit layer, but do not use it as the only state store. Add authoritative tables for runs, actions, observations, permits, confirmations, leases, artifacts, and schema metadata.

The storage implementation must own transaction boundaries explicitly. Callers must not be able to invoke an append operation while another transaction on the same connection is active.

### Existing tests

`tests/test_core.py` currently covers:

- Permit issue/consume/release.
- Rejection of untrusted origins.
- Stale observation rejection.
- Action-ID mismatch.
- Process-local mutation exclusivity.
- TTL validation.
- Strict Pydantic validation.
- Event tampering detection.
- Empty event-chain validity.

These tests are a baseline and must remain passing unless behavior is intentionally changed and the tests are updated to reflect the new contract.

### Missing implementation

The repository does not currently contain:

- A runnable desktop application.
- A Windows native helper.
- UI Automation.
- Screenshot capture.
- `SendInput`.
- Process/window/session/input-desktop inspection.
- DPI or multi-monitor handling.
- A durable state machine.
- Durable permits.
- Restart recovery.
- Idempotency.
- Native-helper IPC.
- Post-action verification.
- Unknown-result reconciliation.
- A secure desktop UI.
- Browser automation.
- Voice integration.
- Model/provider integration.
- Installer or packaging configuration.
- Windows-native integration tests.
- A Windows CI workflow.
- A release/signing process.

There is also no course, schedule, calendar, or event-planning implementation. The course-scheduling checklist must not be implemented unless the product requirements are formally changed.

---

## Implementation Design

### 1. Runtime architecture

The first supported topology is:

```text
CLI or minimal local UI
          |
          v
Python Coordinator
  - protocol validation
  - policy
  - durable state
  - permits
  - run/action state machines
  - confirmation
  - recovery
  - event journal
          |
          | typed local adapter or authenticated IPC
          v
Windows Native Helper
  - COM initialization
  - UI Automation
  - process/window identity
  - session/input-desktop checks
  - DPI/monitor metadata
  - emergency stop
```

The UI, if added, must communicate only with Coordinator methods. It must not call UI Automation, process launch, `SendInput`, or SQLite directly.

### 2. Component responsibilities

#### Python Coordinator

Owns:

- Public task/run API.
- Action validation.
- Permit construction.
- Permit persistence and consumption.
- Lease acquisition.
- State transitions.
- Policy revisions.
- Confirmation requirements.
- Native-helper request authorization.
- Verification orchestration.
- Recovery.
- Audit events.

#### Storage layer

Owns:

- SQLite connection configuration.
- Schema creation and migration.
- Transactions.
- Durable state.
- Event append and verification.
- Artifact metadata.
- Lease records.
- Startup integrity checks.

#### Native helper

Owns:

- Windows COM initialization.
- UI Automation access.
- Top-level window and process inspection.
- Session and input-desktop identity.
- UIA element resolution.
- UIA action execution.
- Native cancellation.
- Emergency stop.
- Native process and window handles.

It must not decide whether an action is allowed.

#### UI or CLI

Owns:

- Displaying run/action status.
- Requesting user confirmation where required.
- Requesting cancellation.
- Displaying verification evidence.
- Displaying errors and recovery status.

It must not receive unrestricted native handles or permit-generation primitives.

### 3. Run state machine

Create a strict run state enum:

```python
from enum import StrEnum


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

The implementation must define an explicit transition table. For example:

```text
IDLE -> TASK_ACCEPTED
TASK_ACCEPTED -> OBSERVING
OBSERVING -> PLANNING
PLANNING -> WAITING_FOR_CONFIRMATION
PLANNING -> READY_TO_EXECUTE
WAITING_FOR_CONFIRMATION -> READY_TO_EXECUTE
READY_TO_EXECUTE -> ACTION_EXECUTING
ACTION_EXECUTING -> VERIFYING
ACTION_EXECUTING -> RECOVERY
VERIFYING -> COMPLETED
VERIFYING -> RECOVERY
RECOVERY -> OBSERVING
RECOVERY -> PAUSED
RECOVERY -> ABORTED
Any nonterminal state -> CANCELLED
```

The final transition table must be encoded in code and tested. Do not rely on informal caller discipline.

### 4. Action state machine

Create:

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

A native helper result must distinguish:

```text
SUCCESS
FAILED_BEFORE_DISPATCH
FAILED_AFTER_DISPATCH
UNKNOWN
```

`UNKNOWN` must never be converted automatically into `FAILED` or `SUCCESS`.

### 5. Observation identity

Add structured identity models in `compuse/protocol/models.py` or a new protocol module:

```python
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class DesktopIdentity(StrictModel):
    session_id: int
    input_desktop: str
    foreground_hwnd: int | None = None
    foreground_process_id: int | None = None
    foreground_process_start: datetime | None = None
    integrity_level: str | None = None


class CoordinateSpace(StrictModel):
    space_id: str
    virtual_left: int
    virtual_top: int
    virtual_width: int
    virtual_height: int
    dpi_scale: float
    monitor_fingerprint: str
```

The existing repository may already define a `StrictModel` equivalent. Reuse the existing project pattern instead of duplicating it.

For the Notepad semantic text operation, coordinate data is not required for dispatch, but desktop/process/window identity is required.

### 6. Target identity

Represent a target with:

```python
class WindowIdentity(StrictModel):
    hwnd: int
    process_id: int
    process_start: datetime
    executable_name: str
    window_title: str | None = None


class UiAutomationTarget(StrictModel):
    automation_id: str | None = None
    name: str | None = None
    control_type: str
    class_name: str | None = None
    window: WindowIdentity
    runtime_id: tuple[int, ...] | None = None
```

The native helper must return enough identity information for the Coordinator to detect that an element or owning window has been replaced.

`runtime_id` must not be treated as a permanent identity across observations. It is an observation-bound identifier and must be revalidated.

### 7. Permit binding

A permit record must include at least:

```text
permit_id
run_id
action_id
action_hash
observation_id
observation_revision
target_identity_hash
coordinate_space_id, nullable
policy_revision
capability_revision
native_helper_revision
confirmation_id, nullable
created_at
expires_at
consumed_at, nullable
lease_id
```

The `target_identity_hash` should be a deterministic hash of the target identity used for dispatch. Do not rely on only the action body.

### 8. Atomic permit consumption

Permit consumption must be a single SQLite transaction:

```text
BEGIN IMMEDIATE

SELECT permit, action, run, lease
  FOR application-level validation

Reject if:
  permit missing
  permit already consumed
  permit expired
  run/action mismatch
  action hash mismatch
  observation revision mismatch
  target identity mismatch
  policy revision mismatch
  native-helper revision mismatch
  lease missing or owned by another Coordinator
  confirmation missing or invalid
  state transition invalid

UPDATE permits
  SET consumed_at = current_utc_time

UPDATE actions
  SET state = 'DISPATCHING'

INSERT state-transition event
INSERT permit-consumed event

COMMIT
```

SQLite does not provide the same `SELECT ... FOR UPDATE` syntax as some server databases. Implement the equivalent using `BEGIN IMMEDIATE`, application-level validation, and conditional `UPDATE` statements that verify the expected current state.

If any condition fails, roll back all changes.

### 9. Idempotency

Every externally requested operation must have an idempotency key.

For a repeated request:

- If the original operation is complete, return the original result.
- If it is executing or unknown, return the current state.
- Do not create a second permit or dispatch a second native action.
- If the idempotency key is reused with a different request hash, reject it.

### 10. Lease model

The Coordinator must acquire a durable lease before mutating the desktop.

A lease record must include:

```text
lease_id
owner_id
run_id
acquired_at
expires_at
heartbeat_at
released_at
```

The owner ID must be unique per Coordinator process. A stale lease may be recovered only after its expiry and after recording a recovery event.

The lease is not a replacement for permit validation. Both are required.

### 11. Native-helper boundary

The native helper must expose typed operations similar to:

```text
get_capabilities()
get_desktop_identity()
enumerate_windows()
capture_ui_tree(window_identity)
resolve_ui_target(window_identity, selector)
invoke_value_pattern(target_identity, value)
focus_window(window_identity)
cancel_current_operation()
emergency_stop()
```

The concrete transport remains an unresolved design choice. It must be selected before implementation begins.

Acceptable first-stage approaches include:

- An in-process test adapter for Python unit tests.
- A local authenticated IPC service.
- A subprocess with a strictly defined request/response protocol.

Do not use unrestricted JSON commands such as:

```json
{"command": "run_anything", "arguments": "..."}
```

Use operation-specific schemas and reject unknown fields.

### 12. UI Automation design

The native helper must:

1. Initialize COM on each worker thread.
2. Obtain the desktop/root UI Automation element.
3. Enumerate top-level windows.
4. Identify windows by HWND and process identity.
5. Resolve targets using multiple properties.
6. Reject zero or multiple matches.
7. Verify supported control patterns.
8. Execute semantic patterns.
9. Capture a post-action observation.

The Notepad operation should use `ValuePattern` when available. It must not fall back automatically to keystrokes during the first milestone.

### 13. Approved launch policy

Add a versioned launch registry. The exact Windows executable path must be resolved and verified on the target system; do not assume one path works on every supported Windows installation.

The registry shape may be:

```json
{
  "notepad": {
    "display_name": "Windows Notepad",
    "executable": "<verified target path>",
    "allowed_arguments": [],
    "expected_process_name": "notepad.exe",
    "expected_window_patterns": ["Notepad"],
    "policy_revision": "notepad-v1"
  }
}
```

The application-launch action must contain only:

```text
application_id = "notepad"
```

It must not contain an arbitrary executable path supplied by a provider or model.

The launcher must verify:

- The selected ID exists.
- The executable path matches the approved registry.
- Arguments are from the approved list.
- The resulting process name matches policy.
- The resulting window belongs to the created process.
- The resulting window is on the expected interactive desktop.

### 14. Notepad text operation

The action should be represented by a typed, constrained operation rather than a generic arbitrary UI command.

Required inputs:

```text
application_id
window selector
text value
expected postcondition
```

The Coordinator must:

1. Observe the approved Notepad window.
2. Resolve one editable text element.
3. Record its UI Automation and window identity.
4. Compute an action hash.
5. Persist the proposal.
6. Issue a permit.
7. Consume it atomically.
8. Ask the native helper to set the value.
9. Capture the resulting value.
10. Compare the actual value with the expected value.
11. Mark the action verified only on an exact match.

### 15. Screenshot and physical input scope

Do not make screenshot capture or `SendInput` prerequisites for the first Notepad slice.

When later implemented:

- Screenshots must be artifact records with hashes and retention rules.
- Coordinate permits must include monitor topology and DPI fingerprints.
- `SendInput` must check its return count.
- Partial input must become `UNKNOWN`.
- Foreground window, session, input desktop, and integrity conditions must be checked immediately before dispatch.
- Held keys/buttons must be released during cancellation and failure.
- Uncertain physical input must never be blindly retried.

### 16. Browser, voice, and provider scope

Defer these until the desktop slice passes.

When eventually implemented:

- Provider output is untrusted data.
- Provider output must pass strict schema validation.
- Provider output cannot create permits.
- Voice commands enter the same task/proposal/permit pipeline.
- Browser automation uses a separate profile per run.
- The user’s normal browser profile must not be attached by default.
- Downloads use a run-specific directory and are hashed.
- Credentials, MFA, and secrets are excluded from the first product scope.

---

## File and Change Map

The paths below distinguish existing files from proposed files. Proposed files must not be assumed to exist until created.

### Existing files to preserve or modify

#### `pyproject.toml`

Modify to add only dependencies and tooling required by the selected implementation.

Required changes:

- Preserve `requires-python = ">=3.11"`.
- Preserve `pydantic>=2.7,<3`.
- Preserve the existing test extra containing `pytest>=8`.
- Add lint/type/test tools only after selecting the project policy.
- Add a CLI entry point only after defining the actual application module.
- Do not add PySide6, Electron, Playwright, or Windows packages until the corresponding milestone is approved.

#### `compuse/protocol/models.py`

Modify to add:

- Run and action state enums.
- Desktop identity models.
- Window identity models.
- UI Automation target models.
- Permit-binding fields.
- Native-helper request/result models.
- Explicit strict models for all new wire structures.

Preserve:

- Strict validation.
- Unknown-field rejection.
- Existing action model compatibility where possible.
- Existing deterministic `digest_action()` behavior.

#### `compuse/coordinator/core.py`

Refactor to:

- Depend on durable repositories rather than `_permits`.
- Keep existing public behavior compatible where practical.
- Add run lifecycle methods.
- Add durable permit issue/consume methods.
- Add lease ownership checks.
- Add idempotency handling.
- Add explicit state transitions.
- Add recovery handling.
- Add cancellation behavior.
- Ensure all authoritative changes occur transactionally.

Proposed method signatures:

```python
class Coordinator:
    def create_run(self, *, idempotency_key: str, task: str) -> RunRecord: ...
    def observe(self, *, run_id: str) -> ObservationRecord: ...
    def propose_action(
        self,
        *,
        run_id: str,
        observation_id: str,
        action: Action,
        idempotency_key: str,
    ) -> ActionRecord: ...
    def issue_permit(self, *, action_id: str) -> PermitRecord: ...
    def consume_permit(self, *, permit_id: str) -> DispatchAuthorization: ...
    def record_executor_result(
        self,
        *,
        action_id: str,
        result: ExecutorResult,
    ) -> ActionRecord: ...
    def verify_action(self, *, action_id: str) -> VerificationResult: ...
    def cancel_run(self, *, run_id: str, reason: str) -> RunRecord: ...
    def recover_run(self, *, run_id: str) -> RunRecord: ...
```

The exact return models must be defined in the protocol layer.

#### `compuse/storage/events.py`

Refactor carefully to:

- Preserve hash-chain semantics.
- Use explicit transaction ownership.
- Avoid unsafe concurrent use of one SQLite connection.
- Add schema/version checks.
- Add startup integrity verification.
- Add event types for state transitions, permits, dispatch, verification, recovery, and cancellation.

Do not remove the existing tamper-detection tests.

#### `tests/test_core.py`

Preserve existing tests and extend them for:

- Durable permits.
- Permit replay.
- Expired permits after restart.
- State transitions.
- Idempotency.
- Lease ownership.
- Unknown executor results.
- Cancellation.
- Recovery.
- Corrupted event chains.
- Database rollback.

### New Python files

#### `compuse/storage/schema.py`

Create:

- Schema version constant.
- Migration runner.
- Database initialization.
- Unknown-future-schema rejection.
- Migration transaction handling.

Proposed interface:

```python
CURRENT_SCHEMA_VERSION: int


def initialize_database(path: str) -> None: ...


def migrate_database(path: str) -> None: ...


def verify_schema(path: str) -> None: ...
```

#### `compuse/storage/repositories.py`

Create repository methods for:

- Runs.
- Actions.
- Observations.
- Permits.
- Confirmations.
- Leases.
- Artifacts.
- Idempotency records.

Repositories must accept an existing transaction/connection context rather than silently opening unrelated transactions.

#### `compuse/storage/database.py`

Create the connection factory and SQLite configuration:

- `PRAGMA foreign_keys = ON`.
- `PRAGMA busy_timeout`.
- `PRAGMA synchronous = FULL`.
- WAL for file-backed databases where supported by the existing design.
- Thread/process access policy.
- UTC timestamp handling.
- Explicit close behavior.

#### `compuse/coordinator/states.py`

Create:

- Run transition table.
- Action transition table.
- Transition validation functions.
- Terminal-state helpers.

Proposed signatures:

```python
def validate_run_transition(
    current: RunState,
    requested: RunState,
) -> None: ...


def validate_action_transition(
    current: ActionState,
    requested: ActionState,
) -> None: ...
```

#### `compuse/coordinator/recovery.py`

Create recovery logic for:

- Coordinator restart.
- Expired leases.
- Actions left in `DISPATCHING`.
- Native-helper disconnect.
- Unknown execution results.
- Cancellation during dispatch.

Recovery must observe before deciding whether an action succeeded.

#### `compuse/coordinator/policy.py`

Create:

- Approved application registry.
- Policy revision handling.
- Risk classification.
- Confirmation requirements.
- Path and argument validation.

#### `compuse/coordinator/executor.py`

Create the typed executor interface:

```python
from typing import Protocol


class Executor(Protocol):
    def observe(self, request: ObserveRequest) -> ObserveResponse: ...

    def execute(self, request: ExecuteRequest) -> ExecuteResponse: ...

    def cancel(self, request: CancelRequest) -> CancelResponse: ...

    def emergency_stop(self) -> None: ...
```

The first implementation may be a fake executor for unit tests. The fake must model success, failure, and unknown results.

#### `compuse/native/__init__.py`

Create the Python-side native-helper adapter package.

#### `compuse/native/protocol.py`

Create strict request/response models and operation names. Reject unknown operations and unknown fields.

#### `compuse/native/fake.py`

Create a deterministic fake native helper for Python tests. It must not claim to test Windows behavior.

#### `compuse/apps/notepad.py`

Create the Notepad workflow orchestration:

```python
class NotepadWorkflow:
    def launch(self, *, run_id: str) -> WindowIdentity: ...
    def set_text(
        self,
        *,
        run_id: str,
        window: WindowIdentity,
        text: str,
    ) -> VerificationResult: ...
```

It must use the Coordinator and executor interfaces, not direct subprocess or Windows API calls.

#### `compuse/cli.py`

Create only if a CLI is selected for the first runnable harness.

The CLI must provide narrowly scoped commands such as:

```text
compuse run-notepad --text "..."
compuse status <run-id>
compuse cancel <run-id>
compuse verify <run-id>
```

Do not add a generic shell command.

### Proposed native-helper files

The repository has no native-helper language or build system. These paths are therefore proposed and require an explicit implementation decision.

#### `native/README.md`

Document:

- Selected language.
- Supported Windows versions.
- Build prerequisites.
- Debug/release commands.
- IPC transport.
- Version compatibility.
- Signing status.

#### `native/src/...`

Create the selected C# or C++/WinRT implementation. The helper must provide:

- COM initialization.
- UI Automation.
- Process/window identity.
- Session/input-desktop checks.
- UIA tree snapshots.
- ValuePattern execution.
- Cancellation.
- Emergency stop.
- Capability/version reporting.

The exact source layout cannot be finalized until the native language is selected.

### Proposed test files

#### `tests/test_storage.py`

Test:

- Schema initialization.
- Migration.
- Rollback.
- Foreign keys.
- Event-chain integrity.
- Corruption detection.
- Restart persistence.

#### `tests/test_states.py`

Test every valid and invalid run/action transition.

#### `tests/test_permits.py`

Test:

- Issuance.
- Expiry.
- Replay.
- Observation mismatch.
- Target mismatch.
- Policy mismatch.
- Lease mismatch.
- Confirmation mismatch.
- Atomic rollback.

#### `tests/test_recovery.py`

Test:

- Coordinator restart.
- Expired lease.
- Dispatching action.
- Unknown result.
- Reconciliation success.
- Reconciliation failure.
- Cancellation.

#### `tests/test_notepad_workflow.py`

Use the fake native helper to test the workflow contract. Label these as fake-helper tests; they are not Windows integration tests.

#### `tests/windows/test_native_uia.py`

Create only when a Windows integration environment is available. Mark tests appropriately so they are skipped on non-Windows systems.

#### `tests/windows/test_notepad_vertical_slice.py`

Run only on an interactive Windows machine and test the full Notepad flow.

### Documentation files

#### `README.md`

Update to distinguish:

- Current coordinator library.
- Implemented Windows capabilities.
- Unimplemented capabilities.
- Supported Windows versions.
- Data storage location.
- How to run tests.
- Safety limitations.

Do not describe the project as a complete computer-use application until the Windows acceptance tests pass.

#### `docs/windows-development.md`

Document:

- Windows setup.
- Native-helper build.
- Python setup.
- Interactive desktop requirements.
- Test commands.
- Known limitations.

#### `docs/protocol.md`

Document:

- Run/action states.
- Permit binding.
- Native-helper request/response schemas.
- Idempotency.
- Recovery semantics.

#### `docs/security.md`

Document:

- Trust boundaries.
- Secret handling.
- Logging restrictions.
- Browser restrictions.
- Emergency stop.
- Fail-closed behavior.
- Artifact retention.

#### `docs/test-matrix.md`

Document:

- OS versions.
- DPI settings.
- Monitor configurations.
- Interactive/locked/secure desktop conditions.
- Applications tested.
- Native-helper versions.

#### `plan.md`

Replace or update the broad plan only after the first milestone is scoped. Clearly label deferred capabilities:

- Browser automation.
- Voice.
- Model providers.
- Screenshot capture.
- Physical input.
- Electron.
- Packaging/signing.

### Files not to create for the first milestone

Do not add these until separately approved:

- Course-import modules.
- Scheduling modules.
- Calendar-export modules.
- Browser subsystem.
- Voice subsystem.
- Arbitrary model execution.
- Electron renderer.
- Physical input fallback.
- Screenshot capture pipeline.

---

## Step-by-Step Build Plan

### Step 1: Establish and record the baseline

**Input:** Clean repository checkout.

**Action:**

```powershell
python --version
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
python -m pytest -ra
```

Inspect:

```powershell
git status --short
Get-ChildItem -Recurse -File
```

**Expected result:** The current test result, Python version, and repository state are recorded.

**Dependency:** None.

**Failure handling:** Stop implementation if the package cannot be installed or the baseline tests cannot be run. Record the exact error instead of assuming a repository defect.

### Step 2: Define the first-milestone scope

**Input:** Repository evidence and baseline results.

**Action:** Record in `docs/windows-development.md` that the first milestone is the model-free Notepad semantic-text vertical slice.

Explicitly defer:

- Course scheduling.
- Browser automation.
- Voice.
- Provider/model integration.
- Electron.
- `SendInput`.
- Screenshot capture.

**Expected result:** Developers have one bounded acceptance target.

**Dependency:** Step 1.

### Step 3: Add schema versioning and database initialization

**Input:** Existing event store.

**Action:** Create `compuse/storage/schema.py` and `compuse/storage/database.py`.

Add tables for:

```text
schema_version
runs
actions
observations
permits
confirmations
leases
artifacts
idempotency_keys
events
```

Add foreign keys, unique constraints, and indexes.

**Expected result:** A fresh database initializes deterministically and an existing database can be checked for compatibility.

**Dependency:** Step 1.

### Step 4: Separate authoritative state from audit events

**Input:** Existing `EventStore`.

**Action:** Keep `events` as the append-only audit chain. Add repository methods for current state. Ensure every state mutation writes both:

1. The authoritative row update.
2. The corresponding event.

Perform both within one transaction.

**Expected result:** Current state can be queried without reconstructing the entire event stream, while the audit chain remains tamper-detectable.

**Dependency:** Step 3.

### Step 5: Implement explicit state transitions

**Input:** Run/action state requirements.

**Action:** Create `compuse/coordinator/states.py`.

Implement transition tables and validation functions. Add tests for all allowed and rejected transitions.

**Expected result:** Invalid lifecycle transitions fail without database mutation.

**Dependency:** Step 3.

### Step 6: Implement durable leases

**Input:** Coordinator process-local mutation lock.

**Action:** Replace the process-only authority with a durable lease:

- Acquire lease before dispatch-capable operations.
- Heartbeat while active.
- Reject mutations from another active owner.
- Expire leases after a bounded timeout.
- Record acquisition, heartbeat, expiry, and release events.

Retain the in-process lock to serialize operations inside one process.

**Expected result:** Two Coordinator processes cannot both own the desktop mutation lease.

**Dependency:** Steps 3 and 5.

### Step 7: Move permits into SQLite

**Input:** Existing in-memory permit map.

**Action:** Store permits durably. Implement atomic issue and consume operations. Add all binding fields and expiry checks.

The `consume_permit()` implementation must:

- Start `BEGIN IMMEDIATE`.
- Validate all bindings.
- Conditionally mark the permit consumed.
- Transition the action to `DISPATCHING`.
- Append events.
- Commit only if every operation succeeds.

**Expected result:** A consumed permit cannot be reused after a process restart or by another process.

**Dependency:** Steps 3, 5, and 6.

### Step 8: Add idempotency

**Input:** Repeated-run and retry requirements.

**Action:** Add an idempotency table keyed by:

```text
idempotency_key
request_hash
operation_type
result_reference
created_at
```

Reject key reuse with a different request hash.

**Expected result:** Repeated caller requests do not create duplicate actions or permits.

**Dependency:** Step 7.

### Step 9: Add recovery states

**Input:** Actions may remain in `DISPATCHING` after a crash.

**Action:** Implement `compuse/coordinator/recovery.py`.

At startup:

1. Verify schema.
2. Verify the event chain.
3. Find expired leases.
4. Find actions in nonterminal dispatch states.
5. Mark them as `UNKNOWN` or `RECONCILING` according to the last known executor result.
6. Require a fresh observation before deciding success or failure.

**Expected result:** Restart does not blindly repeat an uncertain action.

**Dependency:** Steps 5–8.

### Step 10: Define the native-helper protocol

**Input:** Need for Windows APIs without exposing unrestricted authority.

**Action:** Create strict request/response models in `compuse/native/protocol.py`.

Define operation-specific requests for:

- Capabilities.
- Desktop identity.
- Window enumeration.
- UI tree capture.
- Target resolution.
- Semantic text assignment.
- Cancellation.
- Emergency stop.

Include:

```text
protocol_version
native_helper_version
request_id
operation
run_id
action_id, when applicable
permit_id, when applicable
payload
```

Reject unknown operations and fields.

**Expected result:** Python can authorize a typed native operation without exposing arbitrary command execution.

**Dependency:** Steps 5–7.

### Step 11: Implement a fake executor

**Input:** Native-helper protocol.

**Action:** Create `compuse/native/fake.py`.

The fake must simulate:

- Successful observation.
- Target ambiguity.
- Target disappearance.
- Successful text assignment.
- Failure before dispatch.
- Unknown result.
- Verification mismatch.
- Cancellation.

**Expected result:** Coordinator and recovery logic can be tested without Windows.

**Dependency:** Step 10.

### Step 12: Implement Windows identity observation

**Input:** Native-helper interface and Windows test machine.

**Action:** Implement the native helper’s:

- COM initialization.
- Current session identity.
- Input desktop.
- Foreground HWND.
- Foreground process ID and start identity.
- Integrity level where available.
- Top-level window enumeration.

**Expected result:** The Coordinator receives a structured, observation-bound desktop identity.

**Dependency:** Step 10 and an available interactive Windows environment.

**Failure handling:** If the Windows environment is unavailable, implement only the protocol and fake adapter. Mark native behavior unverified.

### Step 13: Implement UI Automation observation

**Input:** Windows identity implementation.

**Action:** Implement:

- UI Automation root access.
- Top-level window lookup.
- UIA tree snapshot.
- Control type/name/class/property extraction.
- Runtime ID capture.
- Supported-pattern detection.
- Exact-match target resolution.

**Expected result:** The helper can resolve one editable Notepad text control or reject the request safely.

**Dependency:** Step 12.

### Step 14: Implement approved Notepad launch

**Input:** Policy registry.

**Action:** Create `compuse/coordinator/policy.py` and `compuse/apps/notepad.py`.

Add an approved logical application ID:

```text
notepad
```

The launcher must:

- Resolve the configured executable.
- Reject arbitrary paths.
- Use approved arguments only.
- Record the launch policy revision.
- Verify the resulting process and window.
- Reject a mismatched process or window.

**Expected result:** The application can launch and identify approved Notepad only.

**Dependency:** Steps 12 and 13.

### Step 15: Implement semantic text assignment

**Input:** Identified Notepad window and editable UIA target.

**Action:** Add native-helper operation for `ValuePattern`.

The Coordinator must:

1. Capture an observation.
2. Resolve exactly one target.
3. Create a typed action.
4. Persist it.
5. Issue a permit.
6. Consume it atomically.
7. Dispatch the native request.
8. Record the native result.
9. Capture a post-action observation.
10. Compare actual and expected text.
11. Transition to `VERIFIED` only on exact equality.

**Expected result:** The first complete computer-use operation works without keystroke or coordinate fallback.

**Dependency:** Steps 7, 9, 13, and 14.

### Step 16: Implement cancellation and emergency stop

**Input:** Native-helper cancellation operations.

**Action:** Wire cancellation through the Coordinator. Invalidate pending permits, send cancellation to the helper, and persist the result.

**Expected result:** Cancellation is visible in durable state and cannot leave an action falsely marked successful.

**Dependency:** Step 15.

### Step 17: Add Windows integration tests

**Input:** Working native helper and interactive Windows machine.

**Action:** Add:

```text
tests/windows/test_native_uia.py
tests/windows/test_notepad_vertical_slice.py
```

Run them from the interactive Windows desktop.

**Expected result:** The complete Notepad workflow is tested against the real Windows UI Automation stack.

**Dependency:** Steps 12–16.

### Step 18: Add a minimal user-facing harness

**Input:** Passing CLI/workflow integration.

**Action:** Add either:

- A constrained CLI, or
- A minimal PySide6 local UI after dependency approval.

The harness may display:

- Current run.
- Current action.
- Confirmation state.
- Verification result.
- Error/recovery state.
- Emergency stop.

It must not provide arbitrary shell execution or direct native access.

**Expected result:** A user can start, observe, cancel, and inspect the Notepad workflow.

**Dependency:** Step 17.

### Step 19: Update documentation

**Input:** Actual implemented behavior and test output.

**Action:** Update:

- `README.md`
- `docs/windows-development.md`
- `docs/protocol.md`
- `docs/security.md`
- `docs/test-matrix.md`
- `docs/supported-capabilities.md`

Document only verified behavior.

**Expected result:** Documentation distinguishes implemented, deferred, and unverified capabilities.

**Dependency:** Step 17.

### Step 20: Defer broader capabilities until acceptance

Only after the Notepad milestone passes should work begin on:

- Screenshot capture.
- DPI and multi-monitor coordinate handling.
- `SendInput` fallback.
- Browser automation.
- Provider/model adapters.
- Voice.
- Desktop UI expansion.
- Packaging and signing.

Each must use the same Coordinator permit and verification pipeline.

---

## Technical Details

### Known dependency versions and constraints

Verified from the repository:

```toml
requires-python = ">=3.11"
dependencies = ["pydantic>=2.7,<3"]
```

Test extra:

```toml
[project.optional-dependencies]
test = ["pytest>=8"]
```

Do not claim a specific Pydantic or Pytest patch version unless it is present in the lock/install output. The repository does not currently provide a complete Windows native dependency list.

### Canonical action hashing

Preserve the current canonical hashing pattern:

```python
from hashlib import sha256
import json

def digest_action(action: Action) -> str:
    canonical = json.dumps(
        action.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(canonical).hexdigest()
```

For desktop authorization, separately hash the target and observation binding:

```python
def digest_binding(binding: BindingModel) -> str:
    canonical = json.dumps(
        binding.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(canonical).hexdigest()
```

The implementation must define `BindingModel` in the protocol package and test hash stability.

### Strict protocol models

Use the project’s existing strict Pydantic pattern. New models must reject unknown fields:

```python
from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
    )
```

If the repository already defines an equivalent base class, reuse it.

### SQLite connection requirements

The storage layer must configure:

```sql
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;
PRAGMA synchronous = FULL;
```

Use WAL for file-backed databases if compatible with the existing storage design.

The implementation must:

- Avoid sharing one connection unsafely across threads.
- Use explicit transaction ownership.
- Close connections deterministically.
- Treat migration failure as fatal.
- Verify the event chain before enabling mutation.
- Refuse unsupported future schema versions.

### Suggested relational schema

The exact SQL must be implemented and tested, but the logical structure is:

```text
schema_version(
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
)

runs(
    run_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    task TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)

actions(
    action_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    state TEXT NOT NULL,
    action_kind TEXT NOT NULL,
    action_hash TEXT NOT NULL,
    observation_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)

observations(
    observation_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    revision INTEGER NOT NULL,
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(run_id, revision)
)

permits(
    permit_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    action_id TEXT NOT NULL REFERENCES actions(action_id),
    action_hash TEXT NOT NULL,
    observation_id TEXT NOT NULL,
    observation_revision INTEGER NOT NULL,
    target_identity_hash TEXT NOT NULL,
    coordinate_space_id TEXT,
    policy_revision TEXT NOT NULL,
    capability_revision TEXT NOT NULL,
    native_helper_revision TEXT NOT NULL,
    confirmation_id TEXT,
    lease_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    consumed_at TEXT
)

leases(
    lease_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    acquired_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    heartbeat_at TEXT NOT NULL,
    released_at TEXT
)

artifacts(
    artifact_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    kind TEXT NOT NULL,
    path TEXT,
    content_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    retention_class TEXT NOT NULL
)

idempotency_keys(
    idempotency_key TEXT PRIMARY KEY,
    operation_type TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    result_reference TEXT NOT NULL,
    created_at TEXT NOT NULL
)

events(
    ...
)
```

The final schema must preserve compatibility with the existing event implementation or include a migration.

### Executor result model

Use a typed result:

```python
from enum import StrEnum


class DispatchStatus(StrEnum):
    SUCCESS = "SUCCESS"
    FAILED_BEFORE_DISPATCH = "FAILED_BEFORE_DISPATCH"
    FAILED_AFTER_DISPATCH = "FAILED_AFTER_DISPATCH"
    UNKNOWN = "UNKNOWN"


class ExecutorResult(StrictModel):
    request_id: str
    status: DispatchStatus
    native_helper_version: str
    error_code: str | None = None
    error_message: str | None = None
    evidence_artifact_id: str | None = None
```

Do not allow a free-form success boolean to represent an uncertain native operation.

### Verification result model

```python
class VerificationResult(StrictModel):
    verified: bool
    verifier: str
    expected_hash: str
    actual_hash: str | None = None
    evidence_artifact_id: str | None = None
    reason: str | None = None
```

For Notepad text, avoid logging the text value by default. Store a hash or a test-mode-only value according to the privacy policy.

### Native helper version compatibility

Every request must include the Coordinator’s expected protocol version. Every response must include:

```text
protocol_version
native_helper_version
capabilities
request_id
```

The Coordinator must reject a helper that:

- Uses an incompatible protocol version.
- Lacks the required capability.
- Returns a response for a different request ID.
- Returns malformed or unknown fields.

### Windows UI Automation constraints

The native implementation must:

- Initialize COM per worker thread.
- Use UI Automation control patterns rather than coordinates where possible.
- Validate the owning process and HWND.
- Reject stale elements.
- Reject ambiguous target resolution.
- Capture post-action state.
- Treat UIA provider failures as execution failures or unknown results according to whether dispatch may have occurred.

### Launch validation

The launch policy must reject:

- Provider-supplied arbitrary executable paths.
- Unapproved command-line arguments.
- Process-name mismatch.
- Window ownership mismatch.
- Unexpected session or desktop.
- Unexpected elevation/integrity conditions.
- Launches outside the approved policy revision.

### Future physical input requirements

When `SendInput` is eventually added, it must:

- Check the API return count.
- Detect partial insertion.
- Check foreground HWND immediately before dispatch.
- Check session and input desktop.
- Track held keys/buttons.
- Release them on cancellation/error.
- Refuse locked or secure desktops.
- Mark uncertain dispatch as `UNKNOWN`.
- Require independent post-action verification.
- Never blindly retry.

### Future browser requirements

When Playwright is added:

- Use one isolated browser context per run.
- Use a separate automation profile.
- Use a separate download directory.
- Do not attach to the user’s normal profile by default.
- Enforce URL and download policies.
- Hash downloaded artifacts.
- Close browser contexts on completion or cancellation.

---

## Testing and Verification

### Verification status

The following were **not executed during research**:

- `python -m pytest -ra`.
- Windows PowerShell commands.
- Windows dependency installation.
- Native-helper build.
- Notepad launch.
- UI Automation.
- Screenshot capture.
- `SendInput`.
- Packaging.
- Installer behavior.
- Code signing.
- Crash recovery on Windows.

The Windows MCP connection was unavailable. These are unverified, not passing.

### Python baseline commands

Run:

```powershell
python -m pip install -e ".[test]"
python -m pytest -ra
```

After implementation, run:

```powershell
python -m pytest -ra
python -m pytest tests/test_core.py tests/test_storage.py tests/test_states.py tests/test_permits.py tests/test_recovery.py -ra
```

If linting and typing tools are added to `pyproject.toml`, run the exact configured commands, for example:

```powershell
python -m ruff check .
python -m mypy compuse
```

Do not add these commands to acceptance documentation until the tools and configuration exist.

### Unit tests

Required unit-test coverage:

#### Protocol

- Unknown fields rejected.
- Strict integer/string behavior.
- Action hash determinism.
- Binding hash determinism.
- Invalid enum values rejected.
- Invalid timestamps rejected.
- Target identity serialization stable.

#### State machines

- Every valid run transition.
- Every invalid run transition.
- Every valid action transition.
- Every invalid action transition.
- Terminal states cannot transition back to active states.

#### Storage

- Fresh schema creation.
- Migration.
- Unknown future schema rejection.
- Foreign-key enforcement.
- Transaction rollback.
- Concurrent write behavior.
- Event-chain verification.
- Event tampering detection.
- Restart persistence.
- Corrupt database fail-closed behavior.

#### Permits

- Issue.
- Expire.
- Consume once.
- Replay rejection.
- Action mismatch.
- Observation mismatch.
- Target mismatch.
- Policy mismatch.
- Capability mismatch.
- Native-helper mismatch.
- Lease mismatch.
- Confirmation mismatch.
- Atomic failure with no partial updates.

#### Recovery

- Action in `DISPATCHING` after restart.
- Native helper disconnect.
- Unknown result.
- Fresh observation shows success.
- Fresh observation shows failure.
- Fresh observation remains ambiguous.
- Expired lease recovery.
- Cancellation during recovery.

#### Idempotency

- Repeat same request returns original result.
- Reuse with different payload rejects.
- Repeat during execution returns current state.
- Repeat after unknown does not dispatch again.

### Fake-executor integration tests

The fake executor must prove that the Coordinator:

- Sends only authorized requests.
- Rejects malformed responses.
- Records native-helper versions.
- Transitions correctly on success/failure/unknown.
- Verifies only after dispatch.
- Does not retry unknown actions automatically.

These tests do not prove Windows functionality.

### Windows-native tests

Run on an unlocked interactive Windows machine.

Required tests:

1. Native helper starts.
2. COM initialization succeeds.
3. Helper reports protocol and capability versions.
4. Current session and input desktop are captured.
5. Notepad is launched only through the approved registry.
6. Process and HWND identity are captured.
7. UIA tree can be inspected.
8. Exactly one text target resolves.
9. `ValuePattern` is available.
10. Text assignment succeeds.
11. Post-action text matches exactly.
12. Foreground-window change causes rejection.
13. Replaced window causes rejection.
14. Ambiguous target causes rejection.
15. Cancel stops the workflow.
16. Helper disconnect produces an unknown/recovery state.
17. Coordinator restart does not replay a consumed permit.

Run the tests using the project’s actual test configuration. Until a Windows marker and configuration exist, do not invent a command-line marker name.

### Manual checks

On a real Windows test machine:

- Start the application.
- Launch Notepad through the application.
- Confirm the expected process/window identity is shown.
- Enter a test string through the workflow.
- Confirm the visible Notepad content.
- Inspect the persisted run and action state.
- Restart the Coordinator.
- Attempt to replay the old permit.
- Move focus to another application before dispatch.
- Confirm the action is rejected.
- Close or replace Notepad before dispatch.
- Confirm the action is rejected or reconciled.
- Cancel during each supported phase.
- Confirm no stale permit is usable.

### Edge cases

Test:

- Empty text.
- Unicode text.
- Newline text.
- Very large text within the documented limit.
- Notepad already running.
- Multiple Notepad windows.
- Notepad closes before observation.
- Notepad closes after permit issuance.
- Foreground window changes.
- UIA target changes.
- Process restarts with the same executable name.
- Coordinator restarts before and after permit consumption.
- Database locked.
- Database corrupted.
- Lease expires.
- Native helper version mismatch.
- Provider returns unknown fields.
- Provider requests an unapproved executable.

### Acceptance evidence

The builder must retain:

- Exact test commands.
- Test output.
- Windows version/build.
- Python version.
- Native-helper version.
- Protocol version.
- Database schema version.
- DPI/monitor setup.
- Interactive desktop conditions.
- Screenshots or logs only where privacy policy permits.
- Known failures and skipped tests.

---

## Security and Reliability

### Trust boundaries

Treat the following as untrusted:

- Provider/model output.
- Voice transcription.
- Browser page content.
- Clipboard content.
- UI Automation text.
- Window titles.
- Downloaded files.
- Screenshots.
- Renderer input.
- Native-helper responses.

These sources may provide data for planning or verification. They may not change policy, create permits, authorize execution, or select arbitrary executables.

### Secrets

Do not place secrets in:

- Source code.
- `.env` files committed to Git.
- Event payloads.
- Screenshots.
- UI Automation artifacts.
- Provider prompts.
- Standard logs.

A secret-storage implementation is not currently present. Before provider or browser credentials are added, select an approved Windows secret mechanism such as Windows Credential Manager or DPAPI and document it.

### Input validation

Validate:

- All Pydantic request and response models.
- All IDs and revisions.
- All application IDs.
- All executable paths against policy.
- All arguments against policy.
- All target identities.
- All timestamps and expiry values.
- All native-helper response IDs.
- All artifact paths against the application data root.
- All download paths against the run-specific download root.

Reject unknown fields.

### Permissions and desktop boundaries

Reject actions when:

- The workstation is locked.
- The secure desktop is active.
- The input desktop is not the expected one.
- The foreground window differs from the permit binding.
- The process identity differs.
- The integrity/elevation boundary is unsupported.
- The Coordinator lease is absent or expired.

The exact supported elevation/UIPI policy is unresolved and must be documented before claiming support.

### Logging

Logs must include:

- Run ID.
- Action ID.
- Request ID.
- Permit ID.
- State transitions.
- Error codes.
- Native-helper version.
- Protocol version.
- Timing and timeout information.

Logs must not include by default:

- Passwords.
- Tokens.
- Clipboard contents.
- Full typed text.
- Browser credentials.
- Sensitive screenshots.
- Unredacted UIA trees containing private data.

### Timeouts and retries

Every native operation must have a timeout.

Safe retry rules:

- Retry observation when no mutation occurred and the observation request itself failed.
- Do not retry a mutation after an unknown result.
- Reconcile by observing the postcondition.
- Retry only after the Coordinator proves that dispatch did not occur.

### Database failure

If event-chain verification, schema verification, or authoritative state loading fails:

- Refuse mutation.
- Do not attempt silent repair.
- Report the database path and integrity failure without exposing sensitive contents.
- Require an explicit recovery procedure.
- Preserve the corrupted database for forensic analysis.

### Artifact handling

Screenshots, UI trees, verification reports, and downloads must:

- Have content hashes.
- Be associated with a run.
- Have retention classes.
- Be stored outside arbitrary user-selected paths.
- Be deleted according to documented retention policy.
- Be excluded from logs unless explicitly configured.

### Emergency stop

The emergency stop must remain available if:

- The provider is unavailable.
- The voice subsystem fails.
- The renderer disconnects.
- The Coordinator is waiting for a response.
- The native helper reports an error.

The first milestone does not include physical input, but the emergency-stop interface must be designed before any `SendInput` implementation.

---

## Deployment and Operations

### Current deployment state

No deployable Windows application currently exists.

There is no verified:

- Windows installer.
- MSIX package.
- MSI package.
- Signed executable.
- Native-helper release artifact.
- Python runtime bundle.
- Electron bundle.
- PySide6 bundle.
- Upgrade process.
- Rollback process.
- Windows service.
- Release workflow.

Do not claim deployment readiness.

### Development startup

Python development:

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
python -m pytest -ra
```

The native-helper startup command is unknown until its language, build system, and transport are selected. Document the exact command in `docs/windows-development.md` after implementation.

### Required configuration

The first milestone should use local configuration only. At minimum, define:

```text
COMPUSE_DATABASE_PATH
COMPUSE_LOG_LEVEL
COMPUSE_POLICY_PATH
COMPUSE_ARTIFACT_ROOT
COMPUSE_NATIVE_HELPER_ENDPOINT
COMPUSE_NATIVE_HELPER_PROTOCOL_VERSION
```

These names are proposed configuration names and must not be documented as supported until implemented.

Configuration requirements:

- Use absolute, controlled paths.
- Keep the database and artifacts under the application data directory by default.
- Do not accept executable paths from untrusted configuration.
- Validate configuration at startup.
- Fail closed on missing or invalid policy.

### Database startup

Startup must:

1. Resolve the configured database path.
2. Open SQLite with required pragmas.
3. Apply only known migrations.
4. Reject future schema versions.
5. Verify event-chain integrity.
6. Load active runs and leases.
7. Mark expired leases for recovery.
8. Identify uncertain actions.
9. Start the native helper only after storage verification succeeds.

### Native helper startup

The Coordinator must verify:

- Executable identity.
- Helper version.
- Protocol version.
- Capability set.
- Connection identity.
- Request/response correlation.
- Shutdown behavior.

The helper must not start arbitrary child processes based on request payloads.

### Monitoring

The first milestone should record:

- Coordinator startup/shutdown.
- Native-helper connect/disconnect.
- Run state transitions.
- Action state transitions.
- Permit issuance/consumption.
- Verification outcomes.
- Recovery events.
- Database integrity failures.
- Timeouts.

A centralized monitoring service is not present and is not required for the local prototype.

### Packaging

Before packaging begins, decide:

- Supported Windows versions.
- x64 and/or ARM64.
- Framework-dependent or self-contained runtime.
- MSIX, MSI, or direct-download installer.
- Code-signing ownership.
- Per-user or machine-wide installation.
- Data migration location.
- Update and rollback strategy.

These decisions are currently unresolved.

### Rollback

A release must support:

- Database backup before migration.
- Migration failure recovery.
- Native-helper version compatibility.
- Reverting application binaries without losing authoritative state.
- Explicit handling of newer schema versions.

Do not implement destructive migrations without a tested backup and rollback procedure.

---

## Gaps and Unknowns

The following are unresolved and must be answered before the related implementation is finalized.

### Product scope

1. Is the actual product a Windows computer-use application, or has the requirement changed to course scheduling?
2. Which applications besides Notepad must be supported?
3. Is browser automation part of the first release?
4. Is voice part of the first release?
5. Is provider/model integration part of the first release?
6. Is Electron required, or is a Python desktop UI acceptable?

### Windows support

7. Which Windows versions and builds are supported?
8. Is Windows 11 x64 the only target?
9. Is ARM64 required?
10. Are RDP sessions supported?
11. Are multiple user sessions supported?
12. Are elevated applications supported?
13. What integrity/UIPI boundaries are supported?
14. Is secure-desktop behavior expected to be supported or explicitly rejected?

### Native implementation

15. Should the native helper use C#, C++/WinRT, or another language?
16. What build toolchain is available on the Windows machine?
17. What IPC transport is approved?
18. Must the native helper be a separate process in the first milestone?
19. What native-helper versioning policy is required?
20. Who owns native code signing?

### UI

21. Is a desktop UI required for the first milestone?
22. If yes, is PySide6 acceptable?
23. If Electron is required, what Node/Electron versions and packaging tools are approved?
24. What is the emergency-stop user experience?

### Security and privacy

25. What data may leave the machine?
26. Are screenshots allowed?
27. Are UI Automation text values allowed in logs or artifacts?
28. What are artifact retention periods?
29. Is encryption at rest required?
30. Which secret store is approved?
31. Are credential and MFA workflows explicitly prohibited?

### Packaging and operations

32. Is distribution through Microsoft Store, MSIX, MSI, or direct download?
33. Is a signing certificate available?
34. What installer and update mechanism is required?
35. What crash-reporting policy is required?
36. What rollback behavior is required?

### Test access

37. Is an interactive Windows 11 machine or VM available?
38. Is the requested `winmcp-7e6c6443#run_powershell` connection available to the builder?
39. Can the builder test locked workstation, secure desktop, RDP, elevated processes, DPI changes, and multiple monitors?
40. Which Windows applications are available for the application compatibility matrix?

### Unverified behavior

The following remain unverified because Windows execution was unavailable during research:

- Actual Notepad executable location on the target system.
- Native-helper build.
- COM/UI Automation initialization.
- Notepad UIA tree structure on the target Windows build.
- `ValuePattern` behavior.
- Foreground-window checks.
- Session/input-desktop checks.
- DPI and monitor behavior.
- Screenshot APIs.
- `SendInput`.
- Installer behavior.
- Code signing.
- Restart recovery on Windows.
- Full integration test results.

The builder must report each item as verified, failed, skipped, or blocked. “Not tested” must not be reported as “working.”

---

## Builder Handoff

Deliver the following in the first implementation milestone:

- [ ] Baseline test output from the clean repository.
- [ ] Durable SQLite schema with migrations.
- [ ] Separate authoritative state tables and append-only event journal.
- [ ] Explicit run and action state machines.
- [ ] Durable permits with one-time consumption.
- [ ] Durable Coordinator lease.
- [ ] Idempotency handling.
- [ ] Restart recovery for uncertain actions.
- [ ] Strict native-helper request/response models.
- [ ] Fake executor and comprehensive Python tests.
- [ ] Selected native-helper language and documented build process.
- [ ] Windows process/window/session identity observation.
- [ ] Windows UI Automation observation and target resolution.
- [ ] Approved Notepad launch policy.
- [ ] Semantic Notepad text assignment through `ValuePattern`.
- [ ] Independent post-action verification.
- [ ] Cancellation and emergency-stop plumbing.
- [ ] Windows integration tests on an interactive machine.
- [ ] Updated README and Windows development documentation.
- [ ] Security and privacy documentation.
- [ ] Explicit list of deferred features.
- [ ] Exact commands used to build and test.
- [ ] Exact versions of Python, Windows, native helper, and protocol.
- [ ] Test output and environment details.
- [ ] A report of every skipped, blocked, failed, or unverified check.

Do not deliver or claim:

- Course scheduling functionality.
- Calendar export.
- Browser automation.
- Voice automation.
- Model-driven arbitrary computer use.
- Screenshot capture.
- `SendInput` support.
- Electron packaging.
- Windows installer readiness.

Those capabilities are outside the first verified vertical slice and require separate implementation and acceptance work.
