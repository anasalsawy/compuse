# Evidence-Based Implementation Research Report: `anasalsawy/compuse`

## 1. Task interpretation and exact requirements

### Interpreted task

The requested outcome is not merely to improve the existing Python package. It is to turn `anasalsawy/compuse` into a complete Windows computer-use desktop application, including:

- Windows screen and window observation;
- UI Automation;
- mouse and keyboard control;
- application launching;
- browser automation and isolation;
- an agent loop that can plan, act, observe, and verify;
- a desktop UI;
- safety controls and user confirmation;
- durable state, permits, event logging, recovery, and watchdogs;
- packaging and deployment as a Windows app;
- Windows-specific testing on an actual interactive desktop.

### Important distinction

The repository currently implements a **portable safety/coordinator core**, not a working Windows computer-use application.

This is explicitly stated in the repository README:

> “This repository intentionally ships a portable model-free foundation, not the complete Windows product described in `plan.md`.”

The repository also explicitly states that the coordinator:

- does not inject input;
- does not launch programs;
- does not browse;
- does not use Electron;
- does not process voice;
- does not claim verification.

The task therefore requires a substantial product implementation rather than a small bug fix.

### Required end state

A complete first release should implement the following bounded product contract:

- Windows 11 desktop application;
- one interactive desktop session;
- one physical desktop mutation in flight globally;
- same-integrity applications by default;
- Coordinator-owned permissions and state transitions;
- Windows UI Automation first;
- screenshot and keyboard/mouse fallback;
- Playwright for browser-owned workflows;
- explicit, isolated CDP only for agent-owned browser processes;
- deterministic verification before model-based verification;
- durable SQLite event logging;
- local IPC between desktop UI and coordinator;
- visible user confirmation for consequential actions;
- optional push-to-talk voice;
- no arbitrary shell/code execution;
- published supported-application matrix;
- explicit unsupported boundaries for UAC, credentials, MFA, secure desktop, and elevated applications.

---

## 2. Existing repository state and relevant file paths

### Verified repository metadata

Repository:

- URL: <https://github.com/anasalsawy/compuse>
- Default branch: `main`
- Language: Python
- Repository visibility: public
- Repository status: not archived
- Branches: only `main`
- Open issues: none returned
- Pull request lookup for PR 1: `404 Not Found`
- Repository creation date reported by GitHub: 2026-09-12
- Latest visible commit: `eb6c712f92e7edad1a3af3521decb19d1a76b4a7`
- Latest commit message: `feat: extend typed action protocol and normalize observations`

The GitHub repository metadata reports `open_issues_count: 0`.

### Current repository tree

```text
.github/
└── workflows/
    └── test.yml

LICENSE
README.md
plan.md
pyproject.toml

compuse/
├── __init__.py
├── coordinator/
│   ├── __init__.py
│   └── core.py
├── protocol/
│   ├── __init__.py
│   └── models.py
└── storage/
    ├── __init__.py
    └── events.py

docs/
├── final-execution-checklist.md
└── supported-capabilities.md

tests/
└── test_core.py
```

There is no verified implementation of:

- `desktop/`;
- Electron;
- React;
- Windows executor;
- UI Automation adapter;
- screen capture;
- display/DPI handling;
- browser integration;
- Playwright;
- voice;
- verification subsystem;
- recovery subsystem;
- IPC server;
- installer;
- Windows packaging;
- application launch registry;
- native Windows sidecar;
- end-to-end Windows tests.

### Current README

The README identifies the repository as:

> “a safety-first, local-first coordination core for a future Windows computer-use agent.”

It lists implemented features:

- strict Pydantic protocol models;
- observation and coordinate-space binding;
- expiring, single-use permits;
- Coordinator-owned policy checks;
- thread-safe in-process mutation boundary;
- SQLite WAL event journal;
- SHA-256 event hash chains;
- explicit rejection of environment content and provider output as authority.

It also states that the current code does **not**:

- inject input;
- launch programs;
- browse;
- use Electron;
- process voice;
- claim verification.

### `compuse/protocol/models.py`

The current protocol contains:

- `StrictModel`;
- `Origin`;
- `ActionKind`;
- typed action models;
- `Observation`;
- `ActionProposal`;
- `Permit`;
- `digest_action`;
- `now`.

Current action kinds include:

```text
wait
screenshot
mouse_move
type
click
double_click
drag
scroll
keypress
key_combo
window.focus
application.launch
```

Important current protocol properties:

- Pydantic models use `extra="forbid"`;
- strict model validation is enabled;
- actions are discriminated by `kind`;
- observations include:
  - run ID;
  - revision;
  - timestamp;
  - coordinate-space ID;
  - foreground window;
  - process ID;
  - Windows session ID;
  - input desktop;
- proposals bind actions to:
  - observation revision;
  - coordinate space;
  - policy revision;
  - tool;
  - optional capability hash;
  - optional launch/browser revisions;
  - optional window/process/session identity;
  - optional confirmation ID;
- permits contain an action digest and expiration.

### Current limitations in the protocol

The protocol is useful as a foundation, but it is incomplete for a production Windows app.

Missing or insufficient protocol concepts include:

- monitor origin and dimensions;
- physical DPI;
- display topology;
- screenshot artifact reference;
- screenshot hash;
- transform matrix;
- UIA tree hash;
- browser state reference;
- application integrity level;
- target HWND as a typed field;
- exact target process identity;
- permission scope;
- confirmation token binding;
- action risk classification;
- verification requirements;
- executor capability version;
- permit consumption count;
- recovery/unknown state;
- artifact provenance;
- redaction state;
- cancellation state;
- session ownership token.

### `compuse/coordinator/core.py`

The Coordinator currently:

- validates TTL;
- rejects `ENVIRONMENT_CONTENT`;
- rejects `PROVIDER_OUTPUT`;
- checks run ID and observation revision;
- checks coordinate-space ID;
- checks policy revision;
- issues in-memory permits;
- appends permit-issued events;
- consumes permits;
- enforces one active permit per Coordinator instance;
- rejects stale or mismatched proposals;
- releases the mutation boundary;
- removes expired permits.

This is a good model-free safety kernel.

### Critical Coordinator limitations

The current implementation does not provide:

1. **Durable permits**

   Permits are held in:

   ```python
   self._permits = {}
   ```

   A process restart loses all permits.

2. **Atomic durable permit consumption**

   The implementation marks the in-memory permit as consumed and then appends an event. The planned architecture requires durable atomic validation and consumption, conceptually:

   ```text
   BEGIN IMMEDIATE
       validate all bindings and current state
       increment uses
       append permit_consumed event
   COMMIT
   ```

3. **Persistent run/action state machines**

   No run-state or action-state tables exist.

4. **Post-action verification**

   `consume()` returns the action. It does not dispatch it, collect executor output, capture post-state, or verify the result.

5. **Unknown-state recovery**

   If an external action occurs and the process crashes, there is no reconciliation flow.

6. **Desktop-session locking**

   There is no OS-level mutex or durable lease.

7. **Cancellation/watchdog behavior**

   There is no cancellation token, emergency stop, watchdog, or stuck-action recovery.

8. **Policy engine**

   The current policy check is only a policy revision string and origin check.

9. **Confirmation enforcement**

   A `confirmation_id` exists in the model but is not validated by Coordinator logic.

10. **Exact binding completeness**

    The planned permit binding includes more fields than the current `Permit`, including exact arguments, capability revision, target process/window identity, and confirmation record.

### `compuse/storage/events.py`

The current event store:

- uses SQLite;
- enables foreign keys;
- sets busy timeout;
- sets `synchronous=FULL`;
- enables WAL for file-backed stores;
- stores:
  - run ID;
  - sequence;
  - event type;
  - JSON payload;
  - timestamp;
  - previous hash;
  - event hash;
- verifies the per-run hash chain.

This is one of the strongest parts of the current code.

### Event-store limitations

The event store still needs:

- schema migrations;
- explicit schema versioning;
- artifact manifest tables;
- action/run state tables;
- permit tables;
- confirmation tables;
- lease tables;
- checkpoint tables;
- retention policy;
- backup and restore handling that preserves `-wal` and `-shm`;
- protection against external database replacement;
- canonical artifact root enforcement;
- symlink/reparse-point checks;
- startup chain verification for all runs;
- integrity-failure behavior;
- durable event insertion integrated into Coordinator transactions.

The plan requires SQLite runtime verification. The repository itself does not currently enforce the required SQLite version.

### `docs/supported-capabilities.md`

This document is explicit:

| Capability | Status |
|---|---|
| Strict typed protocol | supported |
| Observation-bound permits | supported |
| Exact action/policy/coordinate binding | supported |
| Thread-safe mutation boundary | supported |
| SQLite hash-chain journal | supported |
| Windows UIA and input | planned |
| DPI/transforms/session safety | planned |
| Browser/Playwright/CDP isolation | planned |
| Electron renderer/main/IPC | planned |
| Voice, confirmation tokens, emergency stop | planned |
| Independent verification/recovery/watchdog | planned |
| Credentials, MFA, UAC, secure desktop | requires user intervention |
| Arbitrary shell/code execution | unsupported |

This is direct evidence that the repository is not currently a complete Windows computer-use app.

### `plan.md`

`plan.md` is the repository’s authoritative implementation specification. It describes:

- Electron renderer/main architecture;
- Python Coordinator;
- Python Windows executor;
- optional .NET UIA sidecar;
- verifier;
- storage;
- voice;
- strict typed protocol;
- state machines;
- permits;
- browser isolation;
- desktop-session locking;
- IPC security;
- supported-application matrix;
- packaging and testing.

The plan contains the intended target architecture, but most of the described directories do not yet exist.

### `tests/test_core.py`

The existing tests cover:

- permit issue/consume/release;
- untrusted origins;
- stale observations;
- mismatched action IDs;
- mutation boundary exclusivity;
- owner-only release;
- TTL validation;
- strict model validation;
- event tamper detection;
- empty event-chain verification.

These are valuable unit tests for the existing kernel.

They do not cover:

- Windows APIs;
- UI Automation;
- screen capture;
- input injection;
- DPI;
- multiple monitors;
- process/session identity;
- browser automation;
- Electron;
- IPC;
- voice;
- cancellation;
- crash recovery;
- verification;
- packaging;
- installation;
- end-to-end task execution.

### `.github/workflows/test.yml`

The CI workflow:

- runs on Ubuntu;
- tests Python 3.11, 3.12, and 3.13;
- installs `.[test]`;
- runs pytest with coverage;
- requires 80% coverage.

This is not enough for a Windows desktop product. A Windows CI job is required for:

- UIA;
- screen capture;
- input;
- Windows process/window behavior;
- packaging;
- installer validation.

Some Windows UI tests will require an interactive desktop and should not be assumed to work on ordinary headless CI runners.

### `pyproject.toml`

The raw-file retrieval for `pyproject.toml` returned an HTTP error in the tool output, so the exact dependency declarations could not be independently read from that call.

**NO DATA: the raw `pyproject.toml` fetch returned an HTTP error.**

The README says the project requires Python 3.11+ and can be installed with:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e '.[test]'
pytest -q
```

The implementation team must re-read and validate the actual `pyproject.toml` directly before changing dependencies.

---

## 3. Recommended architecture and implementation boundaries

The repository’s proposed architecture is appropriate, but it needs to be implemented in stages.

## Recommended runtime topology

```text
Electron Renderer
    React task UI
    confirmation UI
    live observations
    evidence viewer
    run/action state display

Electron Main
    IPC broker
    sender/origin validation
    lifecycle management
    confirmation broker
    emergency-stop forwarding

Python Coordinator
    authoritative state machine
    policy engine
    permit issuance/consumption
    scheduler
    watchdog
    recovery
    desktop-session lock
    SQLite writer
    executor orchestration

Windows Executor
    screenshot adapter
    display/DPI adapter
    UIA adapter
    semantic action adapter
    mouse/keyboard fallback
    window/process manager
    application launch registry
    clipboard manager
    cancellation cleanup

Verifier
    UIA verification
    browser/DOM verification
    file verification
    process/window verification
    optional visual verification

Browser subsystem
    Playwright persistent contexts
    isolated run profiles
    download directories
    optional agent-owned CDP

Voice subsystem
    push-to-talk capture
    speech-to-text
    confirmation parser
    TTS
    emergency stop outside model authority

Storage
    SQLite migrations
    events
    permits
    actions
    runs
    artifacts
    checkpoints
    leases
    confirmations

Packaging
    Electron/Windows packaging
    Python runtime bundling
    installer
    code signing
    migration handling
```

## Ownership boundaries

The following boundaries should be enforced:

| Capability | Owner |
|---|---|
| Create run | Coordinator |
| Accept user task | Main/Coordinator |
| Propose action | Strategist |
| Issue permit | Coordinator only |
| Consume permit | Coordinator only |
| Execute input | Windows Executor only |
| Write authoritative events | Coordinator/storage only |
| Verify action | Verifier |
| Render UI | Renderer |
| IPC validation | Electron Main |
| Emergency stop | Main + Coordinator + executor cleanup |
| Launch application | Coordinator through launch registry |
| Browser profile creation | Browser subsystem under Coordinator |
| Confirmation token creation | Coordinator |
| Confirmation display | Renderer |
| Confirmation acceptance | Main/Coordinator |

The Executor must never be able to bypass the Coordinator for mutation.

---

## 4. Required APIs, libraries, SDKs, tools, versions, configuration, and environment variables

## Windows screen capture

Microsoft’s official `Windows.Graphics.Capture` API provides:

- display capture;
- application-window capture;
- secure system picker UI;
- visible yellow capture border;
- `GraphicsCapturePicker`;
- `GraphicsCaptureItem`;
- `Direct3D11CaptureFramePool`;
- `GraphicsCaptureSession`;
- `FrameArrived`;
- `TryGetNextFrame`;
- capture support detection through `GraphicsCaptureSession.IsSupported()`.

Microsoft documents that:

- the capture API is for Windows desktop devices and Windows Mixed Reality;
- the user explicitly selects the display/window;
- WinUI 3 picker objects must be initialized with the owner HWND;
- capture frames must be disposed;
- frame buffers must be recreated when dimensions or devices change;
- capture work should not block the UI thread.

Recommended implementation:

- use a native Windows helper for `Windows.Graphics.Capture`;
- expose screenshot capture through a small Python-facing adapter;
- return:
  - PNG/JPEG artifact;
  - capture target;
  - HWND/display identity;
  - physical dimensions;
  - DPI;
  - timestamp;
  - coordinate-space ID;
  - hash;
  - capture mechanism;
  - crop/transform metadata.

Fallbacks may include:

- PrintWindow;
- BitBlt/screen DC;
- desktop duplication;
- a third-party native library.

Fallback behavior must be explicit, tested, and recorded in evidence. Do not silently treat a blank or stale frame as a valid observation.

## Windows input injection

Microsoft’s `SendInput` API synthesizes:

- keyboard input;
- mouse movement;
- mouse buttons.

The Microsoft documentation states:

- the function returns the number of successfully inserted events;
- zero indicates failure;
- the function is subject to UIPI;
- input can only be injected into applications at equal or lower integrity;
- return values do not explicitly identify UIPI as the failure reason;
- already-held keys can interfere;
- callers must clean up keys/buttons.

Recommended API wrapper:

```python
class InputInjector(Protocol):
    def move(self, x: int, y: int) -> InputResult: ...
    def click(self, x: int, y: int, button: MouseButton) -> InputResult: ...
    def drag(
        self,
        start: Point,
        end: Point,
        duration_ms: int,
    ) -> InputResult: ...
    def key_down(self, key: Key) -> InputResult: ...
    def key_up(self, key: Key) -> InputResult: ...
    def type_text(self, text: str) -> InputResult: ...
    def cleanup_pressed_inputs(self) -> None: ...
```

Every injection must:

1. validate interactive desktop state;
2. validate target window and foreground state;
3. validate integrity-level compatibility;
4. validate coordinates;
5. dispatch;
6. inspect return count;
7. capture post-state;
8. release all temporary input state;
9. return structured failure if any step is uncertain.

Do not use arbitrary model-supplied virtual-key names without a strict key map.

## UI Automation

Microsoft documentation identifies UI Automation as the appropriate Windows automation model for cross-process UI inspection and control.

The implementation should use a single primary abstraction. The repository plan correctly warns against competing ownership abstractions between libraries such as `uiautomation` and `pywinauto`.

Recommended interface:

```python
class WindowsUIAAdapter(Protocol):
    def list_windows(self) -> list[WindowInfo]: ...

    def inspect_window(
        self,
        hwnd: int,
        *,
        max_depth: int = 12,
        interactive_only: bool = False,
    ) -> UIATree: ...

    def find(
        self,
        target: ElementTarget,
        *,
        window: WindowIdentity,
    ) -> list[UIAElementRef]: ...

    def invoke(self, element: UIAElementRef) -> UIAActionResult: ...

    def set_value(
        self,
        element: UIAElementRef,
        value: str,
    ) -> UIAActionResult: ...

    def select(self, element: UIAElementRef) -> UIAActionResult: ...

    def expand(self, element: UIAElementRef) -> UIAActionResult: ...

    def collapse(self, element: UIAElementRef) -> UIAActionResult: ...

    def focus(self, element: UIAElementRef) -> UIAActionResult: ...

    def read_properties(
        self,
        element: UIAElementRef,
    ) -> UIAProperties: ...
```

Element resolution should score:

- AutomationId;
- RuntimeId;
- control type;
- normalized name;
- class name;
- ancestry;
- window identity;
- process identity;
- bounds;
- captured-tree identity.

Reject ambiguous matches rather than selecting the first match.

Use UIA semantic operations before physical input. Microsoft’s `winapp ui` documentation supports this design: UIA pattern operations are preferable where available, while physical input should be reserved for controls that cannot be driven semantically.

## DPI and coordinate handling

Microsoft documents that UI Automation bounds and clickable points use physical coordinates and that DPI awareness is required for correct results.

Required work:

- configure process DPI awareness in the application manifest;
- verify the effective DPI-awareness context at startup;
- record per-monitor DPI;
- record virtual desktop origin;
- support negative monitor coordinates;
- distinguish logical and physical coordinates;
- preserve transforms used to map model/image coordinates to physical pixels.

Recommended model:

```python
class CoordinateSpace(BaseModel):
    id: str
    origin_x: int
    origin_y: int
    width_px: int
    height_px: int
    image_width_px: int
    image_height_px: int
    dpi_x: int
    dpi_y: int
    scale_x: float
    scale_y: float
    crop_left: int
    crop_top: int
    letterbox_left: int
    letterbox_top: int
    source: Literal["desktop", "monitor", "window", "element"]
    screenshot_hash: str
```

Coordinate actions must be rejected if:

- the display topology changed;
- the target window moved;
- the DPI changed;
- the screenshot hash differs;
- the coordinate-space ID is stale;
- dimensions are invalid;
- crop/padding metadata is missing.

## Browser automation

Recommended:

- Playwright;
- dedicated persistent browser contexts;
- one browser profile per run;
- isolated download directories;
- explicit profile locking;
- browser process identity tracking;
- permission denial by default;
- allowlisted URLs;
- deterministic browser verification.

Browser policy should reject by default:

- `file:`;
- `data:`;
- `javascript:`;
- arbitrary local profile attachment;
- the user’s daily browser;
- unknown CDP endpoints;
- redirects outside the approved policy.

CDP should only attach to a browser process that Compuse launched and can identify by:

- process ID;
- profile directory;
- launch token;
- expected command-line arguments;
- expected debugging endpoint.

## Electron and UI

Recommended stack:

- Electron;
- React;
- TypeScript;
- context isolation;
- disabled Node integration in renderer;
- restrictive Content Security Policy;
- preload-only bridge;
- no direct filesystem or process access from renderer;
- navigation allowlist;
- window-open deny-by-default;
- permission request deny-by-default;
- strict IPC schemas.

Example renderer bridge shape:

```typescript
type CompuseBridge = {
  createRun(input: CreateRunInput): Promise<Run>;
  requestObservation(runId: string): Promise<Observation>;
  requestConfirmation(input: ConfirmationRequest): Promise<Confirmation>;
  cancelRun(runId: string): Promise<void>;
  emergencyStop(): Promise<void>;
  subscribeEvents(
    runId: string,
    listener: (event: CompuseEvent) => void,
  ): () => void;
};
```

Every main-process handler must validate:

- sender frame;
- sender origin;
- `webContents` identity;
- run ownership;
- schema;
- message size;
- rate limits;
- operation authorization.

## Local IPC

Recommended options:

1. Windows named pipe; or
2. loopback HTTP/WebSocket with a random per-launch token.

The IPC server must:

- bind only to local machine;
- use a random token;
- use constant-time token comparison;
- validate origin and client identity;
- reject oversized messages;
- rate-limit requests;
- bind lifecycle to the desktop application;
- expose no direct action-dispatch endpoint to untrusted clients.

Dangerous Coordinator operations should remain private and not be exposed through a public API surface.

## Voice

The repository plan specifies push-to-talk as the MVP.

Required properties:

- push-to-talk, not always-listening by default;
- partial transcripts never mutate;
- exact action-bound confirmation token;
- confirmation expires;
- confirmation is one-use;
- confirmation binds to exact action hash;
- TTS output must not be accepted as confirmation;
- voice replay must be tested;
- emergency stop must work independently of speech recognition.

The actual STT/TTS provider is not selected in the repository. This is an unresolved product decision.

## Storage and SQLite

The target plan requires:

- WAL;
- `foreign_keys=ON`;
- `busy_timeout`;
- `synchronous=FULL`;
- tested SQLite runtime;
- event hash chain;
- artifact manifests;
- root-restricted paths;
- reparse-point/symlink protection;
- startup verification.

Recommended tables:

```sql
runs (
    run_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    mode TEXT NOT NULL,
    policy_revision TEXT NOT NULL
);

actions (
    action_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    state TEXT NOT NULL,
    action_hash TEXT NOT NULL,
    proposal_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

permits (
    permit_id TEXT PRIMARY KEY,
    action_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    action_hash TEXT NOT NULL,
    observation_revision INTEGER NOT NULL,
    coordinate_space_id TEXT NOT NULL,
    policy_revision TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    consumed_at TEXT,
    use_count INTEGER NOT NULL DEFAULT 0,
    confirmation_id TEXT
);

observations (
    observation_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    coordinate_space_id TEXT NOT NULL,
    screenshot_hash TEXT,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

artifacts (
    artifact_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    origin TEXT NOT NULL,
    redaction_state TEXT NOT NULL,
    capture_metadata_json TEXT NOT NULL,
    retained_until TEXT
);

leases (
    lease_id TEXT PRIMARY KEY,
    device_id TEXT NOT NULL,
    windows_session_id INTEGER NOT NULL,
    user_name TEXT NOT NULL,
    input_desktop TEXT NOT NULL,
    owner_token_hash TEXT NOT NULL,
    heartbeat_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

events (
    run_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    type TEXT NOT NULL,
    payload TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    previous_event_hash TEXT NOT NULL,
    event_hash TEXT NOT NULL,
    PRIMARY KEY (run_id, seq)
);
```

---

## 5. Concrete code patterns, function signatures, schemas, commands, and integration details

## Add an executor abstraction

The current package has no executor. Add:

```text
compuse/
├── executor/
│   ├── __init__.py
│   ├── base.py
│   ├── windows.py
│   ├── models.py
│   ├── screenshot.py
│   ├── uia.py
│   ├── input.py
│   ├── windows.py
│   ├── process.py
│   ├── display.py
│   ├── clipboard.py
│   └── cancellation.py
```

Example:

```python
class Executor(Protocol):
    def observe(self, request: ObservationRequest) -> ObservationResult: ...
    def execute(
        self,
        action: Action,
        *,
        permit: Permit,
        observation: Observation,
        cancellation: CancellationToken,
    ) -> ExecutionResult: ...
    def emergency_stop(self) -> None: ...
```

## Add a post-action lifecycle

The current lifecycle ends at permit consumption. It should become:

```python
async def execute_action(
    coordinator: Coordinator,
    proposal: ActionProposal,
    observation: Observation,
) -> ActionOutcome:
    permit = await coordinator.issue(proposal, observation)

    await coordinator.transition(
        proposal.action_id,
        ActionState.PERMITTED,
    )

    action = await coordinator.consume(
        permit.permit_id,
        proposal,
        observation,
    )

    try:
        result = await executor.execute(
            action,
            permit=permit,
            observation=observation,
            cancellation=cancellation,
        )

        await coordinator.transition(
            proposal.action_id,
            ActionState.EXECUTOR_RETURNED,
        )

        post_observation = await executor.observe(
            ObservationRequest.for_action(proposal.action_id)
        )

        verification = await verifier.verify(
            proposal=proposal,
            pre=observation,
            execution=result,
            post=post_observation,
        )

        if verification.success:
            await coordinator.transition(
                proposal.action_id,
                ActionState.VERIFIED,
            )
        else:
            await coordinator.transition(
                proposal.action_id,
                ActionState.FAILED,
            )

        return ActionOutcome(
            execution=result,
            post_observation=post_observation,
            verification=verification,
        )

    except UnknownExecutionState:
        await coordinator.transition(
            proposal.action_id,
            ActionState.UNKNOWN,
        )
        return await recovery.reconcile(proposal.action_id)

    finally:
        await coordinator.release(permit.permit_id)
```

## Add run and action state enums

```python
class RunState(StrEnum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    TASK_ACCEPTED = "TASK_ACCEPTED"
    PLANNING = "PLANNING"
    PLAN_REVIEW = "PLAN_REVIEW"
    WAITING_FOR_USER = "WAITING_FOR_USER"
    READY_TO_EXECUTE = "READY_TO_EXECUTE"
    ACTION_REVIEW = "ACTION_REVIEW"
    WAITING_FOR_CONFIRMATION = "WAITING_FOR_CONFIRMATION"
    ACTION_EXECUTING = "ACTION_EXECUTING"
    VERIFYING = "VERIFYING"
    CHECKPOINTED = "CHECKPOINTED"
    RECOVERY = "RECOVERY"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    PAUSED = "PAUSED"
    ABORTED = "ABORTED"
```

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

Only the Coordinator should perform transitions.

## Add structured executor results

```python
class ExecutionStatus(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    UNKNOWN = "unknown"
    CANCELLED = "cancelled"
```

```python
class ExecutionResult(StrictModel):
    status: ExecutionStatus
    mechanism: str
    started_at: datetime
    finished_at: datetime
    target_window: WindowIdentity | None = None
    target_process: ProcessIdentity | None = None
    warnings: tuple[str, ...] = ()
    error_code: str | None = None
    error_message: str | None = None
    evidence_ids: tuple[str, ...] = ()
```

## Add risk and confirmation schemas

```python
class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
```

```python
class ConfirmationRequest(StrictModel):
    confirmation_id: UUID
    run_id: str
    action_id: str
    action_hash: str
    risk: RiskLevel
    phrase: str
    expires_at: datetime
    one_use: bool = True
```

The user should confirm the exact phrase, not a generic “yes”.

## Add application launch registry

```python
class LaunchTarget(StrictModel):
    target_id: str
    display_name: str
    executable: str
    arguments: tuple[str, ...] = ()
    working_directory: str | None = None
    expected_process_names: tuple[str, ...]
    expected_window_patterns: tuple[str, ...]
    allowed_hashes: tuple[str, ...] = ()
    publisher: str | None = None
```

The model should only choose:

```json
{
  "target_id": "notepad"
}
```

It must never provide arbitrary executable paths or shell strings.

## Add Windows session identity checks

```python
class DesktopIdentity(StrictModel):
    windows_session_id: int
    user_name: str
    input_desktop: str
    integrity_level: str
    foreground_hwnd: int | None
    foreground_pid: int | None
```

Before focus-dependent actions:

```python
def validate_focus_target(
    expected: WindowIdentity,
    actual: DesktopIdentity,
) -> None:
    if actual.windows_session_id != expected.session_id:
        raise FocusMismatch("session mismatch")
    if actual.input_desktop != expected.input_desktop:
        raise FocusMismatch("input desktop mismatch")
    if actual.foreground_hwnd != expected.hwnd:
        raise FocusMismatch("foreground window mismatch")
    if actual.foreground_pid != expected.process_id:
        raise FocusMismatch("foreground process mismatch")
```

## Add Windows commands for development

The plan recommends the following initial setup:

```powershell
git clone https://github.com/anasalsawy/compuse.git
cd compuse

py -m venv .venv
.\\.venv\\Scripts\\Activate.ps1

python -m pip install --upgrade pip
pip install uv

uv sync --locked
npm ci

python -c "import sqlite3; print(sqlite3.sqlite_version)"
```

For browser support:

```powershell
python -m playwright install chromium
```

Current repository state does not verify that `uv.lock`, `package.json`, or `package-lock.json` exist. They are described in `plan.md`, but they are absent from the verified repository tree. They must be added or the plan must be revised.

---

## 6. Testing, validation, error handling, security, and deployment requirements

## Testing layers

### Unit tests

Continue testing:

- strict schemas;
- origin restrictions;
- action digest stability;
- permit binding;
- TTL;
- event-chain tamper detection;
- state transitions;
- confirmation token rules;
- path restrictions;
- URL restrictions;
- redaction state;
- coordinate transforms.

Add tests for:

- durable permits;
- duplicate requests;
- atomic consumption;
- transaction rollback;
- action hash mismatch;
- policy revision mismatch;
- executor capability mismatch;
- stale screenshot;
- stale coordinate space;
- stale HWND;
- stale process ID;
- session mismatch;
- integrity mismatch;
- expired confirmation;
- repeated confirmation;
- crash recovery;
- unknown side effects.

### Windows integration tests

Use a dedicated Windows test environment containing:

- Notepad;
- a Win32 test app;
- a WinForms test app;
- a WPF test app;
- a WinUI 3 test app;
- an Electron test app;
- a Qt test app;
- Chromium/Edge;
- WebView2;
- a test app with known controls and AutomationIds.

Test:

- window enumeration;
- UIA tree inspection;
- `InvokePattern`;
- `ValuePattern`;
- selection;
- expand/collapse;
- focus;
- screenshot capture;
- input injection;
- target window validation;
- process identity;
- foreground handling;
- cancellation;
- held-key cleanup.

### DPI and multi-monitor tests

Required matrix:

- 100% DPI;
- 125% DPI;
- 150% DPI;
- 200% DPI;
- one monitor;
- two monitors;
- monitor left of primary;
- monitor above primary;
- mixed DPI;
- window moved between monitors;
- display attach/detach;
- resolution change;
- scaling change while app is running.

Assertions:

- screenshot and UIA coordinates agree;
- clicks land on the intended target;
- stale coordinate-space actions are rejected;
- negative virtual coordinates are handled;
- crop and letterbox transforms are correct.

### Secure desktop and privilege tests

Test and explicitly classify:

- ordinary medium-integrity app;
- elevated high-integrity app;
- UAC prompt;
- Windows Hello;
- credential dialog;
- locked workstation;
- secure desktop;
- unknown input desktop;
- RDP session;
- disconnected RDP session.

Expected behavior for unsupported/high-risk cases:

- pause;
- return a typed `requires_user_intervention` outcome;
- do not claim success;
- do not retry blindly;
- do not attempt to bypass Windows security.

Microsoft states that:

- `SendInput` is subject to UIPI;
- UIAccess has strict signing and secure-installation requirements;
- UIAccess does not grant access to system-integrity UI;
- UAC and secure-desktop automation should not be treated as ordinary desktop automation.

### Browser tests

Test:

- isolated profiles;
- profile locking;
- run-specific downloads;
- permission denial;
- URL allowlists;
- redirects;
- download hashes;
- process identity;
- explicit CDP attachment;
- rejection of the user’s daily profile;
- browser process crash;
- browser restart;
- stale browser references.

### IPC and Electron security tests

Test:

- invalid sender;
- wrong origin;
- stale token;
- wrong run ownership;
- oversized messages;
- malformed payload;
- replayed confirmation;
- unauthorized action dispatch;
- renderer navigation;
- `window.open`;
- permission prompts;
- preload bridge exposure;
- renderer compromise assumptions.

### Voice tests

Test:

- partial transcript;
- final transcript;
- replayed phrase;
- TTS echo;
- confirmation expiry;
- confirmation for altered action;
- microphone failure;
- STT outage;
- emergency stop while STT is unavailable.

### Crash and recovery tests

Inject process termination at:

- before permit issue;
- after permit issue;
- during transaction;
- after permit consumption;
- before physical dispatch;
- during input;
- after physical dispatch;
- before post-observation;
- during verification;
- after unknown state.

The application must never blindly repeat an action whose physical outcome is uncertain.

## Error-handling requirements

Every failure should include:

```python
class CompuseError(StrictModel):
    code: str
    message: str
    retryable: bool
    requires_user_intervention: bool
    state: str
    evidence_ids: tuple[str, ...] = ()
```

Recommended error codes:

```text
stale_observation
stale_coordinate_space
target_not_found
target_ambiguous
window_mismatch
process_mismatch
session_mismatch
integrity_mismatch
input_desktop_mismatch
no_interactive_desktop
uipi_blocked
send_input_failed
capture_unsupported
capture_device_lost
uia_pattern_unavailable
browser_profile_locked
browser_not_agent_owned
confirmation_required
confirmation_expired
confirmation_replayed
permit_expired
permit_consumed
permit_binding_mismatch
unknown_execution_state
event_integrity_failure
ipc_unauthorized
launch_target_not_allowed
```

## Security requirements

The system controls a real desktop. Its threat model must include:

- malicious webpage content;
- malicious document content;
- clipboard injection;
- prompt injection;
- compromised provider output;
- compromised renderer;
- stale permit replay;
- database tampering;
- artifact substitution;
- voice replay;
- wrong foreground window;
- wrong input desktop;
- browser profile compromise;
- credential exposure.

Non-negotiable controls:

- environment content is data, never authority;
- provider output is data, never authority;
- no arbitrary shell execution;
- no model-generated executable paths;
- no user daily browser CDP attachment;
- no credential or MFA automation;
- no claims of success without verification;
- no blind retries after uncertainty;
- no permit reuse;
- no remote exposure without authentication;
- no sensitive artifacts transmitted when redaction is unknown;
- emergency stop outside the model loop.

## Packaging and deployment

### Windows package

The repository currently has no packaging implementation. The target should select one:

- MSIX;
- signed NSIS installer;
- Windows App SDK package;
- Electron Forge/Builder output wrapped in an installer.

For the first release, a practical architecture is:

- Electron desktop shell;
- bundled Python runtime or packaged Python Coordinator;
- Windows native helper binaries;
- isolated application data directory;
- per-user logs and artifacts;
- migration runner;
- signed installer.

### Signing

Microsoft’s MSIX documentation states:

- deployable MSIX packages must be signed;
- the signing certificate must be trusted by the device;
- development can use a self-signed certificate;
- production can use Azure Artifact Signing or an OV certificate;
- timestamping is highly recommended;
- package integrity enforcement is available through package manifest configuration.

Required deployment work:

- development certificate generation;
- production certificate strategy;
- timestamping;
- certificate rotation;
- CI secret handling;
- SmartScreen expectations;
- package integrity;
- upgrade/migration tests;
- uninstall behavior;
- rollback behavior.

### UIAccess caution

Microsoft states that UIAccess requires:

- a legitimate assistive-technology scenario;
- Authenticode signing;
- secure installation location;
- manifest `uiAccess="true"`;
- administrator-related conditions.

Compuse should not enable UIAccess merely to bypass normal Windows security restrictions. The product contract should remain same-integrity by default, with elevated applications classified as unsupported or user-intervention-required unless a separately reviewed accessibility design justifies UIAccess.

---

## 7. Risks, compatibility concerns, and likely failure points

## High-risk technical areas

### 1. The current repository is not a Windows app

The core is portable Python. It has no UI, no executor, and no Windows integration.

### 2. Screen capture consent and reliability

Windows Graphics Capture uses user consent and visible capture indication. Device loss, resize, HDR, and frame lifetime require careful handling.

### 3. UIPI and integrity levels

`SendInput` can fail across integrity boundaries. A zero return value does not clearly identify UIPI as the cause.

### 4. DPI errors

Incorrect DPI awareness can produce clicks that are visually plausible but physically wrong.

### 5. UIA inconsistency

Different applications expose different controls and patterns:

- Win32;
- WPF;
- WinForms;
- WinUI;
- Electron;
- Qt;
- browser surfaces;
- custom-drawn controls.

No universal UIA behavior should be assumed.

### 6. Foreground and focus races

Another process can steal focus between validation and input dispatch.

### 7. Verification false positives

An executor returning successfully does not prove that the action produced the desired state.

### 8. Unknown physical side effects

A process crash after input dispatch can leave the desktop changed with no durable success record.

### 9. Renderer compromise

Electron renderers must not possess direct authority to issue permits or dispatch actions.

### 10. Browser-profile leakage

Attaching to the user’s normal browser can expose credentials, cookies, private tabs, and sensitive pages.

### 11. Artifact sensitivity

Screenshots may contain passwords, personal data, tokens, and private communications. Redaction must be explicit and failure-aware.

### 12. Voice replay and TTS echo

A voice confirmation path can accidentally confirm its own spoken prompt or accept replayed audio.

### 13. Packaging complexity

A complete desktop app must package:

- Electron;
- Python;
- native helper(s);
- browser assets;
- certificates;
- migrations;
- update logic.

### 14. CI limitations

Interactive desktop automation generally cannot be validated fully on ordinary headless CI runners. A Windows interactive test harness is required.

## Compatibility concerns

- Windows version and build must be declared.
- Python version must be supported and pinned.
- SQLite version must be verified.
- Playwright browser versions must be pinned.
- Windows App SDK and WinUI dependencies must be pinned if used.
- Native helpers require architecture decisions: x64 first, possibly ARM64 later.
- RDP behavior must be separately tested.
- HDR capture needs explicit handling.
- UAC and secure desktop must not be treated as ordinary UI.
- Multi-monitor mixed-DPI behavior must be tested.
- Electron sandbox compatibility with native helpers must be tested.

---

## 8. Missing information, assumptions, unresolved questions, and unknowns

## Missing information

### Exact dependency configuration

The `pyproject.toml` fetch failed in the investigation tool.

**NO DATA: the raw `pyproject.toml` fetch returned an HTTP error.**

The exact dependency list, package metadata, and test extras must be verified locally.

### Windows test environment

No `winmcp-7e6c6443#run_powershell` connection was available through the provided tools. Therefore:

- the app was not run;
- PowerShell commands were not executed;
- Windows APIs were not tested;
- screenshots were not captured;
- UI Automation was not exercised;
- packaging was not validated;
- no end-to-end Windows result can be claimed.

### Current GitHub repository issues

GitHub returned no repository issues.

**NO DATA: repository issues returned none.**

This does not prove that no work is needed; it only means no issues were returned.

### Pull request status

A request for pull request 1 returned `404 Not Found`.

**NO DATA: pull request 1 does not exist or is not accessible.**

### Actual Windows-side implementation

The verified tree contains no Windows executor or desktop application. `plan.md` describes these components, but they are not present.

### Model/provider choice

The repository does not define:

- an LLM provider;
- API endpoint;
- model;
- authentication mechanism;
- rate limits;
- cost controls;
- prompt format;
- model computer-use protocol.

This must remain an adapter boundary rather than being hard-coded into the safety core.

### Voice provider

No STT/TTS provider is selected.

### Product UI design

The desired user experience, accessibility requirements, branding, and task interaction model are unspecified.

### Distribution model

Unknown:

- Microsoft Store;
- direct signed installer;
- enterprise deployment;
- portable development package;
- managed organization deployment.

## Assumptions

The following are recommendations or assumptions, not verified repository facts:

1. Windows 11 is the primary target.
2. x64 is the first release architecture.
3. Electron is acceptable for the desktop UI.
4. Python remains the Coordinator language.
5. UIA-first automation is preferred to screenshot-only automation.
6. Same-integrity automation is the default.
7. Shell execution remains permanently unsupported.
8. Browser automation uses Playwright.
9. A model/provider will be integrated behind a typed strategist interface.
10. A dedicated Windows native helper may be required for screen capture and robust UIA/input behavior.

## Unresolved product decisions

- Which LLM/provider will be supported?
- Is the app local-only or does it communicate with a remote model?
- What data may leave the machine?
- Is offline operation required?
- Which applications are in the initial supported matrix?
- Is UIAccess permitted?
- Is browser automation part of MVP or post-MVP?
- Which STT/TTS provider is acceptable?
- Is voice required for first release?
- Is an interactive Windows CI machine available?
- Which packaging format is required?
- Who owns signing certificates?
- How are updates delivered?
- What is the retention period for screenshots and event logs?
- What actions require visible confirmation?
- What is the emergency-stop keyboard shortcut?
- What is the recovery behavior for uncertain actions?

---

## 9. Practical implementation sequence for builders

## Phase 0 — Establish the build baseline

1. Re-read `pyproject.toml` locally.
2. Confirm Python version and test extras.
3. Decide whether to use `uv`.
4. Add lock files if they are part of the chosen workflow.
5. Define Windows 11 minimum build.
6. Define x64/ARM64 scope.
7. Add a Windows development setup document.
8. Add a supported-application matrix template.
9. Establish a disposable Windows test machine.
10. Never use production credentials during testing.

## Phase 1 — Strengthen the protocol

1. Extend observations with:
   - monitor metadata;
   - DPI;
   - screenshot artifacts;
   - transform metadata;
   - UIA tree hash;
   - browser state;
   - integrity level;
   - HWND.
2. Add run and action states.
3. Add risk levels.
4. Add confirmation requests.
5. Add typed errors.
6. Add executor capability hashes.
7. Add artifact provenance.
8. Add redaction state.
9. Add cancellation state.
10. Add explicit unknown execution state.

## Phase 2 — Make permits durable

1. Add a `permits` table.
2. Move permit issuance into SQLite.
3. Implement `BEGIN IMMEDIATE`.
4. Validate and consume permits atomically.
5. Bind permits to:
   - exact action hash;
   - run;
   - observation;
   - coordinate space;
   - policy;
   - target window/process/session;
   - capability hash;
   - launch/browser revision;
   - confirmation.
6. Ensure permits are single-use.
7. Ensure process restart does not recreate permits.
8. Add duplicate-request idempotency.

## Phase 3 — Implement Windows observation

1. Add a Windows executor package.
2. Implement process/session identity.
3. Implement foreground window inspection.
4. Implement display enumeration.
5. Implement DPI detection.
6. Configure DPI awareness in the manifest.
7. Implement screenshot capture.
8. Prefer Windows Graphics Capture.
9. Add explicit fallback mechanisms.
10. Store screenshot hashes and transforms.
11. Add topology-change invalidation.

## Phase 4 — Implement UI Automation

1. Select one primary UIA library or build a native helper.
2. Implement a language-neutral adapter.
3. Implement window enumeration.
4. Implement tree inspection.
5. Implement AutomationId/RuntimeId targeting.
6. Implement ambiguity rejection.
7. Implement semantic `invoke`.
8. Implement semantic `set_value`.
9. Implement select/expand/collapse/focus.
10. Re-resolve targets immediately before mutation.
11. Capture post-action UIA state.

## Phase 5 — Implement physical input fallback

1. Implement safe `SendInput` bindings.
2. Implement mouse movement and clicks.
3. Implement drag.
4. Implement key press and key combinations.
5. Implement text entry.
6. Track pressed keys/buttons.
7. Add cleanup on:
   - cancellation;
   - exception;
   - timeout;
   - process shutdown.
8. Validate foreground target immediately before injection.
9. Reject wrong integrity/session/input desktop.
10. Record the injection mechanism and result.

## Phase 6 — Implement launch registry

1. Add approved launch targets.
2. Add canonical path validation.
3. Add publisher/hash validation.
4. Add expected process/window matching.
5. Use argument arrays.
6. Use `shell=False`.
7. Reject model-supplied executable paths.
8. Add launch policy revision.
9. Add launch verification.

## Phase 7 — Implement verification

1. Build deterministic UIA verifier.
2. Build browser/DOM verifier.
3. Build process/window verifier.
4. Build file/download verifier.
5. Build notification verifier.
6. Add optional visual verifier.
7. Make `VERIFIED` the only normal success state.
8. Store verification evidence.
9. Record provider/model/prompt dimensions for model verification.
10. Add false-success tests.

## Phase 8 — Implement recovery and concurrency safety

1. Add Windows named mutex.
2. Add durable SQLite lease.
3. Add heartbeat.
4. Add stale-lease recovery.
5. Add watchdog.
6. Add cancellation token.
7. Add emergency stop.
8. Add crash reconciliation.
9. Add checkpointing.
10. Ensure uncertain actions are reconciled, not replayed blindly.

## Phase 9 — Implement browser isolation

1. Add Playwright.
2. Create run-specific profiles.
3. Lock profiles.
4. Isolate downloads.
5. Deny permissions by default.
6. Validate URLs and redirects.
7. Track browser process identity.
8. Add explicit agent-owned CDP.
9. Reject user-profile attachment.
10. Add browser crash recovery.

## Phase 10 — Implement Electron desktop app

1. Add Electron main process.
2. Add React renderer.
3. Add preload bridge.
4. Enable context isolation.
5. Disable renderer Node integration.
6. Add strict CSP.
7. Add navigation allowlist.
8. Add IPC schema validation.
9. Add run ownership checks.
10. Add live event streaming.
11. Add confirmation UI.
12. Add evidence viewer.
13. Add emergency-stop control.

## Phase 11 — Implement voice and confirmations

1. Add push-to-talk.
2. Select and document STT provider.
3. Select and document TTS provider.
4. Ensure partial transcripts cannot mutate.
5. Generate random confirmation phrases.
6. Bind confirmations to exact action hashes.
7. Expire and consume confirmations.
8. Disable voice-only confirmation for high-risk operations by default.
9. Add replay/echo tests.
10. Implement emergency stop outside the model loop.

## Phase 12 — Add model integration

1. Define `Strategist` interface.
2. Validate all provider output strictly.
3. Treat provider output as untrusted.
4. Convert provider output into proposals only.
5. Never allow provider output to directly dispatch actions.
6. Restrict action vocabulary.
7. Add prompt-injection tests.
8. Add task cancellation.
9. Add step budget.
10. Add no-progress detection.

## Phase 13 — Package and deploy

1. Choose Electron packaging tool.
2. Bundle Python Coordinator.
3. Bundle native Windows helpers.
4. Bundle or install Playwright browsers.
5. Add migrations.
6. Add per-user data directory.
7. Add logs and retention.
8. Create development-signed package.
9. Add production signing.
10. Add timestamping.
11. Add package-integrity settings.
12. Add upgrade/uninstall tests.
13. Add release CI.
14. Publish supported Windows versions and limitations.

## Phase 14 — Acceptance test

The first complete vertical slice should be model-free:

```text
capture observation
→ acquire desktop-session lock
→ propose allowlisted Notepad action
→ issue permit
→ consume permit atomically
→ execute UIA set-value
→ capture post-observation
→ verify text value
→ append event chain
→ display result in desktop UI
```

Acceptance criteria:

- Notepad is launched only through the allowlist;
- target HWND/PID/session are recorded;
- UIA target is resolved unambiguously;
- permit is bound to the observation;
- one-use consumption is durable;
- text is set through a semantic UIA operation;
- post-state is captured;
- verification succeeds only from independent evidence;
- all events are persisted;
- event hash chain verifies after restart;
- a crash does not cause blind replay.

---

# Final conclusion

`anasalsawy/compuse` is a small but meaningful safety foundation. It is not currently a complete Windows computer-use app.

The verified implementation covers:

- typed action and observation models;
- origin separation;
- observation-bound permits;
- a thread-safe mutation boundary;
- tamper-evident SQLite events;
- unit tests for those facilities.

The verified implementation is missing essentially every Windows product layer:

- Windows capture;
- UI Automation;
- input injection;
- DPI and display handling;
- window/process/session safety;
- application launch;
- browser isolation;
- independent verification;
- crash recovery;
- watchdogs;
- durable permits;
- desktop-session locks;
- Electron UI;
- secure IPC;
- voice;
- confirmation UX;
- packaging;
- signing;
- Windows end-to-end testing.

The correct implementation strategy is to preserve the existing safety core, expand it into a durable Coordinator, then add a Windows executor and verifier before integrating a model or desktop UI. The first release should remain deliberately narrow: same-integrity Windows applications, UIA-first interaction, isolated browser sessions, explicit user confirmation, deterministic verification, and no arbitrary shell, credential, MFA, UAC, or secure-desktop automation.

----------

# Implementation Plan: Complete `anasalsawy/compuse` into a Windows Computer-Use Desktop Application

## Quick Start

The builder must begin by establishing the local build baseline before implementing Windows functionality.

### First actions

1. Clone the repository and inspect the current branch:

   ```powershell
   git clone https://github.com/anasalsawy/compuse.git
   cd compuse
   git status
   git log -1 --oneline
   ```

2. Re-read the actual `pyproject.toml` locally. The research tool could not retrieve it, so dependency declarations, package metadata, and test extras are not independently verified.

3. Create and activate a Python environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   ```

4. Install the existing project and tests using the repository’s documented command:

   ```powershell
   python -m pip install -e '.[test]'
   pytest -q
   ```

5. Verify the runtime versions before changing dependencies:

   ```powershell
   python --version
   python -c "import sqlite3; print(sqlite3.sqlite_version)"
   ```

6. Determine whether the repository already contains JavaScript files, lock files, or packaging files. The research report verified no such files in the current tree, although `plan.md` describes Electron files that do not yet exist.

7. Establish a dedicated Windows 11 test machine with an interactive desktop. Do not use production credentials, the user’s daily browser profile, or sensitive files during development.

8. Implement the first vertical slice before adding model or voice integration:

   ```text
   capture observation
   → acquire desktop-session lock
   → launch allowlisted Notepad target
   → resolve target through UI Automation
   → issue and atomically consume permit
   → perform one semantic UIA action
   → capture post-action state
   → verify the result
   → append events
   → expose result to the desktop UI
   ```

9. Do not claim Windows functionality, packaging, or end-to-end success until it has been executed on an interactive Windows environment.

---

## Requirements

## Functional requirements

The completed application must provide:

1. A Windows desktop application for one interactive desktop session.
2. Screen and window observation.
3. Windows UI Automation inspection and semantic control.
4. Mouse and keyboard fallback input.
5. Allowlisted application launching.
6. Isolated browser automation using Playwright.
7. Explicit CDP support only for browser processes launched and owned by Compuse.
8. A Coordinator-controlled plan/act/observe/verify loop.
9. Deterministic post-action verification before any model-based verification.
10. Durable SQLite state, permits, artifacts, and event logs.
11. Local authenticated IPC between the desktop UI and Coordinator.
12. Visible user confirmation for consequential actions.
13. Optional push-to-talk voice support behind a provider adapter.
14. Cancellation, emergency stop, watchdog, and recovery behavior.
15. Windows packaging and installation.
16. A published supported-application matrix.
17. Explicit handling of unsupported cases including:
    - credentials;
    - MFA;
    - UAC;
    - secure desktop;
    - locked workstation;
    - elevated applications;
    - arbitrary shell or code execution.

## Technical requirements

The implementation must:

- preserve the current typed protocol approach;
- preserve strict Pydantic validation with forbidden extra fields;
- keep environment content and provider output as untrusted data;
- keep permit issuance and consumption under Coordinator control;
- preserve the SQLite event hash chain;
- make permits durable and atomically consumable;
- bind each action to an observation and exact execution context;
- reject stale observations, stale coordinate spaces, stale windows, stale processes, and stale sessions;
- support physical display coordinates, per-monitor DPI, negative monitor coordinates, and topology changes;
- use UI Automation before physical input whenever a semantic control is available;
- prevent the renderer from directly dispatching desktop actions;
- isolate browser profiles and downloads per run;
- prevent arbitrary executable paths and shell strings from being generated by a model;
- make verification evidence explicit and durable;
- fail closed when execution state is uncertain.

## Operational requirements

The application must:

- run only against an interactive Windows desktop;
- operate at same integrity by default;
- expose a visible emergency-stop control;
- stop or pause safely when the desktop session changes;
- avoid blind retries after uncertain physical input;
- record warnings and failures in durable events;
- preserve database integrity across restarts;
- define log and artifact retention;
- document supported Windows versions, architectures, and applications;
- provide an installation, upgrade, rollback, and uninstall procedure.

## Acceptance requirements

A first complete vertical slice is accepted only when it can:

1. Launch an approved Notepad target without arbitrary shell execution.
2. Record target process, window, session, and input desktop identity.
3. Capture a valid observation with screenshot and coordinate metadata.
4. Resolve an unambiguous UIA target.
5. Issue a permit bound to the exact action and observation.
6. Consume the permit exactly once through a durable transaction.
7. Execute a semantic UIA operation.
8. Capture post-action state.
9. Verify the expected result using independent evidence.
10. Persist all lifecycle events.
11. Verify the event hash chain after application restart.
12. Avoid repeating the action after an injected crash at an uncertain point.

---

## Current State

## Existing repository

The verified repository contains:

```text
.github/
└── workflows/
    └── test.yml

LICENSE
README.md
plan.md
pyproject.toml

compuse/
├── __init__.py
├── coordinator/
│   ├── __init__.py
│   └── core.py
├── protocol/
│   ├── __init__.py
│   └── models.py
└── storage/
    ├── __init__.py
    └── events.py

docs/
├── final-execution-checklist.md
└── supported-capabilities.md

tests/
└── test_core.py
```

The repository is currently a portable Python safety/coordinator foundation. The README explicitly states that it is not the complete Windows product.

## Existing protocol

`compuse/protocol/models.py` already provides:

- strict Pydantic models;
- `Origin`;
- typed action models;
- `Observation`;
- `ActionProposal`;
- `Permit`;
- action digesting;
- timestamps;
- observation revision and coordinate-space binding;
- policy revision binding;
- optional launch/browser revisions;
- optional window/process/session identity;
- optional confirmation ID.

These models should be extended rather than replaced.

## Existing Coordinator

`compuse/coordinator/core.py` currently provides:

- TTL validation;
- rejection of `ENVIRONMENT_CONTENT`;
- rejection of `PROVIDER_OUTPUT`;
- run ID checking;
- observation revision checking;
- coordinate-space checking;
- policy revision checking;
- in-memory permit issuance;
- permit consumption;
- one active permit per Coordinator instance;
- stale or mismatched proposal rejection;
- mutation-boundary release;
- expired permit cleanup.

This is the safety foundation and must be preserved.

## Existing storage

`compuse/storage/events.py` provides:

- SQLite storage;
- foreign keys;
- busy timeout;
- `synchronous=FULL`;
- WAL for file-backed databases;
- per-run event sequencing;
- JSON event payloads;
- previous hash and event hash;
- hash-chain verification.

This implementation should remain the basis for durable storage, but must gain migrations and transactional state tables.

## Existing tests

`tests/test_core.py` covers:

- permit issuance and consumption;
- permit release;
- untrusted origins;
- stale observations;
- mismatched action IDs;
- mutation-boundary exclusivity;
- owner-only release;
- TTL validation;
- strict model validation;
- event tamper detection;
- empty event-chain verification.

These tests must continue passing.

## Existing CI

`.github/workflows/test.yml` currently:

- runs on Ubuntu;
- tests Python 3.11, 3.12, and 3.13;
- installs `.[test]`;
- runs pytest with coverage;
- requires 80% coverage.

This is insufficient for Windows desktop automation. A Windows job and an interactive Windows test environment are required.

## Missing systems

The repository does not currently contain verified implementations for:

- Windows screen capture;
- Windows UI Automation;
- physical input;
- DPI or display handling;
- process/window/session inspection;
- application launching;
- browser automation;
- Playwright;
- CDP isolation;
- verification;
- recovery;
- watchdogs;
- durable permits;
- run/action state machines;
- desktop-session locking;
- Electron;
- React;
- IPC;
- voice;
- installer;
- signing;
- Windows end-to-end tests;
- native Windows helper binaries.

`plan.md` describes many of these systems, but the described directories and components are not present in the verified tree.

---

## Implementation Design

## Runtime topology

```text
Electron Renderer
    React task interface
    confirmation interface
    run/action status
    observation and evidence display
    emergency-stop control

Electron Main
    preload bridge
    IPC validation
    sender/origin validation
    lifecycle management
    confirmation broker
    emergency-stop forwarding

Python Coordinator
    run and action state machines
    policy engine
    durable permits
    scheduler
    watchdog
    desktop lease
    recovery
    SQLite event/state writer
    executor orchestration

Windows Executor
    screenshot adapter
    display/DPI adapter
    UIA adapter
    input adapter
    process/window/session adapter
    application launch registry
    clipboard manager
    cancellation cleanup

Verifier
    UIA verification
    browser/DOM verification
    process/window verification
    file/download verification
    optional visual verification

Browser Subsystem
    Playwright persistent contexts
    per-run profiles
    isolated downloads
    process identity tracking
    explicit agent-owned CDP

Voice Subsystem
    push-to-talk capture
    STT adapter
    confirmation parser
    TTS adapter
    independent emergency stop

Storage
    migrations
    runs
    actions
    permits
    observations
    artifacts
    confirmations
    leases
    checkpoints
    events
```

## Ownership boundaries

| Capability | Owner |
|---|---|
| Create run | Coordinator |
| Accept task | Electron Main and Coordinator |
| Generate proposal | Strategist |
| Issue permit | Coordinator |
| Consume permit | Coordinator |
| Execute desktop mutation | Windows Executor |
| Write authoritative events | Coordinator/storage |
| Verify action | Verifier |
| Render UI | Electron Renderer |
| Validate IPC | Electron Main |
| Stop execution | Electron Main, Coordinator, and Executor cleanup |
| Launch application | Coordinator through launch registry |
| Create browser profile | Browser subsystem under Coordinator |
| Create confirmation token | Coordinator |
| Display confirmation | Renderer |
| Accept confirmation | Main and Coordinator |

The renderer must never receive authority to issue permits or directly invoke desktop mutation.

## Run state machine

Add a Coordinator-owned run state machine:

```python
class RunState(StrEnum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    TASK_ACCEPTED = "TASK_ACCEPTED"
    PLANNING = "PLANNING"
    PLAN_REVIEW = "PLAN_REVIEW"
    WAITING_FOR_USER = "WAITING_FOR_USER"
    READY_TO_EXECUTE = "READY_TO_EXECUTE"
    ACTION_REVIEW = "ACTION_REVIEW"
    WAITING_FOR_CONFIRMATION = "WAITING_FOR_CONFIRMATION"
    ACTION_EXECUTING = "ACTION_EXECUTING"
    VERIFYING = "VERIFYING"
    CHECKPOINTED = "CHECKPOINTED"
    RECOVERY = "RECOVERY"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    PAUSED = "PAUSED"
    ABORTED = "ABORTED"
```

## Action state machine

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

Only the Coordinator may transition run or action state.

## Action lifecycle

The lifecycle must progress as follows:

```text
observation
→ proposal
→ policy validation
→ optional confirmation
→ durable permit issuance
→ atomic permit consumption
→ executor dispatch
→ executor result
→ post-action observation
→ deterministic verification
→ verified/failure/unknown
→ event persistence
```

If physical dispatch may have occurred but its result is unknown, transition to `UNKNOWN` and reconcile. Do not retry automatically.

## Executor interface

Add a typed executor boundary:

```python
class Executor(Protocol):
    def observe(
        self,
        request: ObservationRequest,
    ) -> ObservationResult:
        ...

    def execute(
        self,
        action: Action,
        *,
        permit: Permit,
        observation: Observation,
        cancellation: CancellationToken,
    ) -> ExecutionResult:
        ...

    def emergency_stop(self) -> None:
        ...
```

The executor must not issue or consume permits.

## Execution results

Add structured results:

```python
class ExecutionStatus(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    UNKNOWN = "unknown"
    CANCELLED = "cancelled"
```

```python
class ExecutionResult(StrictModel):
    status: ExecutionStatus
    mechanism: str
    started_at: datetime
    finished_at: datetime
    target_window: WindowIdentity | None = None
    target_process: ProcessIdentity | None = None
    warnings: tuple[str, ...] = ()
    error_code: str | None = None
    error_message: str | None = None
    evidence_ids: tuple[str, ...] = ()
```

A successful executor return is not sufficient for application-level success. The verifier must determine whether the desired state was reached.

## Protocol extensions

Extend observations and proposals with:

- monitor origin and dimensions;
- physical DPI;
- display topology;
- screenshot artifact ID;
- screenshot hash;
- coordinate transform metadata;
- UIA tree hash;
- browser state reference;
- application integrity level;
- target HWND;
- exact target process identity;
- permission scope;
- confirmation binding;
- risk level;
- verification requirements;
- executor capability version;
- artifact provenance;
- redaction state;
- cancellation state;
- session ownership token.

Example coordinate-space model:

```python
class CoordinateSpace(BaseModel):
    id: str
    origin_x: int
    origin_y: int
    width_px: int
    height_px: int
    image_width_px: int
    image_height_px: int
    dpi_x: int
    dpi_y: int
    scale_x: float
    scale_y: float
    crop_left: int
    crop_top: int
    letterbox_left: int
    letterbox_top: int
    source: Literal["desktop", "monitor", "window", "element"]
    screenshot_hash: str
```

Reject coordinate actions when:

- display topology changed;
- target window moved;
- DPI changed;
- screenshot hash changed;
- coordinate-space ID is stale;
- dimensions are invalid;
- crop or padding metadata is absent.

## Risk and confirmation model

Add:

```python
class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
```

```python
class ConfirmationRequest(StrictModel):
    confirmation_id: UUID
    run_id: str
    action_id: str
    action_hash: str
    risk: RiskLevel
    phrase: str
    expires_at: datetime
    one_use: bool = True
```

Confirmation validation must ensure:

- the confirmation is bound to the exact action hash;
- the confirmation has not expired;
- it has not already been consumed;
- it belongs to the current run;
- it is consumed once;
- generic “yes” responses are not treated as sufficient where an exact phrase is required.

## Windows observation

The Windows executor must provide:

1. Interactive desktop identity.
2. Foreground window identity.
3. Process identity.
4. Windows session ID.
5. Input desktop identity.
6. Integrity level.
7. Display topology.
8. Per-monitor DPI.
9. Screenshot artifact and hash.
10. UIA tree or tree hash where available.

### Screen capture

Prefer a native helper using Microsoft’s `Windows.Graphics.Capture` API. The adapter must expose:

- display or window capture;
- capture support detection;
- capture target identity;
- physical dimensions;
- DPI;
- timestamp;
- coordinate-space ID;
- artifact path or ID;
- SHA-256 hash;
- capture mechanism;
- crop and transform metadata.

Capture frames must be disposed, and frame pools must be recreated when dimensions or devices change.

Fallback mechanisms may include PrintWindow, BitBlt, desktop duplication, or a third-party native library, but each fallback must be explicit and recorded. Blank or stale captures must not be accepted as valid observations.

### DPI and coordinate handling

Configure DPI awareness in the Windows application manifest and verify the effective process DPI context at startup.

Support:

- 100%, 125%, 150%, and 200% DPI;
- multiple monitors;
- mixed-DPI monitors;
- monitors left or above the primary monitor;
- negative virtual desktop coordinates;
- display attach/detach;
- resolution changes;
- scaling changes;
- window movement between monitors.

## UI Automation

Use one primary UIA abstraction rather than allowing competing libraries to own targeting.

Interface:

```python
class WindowsUIAAdapter(Protocol):
    def list_windows(self) -> list[WindowInfo]:
        ...

    def inspect_window(
        self,
        hwnd: int,
        *,
        max_depth: int = 12,
        interactive_only: bool = False,
    ) -> UIATree:
        ...

    def find(
        self,
        target: ElementTarget,
        *,
        window: WindowIdentity,
    ) -> list[UIAElementRef]:
        ...

    def invoke(self, element: UIAElementRef) -> UIAActionResult:
        ...

    def set_value(
        self,
        element: UIAElementRef,
        value: str,
    ) -> UIAActionResult:
        ...

    def select(self, element: UIAElementRef) -> UIAActionResult:
        ...

    def expand(self, element: UIAElementRef) -> UIAActionResult:
        ...

    def collapse(self, element: UIAElementRef) -> UIAActionResult:
        ...

    def focus(self, element: UIAElementRef) -> UIAActionResult:
        ...

    def read_properties(
        self,
        element: UIAElementRef,
    ) -> UIAProperties:
        ...
```

Target resolution must consider:

- AutomationId;
- RuntimeId;
- control type;
- normalized name;
- class name;
- ancestry;
- window identity;
- process identity;
- bounds;
- captured tree identity.

Reject ambiguous matches instead of selecting the first match.

## Physical input fallback

Use Microsoft `SendInput` through a controlled wrapper:

```python
class InputInjector(Protocol):
    def move(self, x: int, y: int) -> InputResult:
        ...

    def click(
        self,
        x: int,
        y: int,
        button: MouseButton,
    ) -> InputResult:
        ...

    def drag(
        self,
        start: Point,
        end: Point,
        duration_ms: int,
    ) -> InputResult:
        ...

    def key_down(self, key: Key) -> InputResult:
        ...

    def key_up(self, key: Key) -> InputResult:
        ...

    def type_text(self, text: str) -> InputResult:
        ...

    def cleanup_pressed_inputs(self) -> None:
        ...
```

Before every injection:

1. Confirm an interactive desktop.
2. Confirm session and input desktop identity.
3. Confirm target window and process identity.
4. Confirm same-integrity compatibility.
5. Validate physical coordinates.
6. Dispatch through `SendInput`.
7. Inspect the inserted event count.
8. Capture post-state.
9. Release temporary key/button state.
10. Return a structured failure if success is uncertain.

Use a strict key map. Do not accept arbitrary model-supplied virtual-key names.

## Application launch registry

Model output may select only a registered target:

```python
class LaunchTarget(StrictModel):
    target_id: str
    display_name: str
    executable: str
    arguments: tuple[str, ...] = ()
    working_directory: str | None = None
    expected_process_names: tuple[str, ...]
    expected_window_patterns: tuple[str, ...]
    allowed_hashes: tuple[str, ...] = ()
    publisher: str | None = None
```

Launch requirements:

- use allowlisted target IDs;
- use argument arrays;
- use `shell=False`;
- validate canonical paths;
- optionally validate publisher or executable hash;
- verify expected process and window after launch;
- reject model-generated executable paths;
- record launch policy revision.

## Browser subsystem

Use Playwright with:

- one persistent context per run;
- one profile directory per run;
- isolated download directory per run;
- profile locking;
- browser process identity tracking;
- permission denial by default;
- URL allowlists;
- redirect validation;
- explicit agent-owned CDP only.

Reject by default:

- `file:`;
- `data:`;
- `javascript:`;
- arbitrary local profile attachment;
- attachment to the user’s daily browser;
- unknown CDP endpoints;
- redirects outside policy.

CDP attachment is allowed only when Compuse can verify:

- process ID;
- profile directory;
- launch token;
- expected command-line arguments;
- expected debugging endpoint.

## Verification

Implement deterministic verifiers for:

- UIA values and properties;
- UIA selection and expansion state;
- browser DOM state;
- browser URL and navigation state;
- process and window state;
- files and downloads;
- notifications where reliably observable.

Optional visual verification may be added later, but it must not replace deterministic verification where deterministic evidence is available.

`VERIFIED` must only be entered after independent post-action evidence is captured and evaluated.

## Coordinator and durable permits

Permit validation and consumption must occur transactionally:

```text
BEGIN IMMEDIATE
    validate run state
    validate action hash
    validate observation revision
    validate coordinate-space ID
    validate policy revision
    validate target window/process/session
    validate capability hash
    validate confirmation
    validate expiration and use count
    increment use count
    append permit_consumed event
COMMIT
```

A process restart must not recreate or restore an already-consumed permit.

## Desktop-session lock

Implement both:

- a Windows named mutex for OS-level single-owner behavior;
- a durable SQLite lease with heartbeat and expiration.

The lease must record:

- device ID;
- Windows session ID;
- username;
- input desktop;
- owner-token hash;
- heartbeat time;
- expiration time.

When the lease expires, the new process must reconcile the prior owner before performing mutation.

## Electron UI and IPC

Use Electron with React and TypeScript if this architecture is approved.

Required security configuration:

- context isolation enabled;
- renderer Node integration disabled;
- preload-only API;
- restrictive Content Security Policy;
- navigation allowlist;
- deny-by-default `window.open`;
- deny-by-default permission requests;
- strict IPC schemas;
- no direct filesystem or process access from renderer.

Bridge shape:

```typescript
type CompuseBridge = {
  createRun(input: CreateRunInput): Promise<Run>;
  requestObservation(runId: string): Promise<Observation>;
  requestConfirmation(
    input: ConfirmationRequestInput,
  ): Promise<Confirmation>;
  cancelRun(runId: string): Promise<void>;
  emergencyStop(): Promise<void>;
  subscribeEvents(
    runId: string,
    listener: (event: CompuseEvent) => void,
  ): () => void;
};
```

Every IPC handler must validate:

- sender frame;
- sender origin;
- `webContents` identity;
- message schema;
- message size;
- rate limits;
- run ownership;
- operation authorization.

## Local IPC

Use either:

1. a Windows named pipe; or
2. loopback HTTP/WebSocket with a random per-launch token.

The selected mechanism must:

- bind locally only;
- use a random token;
- compare tokens in constant time;
- reject oversized messages;
- rate-limit requests;
- bind lifecycle to the desktop application;
- expose no unauthenticated action-dispatch endpoint.

Dangerous Coordinator operations should remain private.

## Voice

Voice is optional and must be implemented as an adapter.

MVP requirements:

- push-to-talk;
- partial transcripts cannot mutate state;
- final transcript is treated as untrusted input;
- confirmation is exact-action-bound;
- confirmation is one-use and expiring;
- TTS output cannot confirm its own prompt;
- replay and echo tests are required;
- emergency stop works without speech recognition.

The STT and TTS providers are not selected by the research and must remain unresolved until explicitly chosen.

## Model integration

Add a typed strategist interface only after the model-free vertical slice works.

Provider output must:

- be parsed through strict schemas;
- be treated as untrusted;
- produce proposals only;
- never directly dispatch actions;
- use the restricted action vocabulary;
- respect step budgets;
- support cancellation;
- support no-progress detection;
- be tested against prompt injection from webpages, documents, and clipboard content.

---

## File and Change Map

The following map distinguishes existing files from files that must be created. Exact dependency and JavaScript file names must be confirmed after local inspection because they are not present in the verified tree.

## Existing files to preserve and modify

### `compuse/protocol/models.py`

Extend with:

- run and action state enums;
- risk levels;
- typed errors;
- coordinate-space metadata;
- screenshot/artifact references;
- monitor and DPI metadata;
- target HWND and process identity;
- integrity level;
- executor capability hash;
- confirmation records;
- verification requirements;
- cancellation and unknown-state fields;
- artifact provenance and redaction state.

Preserve strict validation and `extra="forbid"` behavior.

### `compuse/coordinator/core.py`

Refactor to:

- use durable permits instead of only `self._permits`;
- perform atomic permit issue and consumption;
- validate confirmation records;
- validate executor capability revisions;
- persist run and action transitions;
- support cancellation;
- support unknown execution state;
- integrate with the desktop lease;
- preserve mutation exclusivity;
- preserve origin rejection;
- preserve observation and policy binding.

### `compuse/storage/events.py`

Extend with:

- schema migrations;
- schema version tracking;
- durable state tables;
- permit transactions;
- artifact manifests;
- startup integrity checks;
- retention support;
- canonical artifact-root checks;
- reparse-point and symlink protection;
- backup/restore documentation;
- integrity-failure behavior.

The existing event hash-chain implementation should remain the authoritative event mechanism.

### `tests/test_core.py`

Preserve existing tests and add tests for:

- durable permit issuance;
- atomic consumption;
- duplicate consumption;
- transaction rollback;
- state transitions;
- confirmations;
- stale target identity;
- capability mismatch;
- unknown execution state;
- cancellation;
- lease ownership;
- recovery behavior.

### `.github/workflows/test.yml`

Preserve the existing Linux matrix and add:

- a Windows unit-test job;
- Windows-specific dependency setup;
- artifact collection for failed tests;
- packaging checks where feasible.

Do not assume ordinary hosted CI provides a usable interactive desktop. Interactive Windows tests require a dedicated environment or self-hosted runner.

### `README.md`

Update to:

- describe the completed product boundaries;
- document supported Windows versions;
- document installation and startup;
- document unsupported UAC, credentials, MFA, and secure desktop behavior;
- document same-integrity limitations;
- document browser profile isolation;
- document artifact and log handling;
- distinguish implemented, planned, and unsupported capabilities.

### `plan.md`

Convert the current specification into an implementation status document after implementation begins.

For each subsystem, mark:

- implemented;
- tested;
- partially implemented;
- blocked;
- unsupported.

Do not present described but unimplemented components as available.

### `docs/supported-capabilities.md`

Replace the current planned-status table with a release matrix covering:

- supported application types;
- UIA patterns;
- browser support;
- same-integrity restriction;
- DPI and monitor support;
- unsupported security boundaries;
- verification limitations;
- known application-specific exceptions.

### `docs/final-execution-checklist.md`

Expand it into a release and test checklist covering:

- environment setup;
- Windows validation;
- packaging;
- signing;
- migration;
- smoke tests;
- crash recovery;
- rollback;
- security review;
- incomplete evidence reporting.

## New Python packages

### `compuse/executor/__init__.py`

Export the executor interfaces and Windows implementation entry points.

### `compuse/executor/base.py`

Define:

- `Executor`;
- `ObservationRequest`;
- `ObservationResult`;
- `ExecutionResult`;
- `CancellationToken`;
- executor capability metadata.

### `compuse/executor/models.py`

Define:

- `WindowIdentity`;
- `ProcessIdentity`;
- `DesktopIdentity`;
- `DisplayInfo`;
- `CoordinateSpace`;
- `InputResult`;
- `UIATree`;
- `UIAElementRef`;
- `UIAProperties`.

### `compuse/executor/windows.py`

Coordinate Windows-specific operations:

- observation;
- UIA;
- input;
- foreground validation;
- process/session inspection;
- cancellation cleanup.

Do not place all native behavior in one unstructured module; delegate to focused adapters.

### `compuse/executor/screenshot.py`

Implement:

- Windows Graphics Capture integration through the selected native helper;
- capture support detection;
- frame lifecycle;
- device-loss handling;
- dimensions and DPI;
- artifact creation;
- screenshot hashing;
- explicit fallback handling.

### `compuse/executor/uia.py`

Implement:

- window enumeration;
- UIA tree inspection;
- target resolution;
- ambiguity rejection;
- semantic invoke;
- value setting;
- selection;
- expand/collapse;
- focus;
- property reads.

### `compuse/executor/input.py`

Implement controlled `SendInput` bindings and cleanup of held keys/buttons.

### `compuse/executor/process.py`

Implement:

- process identity;
- window identity;
- foreground window inspection;
- session identity;
- integrity level;
- input desktop;
- launch verification.

### `compuse/executor/display.py`

Implement:

- monitor enumeration;
- virtual desktop origin;
- physical dimensions;
- per-monitor DPI;
- topology revision;
- coordinate transform creation.

### `compuse/executor/clipboard.py`

Implement clipboard access only if required by supported actions. Record clipboard-originated content as environment data and never treat it as authority.

### `compuse/executor/cancellation.py`

Implement cancellation tokens and cleanup hooks for input and capture operations.

## New Coordinator modules

### `compuse/coordinator/state.py`

Implement Coordinator-owned run and action state transitions.

### `compuse/coordinator/policy.py`

Implement:

- origin checks;
- action allowlists;
- risk classification;
- confirmation requirements;
- application launch policy;
- browser URL policy;
- integrity and session policy;
- unsupported-boundary policy.

### `compuse/coordinator/recovery.py`

Implement:

- unknown execution-state handling;
- checkpoint reconciliation;
- stale lease recovery;
- crash recovery;
- no-blind-retry behavior.

### `compuse/coordinator/watchdog.py`

Implement:

- action timeouts;
- heartbeat monitoring;
- stuck-action detection;
- cancellation escalation;
- emergency-stop forwarding.

### `compuse/coordinator/leases.py`

Implement:

- Windows named mutex integration;
- durable SQLite lease;
- heartbeat;
- expiration;
- owner validation.

### `compuse/coordinator/launch_registry.py`

Implement allowlisted launch targets, canonical path checks, process/window verification, and launch policy revisions.

## New storage modules

### `compuse/storage/migrations.py`

Implement schema versioning and ordered migrations.

### `compuse/storage/repositories.py`

Implement repositories for:

- runs;
- actions;
- permits;
- observations;
- confirmations;
- artifacts;
- leases;
- checkpoints.

### `compuse/storage/artifacts.py`

Implement:

- canonical artifact-root enforcement;
- SHA-256 hashing;
- metadata;
- redaction state;
- retention;
- symlink/reparse-point rejection.

## New verification modules

### `compuse/verification/__init__.py`

Export verifier interfaces.

### `compuse/verification/base.py`

Define:

```python
class Verifier(Protocol):
    def verify(
        self,
        *,
        proposal: ActionProposal,
        pre: Observation,
        execution: ExecutionResult,
        post: Observation,
    ) -> VerificationResult:
        ...
```

### `compuse/verification/uia.py`

Implement deterministic UIA verification.

### `compuse/verification/browser.py`

Implement DOM, URL, navigation, and browser-state verification.

### `compuse/verification/process.py`

Implement process and window verification.

### `compuse/verification/files.py`

Implement file/download verification, including hashes where required.

### `compuse/verification/visual.py`

Optional visual verification. It must not override reliable deterministic evidence.

## New browser modules

### `compuse/browser/__init__.py`

Export browser lifecycle functions.

### `compuse/browser/playwright.py`

Implement isolated Playwright contexts, profile creation, browser launch, downloads, and cleanup.

### `compuse/browser/policy.py`

Implement URL, redirect, permission, and profile-ownership checks.

### `compuse/browser/cdp.py`

Implement explicit agent-owned CDP validation. Reject unknown endpoints and user-profile attachment.

## New native Windows helper

The exact language and project structure are unresolved. If required by the selected capture/UIA implementation, add a native helper directory such as:

```text
native/
└── windows-helper/
```

The helper must expose only the minimum required interface for:

- Windows Graphics Capture;
- UIA operations;
- input or identity operations where Python bindings are insufficient.

The language, build system, and binary packaging must be selected and documented before implementation.

## New Electron application

The research describes Electron/React but the verified repository contains no JavaScript files. After confirming the product decision, create the selected structure, for example:

```text
desktop/
├── package.json
├── package-lock.json
├── tsconfig.json
├── electron/
│   ├── main.ts
│   ├── preload.ts
│   └── ipc.ts
└── renderer/
    ├── index.html
    ├── src/
    │   ├── App.tsx
    │   ├── main.tsx
    │   ├── api.ts
    │   ├── components/
    │   └── state/
    └── styles/
```

These paths are an implementation recommendation, not existing repository facts. The builder must use the chosen package layout consistently.

## New tests

Add:

```text
tests/
├── test_protocol_extensions.py
├── test_storage_migrations.py
├── test_durable_permits.py
├── test_state_machine.py
├── test_confirmations.py
├── test_artifact_security.py
├── test_browser_policy.py
├── test_recovery.py
├── windows/
│   ├── test_display.py
│   ├── test_screenshot.py
│   ├── test_uia.py
│   ├── test_input.py
│   ├── test_process_identity.py
│   └── test_dpi.py
└── integration/
    ├── test_notepad_vertical_slice.py
    ├── test_browser_isolation.py
    ├── test_ipc_security.py
    └── test_crash_recovery.py
```

The exact test organization may differ, but equivalent coverage is required.

---

## Step-by-Step Build Plan

## Step 1: Establish and document the baseline

**Input**

- Existing repository.
- Current `pyproject.toml`.
- Existing test and CI configuration.

**Actions**

1. Read `pyproject.toml` locally.
2. Run current tests.
3. Record Python, SQLite, and operating-system versions.
4. Confirm whether `uv`, Node.js, npm, Electron, or lock files already exist.
5. Create a Windows development setup document.
6. Declare target Windows version and architecture as an explicit product decision.

**Expected result**

- Existing tests pass or known failures are documented.
- Dependency baseline is known.
- Missing JavaScript/package infrastructure is confirmed.
- No dependency changes are made blindly.

**Dependencies**

- None.

## Step 2: Create the protocol extension

**Input**

- Existing strict models.
- Current action and observation fields.

**Actions**

1. Add run and action states.
2. Add risk levels and typed errors.
3. Add coordinate-space and display metadata.
4. Add screenshot and artifact references.
5. Add process/window/session/integrity fields.
6. Add executor capability version.
7. Add confirmation and verification schemas.
8. Add cancellation and unknown-state concepts.
9. Add strict validation tests.

**Expected result**

- All proposed state and evidence are representable without untyped dictionaries.
- Existing protocol tests continue passing.
- Invalid extra fields remain rejected.

**Dependencies**

- Step 1.

## Step 3: Add database migrations and durable state

**Input**

- Existing SQLite event store.

**Actions**

1. Add schema version tracking.
2. Add migrations for runs, actions, permits, observations, artifacts, confirmations, leases, and checkpoints.
3. Preserve WAL, foreign keys, busy timeout, and `synchronous=FULL`.
4. Add transaction helpers.
5. Add repository classes.
6. Add startup schema migration behavior.

**Expected result**

- A new database can be created from migrations.
- An existing database can be upgraded.
- Schema versions are recorded.
- Event storage remains compatible with hash-chain verification.

**Dependencies**

- Steps 1 and 2.

## Step 4: Make permits durable and atomic

**Input**

- Existing in-memory Coordinator permit logic.
- New permit table and transaction helpers.

**Actions**

1. Store permits in SQLite.
2. Bind permits to exact action hash, run, observation, coordinate space, policy, target identity, capability revision, and confirmation.
3. Use `BEGIN IMMEDIATE` for issue/consume operations.
4. Enforce one-use behavior with a durable use count.
5. Reject expired, consumed, mismatched, or stale permits.
6. Add idempotency behavior for duplicate requests.
7. Append lifecycle events inside the transaction.

**Expected result**

- Restarting the process does not recreate permits.
- Concurrent consumers cannot both consume one permit.
- Rollback leaves no partially consumed permit.
- Existing permit safety tests continue passing.

**Dependencies**

- Step 3.

## Step 5: Implement state transitions and lifecycle orchestration

**Input**

- Durable runs, actions, permits, and protocol states.

**Actions**

1. Implement Coordinator-owned run transitions.
2. Implement Coordinator-owned action transitions.
3. Add lifecycle orchestration from observation through verification.
4. Add cancellation transitions.
5. Add explicit `UNKNOWN` state.
6. Append state transition events.

**Expected result**

- Invalid transitions are rejected.
- Every action has a durable lifecycle.
- An executor result cannot directly mark an action verified.

**Dependencies**

- Step 4.

## Step 6: Implement Windows identity and desktop safety

**Input**

- Windows test machine.
- Executor interfaces.

**Actions**

1. Implement Windows session identity.
2. Implement foreground HWND and PID inspection.
3. Implement input desktop inspection.
4. Implement integrity-level inspection.
5. Implement process identity.
6. Add same-integrity policy.
7. Add focus/session validation.
8. Add typed failures for unsupported desktop conditions.

**Expected result**

- The Coordinator can determine whether the current desktop is eligible for mutation.
- Focus-dependent actions reject mismatched windows, processes, sessions, or input desktops.

**Dependencies**

- Steps 2 and 5.
- Interactive Windows environment.

## Step 7: Implement display and DPI handling

**Input**

- Windows display APIs.
- Extended coordinate-space model.

**Actions**

1. Configure process DPI awareness.
2. Enumerate displays.
3. Record virtual desktop origin and dimensions.
4. Record per-monitor DPI.
5. Generate coordinate transforms.
6. Add topology revisioning.
7. Reject stale coordinate spaces.

**Expected result**

- Physical and image coordinates can be mapped deterministically.
- Negative coordinates and mixed-DPI configurations are supported.
- Topology changes invalidate old coordinate-bound actions.

**Dependencies**

- Step 6.

## Step 8: Implement screen capture

**Input**

- Display identity and coordinate model.
- Native helper decision.

**Actions**

1. Implement Windows Graphics Capture through the selected helper.
2. Detect capture support.
3. Capture display or window frames.
4. Dispose frame resources.
5. Handle device loss and resize.
6. Hash captured artifacts.
7. Store artifact metadata.
8. Implement and explicitly label any fallback capture path.
9. Reject blank or stale frames.

**Expected result**

- An observation contains a valid screenshot artifact, hash, timestamp, target identity, dimensions, DPI, and coordinate-space ID.

**Dependencies**

- Step 7.
- Native helper selection.

## Step 9: Implement UI Automation

**Input**

- UIA adapter boundary.
- Windows test applications.

**Actions**

1. Select one primary UIA implementation.
2. Implement window enumeration.
3. Implement tree inspection.
4. Implement target scoring and ambiguity rejection.
5. Implement semantic invoke.
6. Implement value setting.
7. Implement selection, expansion, collapse, and focus.
8. Capture UIA tree hashes.
9. Re-resolve targets immediately before mutation.

**Expected result**

- The executor can inspect and operate supported Win32, WPF, WinForms, WinUI, and other tested application types where their UIA exposure permits.

**Dependencies**

- Steps 6 and 8.

## Step 10: Implement physical input fallback

**Input**

- `SendInput` API.
- Input injector interface.

**Actions**

1. Add safe mouse and keyboard bindings.
2. Add strict key mapping.
3. Validate target focus immediately before dispatch.
4. Inspect insertion counts.
5. Track pressed keys and buttons.
6. Clean up on cancellation, timeout, exception, and shutdown.
7. Capture post-action state.
8. Return `UNKNOWN` if physical outcome cannot be determined.

**Expected result**

- Physical input is available only as a validated fallback.
- Held-input cleanup is reliable.
- UIPI or target failures become typed errors.

**Dependencies**

- Steps 6–9.

## Step 11: Implement application launch registry

**Input**

- Approved application list.
- Process and window inspection.

**Actions**

1. Add allowlisted targets.
2. Validate canonical executable paths.
3. Use argument arrays with `shell=False`.
4. Validate hashes or publishers where configured.
5. Match expected process names and window patterns.
6. Record launch revision and result.

**Expected result**

- The model can select only approved target IDs.
- Arbitrary executable paths and shell commands are rejected.

**Dependencies**

- Step 6.

## Step 12: Implement verification

**Input**

- Pre-observation.
- Execution result.
- Post-observation.
- UIA, browser, process, and file evidence.

**Actions**

1. Implement deterministic UIA verifier.
2. Implement process/window verifier.
3. Implement file/download verifier.
4. Add browser verifier interfaces.
5. Add verification evidence references.
6. Make `VERIFIED` reachable only after successful independent verification.
7. Add false-success tests.

**Expected result**

- Executor success alone does not imply action success.
- Verification failure produces `FAILED`, not `VERIFIED`.
- Missing evidence produces an explicit failure or unknown outcome.

**Dependencies**

- Steps 8–10.

## Step 13: Implement desktop-session locking and recovery

**Input**

- Windows identity.
- Durable lease tables.
- State machine.

**Actions**

1. Add named mutex.
2. Add durable lease and heartbeat.
3. Add stale lease detection.
4. Add watchdog.
5. Add cancellation and emergency stop.
6. Add checkpointing.
7. Add crash reconciliation.
8. Add recovery for actions interrupted at each lifecycle boundary.

**Expected result**

- Only one Compuse instance can mutate the desktop.
- Stale ownership is not silently reused.
- Uncertain actions are reconciled rather than replayed.

**Dependencies**

- Steps 3, 5, and 6.

## Step 14: Implement browser isolation

**Input**

- Playwright dependency decision.
- Browser policy.

**Actions**

1. Install and pin Playwright and Chromium according to the selected dependency workflow.
2. Create per-run persistent profiles.
3. Isolate downloads.
4. Deny permissions by default.
5. Validate URLs and redirects.
6. Track browser process identity.
7. Add explicit agent-owned CDP support.
8. Reject daily browser profile attachment.
9. Add browser crash recovery.

**Expected result**

- Browser runs are isolated and attributable to Compuse.
- User credentials and daily browsing sessions are not exposed through unapproved attachment.

**Dependencies**

- Steps 3, 5, and 12.
- Provider and browser packaging decisions.

## Step 15: Implement local IPC and Electron UI

**Input**

- Coordinator API.
- IPC security decision.
- Electron product decision.

**Actions**

1. Create Electron main process.
2. Create preload bridge.
3. Create React renderer.
4. Enable context isolation.
5. Disable Node integration in renderer.
6. Add CSP and navigation restrictions.
7. Add strict IPC validation.
8. Add run ownership and rate limits.
9. Add live event subscription.
10. Add confirmation interface.
11. Add evidence viewer.
12. Add emergency stop.

**Expected result**

- The UI can create runs, display state, request observations, display confirmations, and cancel runs without receiving direct desktop mutation authority.

**Dependencies**

- Steps 5, 13, and the Electron/package decision.

## Step 16: Implement voice adapters

**Input**

- Selected STT/TTS providers.
- Confirmation model.

**Actions**

1. Add push-to-talk capture.
2. Add STT adapter.
3. Ensure partial transcripts cannot mutate.
4. Add exact confirmation phrase handling.
5. Add TTS adapter if required.
6. Prevent TTS echo confirmation.
7. Add replay and expiry tests.
8. Keep emergency stop independent of speech recognition.

**Expected result**

- Voice is optional, explicit, one-use, and action-bound.

**Dependencies**

- Step 15.
- STT/TTS provider decision.

## Step 17: Add strategist/model adapter

**Input**

- Typed protocol.
- Model/provider decision.

**Actions**

1. Define a `Strategist` interface.
2. Validate provider output strictly.
3. Convert provider output only into proposals.
4. Enforce restricted actions and policies.
5. Add step budgets, cancellation, and no-progress detection.
6. Add prompt-injection tests.
7. Do not put provider credentials in the renderer.

**Expected result**

- Model output remains untrusted and cannot bypass the Coordinator.

**Dependencies**

- Steps 2, 5, 12, and provider decision.

## Step 18: Package and deploy

**Input**

- Electron application.
- Python Coordinator.
- Native helper.
- Browser assets.
- Migration system.

**Actions**

1. Select MSIX, signed NSIS, or another approved Windows packaging format.
2. Bundle or package the Python runtime.
3. Bundle native helpers.
4. Bundle or install supported Playwright browsers.
5. Add per-user data paths.
6. Add migrations on startup.
7. Create development-signed package.
8. Define production certificate and timestamping strategy.
9. Add upgrade, uninstall, rollback, and package-integrity tests.
10. Document SmartScreen and certificate behavior.

**Expected result**

- A reproducible Windows installer can install, upgrade, launch, migrate, and uninstall the application.

**Dependencies**

- Steps 15–17.
- Packaging and signing decisions.

## Step 19: Execute full acceptance testing

**Input**

- Packaged application.
- Interactive Windows test machine.
- Dedicated test applications.

**Actions**

1. Run unit and integration tests.
2. Execute the Notepad vertical slice.
3. Run DPI and multi-monitor matrix.
4. Run UIA application matrix.
5. Run browser isolation tests.
6. Run IPC security tests.
7. Inject crashes across the action lifecycle.
8. Test UAC, secure desktop, credentials, MFA, locked workstation, and elevated applications.
9. Verify that unsupported cases pause or return user-intervention outcomes.
10. Record actual commands, versions, outputs, screenshots, and failures.

**Expected result**

- The acceptance matrix is complete with evidence.
- Any unexecuted or unavailable test is explicitly reported as unverified.

**Dependencies**

- All prior steps.

---

## Technical Details

## Development commands

The repository documentation currently specifies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e '.[test]'
pytest -q
```

The research also recommends the following workflow, but `uv.lock`, `package.json`, and `package-lock.json` were not verified in the current tree:

```powershell
python -m pip install --upgrade pip
pip install uv
uv sync --locked
npm ci
```

Use `uv sync --locked` and `npm ci` only after confirming that the corresponding lock files exist and are part of the selected build workflow.

For browser support, the research specifies:

```powershell
python -m playwright install chromium
```

Verify the actual Playwright dependency and version before running this command.

## Error schema

Use a typed error structure equivalent to:

```python
class CompuseError(StrictModel):
    code: str
    message: str
    retryable: bool
    requires_user_intervention: bool
    state: str
    evidence_ids: tuple[str, ...] = ()
```

Required error codes include:

```text
stale_observation
stale_coordinate_space
target_not_found
target_ambiguous
window_mismatch
process_mismatch
session_mismatch
integrity_mismatch
input_desktop_mismatch
no_interactive_desktop
uipi_blocked
send_input_failed
capture_unsupported
capture_device_lost
uia_pattern_unavailable
browser_profile_locked
browser_not_agent_owned
confirmation_required
confirmation_expired
confirmation_replayed
permit_expired
permit_consumed
permit_binding_mismatch
unknown_execution_state
event_integrity_failure
ipc_unauthorized
launch_target_not_allowed
```

## Storage schema

Implement migrations equivalent to:

```sql
runs (
    run_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    mode TEXT NOT NULL,
    policy_revision TEXT NOT NULL
);

actions (
    action_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    state TEXT NOT NULL,
    action_hash TEXT NOT NULL,
    proposal_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

permits (
    permit_id TEXT PRIMARY KEY,
    action_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    action_hash TEXT NOT NULL,
    observation_revision INTEGER NOT NULL,
    coordinate_space_id TEXT NOT NULL,
    policy_revision TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    consumed_at TEXT,
    use_count INTEGER NOT NULL DEFAULT 0,
    confirmation_id TEXT
);

observations (
    observation_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    coordinate_space_id TEXT NOT NULL,
    screenshot_hash TEXT,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

artifacts (
    artifact_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    origin TEXT NOT NULL,
    redaction_state TEXT NOT NULL,
    capture_metadata_json TEXT NOT NULL,
    retained_until TEXT
);

leases (
    lease_id TEXT PRIMARY KEY,
    device_id TEXT NOT NULL,
    windows_session_id INTEGER NOT NULL,
    user_name TEXT NOT NULL,
    input_desktop TEXT NOT NULL,
    owner_token_hash TEXT NOT NULL,
    heartbeat_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

events (
    run_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    type TEXT NOT NULL,
    payload TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    previous_event_hash TEXT NOT NULL,
    event_hash TEXT NOT NULL,
    PRIMARY KEY (run_id, seq)
);
```

The existing event-store schema and migration compatibility must be checked before applying these changes.

## SQLite requirements

Configure:

- foreign keys enabled;
- WAL for file-backed databases;
- `busy_timeout`;
- `synchronous=FULL`;
- tested SQLite runtime version;
- startup hash-chain verification;
- canonical database path;
- backup procedures that preserve `-wal` and shared-memory files.

On integrity failure, stop mutation and require recovery rather than continuing with potentially corrupted state.

## Windows API boundaries

The implementation must account for these documented behaviors:

- `Windows.Graphics.Capture` requires capture support and user-visible capture behavior.
- Capture frames must be disposed.
- Capture frame pools may need recreation after size or device changes.
- `SendInput` returns the number of inserted events.
- `SendInput` is subject to UIPI and same-or-lower-integrity constraints.
- A zero `SendInput` return does not uniquely identify UIPI as the cause.
- UI Automation coordinates are physical coordinates.
- DPI awareness is required for correct coordinate behavior.
- UIAccess has signing, installation, and security requirements and must not be enabled solely to bypass ordinary Windows protections.

## Browser policy

At minimum, reject:

```text
file:
data:
javascript:
unknown CDP endpoint
daily-user profile
arbitrary local profile
redirect outside allowlist
```

Track browser ownership using:

- process ID;
- profile directory;
- launch token;
- expected command-line arguments;
- expected debugging endpoint.

## Environment variables

The research does not define an authoritative environment-variable set. The builder must document the selected names after implementation.

At minimum, configuration must cover:

- Coordinator database location;
- artifact root;
- IPC endpoint or named-pipe identifier;
- per-launch IPC authentication token handling;
- logging level;
- artifact retention;
- browser executable or managed-browser configuration;
- provider credentials if a remote model/STT/TTS service is selected.

Secrets must not be stored in source control, renderer bundles, event payloads, screenshots, or command-line arguments where avoidable.

---

## Testing and Verification

The following are planned checks. None of the Windows execution checks were verified by the research task because no `winmcp-7e6c6443#run_powershell` connection was available.

## Existing checks to rerun

```powershell
pytest -q
```

Verify:

- existing tests pass;
- coverage remains at least 80% under the current CI policy;
- event tamper detection still works;
- strict model rejection remains active.

## Unit tests

Add tests for:

- action digest stability;
- strict protocol fields;
- coordinate transforms;
- physical and logical coordinate rejection;
- stale screenshot hash;
- stale topology revision;
- stale HWND;
- stale process ID;
- stale session ID;
- integrity mismatch;
- durable permit issue;
- durable permit consumption;
- duplicate consumption;
- expiry;
- confirmation expiry;
- confirmation replay;
- exact action-hash binding;
- transaction rollback;
- run transitions;
- action transitions;
- cancellation;
- unknown state;
- artifact path traversal;
- symlink/reparse-point rejection;
- URL and redirect policies;
- browser profile ownership;
- launch registry restrictions;
- event-chain tampering;
- migration upgrades.

## Windows integration tests

Use an interactive Windows environment containing:

- Notepad;
- Win32 test application;
- WinForms test application;
- WPF test application;
- WinUI 3 test application;
- Electron test application;
- Qt test application;
- Chromium or Edge;
- WebView2;
- a deterministic test application with known AutomationIds.

Test:

- window enumeration;
- UIA tree inspection;
- `InvokePattern`;
- `ValuePattern`;
- select;
- expand/collapse;
- focus;
- screenshot capture;
- foreground validation;
- input injection;
- key cleanup;
- process identity;
- session identity;
- cancellation;
- emergency stop.

## DPI and display matrix

Run with:

- 100% DPI;
- 125% DPI;
- 150% DPI;
- 200% DPI;
- one monitor;
- two monitors;
- monitor left of primary;
- monitor above primary;
- mixed DPI;
- window moved between monitors;
- monitor attach/detach;
- resolution change;
- scaling change during runtime.

Verify:

- screenshot and UIA bounds agree;
- physical clicks land on intended targets;
- negative virtual coordinates work;
- transforms account for crop and letterbox;
- stale coordinate-space actions are rejected.

## Security-boundary tests

Test:

- ordinary medium-integrity application;
- elevated high-integrity application;
- UAC prompt;
- Windows Hello;
- credential dialog;
- locked workstation;
- secure desktop;
- unknown input desktop;
- RDP session;
- disconnected RDP session.

Expected result for unsupported or unsafe cases:

- pause or abort;
- return a typed `requires_user_intervention` result;
- do not claim success;
- do not blindly retry;
- do not bypass Windows security.

## Browser tests

Test:

- run-specific profiles;
- profile locking;
- isolated downloads;
- permission denial;
- URL allowlists;
- redirect rejection;
- download hash verification;
- process identity;
- explicit agent-owned CDP;
- rejection of daily browser profiles;
- browser crash;
- browser restart;
- stale browser references.

## Electron and IPC tests

Test:

- invalid sender;
- invalid origin;
- stale authentication token;
- wrong run ownership;
- oversized messages;
- malformed payloads;
- replayed confirmation;
- unauthorized action dispatch;
- renderer navigation;
- `window.open`;
- permission requests;
- preload bridge exposure;
- renderer compromise assumptions.

## Voice tests

If voice is implemented, test:

- partial transcript;
- final transcript;
- replayed phrase;
- TTS echo;
- confirmation expiry;
- altered action hash;
- microphone failure;
- STT outage;
- emergency stop while STT is unavailable.

## Crash and recovery tests

Terminate the process:

- before permit issue;
- after permit issue;
- during permit transaction;
- after permit consumption;
- before physical dispatch;
- during input;
- after physical dispatch;
- before post-observation;
- during verification;
- after entering unknown state.

The result must be one of:

- safe cancellation;
- explicit failure;
- reconciliation;
- user intervention.

It must never be a blind repeated physical action.

## Manual vertical-slice verification

The builder must manually verify:

1. Start the packaged or development app.
2. Acquire the desktop lease.
3. Launch Notepad through the registry.
4. Capture an observation.
5. Resolve the target text control through UIA.
6. Display a confirmation if policy requires it.
7. Issue and consume one permit.
8. Set text semantically.
9. Capture post-state.
10. Verify the text.
11. Restart the app.
12. Verify the event chain.
13. Confirm the consumed permit cannot be reused.

## Actual execution status

The research report confirms:

- no Windows connection was available;
- no PowerShell commands were executed;
- the application was not run;
- Windows APIs were not tested;
- screenshots were not captured;
- UI Automation was not exercised;
- packaging was not validated;
- no end-to-end Windows result can be claimed.

The builder must update this section with actual commands and results after execution.

---

## Security and Reliability

## Trust boundaries

Treat the following as untrusted data:

- webpage content;
- document content;
- clipboard content;
- screenshots;
- UI labels;
- OCR output;
- provider output;
- model-generated proposals;
- speech transcripts;
- TTS audio;
- browser DOM content.

None of these may grant permission, change policy, approve confirmation, or directly dispatch an action.

## Secrets

- Never commit model, STT, TTS, or browser credentials.
- Do not place credentials in renderer-accessible configuration.
- Do not store credentials in screenshots or event payloads intentionally.
- Redact sensitive artifacts before transmission.
- Mark redaction as unknown when it was not verified.
- Do not attach to the user’s daily browser profile.
- Do not use production credentials for tests.

## Input validation

Validate:

- action kind;
- action arguments;
- key names;
- coordinates;
- target identity;
- process identity;
- session identity;
- coordinate-space ID;
- screenshot hash;
- policy revision;
- confirmation ID;
- capability hash;
- launch target ID;
- browser URL;
- IPC sender;
- IPC origin;
- message size.

Reject ambiguity rather than selecting the first candidate.

## Permissions and integrity

Default to:

- same-integrity applications;
- one active desktop mutation globally;
- no UAC or secure-desktop automation;
- no credentials or MFA automation;
- no arbitrary shell/code execution;
- no unapproved browser profile attachment.

High-integrity or secure-desktop actions must require explicit user intervention or be unsupported.

## Retries and timeouts

- Use short, explicit action timeouts.
- Do not retry a physical action automatically when dispatch status is uncertain.
- Retry observation or verification only when it cannot cause mutation.
- Expire permits and confirmations.
- Use watchdogs for stuck actions.
- Cancel and clean up held input on timeout.

## Logging

Log structured events for:

- run creation;
- observations;
- proposals;
- policy decisions;
- confirmation creation and consumption;
- permit issue and consumption;
- executor dispatch;
- executor result;
- post-observation;
- verification;
- failure;
- cancellation;
- recovery;
- emergency stop;
- lease acquire/release;
- browser launch and shutdown.

Do not log secrets or unredacted sensitive content unnecessarily.

## Artifact handling

- Store artifacts under a canonical root.
- Reject path traversal.
- Reject symlinks and Windows reparse-point escapes.
- Store SHA-256 hashes.
- Store capture provenance.
- Store redaction state.
- Apply retention policies.
- Ensure backups preserve SQLite WAL and shared-memory files when applicable.

## Safe failure

When an unsafe or uncertain condition occurs:

1. Stop new mutation.
2. Release temporary input state.
3. Capture available evidence.
4. Persist a typed error.
5. Enter `FAILED`, `UNKNOWN`, `PAUSED`, or `RECOVERY`.
6. Require reconciliation or user intervention.
7. Never report success without verification.

---

## Deployment and Operations

## Runtime components

The production installation must package or install:

- Electron desktop shell;
- Python Coordinator;
- Windows executor/native helper;
- migrations;
- supported browser assets where applicable;
- per-user data directories;
- logs;
- artifact storage;
- configuration.

The exact bundling mechanism remains a product decision.

## Startup sequence

The application should:

1. Validate configuration.
2. Validate database path and artifact root.
3. Run database migrations.
4. Verify event-chain integrity.
5. Verify required native helpers.
6. Verify Windows version and architecture.
7. Verify interactive desktop availability.
8. Acquire the desktop mutex and durable lease.
9. Start the local IPC endpoint.
10. Start the Electron UI.
11. Expose only safe run and observation operations.

If database integrity or lease ownership cannot be established, the application must not mutate the desktop.

## Data directories

Use an isolated per-user application-data directory for:

- SQLite database;
- WAL and shared-memory files;
- artifacts;
- logs;
- browser profiles;
- downloads;
- crash reports.

The final directory locations must be documented and must not be inferred from untrusted input.

## Packaging

Select and document one packaging strategy:

- MSIX;
- signed NSIS installer;
- Windows App SDK package;
- Electron Forge/Builder output.

The package must support:

- installation;
- upgrade;
- migration;
- rollback;
- uninstall;
- package integrity;
- development signing;
- production signing;
- timestamping.

## Signing

Required operational work:

- development certificate generation;
- production certificate strategy;
- certificate rotation;
- CI secret storage;
- timestamping;
- SmartScreen expectations;
- signing of native helpers;
- signing of installer/package;
- upgrade and certificate-expiration tests.

Do not enable `uiAccess` merely to bypass UIPI. Any UIAccess design requires separate security review, signing, secure installation, and explicit product justification.

## Monitoring

Monitor and expose:

- Coordinator startup failures;
- database integrity failures;
- lease conflicts;
- executor crashes;
- capture device loss;
- UIA resolution failures;
- input injection failures;
- verification failures;
- unknown execution states;
- browser crashes;
- IPC authentication failures;
- emergency stops;
- recovery attempts.

Monitoring must not expose sensitive screenshots or secrets by default.

## Rollback

A release rollback must:

1. stop new runs;
2. preserve the event database and artifacts;
3. reconcile any active or unknown action;
4. release desktop ownership safely;
5. restore the prior application version;
6. rerun migrations or downgrade only through a tested migration strategy;
7. verify event-chain integrity;
8. prevent mutation until startup validation succeeds.

---

## Gaps and Unknowns

The following are unresolved and must not be silently assumed.

## Repository and dependency gaps

1. The raw `pyproject.toml` fetch failed during research.
2. Exact dependency declarations are unverified.
3. Exact test extras are unverified.
4. The repository tree does not verify `uv.lock`.
5. The repository tree does not verify `package.json`.
6. The repository tree does not verify `package-lock.json`.
7. The repository tree does not verify any Electron or React files.
8. The repository tree does not verify any native helper project.
9. The repository does not currently verify a Windows package or installer.

## Execution gaps

1. No `winmcp-7e6c6443#run_powershell` connection was available.
2. No Windows command was executed.
3. The application was not run.
4. Windows screen capture was not tested.
5. UI Automation was not tested.
6. `SendInput` was not tested.
7. DPI behavior was not tested.
8. Multi-monitor behavior was not tested.
9. Browser isolation was not tested.
10. Packaging was not tested.
11. Installation, upgrade, uninstall, and rollback were not tested.
12. No end-to-end result can be claimed.

## Product decisions

The following require explicit decisions:

1. Minimum supported Windows version and build.
2. Initial architecture: x64 only or x64 plus ARM64.
3. Electron acceptance.
4. Native helper language and build system.
5. Primary UIA library or native UIA implementation.
6. LLM/provider selection.
7. Whether the application is local-only.
8. Whether any data may leave the machine.
9. Offline-operation requirement.
10. Initial supported-application matrix.
11. Whether browser automation is MVP or later.
12. STT provider.
13. TTS provider.
14. Whether voice is required for first release.
15. Packaging format.
16. Distribution channel.
17. Signing certificate ownership.
18. Update delivery mechanism.
19. Screenshot and event retention period.
20. Actions requiring confirmation.
21. Emergency-stop keyboard shortcut.
22. Recovery behavior after uncertain actions.
23. UI accessibility and branding requirements.

## Compatibility gaps

The following require verification on the selected Windows environment:

- Windows Graphics Capture support;
- capture behavior under HDR;
- device loss;
- UIA behavior across application frameworks;
- `SendInput` behavior under mixed integrity levels;
- RDP behavior;
- WebView2 behavior;
- Electron sandbox/native-helper interaction;
- Playwright browser version compatibility;
- SQLite runtime version;
- native helper packaging;
- code-signing and SmartScreen behavior.

## Assumptions that must be confirmed

The research recommends, but does not verify:

- Windows 11 as the primary target;
- x64 as the first release architecture;
- Electron as the desktop UI;
- Python as the Coordinator language;
- UIA-first automation;
- same-integrity operation by default;
- Playwright for browsers;
- no arbitrary shell execution;
- a dedicated Windows native helper where required.

These recommendations must be recorded as decisions before implementation is considered complete.

---

## Builder Handoff

The builder must deliver the following:

- [ ] Existing safety-core tests still pass.
- [ ] Protocol models include observation, target, coordinate, risk, confirmation, verification, artifact, capability, cancellation, and unknown-state data.
- [ ] SQLite migrations exist and are tested.
- [ ] Permits are durable, single-use, atomically consumed, and restart-safe.
- [ ] Run and action state machines are Coordinator-owned and persisted.
- [ ] Windows session, desktop, foreground-window, process, and integrity checks exist.
- [ ] Display topology, physical coordinates, DPI, and transforms are implemented.
- [ ] Screen capture is implemented with explicit fallback and artifact hashing.
- [ ] UI Automation is implemented with ambiguity rejection.
- [ ] `SendInput` fallback is implemented with cleanup and failure handling.
- [ ] Application launching uses an allowlist and rejects arbitrary paths or shell strings.
- [ ] Deterministic verification is implemented before model-based verification.
- [ ] Desktop mutex, durable lease, watchdog, cancellation, emergency stop, and recovery exist.
- [ ] Browser profiles and downloads are isolated per run.
- [ ] CDP is restricted to Compuse-owned browser processes.
- [ ] Electron IPC is authenticated and schema-validated.
- [ ] Renderer has no direct desktop mutation authority.
- [ ] Confirmation UI and one-use action-bound confirmations exist where required.
- [ ] Voice is either implemented behind documented adapters or explicitly deferred.
- [ ] Model/provider integration is isolated behind a typed strategist interface.
- [ ] Windows packaging, signing strategy, migrations, upgrade, rollback, and uninstall are documented.
- [ ] Windows integration and interactive end-to-end tests have been executed.
- [ ] Unsupported security boundaries are documented and verified to fail safely.
- [ ] The Notepad vertical slice succeeds with durable evidence.
- [ ] Crash recovery tests show no blind replay after uncertain physical actions.
- [ ] Event-chain verification succeeds after restart.
- [ ] The supported-application matrix is updated.
- [ ] README, `plan.md`, and operational documentation distinguish implemented, deferred, unsupported, and unverified functionality.

The builder’s final report must separately list:

1. Work completed.
2. Tests actually executed, with commands and environment details.
3. Tests not executed.
4. Features blocked by missing credentials, unavailable Windows infrastructure, or unresolved product decisions.
5. Known failures and their reproduction steps.
6. Any deviations from this plan.
7. Any behavior that remains unverified.

No feature may be reported as complete solely because code was written. Windows behavior, packaging, recovery, and end-to-end claims require execution evidence from an appropriate interactive Windows environment.