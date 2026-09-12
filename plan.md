# Implementation Plan: Windows Dual-Lobe Computer-Use Agent

**Status:** Authoritative replacement for the previous `plan.md`  
**Target repository:** `anasalsawy/compuse`  
**Reference repositories:** `skyiron/neuralagentAI`, `anasalsawy/dual-lobe`, `anasalsawy/dual-lobe-proxy`  
**Research date:** 2026-09-12  
**Primary platform:** Windows 11, same-integrity desktop applications  
**Initial execution model:** Local-first, single physical desktop session, one mutating action in flight  
**Security posture:** Human-controlled, permit-bound, evidence-verified automation; no arbitrary shell execution

---

## 1. Product contract

The first releasable version will provide:

> A Windows desktop agent that inspects supported native applications and isolated browser sessions using Windows UI Automation, Playwright/CDP, screenshots, and keyboard/mouse fallback. A Strategist prepares and reviews work, an Executor performs only permitted actions, and a Verifier confirms the resulting real-world state. Every mutation is journaled, cancellable, bound to a current observation, and verified against independent evidence. Consequential operations require exact human confirmation.

The product will **not** promise:

- universal support for all Windows applications;
- reliable control of elevated applications without a separately signed UIAccess component;
- automation of UAC, Windows Hello, logon, or secure-desktop surfaces;
- autonomous password or MFA handling;
- automatic rollback for irreversible actions;
- zero-latency execution;
- complete protection against sensitive information appearing on-screen;
- retrying an uncertain external side effect after a crash;
- prompt-injection immunity;
- measured reliability improvements before the benchmark suite passes.

---

## 2. Verified constraints and decisions

### 2.1 Existing repositories

`NeuralAgent` is a useful Electron/React/FastAPI/Python product shell, but its current execution core is not safe enough to become the authority. Verified limitations include:

- fixed `1280 × 720` screenshot scaling;
- one global coordinate transform;
- no persisted monitor origin or DPI metadata;
- shell-string application launching;
- title-substring window matching;
- sequential execution/polling;
- no durable action permits;
- no authoritative post-action verification;
- no device-level desktop-session lock;
- no durable action journal.

`dual-lobe` supplies the architectural concepts:

- Strategist/Executor separation;
- planning, action, verification, and escalation locks;
- typed messages;
- append-only ledger;
- checkpoints;
- watchdogs;
- recovery.

`dual-lobe-proxy` supplies gateway and persistence patterns, but its normal mode is advisory:

```text
A responds
B reviews afterward
```

That mode cannot prevent an action already delivered to the desktop. Its documented implementation is also text-only and does not execute tools or inspect files. Computer-use mode will therefore be implemented as a new coordinator/runtime, not as a configuration change to normal proxy mode.

### 2.2 Core architecture decisions

| Area | Decision |
|---|---|
| Desktop authority | One local Coordinator process owns permits, state transitions, ledger writes, and desktop-session locking |
| Strategist | Plans, classifies risk, prepares permits, chooses verification, and proposes recovery |
| Executor | Owns desktop side effects only; cannot grant permits or verify itself |
| Verifier | Prefer deterministic evidence; use a separate model only when needed |
| Physical desktop | One mutating action in flight per desktop session |
| Overlap | Strategist computation may overlap an already-permitted Executor action; no speculative action may use unverified post-action state |
| Persistence | SQLite, one authoritative writer, WAL mode, `synchronous=FULL` for safety-critical records |
| Browser | Playwright persistent contexts; CDP only for explicit Chromium/WebView2 attach |
| UI automation | UIA semantic operations first; coordinates only as fallback |
| Voice MVP | Push-to-talk, streaming STT, streamed TTS, emergency local stop |
| Elevated UI | Pause and escalate; do not bypass UIPI/UAC |
| Shell execution | Disabled |
| Remote model input | Artifacts by reference, with hashes, limits, and redaction status |

---

## 3. Target runtime topology

```text
┌─────────────────────────────────────────────────────────────────┐
│ Electron Renderer                                                │
│ React task UI, evidence, confirmation, live state                │
└──────────────────────────────┬──────────────────────────────────┘
                               │ narrow contextBridge API
┌──────────────────────────────▼──────────────────────────────────┐
│ Electron Main Process                                            │
│ IPC validation, confirmation broker, runtime process lifecycle   │
└──────────────────────────────┬──────────────────────────────────┘
                               │ authenticated local IPC
┌──────────────────────────────▼──────────────────────────────────┐
│ Python Coordinator                                               │
│                                                                 │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                │
│  │ Strategist │  │ Executor   │  │ Verifier   │                │
│  │ client     │  │ adapter    │  │ adapters   │                │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘                │
│        │                │                │                       │
│  ┌─────▼────────────────▼────────────────▼──────┐                │
│  │ State machine, permits, scheduler, watchdog  │                │
│  └─────┬─────────────────────────────────────────┘                │
│        │                                                          │
│  ┌─────▼──────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ SQLite ledger  │  │ Artifact     │  │ Desktop      │          │
│  │ single writer  │  │ store        │  │ session lock │          │
│  └────────────────┘  └──────────────┘  └──────────────┘          │
└──────────────────────────────┬──────────────────────────────────┘
                               │ optional future sidecar
                 ┌─────────────▼─────────────┐
                 │ .NET FlaUI sidecar        │
                 │ only if Python UIA proves │
                 │ insufficient              │
                 └───────────────────────────┘
```

### 3.1 Local IPC choice

For the first implementation:

```text
Electron main ↔ Python Coordinator:
    authenticated loopback HTTP/WebSocket

Coordinator ↔ Executor:
    in-process Python call
```

Do not introduce a second process until the state machine works.

For a future FlaUI sidecar:

```text
Coordinator ↔ FlaUI:
    named pipe or localhost gRPC authenticated with a per-launch secret
```

Named pipes are preferred for the sidecar because Windows ACLs can restrict access. If loopback TCP is used, require a random per-launch bearer token, origin validation, and process-lifecycle binding.

---

## 4. Repository structure

Create the following structure, adapting existing NeuralAgent paths only where reuse is demonstrably safe:

```text
compuse/
├── desktop/
│   ├── main/
│   │   ├── main.ts
│   │   ├── ipc.ts
│   │   ├── runtime-client.ts
│   │   └── confirmation-broker.ts
│   ├── preload/
│   │   └── preload.ts
│   └── renderer/
│       ├── src/
│       │   ├── App.tsx
│       │   ├── components/
│       │   ├── hooks/
│       │   ├── store/
│       │   └── types/
│       └── index.html
├── packages/
│   ├── protocol/
│   │   ├── envelope.py
│   │   ├── actions.py
│   │   ├── observations.py
│   │   ├── permits.py
│   │   ├── evidence.py
│   │   ├── confirmations.py
│   │   ├── errors.py
│   │   └── ownership.py
│   ├── coordinator/
│   │   ├── runtime.py
│   │   ├── state_machine.py
│   │   ├── scheduler.py
│   │   ├── permit_service.py
│   │   ├── confirmation_service.py
│   │   ├── watchdog.py
│   │   ├── recovery.py
│   │   └── locks.py
│   ├── windows_executor/
│   │   ├── screenshot.py
│   │   ├── display.py
│   │   ├── dpi.py
│   │   ├── ui_automation.py
│   │   ├── semantic_actions.py
│   │   ├── input_actions.py
│   │   ├── window_manager.py
│   │   ├── process_manager.py
│   │   ├── clipboard.py
│   │   ├── cancellation.py
│   │   ├── browser.py
│   │   └── journal.py
│   ├── verifier/
│   │   ├── deterministic.py
│   │   ├── uia.py
│   │   ├── browser.py
│   │   ├── files.py
│   │   ├── visual.py
│   │   └── policy.py
│   ├── voice/
│   │   ├── capture.py
│   │   ├── stt.py
│   │   ├── tts.py
│   │   ├── vad.py
│   │   ├── aec.py
│   │   ├── barge_in.py
│   │   └── commands.py
│   └── storage/
│       ├── db.py
│       ├── migrations/
│       ├── ledger.py
│       ├── artifacts.py
│       ├── checkpoints.py
│       └── retention.py
├── tests/
│   ├── protocol/
│   ├── coordinator/
│   ├── permits/
│   ├── recovery/
│   ├── fake_executor/
│   ├── fake_provider/
│   ├── windows/
│   ├── browser/
│   ├── voice/
│   ├── security/
│   └── benchmark/
├── installer/
├── pyproject.toml
├── package.json
├── package-lock.json
├── uv.lock
└── README.md
```

---

## 5. Dependency and version policy

Only versions established by the research are fixed here:

- **SQLite:** use version **3.51.3 or later** because SQLite documents a WAL-reset race affecting versions through 3.51.2 in specific concurrent-write/checkpoint conditions.
- **Windows AI streaming speech API:** treat as experimental and require **Windows 11 24H2** and **Windows App SDK 1.7.1 or later** where that API is used.
- Other exact dependency versions were not independently established by the research and must not be invented in this plan. Resolve them through a locked dependency review on the build host.

### 5.1 Required dependency selection

The implementation review must pin and record versions for:

```text
Python
Electron
Node.js
React
FastAPI
Pydantic
SQLAlchemy
Alembic
uiautomation
pywinauto
mss
Pillow
Playwright
Azure Speech SDK, if enabled
OpenTelemetry SDK
pytest
```

The release build must fail if a dependency is not locked.

### 5.2 Initial setup commands

Use the repository’s approved Python and Node versions after the compatibility review:

```powershell
git clone <repository-url> compuse
cd compuse

py -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install uv
uv sync --locked

npm ci
```

Do not commit generated lockfiles until CI has verified the selected versions on the supported Windows build image.

Install Playwright browser assets only after deciding whether the product bundles or requires an existing Edge/Chromium installation:

```powershell
python -m playwright install chromium
```

This command must be part of the installer decision, not run silently on every startup.

---

## 6. Protocol package

All model/provider formats must be converted immediately into provider-independent protocol objects.

### 6.1 Envelope

```python
# packages/protocol/envelope.py
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field


class Actor(str, Enum):
    USER = "user"
    COORDINATOR = "coordinator"
    STRATEGIST = "strategist"
    EXECUTOR = "executor"
    VERIFIER = "verifier"
    ENVIRONMENT = "environment"


class MessageType(str, Enum):
    OBSERVATION = "observation"
    ACTION_PROPOSAL = "action_proposal"
    PERMIT = "permit"
    ACTION_RESULT = "action_result"
    VERIFICATION_REQUEST = "verification_request"
    VERIFICATION_RESULT = "verification_result"
    CONFIRMATION_REQUEST = "confirmation_request"
    CONFIRMATION_RESULT = "confirmation_result"
    RECOVERY_REQUEST = "recovery_request"
    HEARTBEAT = "heartbeat"


class Envelope(BaseModel):
    task_id: str
    run_id: str
    seq: int = Field(ge=0)
    sender: Actor
    recipient: Actor
    message_type: MessageType
    payload: dict
    environment_revision: int | None = None
    correlation_id: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
```

The coordinator must validate:

- sender/recipient compatibility;
- monotonic sequence per run;
- duplicate message idempotency;
- known message type;
- run association;
- environment revision;
- payload schema.

Unknown messages are rejected and journaled.

### 6.2 Content-origin model

```python
from enum import Enum


class ContentOrigin(str, Enum):
    USER_INTENT = "user_intent"
    SYSTEM_POLICY = "system_policy"
    STRATEGIST_INSTRUCTION = "strategist_instruction"
    EXECUTOR_INSTRUCTION = "executor_instruction"
    ENVIRONMENT_CONTENT = "environment_content"
    PROVIDER_OUTPUT = "provider_output"
```

Environment content includes:

```text
screenshots
OCR
UIA labels
browser DOM
documents
emails
notifications
web pages
clipboard text
```

Environment content may inform a decision but can never issue permission, alter policy, or satisfy human confirmation.

---

## 7. Action model

Use Pydantic discriminated unions. Do not use a generic dictionary for actions.

```python
# packages/protocol/actions.py
from typing import Annotated, Literal, Union
from pydantic import BaseModel, Field


class Click(BaseModel):
    kind: Literal["click"]
    x: int
    y: int
    button: Literal["left", "right", "middle"] = "left"
    coordinate_space_id: str
    observation_revision: int


class TypeText(BaseModel):
    kind: Literal["type"]
    text: str
    target_ref: str | None = None
    content_sha256: str
    observation_revision: int


class KeyCombo(BaseModel):
    kind: Literal["key_combo"]
    keys: list[str]
    observation_revision: int


class UIAInvoke(BaseModel):
    kind: Literal["uia.invoke"]
    element_ref: str
    required_pattern: Literal[
        "Invoke", "LegacyIAccessible", "SelectionItem"
    ]
    observation_revision: int


class UIASetValue(BaseModel):
    kind: Literal["uia.set_value"]
    element_ref: str
    value: str
    value_sha256: str
    required_pattern: Literal["Value", "Text"]
    observation_revision: int


class ApplicationLaunch(BaseModel):
    kind: Literal["application.launch"]
    target_id: str
    expected_process_name: str
    expected_window_title: str | None = None


Action = Annotated[
    Union[
        Click,
        TypeText,
        KeyCombo,
        UIAInvoke,
        UIASetValue,
        ApplicationLaunch,
    ],
    Field(discriminator="kind"),
]


class ComputerAction(BaseModel):
    action_id: str
    run_id: str
    action: Action
    risk_class: Literal["low", "medium", "high"]
    expected_result: dict
    required_evidence: list[str]
```

### 7.1 Initial action support

Implement:

```text
screenshot
mouse_move
click
double_click
drag
scroll
keypress
key_combo
type
wait
uia.invoke
uia.set_value
uia.select
uia.expand
uia.collapse
uia.scroll
uia.focus
uia.close
window.focus
application.launch
```

Do not support arbitrary Python, PowerShell, shell strings, or model-generated executable code.

### 7.2 Permit granularity

Use one permit per mutating action:

| Operation | Permit |
|---|---|
| Screenshot/UIA read | observation authorization |
| Mouse move/hover | low-risk permit |
| Click | one permit |
| Type | one permit plus text hash |
| Key combination | one permit |
| Drag | one permit |
| Launch | one permit |
| Browser navigation | one permit plus URL policy |
| Submit/send/delete/purchase | one permit plus exact human confirmation |

Provider action batches must be split into individual internal actions. Do not execute an entire provider batch under one broad permit in the MVP.

---

## 8. Observations and environment revisions

```python
# packages/protocol/observations.py
from pydantic import BaseModel
from datetime import datetime


class WindowIdentity(BaseModel):
    handle: int
    title: str
    process_id: int
    process_name: str
    integrity_level: str | None = None


class MonitorObservation(BaseModel):
    monitor_id: str
    left: int
    top: int
    width: int
    height: int
    dpi_x: int | None
    dpi_y: int | None
    primary: bool
    image_ref: str
    image_sha256: str


class Observation(BaseModel):
    run_id: str
    revision: int
    timestamp: datetime
    foreground_window: WindowIdentity | None
    monitors: list[MonitorObservation]
    coordinate_space_id: str
    ui_tree_ref: str | None
    ui_tree_sha256: str | None
    browser_state_ref: str | None
    clipboard_available: bool
```

Every observation must include:

- timestamp;
- foreground window;
- process identity;
- screen artifact;
- screen hash;
- monitor origin and size;
- DPI when available;
- coordinate-space identifier;
- UI tree hash;
- environment revision.

An action is stale if its revision or coordinate-space identifier does not match the current environment.

---

## 9. Permit model

```python
# packages/protocol/permits.py
from datetime import datetime
from pydantic import BaseModel


class HumanConfirmation(BaseModel):
    confirmation_id: str
    phrase: str
    action_summary: str
    content_sha256: str | None
    expires_at: datetime


class ActionPermit(BaseModel):
    permit_id: str
    run_id: str
    action_id: str
    tool: str
    arguments_sha256: str
    observation_revision: int
    coordinate_space_id: str | None
    window_handle: int | None
    process_id: int | None
    expires_at: datetime
    max_uses: int = 1
    uses: int = 0
    requires_human_confirmation: bool
    confirmation: HumanConfirmation | None = None
```

Validation must check:

1. permit exists;
2. same `run_id`;
3. same `action_id`;
4. same tool;
5. exact argument hash;
6. current observation revision;
7. current coordinate-space identifier;
8. expected foreground window;
9. expected process;
10. not expired;
11. use count available;
12. required confirmation present and unexpired.

```python
def validate_permit(
    permit: ActionPermit,
    action: ComputerAction,
    current: Observation,
    arguments_sha256: str,
) -> None:
    if permit.run_id != action.run_id:
        raise PermitMismatch("run_id")
    if permit.action_id != action.action_id:
        raise PermitMismatch("action_id")
    if permit.arguments_sha256 != arguments_sha256:
        raise PermitMismatch("arguments_sha256")
    if permit.observation_revision != current.revision:
        raise StaleObservationError()
    if permit.uses >= permit.max_uses:
        raise PermitAlreadyUsed()
    if permit.expires_at <= utc_now():
        raise PermitExpired()

    if permit.coordinate_space_id:
        if permit.coordinate_space_id != current.coordinate_space_id:
            raise CoordinateSpaceChanged()

    if permit.window_handle is not None:
        actual = current.foreground_window
        if not actual or actual.handle != permit.window_handle:
            raise WrongWindowError()

    if permit.process_id is not None:
        actual = current.foreground_window
        if not actual or actual.process_id != permit.process_id:
            raise WrongProcessError()
```

---

## 10. State machine

Implement explicit states:

```text
IDLE
LISTENING
TASK_ACCEPTED
PLANNING
PLAN_REVIEW
WAITING_FOR_USER
READY_TO_EXECUTE
ACTION_PROPOSED
ACTION_REVIEW
WAITING_FOR_CONFIRMATION
ACTION_EXECUTING
VERIFYING
CHECKPOINTED
RECOVERY
ROLLBACK
COMPLETION_REVIEW
COMPLETED
CANCELLED
PAUSED
ABORTED
```

### 10.1 Locks

#### Planning lock

A plan cannot become active until the Strategist signs it.

#### Action lock

No mutating action is dispatched without a valid permit.

#### Verification lock

An action cannot transition to `VERIFIED` without evidence.

#### Escalation lock

The runtime attempts bounded recovery before asking the user, unless policy requires immediate confirmation or pause.

### 10.2 State transition rules

```python
VALID_ACTION_TRANSITIONS = {
    "PROPOSED": {"PERMITTED", "BLOCKED", "CANCELLED"},
    "PERMITTED": {"DISPATCHED", "EXPIRED", "CANCELLED"},
    "DISPATCHED": {
        "COMPLETED",
        "FAILED",
        "CANCELLED",
        "UNKNOWN_AFTER_CRASH",
    },
    "COMPLETED": {
        "VERIFIED",
        "RETRY",
        "REPAIR",
        "ROLLBACK",
    },
    "FAILED": {"RETRY", "REPAIR", "ABORT"},
    "UNKNOWN_AFTER_CRASH": {
        "RECONCILED",
        "ASK_USER",
        "ABORT",
    },
}
```

Only the Coordinator may perform transitions.

### 10.3 Role isolation

The Strategist cannot invoke:

```text
click
type
keypress
launch
file_write
send
delete
purchase
```

The Executor cannot:

```text
issue permits
change policy
mark its own action verified
modify the ledger outside the Coordinator API
interpret screen content as authorization
```

Enforce this through a runtime capability registry, not only system prompts.

---

## 11. Safe overlap scheduler

The valid overlap is:

```text
Observation N
    ↓
Strategist prepares candidate N+1
    ↓
Coordinator validates policy
    ↓
Permit issued for N+1
    ↓
Executor executes N+1
    ↓
Executor captures evidence
    ↓
Verifier validates N+1
```

While an already-permitted action executes, the Strategist may:

- prepare expected-result predicates;
- prepare recovery alternatives;
- analyze risk;
- prepare user-facing status;
- draft a candidate next action marked `uncommitted`.

It may not authorize a state-dependent new mutation using an observation that has not yet been captured and verified.

Only one physical desktop mutation may be in flight.

---

## 12. Windows executor

### 12.1 DPI awareness

Set process DPI awareness before creating helper windows:

```python
# packages/windows_executor/dpi.py
import ctypes


DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = ctypes.c_void_p(-4)


def enable_per_monitor_v2() -> None:
    ok = ctypes.windll.user32.SetProcessDpiAwarenessContext(
        DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
    )
    if not ok:
        raise RuntimeError("Unable to enable Per-Monitor V2 DPI awareness")
```

This must be tested on supported Windows builds. If it fails, the executor must enter safe mode rather than silently applying coordinates.

### 12.2 Coordinate metadata

Replace the fixed `1280 × 720` assumption with:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class CoordinateSpace:
    source_left: int
    source_top: int
    source_width: int
    source_height: int
    model_width: int
    model_height: int
    dpi_x: int | None
    dpi_y: int | None
    topology_hash: str
    transform_version: str = "virtual-desktop-affine-v1"


def model_to_screen(
    x_model: float,
    y_model: float,
    space: CoordinateSpace,
) -> tuple[int, int]:
    x = space.source_left + round(
        x_model * space.source_width / space.model_width
    )
    y = space.source_top + round(
        y_model * space.source_height / space.model_height
    )
    return x, y
```

Reject an action when:

- display topology changed;
- monitor metadata is missing;
- screenshot is stale;
- target is outside the virtual desktop;
- DPI awareness is unknown;
- active monitor changed unexpectedly.

### 12.3 Screenshot capture

MVP:

- use `mss` for still screenshots;
- capture the virtual desktop and monitor metadata;
- store the exact mapping used;
- hash the resulting PNG;
- store artifacts outside the ledger.

Future native capture:

- Windows.Graphics.Capture for window/display capture;
- Desktop Duplication for high-frequency full-desktop capture.

Do not claim high-frequency capture until the native path is tested.

### 12.4 UI Automation element references

```python
class ElementRef(BaseModel):
    ref_id: str
    window_handle: int
    process_id: int
    runtime_id: list[int] | None
    automation_id: str | None
    control_type: str
    name: str | None
    class_name: str | None
    bounding_rect: tuple[int, int, int, int] | None
    supported_patterns: set[str]
    observation_revision: int
    structural_path: list[int] | None
```

Re-resolution order:

1. window handle;
2. process ID;
3. RuntimeId;
4. AutomationId;
5. structural path;
6. control type plus normalized name;
7. rectangle proximity only as a last resort.

Runtime IDs are session-scoped and cannot be treated as globally permanent.

### 12.5 Semantic action hierarchy

Use this order:

```text
1. UI Automation control pattern
2. Browser DOM/API
3. Keyboard shortcut
4. Coordinate interaction
5. Pause and escalate
```

UIA patterns include:

```text
Invoke
Value
Text
Selection
SelectionItem
ExpandCollapse
Scroll
Window
Transform
Toggle
LegacyIAccessible
```

Example:

```python
def invoke_element(element_ref: ElementRef) -> ActionResult:
    element = resolve_element(element_ref)
    patterns = element.supported_patterns()

    if "Invoke" in patterns:
        element.invoke()
        mechanism = "Invoke"
    elif "LegacyIAccessible" in patterns:
        element.default_action()
        mechanism = "LegacyIAccessible"
    elif "SelectionItem" in patterns:
        element.select()
        mechanism = "SelectionItem"
    else:
        raise UnsupportedPatternError(element_ref.ref_id)

    return ActionResult(
        success=True,
        mechanism=mechanism,
        target_ref=element_ref.ref_id,
    )
```

The concrete `uiautomation` method names must be verified against the selected locked package version before implementation. The runtime behavior is mandatory: re-resolve, inspect pattern availability, act semantically, return the mechanism, and capture post-state.

### 12.6 Window focus

Before every focus-dependent mutation:

1. inspect current foreground window;
2. compare handle and process ID;
3. attempt focus;
4. verify foreground state;
5. abort if the wrong window is active.

Title substrings are not authoritative.

Pause for:

```text
UAC
Windows Hello
MFA
credential dialogs
secure desktop
lock screen
elevated windows
```

Do not attempt to bypass UIPI or security prompts.

### 12.7 Application launch

Never execute model-provided shell strings such as:

```python
subprocess.Popen(f'start "" "{app_name}"', shell=True)
```

Use a local allowlisted launch registry:

```python
class LaunchTarget(BaseModel):
    target_id: str
    display_name: str
    executable: str
    expected_process_name: str
    allowed: bool = True
```

The model requests a `target_id`, never an arbitrary command.

Launch sequence:

1. resolve target from local registry;
2. launch without shell interpretation where possible;
3. record child process ID;
4. locate its window;
5. wait for readiness;
6. verify foreground identity;
7. capture a fresh observation;
8. authorize later actions only against the verified process/window.

### 12.8 Cancellation-safe input

Cancellation must:

- release all held mouse buttons;
- release all held keys;
- stop text input;
- clear queued actions;
- restore clipboard state in `finally`;
- persist `user_cancelled`;
- update the UI immediately.

### 12.9 Unicode text input

Clipboard insertion is allowed only as a controlled transaction:

1. capture permitted clipboard state;
2. mark clipboard agent-owned;
3. verify target focus;
4. paste;
5. verify target value through UIA where available;
6. restore clipboard in `finally`;
7. redact text from logs and evidence.

Passwords, MFA codes, and secrets are not ordinary `type` actions. The initial policy is user-entered credentials only.

---

## 13. Browser automation

Use Playwright for agent-owned browser sessions.

```python
context = await chromium.launch_persistent_context(
    user_data_dir=str(profile_dir),
    channel="msedge",
    headless=False,
)
```

Do not use the user’s normal browser profile.

Browser hierarchy:

```text
1. Playwright DOM/API
2. WebView2 or Chromium CDP
3. UI Automation
4. keyboard shortcuts
5. coordinates
```

### 13.1 CDP policy

`connectOverCDP` is Chromium-only and lower fidelity than Playwright’s native protocol. Use it only for explicit attach scenarios.

WebView2 attach requires explicit application configuration such as:

```text
WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port=<port>
WEBVIEW2_USER_DATA_FOLDER=<dedicated-folder>
```

Do not infer WebView2 merely from uncovered screen area.

### 13.2 Browser restrictions

Implement:

```text
domain allowlist
navigation timeout
download size limit
request size limit
download directory restriction
authentication pause
dedicated profile
cookie/storage isolation
```

No browser navigation or upload is allowed solely because page content requests it.

---

## 14. Persistence and artifacts

### 14.1 Local paths

```text
%LOCALAPPDATA%\Compuse\agent.db
%LOCALAPPDATA%\Compuse\artifacts\
%LOCALAPPDATA%\Compuse\screenshots\
%LOCALAPPDATA%\Compuse\voice\
%LOCALAPPDATA%\Compuse\checkpoints\
%LOCALAPPDATA%\Compuse\logs\
%LOCALAPPDATA%\Compuse\browser-profiles\
```

### 14.2 SQLite policy

Only the Coordinator writes the authoritative database.

At startup:

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = FULL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;
```

The runtime must:

- verify SQLite is 3.51.3 or later;
- preserve `.db`, `-wal`, and `-shm` together;
- use explicit transactions;
- avoid concurrent process writers;
- test crash recovery;
- never copy only the main database file while WAL mode is active.

### 14.3 Schema

```sql
CREATE TABLE events (
    event_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    actor TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(run_id, seq)
);

CREATE TABLE actions (
    action_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    arguments_json TEXT NOT NULL,
    arguments_sha256 TEXT NOT NULL,
    state TEXT NOT NULL,
    observation_revision INTEGER,
    permit_id TEXT,
    dispatched_at TEXT,
    completed_at TEXT,
    verified_at TEXT
);

CREATE TABLE permits (
    permit_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    action_id TEXT NOT NULL,
    arguments_sha256 TEXT NOT NULL,
    observation_revision INTEGER NOT NULL,
    expires_at TEXT NOT NULL,
    max_uses INTEGER NOT NULL,
    uses INTEGER NOT NULL DEFAULT 0,
    human_confirmation_id TEXT
);
```

Additional tables:

```text
runs
tasks
plans
subtasks
observations
verification_results
evidence
human_confirmations
checkpoints
provider_attempts
voice_commands
memory_entries
desktop_sessions
```

### 14.4 Append-only events

Persist:

```text
run_created
plan_drafted
plan_signed
observation_captured
action_proposed
permit_issued
confirmation_requested
confirmation_received
action_dispatched
action_completed
action_failed
verification_requested
verification_completed
checkpoint_created
recovery_started
escalation_requested
user_cancelled
run_completed
```

Corrections are new events, never edits to old events.

### 14.5 Artifact records

Each artifact stores:

```text
artifact_id
kind
path/reference
sha256
run_id
action_id
observation_revision
created_at
redaction_status
retention_status
```

Artifacts include:

```text
screenshots
UIA trees
browser DOM snapshots
download hashes
clipboard metadata
verification reports
audio only if explicitly enabled
```

---

## 15. Verification

Every mutation requires:

```text
pre-observation
action event
post-observation
verification result
```

A provider response or dispatched input event is not evidence of success.

### 15.1 Deterministic verification adapters

Implement:

```text
UIA property/value
UIA control existence/disappearance
foreground process/window
window title
browser DOM predicate
clipboard value
file existence/hash
download hash
application notification
test result
```

### 15.2 Verification result

```python
class Evidence(BaseModel):
    kind: str
    artifact_ref: str
    artifact_sha256: str
    validated: bool
    origin: ContentOrigin


class VerificationResult(BaseModel):
    action_id: str
    outcome: Literal[
        "success",
        "retry",
        "repair",
        "rollback",
        "ask_user",
        "abort",
    ]
    evidence: list[Evidence]
    notes: str
```

Prefer deterministic verification. Use a separate Verifier model only when the deterministic adapters cannot decide.

The Executor cannot mark its own action verified.

---

## 16. Risk and confirmation policy

Require exact human confirmation by default for:

```text
send
submit
purchase
pay
delete
publish
deploy
upload
share
accept terms
close unsaved work
install software
change security settings
enter credentials
transmit sensitive data
```

Confirmation is bound to:

```text
run ID
action ID
target
arguments/content hash
risk class
expiration
exact confirmation phrase
```

Example UI/speech prompt:

```text
The agent is ready to click “Submit”.
This will send the form to the external website.
Say “confirm submit” or choose Confirm.
```

Generic “yes” must not authorize an action whose target or hash changed.

---

## 17. Recovery and crash semantics

Recovery categories:

```text
retry
repair
rollback
research_needed
ask_user
abort
```

Rules:

- retry only idempotent actions or actions with evidence of transient failure;
- repair focus or re-resolve a target only when policy allows;
- rollback only when a verified inverse exists;
- ask the user for authentication, ambiguity, or consequential confirmation;
- abort when policy cannot be satisfied.

After restart:

1. load the latest checkpoint;
2. find actions dispatched but not verified;
3. capture a fresh observation;
4. compare environment and evidence;
5. never automatically repeat uncertain external side effects;
6. reconcile deterministically where possible;
7. ask the user when state remains uncertain.

An action that may have sent, purchased, deleted, or submitted must be treated as `UNKNOWN_AFTER_CRASH`, not failed.

---

## 18. Watchdog

Detect and persist:

```text
no workspace update
no inter-lobe message
repeated plan hash
repeated failed tool call
expired permit
missed heartbeat
unchanged screen after expected mutation
repeated click at same coordinate
wrong foreground window
repeated screenshot with no progress
permit/revision loop with no evidence
```

Watchdog behavior:

```text
first stall → request observation
second stall → cancel speculative work
third stall → enter RECOVERY
unsafe/ambiguous state → pause and ask user
```

No infinite retry loops.

---

## 19. Provider routing

Configure separate logical routes:

```text
STRATEGIST_PROVIDER
EXECUTOR_PROVIDER
VERIFIER_PROVIDER
VOICE_STT_PROVIDER
VOICE_TTS_PROVIDER
EMBEDDING_PROVIDER
```

Provider-specific formats must remain inside adapters.

Track every provider attempt:

```text
run_id
call_id
provider alias
model
request hash
streaming flag
latency
token usage
status
error type
timestamps
```

### 19.1 OpenAI adapter

Normalize typed `computer_call` actions, preserving:

```text
provider call ID
previous response ID
provider action index
pending safety checks
original provider payload
```

Provider safety checks are advisory metadata. Local permits remain authoritative.

### 19.2 Anthropic adapter

Normalize member-tool or dated computer-use actions while preserving:

```text
provider tool-use ID
batch index
ordered execution
stop-on-first-failure behavior
provider screenshot result
```

If an ordered provider batch contains a failure, later actions are marked `NOT_EXECUTED`; they are not silently attempted.

### 19.3 Multimodal validation

Before provider dispatch:

```text
image MIME type
image dimensions
payload size
artifact existence
artifact/run association
redaction status
provider capability
```

The old text-only rejection must not simply be removed. Add controlled artifact references, limits, hashing, and capability checks.

---

## 20. Voice

### 20.1 MVP pipeline

```text
push-to-talk
    ↓
microphone capture
    ↓
streaming STT
    ↓
partial transcript UI
    ↓
final transcript command parser
    ↓
Coordinator
    ↓
streamed TTS
    ↓
speaker
```

Emergency commands bypass the model:

```text
stop
cancel
pause
abort
do not continue
```

On emergency stop:

1. cancel provider calls;
2. stop queued actions;
3. release keys and mouse buttons;
4. stop TTS;
5. persist cancellation;
6. update UI.

### 20.2 Azure Speech path

Azure Speech supports continuous recognition, interim `recognizing` events, final `recognized` events, cancellation, push/pull audio, and streamed synthesis.

Do not authorize mutations from partial transcripts.

### 20.3 Local Windows speech path

Treat these as separate options:

```text
Windows.Media.SpeechRecognition:
    broader Windows Runtime path; test packaging and availability

Windows AI streaming recognition:
    experimental; Windows 11 24H2 and Windows App SDK 1.7.1+
    behind a feature flag
```

The Electron MVP must not require the experimental Windows AI API.

### 20.4 Barge-in and echo cancellation

MVP:

- push-to-talk;
- local emergency hotkey;
- stop TTS immediately;
- no always-listening mode.

Later:

- VAD;
- AEC using speaker reference;
- continuous recognition;
- wake word;
- voice confirmation.

Audio retention defaults to discard after transcription. Do not store raw audio without explicit user configuration.

---

## 21. Electron security

Renderer configuration:

```text
contextIsolation: true
nodeIntegration: false
sandbox: true where compatible
```

Expose only narrow typed APIs:

```typescript
contextBridge.exposeInMainWorld("compuse", {
  startRun: (request: StartRunRequest) =>
    ipcRenderer.invoke("compuse:start-run", request),

  cancelRun: (runId: string) =>
    ipcRenderer.invoke("compuse:cancel-run", runId),

  confirmPermit: (request: ConfirmationRequest) =>
    ipcRenderer.invoke("compuse:confirm-permit", request),

  subscribeRun: (runId: string, callback: (event: RunEvent) => void) => {
    const channel = `compuse:run:${runId}`;
    const listener = (_event: Electron.IpcRendererEvent, value: RunEvent) =>
      callback(value);
    ipcRenderer.on(channel, listener);
    return () => ipcRenderer.removeListener(channel, listener);
  },
});
```

Do not expose the entire `ipcRenderer`. Validate payloads again in the main process and Coordinator.

---

## 22. Security boundaries

### 22.1 Windows integrity

Initial supported scope:

```text
same-integrity standard desktop applications
```

Pause/escalate for:

```text
elevated applications
UAC
Windows Hello
credential dialogs
secure desktop
locked workstation
```

Do not run the entire product as administrator.

If elevated support is later required, build a narrow, signed UIAccess helper requiring:

- Authenticode signing;
- secure installation path;
- correct manifest;
- separate security review;
- no direct model/network access.

### 22.2 Sensitive information

Initial policy:

- no model-visible passwords;
- no model-visible MFA codes;
- no automatic credential entry;
- user types secrets manually;
- pause screenshots during credential entry where possible;
- never put secrets in logs, events, prompts, or telemetry.

Screen redaction remains defense-in-depth, not a guarantee.

### 22.3 Shell

Shell execution is disabled for MVP.

If later added, require:

```text
command allowlist
working-directory restriction
timeout
output-size limit
network policy
sandbox
human confirmation
separate high-risk permit
full audit trail
```

### 22.4 Browser/network

Require:

```text
domain allowlist
download restrictions
request and response size limits
timeouts
dedicated profile
authentication pause
```

---

## 23. Desktop-session locking

Every run obtains a lock:

```text
device_id
desktop_session_id
interactive_user
foreground-session identity
executor_instance_id
```

Only one run may hold the mutation lease for a physical desktop session.

The lock must be released on:

```text
run completion
run cancellation
executor crash
watchdog timeout
process shutdown
```

On abnormal release, the next run must capture a fresh observation before acting.

Per-run serialization is not sufficient protection for a shared physical desktop.

---

## 24. UI implementation

Display:

```text
task and subtask
Strategist status
Executor status
Verifier status
current application/window
environment revision
permit status
confirmation state
voice state
latest evidence
recovery state
```

Evidence views:

```text
latest screenshot
before/after screenshot
UIA tree
action timeline
permit details
verification result
failure/recovery history
```

Confirmation card:

```text
exact action
target
risk
content/data transmission
reversibility
expiration
required phrase
```

Do not display hidden chain-of-thought. Show concise operational summaries.

---

## 25. API surface

Local Coordinator API:

```text
POST /v1/computer/runs
POST /v1/computer/runs/{id}/observe
POST /v1/computer/runs/{id}/propose
POST /v1/computer/runs/{id}/permit
POST /v1/computer/runs/{id}/execute
POST /v1/computer/runs/{id}/verify
POST /v1/computer/runs/{id}/cancel
GET  /v1/computer/runs/{id}
GET  /v1/computer/runs/{id}/events
GET  /v1/computer/runs/{id}/artifacts/{artifact_id}
WS   /v1/computer/runs/{id}/stream
```

Every request carries:

```text
device_id
desktop_session_id
run_id
correlation_id
executor_instance_id
```

Use correlation IDs across:

```text
Electron
Coordinator
provider
executor
verifier
voice
artifact store
```

---

## 26. Observability

Use OpenTelemetry after the local state machine is stable.

Spans:

```text
run
strategist_call
executor_action
verification
voice_stt
voice_tts
provider_attempt
artifact_capture
confirmation_wait
recovery_attempt
```

Attributes:

```text
run.id
task.id
action.id
permit.id
lobe
provider
model
environment.revision
window.handle
process.id
action.kind
risk.class
verification.outcome
```

Never include raw:

```text
passwords
message bodies
screen text
screenshots
microphone audio
```

Use artifact IDs, hashes, redaction status, and aggregate metrics.

---

## 27. Implementation phases

### Phase 0 — Baseline

1. Create a disposable Windows VM/profile.
2. Run the existing NeuralAgent flow.
3. Record screenshots, UI trees, actions, focus, latency, and failures.
4. Build the failure catalog:
   - launch;
   - focus;
   - UIA;
   - Unicode typing;
   - multi-monitor;
   - DPI;
   - custom controls;
   - crash;
   - cancellation;
   - UAC;
   - network timeout;
   - provider timeout.

Do not use production credentials.

### Phase 1 — Deterministic executor

Implement without models:

- display metadata;
- screenshots;
- UIA snapshots;
- stable element references;
- semantic invoke/set/select/toggle;
- safe typing;
- focus validation;
- application registry;
- cancellation;
- artifact storage;
- before/action/after journal;
- dry-run mode.

### Phase 2 — Coordinator and ledger

Implement:

- protocol;
- SQLite schema;
- state machine;
- desktop lock;
- permits;
- action transitions;
- checkpoints;
- watchdog;
- deterministic verifier;
- fake executor/provider tests.

### Phase 3 — Strategist integration

Add:

- plan generation;
- risk classification;
- action proposal;
- required evidence;
- confirmation policy;
- bounded overlap.

Initially use one model if necessary, while retaining separate runtime capabilities.

### Phase 4 — Provider adapters

Add:

- OpenAI computer-call adapter;
- Anthropic computer-use adapter;
- generic OpenAI-compatible adapter;
- multimodal artifact handling;
- provider-attempt telemetry.

### Phase 5 — Browser

Add:

- Playwright persistent profile;
- DOM actions;
- download policy;
- CDP attach;
- WebView2 explicit attach;
- browser evidence verification.

### Phase 6 — Voice

Add:

- push-to-talk;
- streaming STT;
- streamed TTS;
- local emergency stop;
- confirmation phrases;
- optional AEC/VAD.

### Phase 7 — Product packaging

Add:

- installer;
- pinned dependencies;
- signed binaries;
- crash recovery;
- safe mode;
- privacy settings;
- artifact retention controls.

### Phase 8 — Advanced deployment

Only after MVP safety tests pass:

- FlaUI sidecar;
- optional UIAccess helper;
- Windows Sandbox/VM integration;
- Postgres synchronization;
- remote gateway;
- multi-device coordination.

---

## 28. Testing strategy

### 28.1 Unit tests

Use fakes for:

```text
screen capture
UIA tree
window manager
input adapter
provider
verifier
clock
ledger
```

Test:

- malformed envelopes;
- sender/recipient violations;
- sequence gaps;
- duplicate delivery;
- stale observations;
- permit expiry;
- argument hash mismatch;
- wrong foreground window;
- coordinate-space changes;
- confirmation binding;
- action-state transitions;
- cancellation cleanup;
- watchdog recovery;
- batch stop-on-first-failure;
- executor self-permit attempts;
- executor self-verification attempts.

### 28.2 Windows integration matrix

Native applications:

```text
Notepad
Calculator
Paint
File Explorer
Settings
Win32 test app
WinForms test app
WPF test app
Qt test app
Electron test app
```

Browser:

```text
Edge dedicated profile
Chrome/Chromium dedicated profile
WebView2 sample
downloads
file chooser
popups
new tabs
permission dialogs
```

Display:

```text
single monitor
dual monitor
negative virtual-desktop coordinate
100%, 125%, 150%, 200% DPI
portrait display
hot-plug
resolution change
DPI change
```

Privilege:

```text
same-integrity application
elevated application
UAC
Windows Hello
credential dialog
secure desktop
locked workstation
RDP session
```

### 28.3 Security tests

- web page says “ignore previous instructions”;
- document contains malicious instructions;
- screenshot contains fake approval text;
- provider emits malformed action;
- provider requests unsupported action;
- duplicated provider call;
- stale permit after focus changes;
- action after user cancellation;
- crash immediately after dispatch;
- uncertain submit after restart;
- attempted password typing;
- attempted upload of sensitive file;
- attempted shell execution;
- attempted action against an elevated window.

### 28.4 Voice tests

- partial transcript must not mutate;
- final transcript creates task;
- “stop” interrupts TTS;
- stop works while executor is dragging;
- agent TTS is not recognized as user command;
- Bluetooth microphone/speaker latency;
- device switching;
- push-to-talk release;
- expired voice confirmation;
- changed action after spoken confirmation.

---

## 29. Evaluation

Compare:

```text
single-agent sequential baseline
existing NeuralAgent loop
dual-lobe gated mode
dual-lobe bounded-overlap mode
dual-lobe with deterministic verification
dual-lobe with Verifier model
voice-enabled mode
voice-disabled mode
```

Measure:

```text
task success
false-success rate
unsafe action rate
unauthorized side-effect rate
verification precision
recovery success
duplicate side effects
time to first action
time between verified actions
provider latency
voice latency
barge-in latency
cost
escalation rate
context size
Strategist overhead
```

Task suite:

```text
native controls
browser navigation
forms
file operations
window switching
multi-monitor
DPI scaling
custom-rendered controls
application crash
network failure
prompt injection
UAC/authentication
destructive actions
voice interruption
post-crash reconciliation
```

Do not claim improvement until these measurements exist.

Release thresholds must be defined before release. The research does not provide valid thresholds, so the team must establish them from baseline measurements.

---

## 30. Deployment and recovery

### 30.1 Safe mode

Safe mode starts with:

```text
no external side effects
no shell
screenshots/UIA only
human confirmation for every mutation
```

### 30.2 Installer

The installer must eventually include:

```text
Electron application
Python runtime/executor
locked dependencies
browser policy
voice dependencies
database migration
artifact directories
configuration migration
first-run privacy controls
crash recovery registration
```

No independently verified one-click installer or signing pipeline exists yet. These must be implemented and tested.

### 30.3 Restart handling

On restart:

1. restore database and checkpoints;
2. identify pending/unknown actions;
3. capture fresh observation;
4. reconcile using deterministic evidence;
5. never repeat uncertain external side effects automatically;
6. require user resolution when ambiguity remains.

---

## 31. Remaining unresolved gaps

These items cannot be resolved from the available research alone and require implementation or controlled testing.

### 31.1 Runtime compatibility

The referenced repositories were inspected but not executed on Windows in this research. Unverified:

- actual installation;
- current build behavior;
- provider compatibility;
- UIA coverage on target applications;
- Electron packaging;
- latency and memory usage;
- crash recovery.

### 31.2 Exact dependency versions

The research did not establish exact compatible versions for:

- Electron;
- Node.js;
- Python;
- React;
- FastAPI;
- Pydantic;
- SQLAlchemy;
- `uiautomation`;
- `pywinauto`;
- Playwright;
- Azure Speech SDK;
- OpenTelemetry.

Resolve these in a Windows CI environment and commit lockfiles. Do not infer versions from this document.

### 31.3 UIA application coverage

No reliable percentage is known for applications exposing sufficient UIA patterns. Build a supported-application matrix before expanding scope.

### 31.4 Secure desktop detection

Reliable handling of UAC, Windows Hello, credential dialogs, lock screen, and RDP edge cases requires actual Windows testing.

### 31.5 Screen redaction

No complete redaction mechanism has been verified. Implement defense-in-depth, but do not represent redaction as a guarantee.

### 31.6 Credential isolation

No complete vault or secure-entry design is established. Initial behavior must be manual user entry with model and ledger exclusion.

### 31.7 Voice quality

AEC, VAD, Bluetooth latency, microphone switching, and TTS self-triggering require hardware testing.

### 31.8 Model independence

Separate Strategist and Verifier providers do not guarantee independent errors. Measure false-success behavior empirically.

### 31.9 Artifact retention

Retention, encryption, deletion, backup, and export policies remain product decisions.

### 31.10 SQLite/Postgres synchronization

Local SQLite is authoritative for the MVP. Replication or server synchronization is not defined and must not be assumed safe.

### 31.11 License compatibility

Verified or reported licenses include:

```text
NeuralAgent: MIT
uiautomation: Apache 2.0
pywinauto: BSD 3-Clause
dual-lobe documentation: CC BY-NC-SA 4.0
```

FlaUI and dual-lobe-proxy license details require direct legal review before redistribution. Implement architecture independently where licensing is uncertain. Do not copy CC BY-NC-SA material into a commercial product without approval.

---

## 32. Required acceptance criteria

The MVP is not complete until all of the following are true:

### Executor

- [ ] A screenshot includes monitor origin, dimensions, DPI metadata, coordinate-space ID, and hash.
- [ ] Coordinate actions are rejected when the display topology changes.
- [ ] UIA actions re-resolve the element before acting.
- [ ] UIA actions verify the required pattern.
- [ ] Focus-dependent actions verify foreground handle and process.
- [ ] Application launch uses an allowlisted target, not a shell string.
- [ ] Cancellation releases held keys and mouse buttons.
- [ ] Clipboard state is restored in all paths.
- [ ] Elevated/secure desktop surfaces cause pause/escalation.

### Coordinator

- [ ] Only the Coordinator can issue permits.
- [ ] Only the Coordinator writes the authoritative ledger.
- [ ] Every mutation has pre-observation, action event, post-observation, and verification result.
- [ ] Every permit binds action ID, argument hash, revision, and expiration.
- [ ] One physical desktop mutation can be in flight.
- [ ] Duplicate messages are idempotent.
- [ ] Restart never blindly repeats an uncertain external side effect.
- [ ] Watchdog prevents infinite loops.

### Safety

- [ ] Consequential operations require exact confirmation.
- [ ] Environment content cannot grant authorization.
- [ ] Passwords and MFA codes are excluded from model-visible logs and artifacts.
- [ ] Shell execution is disabled.
- [ ] Browser profiles are isolated.
- [ ] Prompt-injection tests pass without granting unauthorized actions.

### Voice

- [ ] Push-to-talk works.
- [ ] Partial transcripts never mutate the desktop.
- [ ] Emergency stop bypasses the model.
- [ ] TTS can be interrupted.
- [ ] Confirmation is bound to an unexpired exact action.
- [ ] Raw audio is not retained by default.

### Evaluation

- [ ] Baseline measurements exist.
- [ ] Dual-lobe measurements exist.
- [ ] False-success and unauthorized-side-effect rates are measured.
- [ ] Post-crash reconciliation is tested.
- [ ] Release thresholds are documented and met.

---

## 33. Final implementation priority

Implement in this order:

```text
1. deterministic Windows executor
2. observation and coordinate model
3. UIA semantic references/actions
4. SQLite ledger and checkpoints
5. Coordinator state machine
6. permits and human confirmation
7. deterministic verification
8. watchdog and recovery
9. Strategist integration
10. provider adapters
11. Playwright/CDP browser layer
12. push-to-talk voice
13. packaging/signing
14. optional FlaUI/UIAccess/server features
```

The fundamental rule is:

```text
No permit without current state.
No mutation without a permit.
No success without evidence.
No retry after uncertainty without reconciliation.
No environment content can authorize an action.
```

This architecture preserves the useful Electron/React and Windows automation foundations while replacing the sequential, unverified NeuralAgent loop with a durable, typed, role-isolated, permit-bound computer-use runtime.