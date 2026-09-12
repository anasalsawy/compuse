# Implementation Plan: Windows Dual-Lobe Computer-Use Agent

## Task Summary

Build a Windows desktop computer-use agent with:

1. **Electron and React desktop UI**
2. **Windows-native computer control**
   - Windows UI Automation
   - Screenshot capture
   - Mouse and keyboard input
   - Application launch and window focus
   - Browser automation
3. **Real-time voice interaction**
   - Streaming speech-to-text
   - Streaming text-to-speech
   - Barge-in and interruption
   - Voice confirmations
4. **Dual-lobe execution**
   - Strategist lobe for planning, risk analysis, authorization, verification, and memory
   - Executor lobe for desktop actions and other side effects
5. **Safety and reliability controls**
   - Planning, action, verification, and escalation locks
   - Typed inter-lobe messages
   - Action permits
   - Append-only event ledger
   - Durable checkpoints
   - Independent evidence verification
   - Watchdog and recovery
   - Human confirmation for consequential actions
6. **Provider and persistence infrastructure**
   - Separate model routes for Strategist, Executor, and Verifier
   - OpenAI-compatible gateway patterns
   - Local-first persistence with optional Postgres
   - Evidence and artifact storage
   - Per-device desktop-session serialization

The implementation must not be a simple second LLM call around the existing NeuralAgent loop. NeuralAgent currently uses a sequential polling loop, while the dual-lobe design requires explicit role separation, permission gates, verification, durable state, and bounded overlap between reasoning and execution.

The practical target is:

> Eliminate unnecessary idle time by allowing the Strategist to prepare safe follow-up work while the Executor performs an already-authorized action, without allowing stale or unverified state to authorize a new side effect.

A literally zero-latency “no thinking gap” is not achievable when new screenshots, model responses, verification, or human confirmation are required. The implementation should optimize for **no unnecessary idle gap** while preserving correctness and safety.

---

## Key Findings

### 1. Existing repositories provide complementary foundations

#### NeuralAgent provides

- Electron desktop shell
- React interface
- FastAPI backend
- Python desktop automation daemon
- Screenshot-based control
- PyAutoGUI input
- Windows application launch and focus
- Windows UI Automation extraction
- Browser/background automation
- Task, plan, and subtask lifecycle
- Multiple LLM provider configuration

Important existing paths include:

```text
desktop/main.js
desktop/electron/preload.js
desktop/neuralagent-app/src/
desktop/aiagent/main.py
desktop/aiagent/ui_extraction.py
backend/main.py
backend/routers/aiagent/
backend/schemas/aiagent.py
backend/utils/llm_provider.py
backend/utils/procedures.py
```

#### dual-lobe provides

- Strategist/Executor separation
- Exclusive tool ownership
- Planning lock
- Action lock
- Verification lock
- Escalation lock
- Typed protocol envelopes
- Append-only event ledger
- Durable checkpoints
- Evidence and claim model
- Watchdog signals
- Recovery and escalation concepts

Important specification files include:

```text
SPEC.md
EXPERIMENTS.md
docs/production-architecture-and-platform-integration.md
docs/runtime-and-oversight-reference.md
```

#### dual-lobe-proxy provides

- OpenAI-compatible gateway
- Provider registry
- Run identity
- Streaming response patterns
- Correlation headers
- Persistent Postgres models
- Background B-lobe worker
- Outbox/job queue
- Shared memory
- Director mode
- Evidence and claim structures
- Per-run serialization
- Telemetry

Important implementation areas include:

```text
src/dual_lobe/api/
src/dual_lobe/b/
src/dual_lobe/core/
src/dual_lobe/director/
src/dual_lobe/evidence/
src/dual_lobe/provider/
src/dual_lobe/state/
```

### 2. NeuralAgent’s current execution loop is sequential

The current Python loop follows this pattern:

```python
while True:
    current_subtask_response = get_current_subtask()
    action_response = get_next_step()
    perform_action(action_response)
```

Consequences:

- The model is idle while desktop actions execute.
- The desktop agent is idle while the model generates.
- There is no Strategist/Executor overlap.
- There is no action permit lifecycle.
- There is no independent verification gate.
- There is no durable local action ledger.
- There is no device-level desktop lock.
- There is no explicit watchdog or recovery state machine.

Replace this polling model with a local event-driven runtime using a typed protocol over local IPC. The research identified named pipes, local WebSocket, gRPC, stdio, and equivalent local sockets as viable communication patterns; the exact transport remains an implementation choice.

### 3. Tool ownership must be enforced in code

The Strategist and Executor must not share unrestricted access to side-effecting tools.

#### Strategist-owned capabilities

Examples:

```text
task_decomposition
web_research
memory_search
risk_classifier
policy_checker
source_verifier
plan_critic
artifact_validator
test_runner
stall_detector
memory_curator
approval_gate
state_verifier
```

#### Executor-owned capabilities

Examples:

```text
click
double_click
drag
type
keypress
launch_application
focus_window
browser_action
file_write
file_edit
send_message
submit_form
delete
purchase
deploy
```

#### Shared observation substrate

Both lobes may receive controlled observations such as:

```text
screenshot
UI Automation tree
foreground window
process state
clipboard metadata
browser state
tool result
```

Shared observations must go through the observation layer. They must not create a hidden route around the Tool Router or permit system.

### 4. The current dual-lobe-proxy normal mode is not sufficient

The proxy’s normal mode follows:

```text
A responds
B reviews in the background
```

This is useful for advisory observation, but it cannot prevent an action already delivered to the desktop.

Computer-use mode must instead implement:

```text
Strategist proposes or reviews
Strategist permits
Executor executes
Executor captures evidence
Strategist verifies
Run advances
```

The existing proxy’s Director mode is closer to the desired behavior, but it currently handles text and generic tool calls rather than Windows UI state, screenshots, permits, or execution evidence.

### 5. Computer-use support must become multimodal

The proxy currently rejects image and audio input:

```python
if isinstance(content, list) and any(
    not isinstance(part, dict) or part.get("type") != "text"
    for part in content
):
    raise HTTPException(status_code=400, detail="image/audio input is disabled; text only")
```

Do not merely remove this rejection. Add controlled support for:

- Screenshot artifacts
- PNG/JPEG payloads
- UI Automation JSON
- Window/process metadata
- Tool-result JSON
- Artifact references
- Hashes
- Redaction
- Payload and dimension limits
- Provider capability validation

### 6. Windows UI Automation should be the primary control path

NeuralAgent currently extracts control types and bounds using:

```python
import uiautomation as auto
foreground = auto.GetForegroundControl()
```

Supported control types include:

```text
ButtonControl
EditControl
CheckBoxControl
ComboBoxControl
HyperlinkControl
TabItemControl
MenuItemControl
```

Microsoft UI Automation also exposes semantic control patterns:

```text
Invoke
Value
Text
Selection
ExpandCollapse
Scroll
Window
Transform
```

Prefer semantic actions such as:

```text
uia.invoke
uia.set_value
uia.select
uia.expand
uia.collapse
uia.scroll
uia.focus
uia.close
```

Use coordinate actions only as fallback for custom-rendered or inaccessible surfaces.

### 7. Screenshot coordinates currently use a fixed model canvas

NeuralAgent assumes:

```python
TARGET_W = 1280
TARGET_H = 720
```

and scales model coordinates to the physical screen.

This must be replaced or extended with explicit display metadata because the current approach does not explicitly handle:

- Multiple monitors
- Negative virtual-desktop coordinates
- Per-monitor DPI
- Different monitor scale factors
- Window coordinates versus virtual-desktop coordinates
- Screenshot-to-input transformation consistency

The implementation must preserve the mapping metadata with every observation and action.

### 8. Verification must inspect the real environment

The system must not mark an action successful merely because an input event was dispatched.

Verification evidence may include:

```text
post-action screenshot
UI Automation property/value
window title
foreground process
browser DOM state
clipboard content
application notification
download file hash
test result
API response
```

Every mutating action requires:

```text
pre-observation
action event
post-observation
verification result
```

### 9. Voice APIs have different deployment characteristics

The findings identify:

- Windows on-device Speech Recognition for low-latency, potentially offline speech recognition, with documented Windows 11 24H2 and Windows App SDK requirements for the referenced API.
- Azure Speech SDK for streaming recognition and synthesis, including audio streams, synthesis events, and streaming output.

The voice layer must therefore support a local path, cloud fallback, or both. The exact API choice and supported Windows-version policy remain open.

### 10. External screen content is untrusted

Web pages, documents, emails, notifications, and screenshots may contain prompt-injection text.

The system must maintain separate data categories:

```text
user_intent
system_policy
strategist_instruction
executor_instruction
environment_content
```

Environment content may inform decisions but must not grant permissions or override policy.

### 11. Consequential operations require confirmation

The system should require human confirmation by default for:

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
```

Confirmation must be bound to the exact action, target, relevant content or argument hash, run ID, and expiration time.

---

## Step-by-Step Build Plan

## Phase 0: Establish a tested baseline

### Step 0.1: Create a disposable Windows test environment

Use a disposable Windows profile, VM, or otherwise isolated environment for initial testing. The external computer-use guidance recommends isolated environments and minimal privileges.

Do not begin with:

- Production credentials
- Financial accounts
- Personal mailboxes
- Unrestricted file access
- Broad network access
- Arbitrary shell access

### Step 0.2: Run and document the existing NeuralAgent flow

Before modifying the runtime, execute representative tasks and record:

```text
task input
current subtask responses
model action responses
screenshots
UI extraction output
foreground window
input events
final result
failure behavior
```

The investigation did not execute the repositories or validate them on Windows, so this baseline is required.

### Step 0.3: Build a failure catalog

At minimum, test:

```text
application launch
application readiness
window focus
browser navigation
native button invocation
text entry
Unicode text entry
multi-monitor screenshots
DPI-scaled displays
wrong-window focus
UIA element unavailable
custom-rendered controls
application crash
user cancellation
UAC prompt
secure desktop
network timeout
model timeout
```

Record latency and failure modes. Use these results to define the first supported task set.

### Step 0.4: Preserve the existing product shell

Reuse the existing Electron/React shell where practical:

```text
Electron process
React renderer
existing task/thread UI
existing overlay concepts
existing Python agent process management
```

The new runtime should be introduced behind an explicit dual-lobe service boundary rather than mixed into every existing route.

---

## Phase 1: Define the normalized protocol and domain schemas

Create a provider-independent protocol package. Do not allow Anthropic- or OpenAI-specific action formats to spread throughout the application.

Suggested package:

```text
packages/protocol/
```

or, if extending NeuralAgent:

```text
desktop/aiagent/protocol/
```

### Step 1.1: Define protocol envelope

Use the dual-lobe envelope as the base:

```json
{
  "task_id": "string",
  "run_id": "string",
  "seq": 42,
  "from_lobe": "executor",
  "to_lobe": "strategist",
  "message_type": "action_result",
  "payload": {}
}
```

Extend it with computer-use metadata:

```json
{
  "environment_revision": 81,
  "screen_hash": "sha256:...",
  "ui_tree_hash": "sha256:...",
  "window_handle": "0x123456",
  "process_id": 1234,
  "action_id": "action-456",
  "permit_id": "permit-456",
  "risk_class": "low",
  "requires_confirmation": false,
  "expected_observation": {},
  "expiration": "2026-09-12T12:00:00Z"
}
```

Required validation rules:

- `task_id` and `run_id` must be present.
- Sequence numbers must be monotonic per run.
- Sender and recipient must be valid for the message type.
- Duplicate messages must be handled idempotently.
- Unknown message types must be rejected.
- Stale environment revisions must not authorize state-dependent actions.
- A permit must reference a specific action.

### Step 1.2: Define observation schema

Implement an observation object containing:

```json
{
  "run_id": "run-123",
  "revision": 42,
  "timestamp": "2026-09-12T12:00:00Z",
  "foreground_window": {
    "handle": "0x123",
    "title": "Notepad",
    "process_id": 456,
    "process_name": "notepad.exe"
  },
  "screens": [
    {
      "monitor_id": "DISPLAY1",
      "width": 1920,
      "height": 1080,
      "image_ref": "artifact://screens/42.png",
      "sha256": "sha256:..."
    }
  ],
  "ui_elements": [],
  "clipboard": {
    "available": false
  }
}
```

Each observation must include:

- Environment revision
- Timestamp
- Foreground window identity
- Process identity
- Screen artifact reference
- Screen hash
- UI tree hash
- Monitor and coordinate metadata
- UI elements when available

### Step 1.3: Define normalized computer actions

At minimum support:

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

Represent actions as typed objects. A Python pattern may use Pydantic discriminated unions:

```python
class ClickAction(BaseModel):
    kind: Literal["click"]
    x: int
    y: int
    button: Literal["left", "right", "middle"] = "left"

class UIAInvokeAction(BaseModel):
    kind: Literal["uia.invoke"]
    element_id: str

class ComputerAction(BaseModel):
    action_id: str
    action: ClickAction | UIAInvokeAction
    expected_result: dict
    risk: str
```

Reject:

- Unknown action kinds
- Missing target identifiers
- Invalid coordinates
- Invalid key names
- Actions referencing stale UI elements
- Action batches after the first failed action
- Unpermitted side effects
- Arbitrary Python or shell code

### Step 1.4: Define permits

A permit must bind authorization to the exact action:

```json
{
  "permit_id": "permit-123",
  "run_id": "run-123",
  "action_id": "action-456",
  "decision": "permit",
  "tool": "uia.invoke",
  "arguments_hash": "sha256:...",
  "screen_hash": "sha256:...",
  "window_handle": "0x123456",
  "allowed_tools": ["uia.invoke"],
  "ttl_seconds": 10,
  "max_uses": 1,
  "requires_human_confirmation": false
}
```

Validate before execution:

1. Permit exists.
2. Permit belongs to the same run.
3. Permit references the same action ID.
4. Tool name matches.
5. Arguments hash matches.
6. Environment revision or screen hash is still valid.
7. Foreground window/process is still allowed.
8. Permit has not expired.
9. Permit use count is not exhausted.
10. Human confirmation exists if required.

### Step 1.5: Define verification results

Use:

```json
{
  "message_type": "verify_result",
  "run_id": "run-123",
  "action_id": "action-43",
  "outcome": "success",
  "evidence": [
    {
      "kind": "uia_property",
      "artifact_ref": "artifact://observations/43.json",
      "artifact_hash": "sha256:...",
      "validated": true
    }
  ],
  "notes": "Target edit control now contains the requested value."
}
```

Supported outcomes:

```text
success
retry
repair
rollback
```

No action may transition to verified success without evidence.

---

## Phase 2: Implement the Windows executor

Create a standalone executor service that can be tested independently of model calls.

Suggested structure:

```text
packages/windows-executor/
├── screen_capture.py
├── coordinate_mapper.py
├── ui_automation.py
├── input_adapter.py
├── window_manager.py
├── process_manager.py
├── clipboard_manager.py
├── browser_adapter.py
├── cancellation.py
├── action_validator.py
└── journal.py
```

If retaining NeuralAgent’s Python structure, place the equivalent components under:

```text
desktop/aiagent/executor/
```

### Step 2.1: Implement screen capture

Support:

```text
full virtual desktop
per-monitor capture
active-window capture
region capture
```

Every capture must record:

```text
monitor identity
physical dimensions
virtual-desktop origin
DPI/scale metadata when available
model canvas dimensions
coordinate transform
timestamp
SHA-256 hash
artifact reference
```

Support redaction before sending screenshots to a provider. The exact redaction mechanism is not specified by the research and must be designed and tested.

### Step 2.2: Replace fixed coordinate assumptions

NeuralAgent currently uses:

```python
TARGET_W = 1280
TARGET_H = 720
```

Retain a normalized model canvas only if the transform is explicit and reversible. Store:

```json
{
  "virtual_screen": {
    "left": -1920,
    "top": 0,
    "width": 3840,
    "height": 2160
  },
  "monitors": [],
  "model_canvas": {
    "width": 1280,
    "height": 720
  },
  "transform": {
    "type": "per_monitor_affine"
  }
}
```

Reject or pause when:

- Monitor metadata is missing.
- The active monitor changes unexpectedly.
- Screenshot and input coordinate spaces do not match.
- The target lies outside the permitted screen bounds.
- DPI changes invalidate the mapping.

### Step 2.3: Implement UI Automation discovery

Use the existing `uiautomation` approach as the starting point:

```python
foreground = auto.GetForegroundControl()
```

Extract, where available:

```text
element ID
control type
name/label
automation ID
class name
bounds
enabled state
focused state
process ID
window handle
supported control patterns
```

Use the control tree to create stable references. Do not rely solely on labels and rectangles.

### Step 2.4: Implement semantic UIA operations

Implement adapters for:

```text
InvokePattern
ValuePattern
TextPattern
SelectionPattern
ExpandCollapsePattern
ScrollPattern
WindowPattern
TransformPattern
```

Action selection order:

1. Use an appropriate UIA control pattern.
2. Use application DOM/API if available.
3. Use keyboard shortcut if reliable and authorized.
4. Use coordinate interaction as a fallback.
5. Pause and escalate if the target cannot be identified safely.

### Step 2.5: Implement coordinate and input fallback

Support the existing action family:

```text
left_click
double_click
triple_click
right_click
mouse_move
left_click_drag
left_mouse_down
left_mouse_up
key
key_combo
type
hold_key
scroll
wait
request_screenshot
```

Ensure cancellation always:

- Releases held mouse buttons.
- Releases held keys.
- Stops long text input.
- Stops queued actions.
- Persists a cancellation event.

### Step 2.6: Implement safe text input

Retain the existing distinction between ASCII typing and clipboard-based Unicode insertion, but add:

```text
focus verification
secure-field detection
secret redaction
paste success verification
cancellation
user-visible action status
```

Do not type secrets or authentication codes without an explicit policy and confirmation path.

### Step 2.7: Implement application launch and readiness

NeuralAgent currently attempts:

```text
start "" "app_name"
PowerShell Get-StartApps
explorer.exe shell:AppsFolder\\APPID
```

Implement launch as a typed operation, not a free-form shell string. The application name must be safely escaped and validated.

Return:

```json
{
  "success": true,
  "process_id": 1234,
  "window_handle": "0x123456",
  "window_title": "Notepad",
  "ready": true
}
```

After launch:

1. Identify the process.
2. Identify the window.
3. Wait for readiness.
4. Verify foreground focus.
5. Capture a new observation.
6. Permit follow-up actions only against the verified process/window.

### Step 2.8: Implement window focus safely

Improve the existing title-matching behavior by preferring:

```text
process ID
window handle
exact window identity
```

Use title fragments only as fallback.

Before every input mutation:

1. Check expected process ID.
2. Check expected window handle.
3. Bring the window to the foreground.
4. Verify the foreground window.
5. Abort if the wrong window is active.

Detect and pause on:

```text
UAC prompt
secure desktop
credential dialog
MFA prompt
Windows Hello
protected desktop
```

The agent must not bypass authentication or security prompts.

### Step 2.9: Add browser automation

Use browser automation when a browser DOM or CDP session is available. The research identifies Playwright/CDP-style browser automation as the appropriate layer, while NeuralAgent currently has browser/background support.

Use the hierarchy:

```text
browser DOM/API
UI Automation
keyboard shortcuts
coordinate interaction
```

Keep browser sessions alive across action cycles. Capture browser state and screenshots after actions.

### Step 2.10: Add executor-local journaling

Persist every action transition:

```text
PROPOSED
PERMITTED
DISPATCHED
COMPLETED
VERIFIED
FAILED
RETRIED
ROLLED_BACK
CANCELLED
```

Write the journal before dispatching the action so a crash cannot erase the fact that an action was attempted.

---

## Phase 3: Implement persistence and artifacts

### Step 3.1: Start with local-first persistence

Use SQLite for the desktop-first implementation.

Store:

```text
runs
tasks
plans
subtasks
protocol_messages
computer_actions
action_permits
action_results
verification_results
events
claims
evidence
human_confirmations
voice_commands
checkpoints
memory_entries
```

Use the dual-lobe-proxy model concepts as the schema reference:

```text
Run
Event
Claim
Evidence
BState
BJob
Outbox
MemoryEntry
ProviderAttempt
```

### Step 3.2: Add artifact storage

Store screenshots and other evidence outside the main event rows:

```text
%LOCALAPPDATA%\\DualLobeAgent\\
├── agent.db
├── artifacts\\
├── screenshots\\
├── logs\\
├── voice\\
└── checkpoints\\
```

Each artifact record must contain:

```text
artifact ID
kind
path or object reference
SHA-256 hash
creation time
run ID
action ID
observation revision
retention status
redaction status
```

### Step 3.3: Implement append-only events

Events must be immutable. Corrections are represented by later events.

Include:

```text
run_created
plan_drafted
plan_signed
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

### Step 3.4: Add checkpoints

A checkpoint must capture:

```text
run state
current task/subtask
verified environment revision
foreground window
last verified action
pending permit
recovery attempt count
memory summary
required next evidence
```

Use checkpoints to recover after:

```text
process crash
provider timeout
network failure
desktop application crash
system restart
```

---

## Phase 4: Implement the dual-lobe state machine

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
```

### Step 4.1: Implement the four locks

#### Planning lock

A plan cannot become active until the Strategist signs it.

#### Action lock

The Executor cannot dispatch a mutating action without a valid permit.

#### Verification lock

An action cannot be marked successful until the Strategist or designated Verifier validates evidence.

#### Escalation lock

The system must attempt defined internal recovery paths before asking the user for help.

Persist every lock transition.

### Step 4.2: Implement role isolation

The Strategist process must not call Executor-owned tools.

The Executor process must not:

- Modify policy
- Grant its own permits
- Mark its own action verified
- Escalate directly without the defined protocol
- Interpret screen text as authorization

Enforce tool ownership in the runtime registry, not only in prompts.

### Step 4.3: Implement action review

For each proposal, the Strategist must classify:

```text
risk
external side effect
reversibility
data transmission
financial impact
destructive impact
required evidence
confirmation requirement
```

Return one of:

```text
permit
revise
block
research_needed
```

### Step 4.4: Implement human confirmation

For consequential actions, display and optionally speak:

```text
The agent is ready to click “Submit.”
This will send the form externally.
Do you want to continue?
```

Bind confirmation to:

```text
run ID
action ID
target
arguments/content hash
expiration
exact operation
```

Do not accept generic “yes” for a changed or stale action.

---

## Phase 5: Implement bounded Strategist/Executor overlap

### Step 5.1: Use a bounded pipeline

Use this sequence:

```text
Observation N
    ↓
Strategist prepares candidate action N+1
    ↓
Strategist issues permit N+1
    ↓
Executor executes N+1
    ↓
Executor captures evidence
    ↓
Strategist verifies N+1
```

While the Executor is performing an already-permitted action, the Strategist may:

- Evaluate the expected result.
- Prepare recovery options.
- Analyze risk.
- Prepare candidate next actions.
- Inspect prior evidence.
- Prepare verification criteria.

The Strategist may not authorize a new state-dependent action based on an observation that has not yet been captured.

### Step 5.2: Classify action overlap

#### Low-risk, reversible actions

Examples:

```text
mouse movement
hover
screenshot
read UI tree
focus a known window
safe scrolling
```

These may be prepared and, where the environment is stable, pipelined with minimal delay.

#### Local reversible mutations

Examples:

```text
type into a verified field
select a dropdown
open an application
switch tabs
```

These require a scoped permit and post-action verification.

#### External or potentially reversible side effects

Examples:

```text
save a file
upload a file
change an account setting
send a draft
```

These require exact target and argument binding, evidence, and policy evaluation.

#### Irreversible or consequential actions

Examples:

```text
purchase
payment
delete
send message
submit
publish
deploy
accept terms
```

These require human confirmation by default.

### Step 5.3: Add stale-state protection

Every state-dependent action must include:

```text
observation revision
screen hash
UI tree hash
foreground window
process ID
target element identity
```

Reject the action if any required precondition has changed.

### Step 5.4: Add device-level serialization

The proxy currently uses per-run Postgres advisory locking. That is insufficient for a physical desktop controlled by multiple runs.

Implement a lock over:

```text
device_id
desktop_session_id
window_scope
executor_instance_id
```

For one physical desktop, allow only one mutating action in flight. For isolated virtual desktops or VMs, the lock may be scoped to the isolated environment.

---

## Phase 6: Implement verification and recovery

### Step 6.1: Add independent verification modes

Implement verification adapters for:

```text
UIA property/value
window title
foreground process
screenshot comparison
browser DOM
clipboard value
file existence and hash
download result
application notification
test result
API response
```

### Step 6.2: Verify actual state, not model claims

The Verifier must inspect artifacts generated by the Executor. It must not rely solely on:

```text
“I clicked the button”
“The form was submitted”
“The file was saved”
```

### Step 6.3: Implement recovery categories

Use:

```text
retry
repair
rollback
research_needed
ask_user
abort
```

Examples:

- Retry with the same action only if the action is idempotent and evidence indicates a transient failure.
- Repair when the expected target moved or focus was lost.
- Roll back only when a verified rollback operation exists.
- Ask the user when authentication, ambiguity, or consequential confirmation blocks progress.
- Abort when policy or safety cannot be satisfied.

### Step 6.4: Implement watchdog signals

Detect:

```text
no workspace update
no inter-lobe message
repeated plan hash
repeated failed tool call
expired permit
missed heartbeat
repeated screenshot with no progress
repeated click at same coordinates
unchanged screen after expected mutation
wrong foreground window
permit/revise cycle with no new evidence
```

Persist watchdog events and transition to recovery rather than looping indefinitely.

---

## Phase 7: Implement provider routing

### Step 7.1: Define provider roles

Configure separate routes for:

```text
STRATEGIST_PROVIDER
EXECUTOR_PROVIDER
VERIFIER_PROVIDER
VOICE_STT_PROVIDER
VOICE_TTS_PROVIDER
EMBEDDING_PROVIDER
```

The existing NeuralAgent roles can inform the mapping:

```text
PLANNER_AGENT → Strategist
COMPUTER_USE_AGENT → Executor
new VERIFIER_AGENT → Verifier
```

Do not assume role names alone provide isolation. Enforce isolation in the runtime.

### Step 7.2: Normalize provider-specific formats

Implement adapters for provider-specific:

```text
tool calls
computer actions
image inputs
streaming events
usage metadata
errors
```

Convert them immediately into the internal schemas.

### Step 7.3: Add multimodal request validation

Validate:

```text
image type
image dimensions
payload size
artifact existence
run association
redaction state
provider capability
```

Reject unsupported input before sending it to a provider.

### Step 7.4: Track provider attempts

Reuse the proxy’s ProviderAttempt concept. Record:

```text
run ID
call ID
provider alias
logical model
streaming flag
request hash
latency
token usage
status
error type
timestamps
```

Use this for debugging, cost limits, and evaluation.

---

## Phase 8: Implement voice interaction

### Step 8.1: Create the voice pipeline

Implement:

```text
microphone
→ audio capture
→ voice activity detection
→ streaming STT
→ partial transcript events
→ command arbiter
→ Strategist or local control path
→ streamed response text
→ chunked TTS
→ speaker
```

### Step 8.2: Choose local/cloud speech policy

The findings identify two paths:

1. Windows on-device Speech Recognition where the supported Windows and Windows App SDK requirements are met.
2. Azure Speech SDK for streaming recognition and synthesis.

Implement a policy such as:

```text
attempt local recognition
if unavailable, use configured cloud provider
if unavailable, offer typed input
```

The exact Windows compatibility matrix must be established during implementation because the research did not validate runtime availability.

### Step 8.3: Display partial transcripts

Show stable partial results in the UI:

```text
Listening...
open the browser...
open the browser and search...
open the browser and search for...
```

Only final or sufficiently stable speech should create a task or mutation.

### Step 8.4: Implement emergency local commands

These commands must bypass the LLM:

```text
stop
cancel
pause
abort
do not continue
close agent
```

On receipt:

1. Cancel pending provider calls.
2. Stop queued actions.
3. Release held keys and mouse buttons.
4. Stop TTS.
5. Mark the run cancelled or paused.
6. Persist the event.
7. Update the UI immediately.

### Step 8.5: Implement barge-in

Use audio echo cancellation and prevent the agent’s own TTS from being interpreted as user speech.

When the user interrupts:

```text
stop TTS
stop or pause execution
capture current observation
persist interruption
route the command
```

### Step 8.6: Implement voice confirmation

Confirmation must refer to an exact action:

```text
The agent is ready to send this message to Alice. Say “confirm send” to continue.
```

Do not accept a confirmation for an expired or changed permit.

### Step 8.7: Implement streamed TTS

Use chunked text output and begin playback when the first audio chunk arrives. Reuse synthesizer connections where supported by the selected SDK.

Do not speak hidden reasoning. Speak concise operational status.

---

## Phase 9: Build the desktop UI

### Step 9.1: Add live run status

Display:

```text
current task
current subtask
Strategist status
Executor status
Verifier status
current window
current application
voice status
permit status
confirmation state
```

### Step 9.2: Add live evidence

Provide views for:

```text
latest screenshot
before/after screenshots
UI Automation tree
action timeline
permit record
verification result
failure and recovery
```

### Step 9.3: Add confirmation controls

Support:

```text
Confirm
Reject
Pause
Stop
Edit
Retry
```

The UI must show:

```text
exact action
target
risk
expected result
data transmission status
reversibility
expiration
```

### Step 9.4: Add safe operational summaries

Show concise messages such as:

```text
I found the correct button.
This action will send the form.
I need your confirmation before continuing.
The action was cancelled.
The task is complete and I verified the result.
```

Do not expose hidden chain-of-thought.

---

## Phase 10: Add API and gateway endpoints

If extending dual-lobe-proxy, add computer-use endpoints modeled on its existing API structure:

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

Add records for:

```text
device_id
desktop_session_id
monitor_id
window_scope
executor_instance_id
```

Use correlation headers and run IDs throughout the Electron, local executor, gateway, provider, and voice layers.

---

## Phase 11: Add security controls

### Step 11.1: Implement content trust boundaries

Tag all inputs as one of:

```text
user_intent
system_policy
strategist_instruction
executor_instruction
environment_content
```

Only system policy, user intent, and authorized Strategist instructions may control the runtime.

### Step 11.2: Implement sensitive-data protections

At minimum plan controls for:

```text
password fields
credit cards
authentication codes
private messages
personal files
health data
financial documents
```

Potential implementation mechanisms include:

```text
screen redaction
secure-window blocking
credential vault integration
credential-field detection
no screenshot transmission for protected regions
application allowlists
user confirmation before external transmission
```

The research identifies these requirements but does not specify a complete redaction implementation; this remains an engineering gap.

### Step 11.3: Restrict network and browser access

Use allowlists where possible. The external computer-use guidance recommends internet allowlists and isolated environments.

The existing NeuralAgent server-side URL tools do not visibly enforce a complete domain allowlist or comprehensive request-size/time policy. Add those controls before enabling equivalent tools.

### Step 11.4: Defer shell execution

Do not expose arbitrary shell execution in the MVP.

If added later, require:

```text
disabled-by-default policy
command allowlist
working-directory restriction
timeout
output-size limit
network policy
human confirmation
sandbox
full audit trail
separate high-risk permit
```

---

## Phase 12: Package and deploy

### Step 12.1: Create a Windows installer

The research found no independently verified one-command installer or signed binary distribution in NeuralAgent. Implement and validate:

```text
Electron application
Python executor runtime
voice dependencies
configuration
local database
artifact directories
provider credentials
first-run permissions
```

### Step 12.2: Add crash recovery

On restart:

1. Load the last checkpoint.
2. Detect actions that were dispatched but not verified.
3. Capture a fresh observation.
4. Do not automatically repeat an uncertain external side effect.
5. Ask the Strategist or user to resolve ambiguity.
6. Resume only after state is reconciled.

### Step 12.3: Add safe mode

Safe mode should start with:

```text
no external side effects
no shell execution
screenshots and UI tree only
human confirmation for every mutation
```

Use it for diagnostics and first-run validation.

---

## Phase 13: Evaluate the implementation

Compare at minimum:

```text
single-agent sequential baseline
existing NeuralAgent loop
dual-lobe gated mode
dual-lobe overlapped mode
dual-lobe with voice
dual-lobe without voice
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
latency
provider cost
voice command latency
barge-in latency
user escalation rate
context size
Strategist overhead
```

Use task suites covering:

```text
native applications
browser navigation
forms
file operations
window switching
multi-monitor layouts
DPI scaling
custom-rendered controls
application failures
network failures
prompt injection
UAC/authentication
destructive actions
voice interruption
```

The dual-lobe research explicitly calls for empirical evaluation and ablation. Do not claim reliability improvements until these comparisons are measured.

---

## Known Constraints and Pitfalls

### Repository and runtime constraints

- The repositories were inspected but not executed during the investigation.
- Runtime behavior, Windows compatibility, latency, model quality, and end-to-end readiness are not independently confirmed.
- NeuralAgent contains compiled artifacts and a binary-like background-agent file; readable source should be treated as authoritative.
- The existing NeuralAgent setup is multi-process and multi-step rather than a verified one-command Windows installation.
- The existing background mode is described as Windows-only through WSL and browser-only.

### Architecture constraints

- A post-response observer cannot prevent an action that already occurred.
- Per-run serialization does not protect a shared physical desktop from multiple concurrent runs.
- Prompt instructions cannot replace runtime tool ownership or permit enforcement.
- The Strategist must not be allowed to mutate the environment.
- The Executor must not be allowed to authorize or verify its own action.
- Shared memory must not become a bypass around the Tool Router.
- A true zero-latency loop is impossible when fresh state, model generation, verification, or human confirmation is required.

### Windows automation constraints

- UI Automation trees are dynamic.
- Applications expose different levels of UIA support.
- Custom controls may have incomplete or missing providers.
- UIA control patterns are preferable to coordinates but are not universally available.
- Foreground-window activation on Windows has restrictions.
- Window-title substring matching can focus the wrong window.
- UAC and secure desktop surfaces require special handling.
- The current fixed `1280 × 720` coordinate mapping does not explicitly solve multi-monitor, negative coordinates, or per-monitor DPI.
- Desktop icon discovery based on `SysListView32` is brittle.
- The current WebView detection is a heuristic and can produce false positives.
- Screenshot and UIA coordinate systems can become inconsistent if transformations are not recorded.

### Input constraints

- Unicode insertion currently relies on clipboard behavior.
- Clipboard paste can fail or target the wrong field if focus is lost.
- Input events may be delivered successfully even when the application does not reach the expected state.
- Long typing and held keys require cancellation-safe cleanup.
- Secret entry must not be treated like ordinary text input.

### Provider constraints

- Provider-specific computer-use schemas must be normalized.
- The existing proxy rejects image and audio content.
- Multimodal support requires payload limits, artifact storage, redaction, hashing, and provider capability checks.
- Different model providers may have different action ordering, tool-result, streaming, and screenshot requirements.
- Independent verification is less effective if Strategist, Executor, and Verifier share identical failure modes; different model families or providers are preferable where feasible.

### Security constraints

- Screen content is untrusted and may contain prompt injection.
- On-screen text must not grant permissions.
- Browser and URL tools require allowlists and request limits.
- Consequential actions require explicit confirmation.
- Arbitrary shell execution is unsafe for the initial product.
- Credentials, passwords, MFA prompts, and secure desktop content must not be exposed casually to remote models.
- The agent must not bypass authentication or security prompts.

### Voice constraints

- Windows on-device speech APIs have documented Windows and Windows App SDK requirements for the referenced implementation.
- Cloud speech introduces network, privacy, credential, and cost dependencies.
- Microphone input can capture the agent’s own TTS without echo cancellation.
- Voice stop commands must not depend on a model response.
- Partial transcripts must not trigger mutations prematurely.
- Voice confirmation must be bound to the exact action and expire.

### Persistence constraints

- An outbox or background job can be lost or delayed if the process crashes unless durable state and retry behavior are implemented.
- A provider response is not evidence that a desktop action succeeded.
- An action dispatched before a crash must not automatically be repeated unless idempotency is known.
- Artifact retention and redaction policies are required but not specified by the existing repositories.

---

## Open Gaps and Unknowns

### Repository and implementation unknowns

1. **Actual runtime behavior**
   - The repositories were not started or tested on a Windows machine.
   - End-to-end compatibility is unknown.

2. **Supported Windows versions**
   - The exact supported Windows version for the final product is not established.
   - The Windows on-device speech API findings reference Windows 11 24H2 and specific Windows App SDK requirements, but broader compatibility is unknown.

3. **Installer and signing**
   - No verified one-click Windows installer was identified.
   - No signed binary distribution process was established.

4. **License compatibility**
   - The investigation did not establish a complete license compatibility analysis across all repositories and dependencies.
   - The dual-lobe repository documentation states CC BY-NC-SA 4.0, while repository license metadata was not returned.
   - Perform legal review before copying code or documentation into a commercial product.

### Windows automation unknowns

5. **DPI and multi-monitor implementation**
   - The research identifies the current fixed 1280×720 limitation but does not provide a tested replacement.
   - The exact Windows API strategy for per-monitor DPI awareness and coordinate transforms must be selected and tested.

6. **UIA provider coverage**
   - The percentage of target applications exposing reliable control patterns is unknown.
   - A supported-application matrix must be created.

7. **Browser adapter**
   - The findings recommend Playwright/CDP-style browser automation, but no integrated adapter was found in the investigated dual-lobe code.
   - Browser session persistence, profile isolation, download handling, and authentication behavior require implementation and testing.

8. **Secure desktop behavior**
   - The exact detection and response behavior for UAC, Windows Hello, MFA, password dialogs, and protected desktops is not specified.
   - The implementation must define when to pause, what evidence to show, and how the user resumes.

9. **WebView detection**
   - Existing NeuralAgent behavior only estimates uncovered screen area.
   - No validated WebView2, Chromium, accessibility-tree, or CDP detection strategy was found.

10. **Desktop icon semantics**
    - Existing icon extraction returns labels and bounds but does not establish a reliable shell action or stable identifier.
    - A stable desktop-icon model is required.

### Dual-lobe scheduling unknowns

11. **Safe overlap boundaries**
    - The research defines bounded overlap conceptually but does not specify which action classes can safely overlap on every application.
    - Benchmark action categories before enabling speculative preparation or execution.

12. **Permit granularity**
    - It is not established whether permits should authorize one raw input, one semantic action, one action batch, or a short sequence.
    - The recommended starting point is one permit per mutating action, with explicit evidence requirements.

13. **Verification authority**
    - The final product must decide whether verification is performed by the Strategist, a separate Verifier model, deterministic adapters, or a combination.
    - Deterministic evidence should be preferred where available.

14. **Rollback support**
    - Many desktop actions are not safely reversible.
    - The implementation must identify which actions support rollback and must not promise rollback where no reliable inverse exists.

15. **Idempotency**
    - The repositories do not provide a complete idempotency model for external desktop actions.
    - Each high-risk action must define whether retry is safe before automatic retry is allowed.

### Voice unknowns

16. **Local speech availability**
    - The findings identify Windows on-device speech APIs but do not establish availability across target devices.
    - Test supported hardware, Windows versions, packaging modes, languages, and offline behavior.

17. **Voice provider selection**
    - The final STT and TTS provider strategy is not selected.
    - Compare local recognition, Azure Speech SDK, and any other approved providers for latency, privacy, cost, and reliability.

18. **Wake-word behavior**
    - The research covers streaming recognition and interruption but does not define a wake-word system.
    - Decide whether the MVP uses push-to-talk, always-listening, wake word, or a combination.

19. **Audio privacy**
    - Retention, transmission, and redaction policies for microphone audio are not specified.
    - Define whether audio is stored, transmitted, or discarded after transcription.

### Security unknowns

20. **Screen redaction**
    - The research identifies sensitive-data exposure as a risk but does not define a complete redaction implementation.
    - Specify detection, masking, user override, model-side handling, and artifact retention.

21. **Credential isolation**
    - No credential-vault integration was identified.
    - Decide how passwords, tokens, MFA codes, and private data are entered without exposing them to models.

22. **Network policy**
    - Existing URL and PDF tools do not visibly implement complete domain, size, timeout, or content restrictions.
    - Define network allowlists and enforce them in the runtime.

23. **Shell policy**
    - The final product scope does not establish whether shell execution will ever be supported.
    - Keep it disabled for MVP and define a separate security review if added.

### Persistence and deployment unknowns

24. **SQLite versus Postgres boundary**
    - The findings recommend SQLite for local-first mode and Postgres for server mode, but synchronization and migration behavior are not defined.
    - Decide whether local state is authoritative, replicated, or only cached.

25. **Artifact retention**
    - Screenshot, UI tree, voice, and evidence retention periods are not specified.
    - Define user controls, automatic deletion, encryption, and audit requirements.

26. **Crash recovery semantics**
    - The repositories provide checkpoint and job patterns but do not establish how to reconcile an action that may have occurred just before a crash.
    - Implement conservative reconciliation and require user input when an external side effect is uncertain.

27. **Multi-device behavior**
    - Device identity and desktop-session identity are not present in the existing proxy design.
    - Define whether runs may move between devices and how a physical desktop is reserved.

### Evaluation unknowns

28. **Task benchmark**
    - No standardized Windows task suite is supplied.
    - Create a benchmark covering native UI, browser UI, custom surfaces, voice, interruptions, prompt injection, and consequential actions.

29. **Success definition**
    - The research identifies metrics but does not define thresholds.
    - Establish release criteria for task success, false success, unauthorized side effects, verification precision, recovery, and latency.

30. **Model selection**
    - The findings identify separate Strategist, Executor, and Verifier roles but do not prescribe specific models.
    - Select models through controlled evaluation rather than assuming the existing provider roles are sufficient.

31. **Cost and latency budgets**
    - No target budgets were established for model calls, screenshots, voice, or verification.
    - Define budgets before enabling overlapping work so that overlap does not create uncontrolled provider cost or resource usage.
