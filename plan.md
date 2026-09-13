# Deep Findings Report: `anasalsawy/compuse`

## 1. Task interpretation and exact requirements

### Verified task status

The supplied task is:

> None

There is no explicit feature request, defect description, acceptance criterion, external integration, or requested code change.

The repository does contain an instruction at the beginning of `plan.md`:

> “INSTRUCTIONS FOR BUILDERS >> PLEASE COMPLETE THIS TURNING IT INTO A TESTED AND VERIFIED READY TO INSTALL WINDOWS APP”

That instruction is repository content, not the user’s task statement. It conflicts with the explicit task value of `None`. Therefore:

- **No implementation can be mandated as the direct answer to the current task.**
- The appropriate deliverable is an implementation-readiness and gap audit.
- If the intended objective is indeed to turn the prototype into a Windows application, that is a substantial new product phase, not a small incremental change.

### Practical interpretation if the hidden intended objective is Windows delivery

Assuming the builder instruction is intended to define the next project phase, the actual required outcome would be:

1. Preserve the existing safety-first portable coordination core.
2. Add durable coordinator state and recovery.
3. Add a Windows-native observation layer.
4. Add a Windows executor with strict identity and policy checks.
5. Add independent postcondition verification.
6. Add local authenticated IPC between the UI and coordinator.
7. Add a Windows desktop UI and installer.
8. Add Windows-native acceptance tests on interactive desktops.
9. Package and sign the application.
10. Do not claim successful computer-use behavior until those tests and verification paths exist.

That is a recommendation and inferred scope, not a currently confirmed user requirement.

---

## 2. Source limitations and evidence quality

The initial context said:

> “I’m unable to retrieve the raw file content.”

The repository was nevertheless inspected through GitHub tree, repository-content, raw-file, commit, and documentation access.

### Important limitation

Some GitHub raw-content requests returned temporary signed Cloudflare R2 URLs. Several of those URLs were successfully read, but one workflow fetch failed.

Therefore:

- The repository tree was successfully verified.
- Core source files, tests, documentation, README, and configuration were successfully obtained.
- The workflow was obtained through the repository-content response.
- The final checklist claims local test/build results, but those results were **not rerun by this investigation**.
- GitHub Actions execution status was not independently inspected.
- No new code was executed in the research environment.

Where the repository itself claims local execution results, those are reported as **repository-documented claims**, not as independently reproduced results.

---

# 3. Existing repository state

## 3.1 Repository structure

The current `main` tree contains:

```text
.github/
  workflows/
    test.yml

LICENSE
README.md

compuse/
  __init__.py
  coordinator/
    __init__.py
    core.py
    states.py
  protocol/
    __init__.py
    models.py
  storage/
    __init__.py
    events.py

docs/
  final-execution-checklist.md
  protocol.md
  security.md
  supported-capabilities.md
  test-matrix.md
  windows-development.md

plan.md
pyproject.toml

tests/
  test_core.py
  test_states.py
  test_storage.py
```

There are no visible:

- Electron files;
- frontend files;
- Windows-native helper projects;
- C#, C++, Rust, or Cython extensions;
- database migration directory;
- CLI entry point;
- service or daemon entry point;
- installer configuration;
- signing configuration;
- browser integration;
- voice integration;
- IPC protocol implementation;
- screenshots or artifact store;
- Windows integration test suite;
- lock file.

## 3.2 Recent history

The latest commits show a rapid prototype-hardening sequence:

- `Implement safety-first coordination core`
- `fix: harden protocol permits and event journal`
- `test: expand coordination invariants and CI quality gates`
- `feat: extend typed action protocol and normalize observations`
- `fix: make event journal transaction-safe and thread-safe`
- `fix: harden event journal concurrency and packaging checks`
- `docs: save complete implementation plan`

The latest observed commit is:

```text
43c8198c6d706fe8c89f90359248a2860edb51e9
docs: save complete implementation plan
```

The repository commit metadata reports the latest commit as unsigned.

The commit history confirms that the current repository is a recently assembled prototype, not an already-existing Windows application awaiting packaging.

## 3.3 Package configuration

`pyproject.toml` currently defines:

```toml
[build-system]
requires = ["hatchling>=1.25"]
build-backend = "hatchling.build"

[project]
name = "compuse"
version = "0.2.1"
description = "Safety-first coordination core for local-first computer use"
readme = "README.md"
requires-python = ">=3.11"
license = {file = "LICENSE"}
dependencies = ["pydantic>=2.7,<3"]

[project.optional-dependencies]
test = ["pytest>=8", "pytest-cov>=5"]

[tool.hatch.build.targets.wheel]
packages = ["compuse"]

[tool.pytest.ini_options]
pythonpath = ["."]
addopts = "-ra"
```

### Verified implications

- Runtime support begins at Python 3.11.
- Pydantic 2.x is the only runtime dependency.
- Pytest and pytest-cov are optional test dependencies.
- Hatchling is used as the build backend.
- The package uses a flat layout with `compuse/` as the package root.
- No application entry point is defined.
- No Windows-only dependencies are declared.
- No GUI dependency is declared.
- No IPC, database migration, native helper, or installer dependency is declared.
- No lock file is present in the repository tree.

### Version inconsistency

`pyproject.toml` reports version `0.2.1`.

However, `docs/final-execution-checklist.md` claims artifacts:

```text
compuse-0.2.0-py3-none-any.whl
compuse-0.2.0.tar.gz
```

This is a concrete documentation inconsistency. It must be corrected before release automation or installation instructions are treated as authoritative.

---

# 4. Current implementation

## 4.1 Protocol models

`compuse/protocol/models.py` contains strict Pydantic models.

The base configuration is equivalent to:

```python
class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
```

Pydantic’s official documentation verifies that:

- `strict=True` reduces coercion and rejects values of the wrong type;
- strict mode can be configured at model, field, or validation-call level;
- discriminated unions select one variant based on a discriminator;
- discriminated unions are generally more predictable and efficient than untagged unions.

This repository uses those mechanisms appropriately for a narrow authority boundary.

### Origins

The protocol defines:

```text
USER_INTENT
SYSTEM_POLICY
STRATEGIST_INSTRUCTION
EXECUTOR_INSTRUCTION
ENVIRONMENT_CONTENT
PROVIDER_OUTPUT
```

The coordinator rejects proposals from:

```text
ENVIRONMENT_CONTENT
PROVIDER_OUTPUT
```

This is a valid authority-boundary design. Observed environment data and provider/model output cannot independently become authorization for a mutating action.

### Action variants currently present

The action union includes:

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

The repository defines models for these action categories:

- `Wait`
- `Screenshot`
- `MouseMove`
- `TypeText`
- `Click`
- `DoubleClick`
- `Drag`
- `Scroll`
- `Keypress`
- `KeyCombo`
- `FocusWindow`
- `ApplicationLaunch`

The current action models validate bounded values such as:

- wait duration;
- coordinates;
- text length;
- key-combination length;
- identifier lengths;
- nonnegative process/session IDs.

### Important gap

Although the protocol has action kinds for mouse movement, drag, keypress, and application launch, the repository’s documented supported-capabilities table says the implementation is only a portable typed protocol foundation.

There is no executor that performs any of these actions.

A typed `ApplicationLaunch` model is not an application launcher. A typed `Click` model is not a mouse driver. This distinction must remain explicit.

## 4.2 Observation model

The observation model contains:

```python
class Observation(StrictModel):
    run_id: str
    revision: int
    captured_at: datetime
    coordinate_space_id: str
    foreground_window: str | None
    process_id: int | None
    session_id: int | None
    input_desktop: str | None
```

The timestamp validator requires timezone awareness and normalizes values to UTC.

This is a good foundation for stale-observation and coordinate-space validation.

However, no Windows code currently populates:

- actual foreground window identity;
- process identity;
- session identity;
- input desktop;
- display topology;
- monitor DPI;
- screenshot metadata;
- UI Automation element identity.

## 4.3 Proposal and permit models

An `ActionProposal` binds an action to:

- `action_id`;
- `run_id`;
- action payload;
- origin;
- observation revision;
- coordinate-space ID;
- policy revision;
- optional tool/capability/launch/browser/window/process/session fields;
- optional confirmation ID.

A `Permit` carries:

- permit UUID;
- run ID;
- action ID;
- SHA-256 action hash;
- observation revision;
- coordinate-space ID;
- policy revision;
- expiry;
- consumed flag;
- optional tool/capability/launch/browser/window/process/session fields;
- optional confirmation ID.

`digest_action()` canonicalizes the action using JSON with sorted keys and compact separators, then hashes it with SHA-256.

Example implementation pattern:

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

This is appropriate for deterministic action binding, but the following should be clarified before treating it as a long-term protocol:

- canonical encoding version;
- Unicode normalization policy;
- whether numeric representation is stable across versions;
- whether action schema version must be included;
- whether the hash should cover all permit-relevant metadata or only the action body;
- whether a cryptographic keyed MAC or signature is required across process boundaries.

SHA-256 alone provides integrity of a value only when the trusted party controls or authenticates the value being compared. It does not authenticate an untrusted caller.

## 4.4 Coordinator

`compuse/coordinator/core.py` implements:

```python
class Coordinator:
    def issue(
        self,
        proposal: ActionProposal,
        observation: Observation,
        ttl: float = 30,
    ) -> Permit:
        ...

    def consume(
        self,
        permit_id,
        proposal: ActionProposal,
        observation: Observation,
    ):
        ...

    def release(self, permit_id):
        ...

    def cleanup(self):
        ...
```

### `issue()` currently verifies

- TTL is greater than zero and no more than 300 seconds;
- origin is not environment content or provider output;
- proposal and observation run IDs match;
- proposal observation revision matches;
- coordinate-space IDs match;
- policy revision is current.

It then creates an expiring permit, stores it in an in-memory dictionary, and appends a `permit_issued` event.

### `consume()` currently verifies

- no other permit is active;
- permit exists;
- permit is not consumed;
- permit is not expired;
- proposal action/run identity matches;
- origin remains trusted;
- policy and coordinate-space binding match;
- observation run/revision/coordinate-space binding match;
- proposal action digest matches the permit;
- original stored proposal action digest matches the permit.

It marks the in-memory permit consumed, sets the active permit, appends `permit_consumed`, and returns the typed action.

### Critical semantic boundary

`consume()` authorizes and reserves an action. It does not:

- dispatch input;
- launch an application;
- call UI Automation;
- call `SendInput`;
- capture a post-action observation;
- verify a postcondition;
- decide whether the action succeeded;
- reconcile an unknown executor result.

This is correctly documented.

### Critical durability defect

Permit state is held in:

```python
self._permits = {}
self._active_permit = None
```

Therefore:

- permits disappear on process restart;
- consumed state disappears on restart;
- active mutation ownership disappears on restart;
- an event record does not itself prevent permit replay;
- issuing and consuming are not durable state-machine operations;
- there is no cross-process lease;
- there is no durable idempotency record.

This is the highest-priority implementation gap if the project is intended to control a desktop.

## 4.5 Lifecycle state tables

`compuse/coordinator/states.py` defines:

### Run states

```text
IDLE
TASK_ACCEPTED
OBSERVING
PLANNING
WAITING_FOR_CONFIRMATION
READY_TO_EXECUTE
ACTION_EXECUTING
VERIFYING
RECOVERY
PAUSED
COMPLETED
CANCELLED
ABORTED
```

### Action states

```text
PROPOSED
PERMIT_PENDING
PERMITTED
DISPATCHING
DISPATCHED
EXECUTOR_RETURNED
VERIFICATION_PENDING
VERIFIED
FAILED
UNKNOWN
RECONCILING
RECONCILED_SUCCESS
RECONCILED_FAILURE
CANCELLED
ABORTED
```

Transitions are fail-closed through explicit lookup tables.

This is a good foundation. The missing piece is ownership and persistence: the state functions validate transitions but do not store a durable current state, append transition events, enforce monotonic versioning, or recover from a crash.

## 4.6 Event journal

`compuse/storage/events.py` implements a SQLite event store.

Verified features:

- one SQLite connection per `EventStore`;
- `check_same_thread=False`;
- an `RLock`;
- `PRAGMA foreign_keys=ON`;
- `PRAGMA busy_timeout=10000`;
- `PRAGMA synchronous=FULL`;
- WAL mode for file-backed databases;
- explicit `BEGIN IMMEDIATE`;
- per-run sequence numbers;
- SHA-256 hash chaining;
- canonical JSON payloads;
- context-manager support;
- chain verification;
- tamper detection;
- sequence-gap detection.

The event hash includes:

```text
previous hash
run ID
sequence
event type
serialized payload
timestamp
```

The genesis previous hash is 64 zeroes.

### Relevant official SQLite findings

Official SQLite documentation confirms:

- SQLite supports multiple readers but only one simultaneous writer;
- `BEGIN IMMEDIATE` starts a write transaction immediately;
- WAL allows readers and writers to operate concurrently under snapshot isolation;
- transactions should be explicit where atomic multi-step state changes are required;
- Python’s `sqlite3` documentation warns that connections shared across threads require caller-side serialization;
- `sqlite3.Connection.backup()` can create a backup while the database is being accessed.

The current `RLock` and `BEGIN IMMEDIATE` are therefore sensible for the current single-instance design.

### Important limitation

The current test suite accesses `store.db` directly to tamper with the database:

```python
store.db.execute(...)
```

That is acceptable for a white-box integrity test, but the public API does not prevent callers from bypassing the store’s locking and transaction rules. The docstring says callers should not use `db` directly, but the attribute remains public.

Recommended change:

```python
self._db = sqlite3.connect(...)
```

and expose controlled test-only or administrative APIs where necessary.

### Durability nuance

`PRAGMA synchronous=FULL` is useful, but the project should document its durability assumptions:

- filesystem behavior;
- operating system caching;
- backup procedure;
- handling of `-wal` and `-shm` files;
- response to disk-full and I/O errors;
- journal corruption handling;
- retention and growth limits;
- startup behavior when integrity verification fails.

A hash chain detects modification or loss. It does not provide independent external archival, key-based authenticity, or guaranteed disaster recovery.

---

# 5. Existing tests and CI

## 5.1 Test files

The repository contains:

```text
tests/test_core.py
tests/test_states.py
tests/test_storage.py
```

The tests cover:

- issue/consume/release;
- rejection of untrusted origins;
- stale and mismatched bindings;
- single mutation boundary;
- invalid TTL;
- strict model validation;
- event tampering;
- sequence gaps;
- empty chains;
- concurrent event appends;
- lifecycle transition rules.

The tests are focused on invariants rather than broad application behavior.

## 5.2 CI workflow

`.github/workflows/test.yml` runs on push and pull request:

```yaml
strategy:
  matrix:
    python-version: ["3.11", "3.12", "3.13"]
```

It:

1. checks out the repository;
2. installs Python;
3. upgrades pip;
4. installs `.[test]`;
5. runs:

```bash
pytest --cov=compuse --cov-report=term-missing --cov-fail-under=80
```

The workflow uses:

```yaml
permissions:
  contents: read
```

That is an appropriately narrow default permission.

## 5.3 Repository-documented test claims

`docs/final-execution-checklist.md` claims:

- seven tests passed;
- 98.32% coverage;
- wheel and sdist built successfully;
- the audited version produced `compuse-0.2.0` artifacts;
- Windows-native execution was not performed;
- GitHub Actions was not independently inspected.

These results were not rerun during this investigation. Treat them as historical repository documentation, not current verification.

## 5.4 Missing tests

Before desktop integration, add tests for:

### Protocol

- invalid UUIDs;
- invalid SHA-256 hashes;
- malformed capability hashes;
- naive timestamps;
- timestamp offset normalization;
- oversized identifiers;
- invalid process/session IDs;
- unknown action kinds;
- extra fields at every nested level;
- canonical digest stability;
- schema-version changes.

### Permit lifecycle

- expiry;
- replay after consume;
- replay after restart;
- duplicate action IDs;
- duplicate request IDs;
- consume with changed original proposal;
- consume with changed tool;
- consume with changed capability hash;
- consume with changed window/process/session identity;
- concurrent issue;
- concurrent consume;
- concurrent release;
- failed event append;
- failed database commit;
- crash between state mutation and event append.

### Event storage

- reopening a database;
- WAL recovery;
- rollback after insert failure;
- disk-full behavior;
- corrupted payload;
- corrupted timestamp;
- duplicate hash;
- duplicate sequence;
- cross-process writer contention;
- backup and restore;
- startup integrity failure.

### Windows-specific testing

- unlocked interactive session;
- locked session;
- disconnected RDP session;
- wrong session;
- wrong input desktop;
- foreground-window change;
- process restart;
- process ID reuse;
- window handle reuse;
- monitor topology change;
- DPI change;
- multi-monitor coordinate conversion;
- UAC/integrity-level mismatch;
- secure desktop;
- cancellation during input;
- executor crash;
- helper timeout;
- unknown dispatch result.

---

# 6. What must be built for a Windows application

The repository is not currently a Windows application. The required implementation should be divided into explicit boundaries.

## 6.1 Recommended architecture

```text
Electron or native desktop UI
        |
        | authenticated local IPC
        v
Python Coordinator service
        |
        +-- durable SQLite state
        +-- policy engine
        +-- permit manager
        +-- lifecycle state machine
        +-- recovery/watchdog
        +-- evidence/artifact manager
        |
        | authenticated restricted IPC
        v
Windows executor/helper
        |
        +-- observation provider
        +-- UI Automation adapter
        +-- window/process/session identity
        +-- screenshot provider
        +-- input dispatch
        +-- launch registry
        +-- cancellation / emergency stop
```

The Coordinator must remain the only authority that can:

- accept user intent;
- validate proposals;
- issue permits;
- consume permits;
- transition authoritative states;
- classify executor outcomes;
- declare verification results.

The executor should be treated as a capability-limited worker. It must not be able to self-authorize arbitrary actions.

## 6.2 Component boundaries

### A. Durable Coordinator

Add modules such as:

```text
compuse/coordinator/runtime.py
compuse/coordinator/policy.py
compuse/coordinator/permits.py
compuse/coordinator/recovery.py
compuse/coordinator/leases.py
compuse/coordinator/idempotency.py
```

The exact filenames are recommendations.

Responsibilities:

- durable run records;
- durable action records;
- durable permit records;
- atomic consume;
- idempotency;
- lease ownership;
- lifecycle transitions;
- recovery after restart;
- watchdog heartbeat;
- safe-mode entry;
- event append and state update in one transaction.

### B. Database schema and migrations

At minimum, add tables for:

```text
schema_migrations
runs
actions
permits
leases
idempotency_keys
observations
executor_requests
executor_results
verifications
artifacts
checkpoints
confirmations
```

Possible key fields:

```text
runs:
  run_id
  state
  state_revision
  created_at
  updated_at
  owner_instance_id
  recovery_required

actions:
  action_id
  run_id
  request_id
  state
  state_revision
  action_kind
  action_json
  action_hash
  observation_revision
  policy_revision
  capability_hash
  created_at
  updated_at

permits:
  permit_id
  action_id
  run_id
  status
  issued_at
  expires_at
  consumed_at
  consumed_by
  action_hash
  permit_version

leases:
  lease_name
  owner_id
  acquired_at
  expires_at
  heartbeat_at

idempotency_keys:
  request_id
  operation
  response_json
  created_at
  expires_at
```

Do not rely on reconstructing all state only from an append-only event table unless that design is deliberately chosen and thoroughly implemented.

### C. Windows observation provider

The observation provider should capture:

- Windows build;
- current user/session;
- interactive session ID;
- input desktop;
- foreground window handle;
- foreground process ID;
- process executable identity;
- window title/class where permitted;
- monitor topology;
- monitor bounds;
- effective DPI;
- coordinate-space identifier;
- timestamp;
- screenshot metadata;
- UI Automation root or target identity.

The observation needs a stable, explicit coordinate-space version. Any display, DPI, monitor, scaling, or topology change should invalidate coordinate-dependent permits.

### D. Windows executor

The executor must support only explicit capability contracts.

Potential adapters:

- screenshot;
- wait;
- UI Automation semantic action;
- mouse movement;
- click/double-click;
- drag;
- keyboard keypress;
- key combination;
- text entry;
- focus window;
- allowlisted application launch.

The executor must reject:

- stale observations;
- wrong run;
- wrong permit;
- wrong process;
- wrong session;
- wrong input desktop;
- expired permit;
- reused permit;
- unrecognized capability revision;
- target that is not allowlisted.

### E. UI Automation

Microsoft documents UI Automation as a COM-based accessibility and automation framework exposing a tree of UI elements and control patterns.

Important implementation details from Microsoft documentation:

- use the current UI Automation COM interfaces rather than deprecated legacy functions;
- UI Automation calls that interact with the entire desktop should generally execute on a separate COM MTA thread;
- clients should account for DPI and physical coordinate behavior;
- UI Automation does not provide unrestricted cross-user process communication;
- control patterns and providers vary by application.

Recommended boundary:

```python
class UiaAdapter(Protocol):
    def locate(self, locator: Locator, observation: Observation) -> ElementRef:
        ...

    def invoke(self, element: ElementRef) -> UiaResult:
        ...

    def set_value(self, element: ElementRef, value: str) -> UiaResult:
        ...

    def select(self, element: ElementRef) -> UiaResult:
        ...
```

Every returned `ElementRef` should include enough identity for revalidation:

```text
automation_id
runtime_id
control_type
name
class_name
process_id
window_handle
bounds
captured_observation_revision
```

Do not treat a cached UI Automation element as valid indefinitely. Re-locate or verify it against the current observation before dispatch.

### F. Physical input

Microsoft’s `SendInput` API synthesizes keyboard and mouse input, but official documentation states:

- it is subject to User Interface Privilege Isolation;
- injection is allowed only into applications at an equal or lower integrity level;
- zero return means input was not inserted;
- a zero return does not necessarily identify UIPI as the cause;
- `SendInput` does not reset existing keyboard state.

Therefore, an executor cannot interpret a successful API call as proof that the target application accepted or processed the input.

Required sequence:

```text
permit
→ pre-dispatch identity check
→ dispatch
→ record API result
→ capture new observation
→ verify postcondition
```

A `SendInput` return count is an executor result, not a semantic success result.

### G. DPI and coordinate transforms

Microsoft’s DPI documentation confirms that desktop applications must explicitly handle DPI awareness and that per-monitor DPI awareness is the recommended mode for modern desktop applications.

The implementation should:

- select and document a DPI awareness mode;
- record DPI and monitor topology in observations;
- define physical versus logical coordinates;
- assign a coordinate-space ID;
- invalidate coordinate permits when topology/DPI changes;
- test multi-monitor configurations;
- test monitor docking/undocking;
- test RDP scaling;
- avoid mixing virtualized and physical coordinates.

Never permit a coordinate action to proceed based only on stale screen dimensions.

### H. Verification and evidence

A successful dispatch is not a successful task.

Add verifiers for:

- window appeared;
- process launched;
- target window focused;
- UI Automation property changed;
- text value changed;
- button state changed;
- expected control appeared/disappeared;
- screenshot region changed according to a declared predicate;
- file/download appeared with expected identity;
- clipboard changed, if clipboard use is explicitly supported.

Each verification result should include:

```text
verification_id
action_id
observation_before
observation_after
predicate
result
confidence or certainty classification
artifact references
timestamp
```

Use explicit result categories:

```text
VERIFIED
FAILED
UNKNOWN
REQUIRES_USER_INTERVENTION
```

Do not convert `UNKNOWN` into `FAILED` or `VERIFIED` without a documented reconciliation path.

### I. IPC

No IPC currently exists.

A recommended future design:

- bind only to a local transport;
- authenticate peers;
- use request IDs;
- enforce message size limits;
- reject unknown fields;
- include protocol version;
- include caller identity;
- include cancellation;
- include deadlines;
- use structured responses;
- prevent the UI from directly invoking executor operations;
- avoid exposing a raw socket to arbitrary local processes without authentication.

On Windows, named pipes are a plausible local transport, but the exact transport should be selected based on:

- ACL support;
- peer identity;
- Electron integration;
- Python support;
- packaging complexity;
- denial-of-service behavior;
- protocol versioning.

No external service API is required by the current repository.

## 6.3 Electron or desktop UI

The repository has no UI.

If Electron is selected, add:

```text
desktop/
  package.json
  electron/
    main.ts
    preload.ts
    ipc.ts
  renderer/
    ...
```

The UI must not hold authority. It should request operations from the Coordinator.

Required UI capabilities:

- show current run state;
- show current observation age;
- show proposed action;
- show policy decision;
- show confirmation state;
- show permit expiry;
- show executor state;
- show verification result;
- show unknown/recovery state;
- provide cancel/abort;
- expose emergency stop;
- show audit trail;
- show safe mode.

Recommended security requirements:

- `contextIsolation: true`;
- `nodeIntegration: false`;
- narrow preload API;
- strict IPC schemas;
- no arbitrary command execution from renderer;
- no direct access to Coordinator database;
- no direct executor control;
- CSP;
- dependency auditing;
- signed packaged binaries.

Electron is not currently configured and no version can be verified from the repository.

## 6.4 Installer and deployment

There is no installer configuration.

A complete Windows delivery requires decisions about:

- per-user versus per-machine installation;
- install directory;
- Python runtime bundling;
- Electron runtime bundling;
- native helper deployment;
- service versus user-session process;
- auto-start behavior;
- update mechanism;
- rollback;
- database migration;
- log location;
- artifact storage;
- code signing;
- SmartScreen reputation;
- uninstall behavior;
- crash recovery;
- least-privilege execution.

For desktop input, a service running in Session 0 cannot directly control the interactive user desktop in the normal model. The architecture must explicitly separate:

- per-user interactive Coordinator/UI;
- per-user executor/helper;
- privileged operations, if any;
- session identity and desktop identity.

Do not install an unattended input-capable service without a clear security model.

---

# 7. Required libraries, tools, versions, and configuration

## 7.1 Existing verified dependencies

Runtime:

```text
Python >= 3.11
pydantic >= 2.7, < 3
```

Testing:

```text
pytest >= 8
pytest-cov >= 5
```

Build:

```text
hatchling >= 1.25
```

These are verified from `pyproject.toml`.

## 7.2 Recommended additions by phase

These are recommendations, not current repository dependencies.

### Durable database

Prefer the standard-library `sqlite3` initially. Add a migration layer rather than immediately adding an ORM.

Possible choices:

- hand-written SQL migrations;
- Alembic if SQLAlchemy is introduced;
- yoyo-migrations;
- a small internal migration runner.

For this project, a small explicit migration runner may be preferable initially because the schema is safety-critical and the current code already uses direct SQLite.

### Windows APIs

Possible implementation choices:

- Python `ctypes` for narrow Win32 calls;
- `pywin32` for established Windows API access;
- `comtypes` for COM/UI Automation;
- C# helper using Windows UI Automation;
- C++ helper using official UI Automation COM APIs;
- Rust helper using Windows crate.

Recommendation:

- prototype observation and UI Automation with `pywin32`/`comtypes` only if their threading and packaging behavior is acceptable;
- prefer a separately versioned native helper for production-grade Windows interaction;
- keep the Python Coordinator independent of the helper implementation.

No such library is currently configured or verified in the repository.

### GUI

Possible options:

- Electron;
- Tauri;
- WinUI 3;
- WPF;
- PySide6;
- Tkinter.

The plan and repository language suggest Electron was contemplated, but no Electron files exist. Do not add Electron merely because it appears in planning text without confirming the product requirement.

### Packaging

For Python distribution:

- retain Hatchling;
- build both wheel and sdist;
- test installation from the wheel in a clean environment;
- maintain a reproducible dependency strategy.

For a bundled Windows application:

- Electron Builder;
- WiX;
- MSIX;
- Inno Setup;
- Squirrel;
- Tauri bundler.

Selection is unresolved.

### Test tools

Recommended:

- `pytest`;
- `pytest-cov`;
- `hypothesis` for protocol/property tests;
- `ruff` for linting/formatting;
- `mypy` or `pyright` for static typing;
- `pip-audit` for dependency vulnerabilities;
- `bandit` only if its findings are actionable;
- Windows-native test runner on self-hosted Windows;
- fake executor and fake observer for deterministic tests.

Do not add tools to CI unless the project commits to maintaining the corresponding policy.

## 7.3 Configuration and environment variables

The current repository defines no environment variables.

A future application may need configuration such as:

```text
COMPUSE_DATA_DIR
COMPUSE_DB_PATH
COMPUSE_LOG_LEVEL
COMPUSE_HELPER_PATH
COMPUSE_HELPER_PIPE
COMPUSE_POLICY_REVISION
COMPUSE_CAPABILITY_REVISION
COMPUSE_ARTIFACT_DIR
COMPUSE_MAX_EVENT_BYTES
COMPUSE_PERMIT_TTL_SECONDS
COMPUSE_SAFE_MODE
COMPUSE_DISABLE_PHYSICAL_INPUT
```

Recommendations:

- prefer explicit configuration files over undocumented environment variables;
- validate configuration at startup;
- do not place secrets in environment variables unless necessary;
- do not permit environment variables to silently weaken safety policy;
- expose the effective configuration in diagnostics without exposing secrets;
- separate development and production configuration;
- include a configuration version.

---

# 8. Concrete implementation patterns

## 8.1 Durable atomic permit consumption

The current implementation must not remain an in-memory-only permit system for a real executor.

A durable consume operation should conceptually be:

```python
def consume_permit(
    conn: sqlite3.Connection,
    *,
    permit_id: UUID,
    request_id: str,
    now_utc: datetime,
) -> ConsumeResult:
    conn.execute("BEGIN IMMEDIATE")

    permit = conn.execute(
        """
        SELECT *
        FROM permits
        WHERE permit_id = ?
        """,
        (str(permit_id),),
    ).fetchone()

    if permit is None:
        conn.rollback()
        raise PermitError("permit is unavailable")

    if permit["status"] != "ISSUED":
        conn.rollback()
        raise PermitError("permit is not consumable")

    if permit["expires_at"] <= now_utc.isoformat():
        conn.rollback()
        raise PermitError("permit is expired")

    conn.execute(
        """
        UPDATE permits
        SET status = 'CONSUMED',
            consumed_at = ?,
            consumed_by = ?
        WHERE permit_id = ?
          AND status = 'ISSUED'
        """,
        (now_utc.isoformat(), request_id, str(permit_id)),
    )

    if conn.execute("SELECT changes()").fetchone()[0] != 1:
        conn.rollback()
        raise PermitError("permit was concurrently consumed")

    append_event_in_same_transaction(
        conn,
        run_id=permit["run_id"],
        event_type="permit_consumed",
        payload={"permit_id": str(permit_id), "request_id": request_id},
        timestamp=now_utc.isoformat(),
    )

    conn.commit()
    return ConsumeResult(...)
```

The actual implementation should use parameterized SQL, explicit schema versioning, and a database abstraction that prevents accidental transaction fragmentation.

## 8.2 Idempotency

Define request identity separately from action identity:

```python
class RequestId(StrictStr):
    ...
```

or use a constrained string field:

```python
request_id: str = Field(min_length=1, max_length=128)
```

Persist:

```text
request_id
operation
request_hash
response_json
created_at
expires_at
```

Behavior:

- same request ID and same request hash → return stored response;
- same request ID and different request hash → reject;
- unknown request ID → process once;
- crash after commit but before response → retry returns stored response.

## 8.3 Structured executor results

Use a discriminated result model:

```python
class ExecutorReturned(StrictModel):
    kind: Literal["returned"] = "returned"
    request_id: str
    started_at: datetime
    finished_at: datetime
    api_result: dict[str, object]

class ExecutorUnknown(StrictModel):
    kind: Literal["unknown"] = "unknown"
    request_id: str
    reason: str
    retry_allowed: bool = False

class ExecutorFailed(StrictModel):
    kind: Literal["failed"] = "failed"
    request_id: str
    error_code: str
    message: str
```

The Coordinator should classify results and transition state. The executor should not decide that a desktop mutation was semantically successful.

## 8.4 Action state transition API

The current pure function is useful, but a durable service needs an API such as:

```python
def transition_action(
    action_id: str,
    expected_revision: int,
    target: ActionState,
    *,
    reason: str | None = None,
) -> ActionRecord:
    ...
```

The database update should use optimistic concurrency:

```sql
UPDATE actions
SET state = ?,
    state_revision = state_revision + 1,
    updated_at = ?
WHERE action_id = ?
  AND state_revision = ?
  AND state = ?
```

If zero rows are updated, reject the transition as stale or concurrent.

## 8.5 Observation invalidation

Every observation should carry a stable identity:

```python
class Observation(StrictModel):
    observation_id: str
    run_id: str
    revision: int
    captured_at: datetime
    coordinate_space_id: str
    display_topology_hash: str
    dpi_snapshot_hash: str
    foreground_window: str | None
    process_id: int | None
    session_id: int | None
    input_desktop: str | None
```

A coordinate action should require:

```text
proposal.coordinate_space_id == current_observation.coordinate_space_id
proposal.observation_revision == current_observation.revision
proposal.display_topology_hash == current_observation.display_topology_hash
proposal.dpi_snapshot_hash == current_observation.dpi_snapshot_hash
```

## 8.6 Event API hardening

Recommended changes:

- make the SQLite connection private;
- provide a transaction context manager;
- expose `append_in_transaction()`;
- normalize timestamps at the boundary;
- enforce event-type constraints;
- enforce payload-size limits;
- store schema version;
- verify integrity during startup;
- add checkpoint/backup APIs;
- define corruption response;
- test reopen/recovery.

Example:

```python
with store.transaction() as tx:
    tx.update_permit(...)
    tx.append_event(...)
```

This prevents the permit row and event journal from being committed separately.

---

# 9. Security analysis

## 9.1 Current guarantees

The repository currently provides:

- strict typed protocol validation;
- rejection of unknown fields;
- bounded input values;
- rejection of environment/provider origins as authority;
- observation and coordinate-space binding;
- expiring one-use in-process permits;
- one-active-mutation in-process boundary;
- SQLite hash-chain journaling;
- tamper and sequence-gap detection;
- explicit lifecycle transition tables.

## 9.2 Current non-guarantees

The current repository does not provide:

- durable authorization;
- authenticated IPC;
- process isolation;
- Windows session enforcement;
- desktop identity enforcement;
- executor isolation;
- secure credential handling;
- postcondition verification;
- recovery after crash;
- idempotency;
- durable leases;
- protection against another local process;
- emergency stop;
- signed release artifacts;
- installer security;
- browser isolation;
- voice privacy guarantees.

The repository’s `docs/security.md` correctly warns not to treat the prototype as a security boundary for unattended desktop control.

## 9.3 Windows-specific security risks

### Integrity levels and UIPI

`SendInput` can be blocked by UIPI. The executor must record this as a dispatch failure or unknown result and must not misclassify it as successful input.

### Session and desktop confusion

A process can exist in a different Windows session or input desktop from the intended user. Session ID and input desktop need to be captured and validated before dispatch.

### Window handle reuse

Window handles and process IDs can be reused. They must be bound to additional identity:

- process creation time;
- executable path;
- image hash where appropriate;
- window class/title;
- UI Automation runtime ID;
- observation revision.

### DPI virtualization

Logical and physical coordinates can diverge. Coordinate permits must be invalidated after DPI or monitor-topology changes.

### Secure desktop

UAC prompts and the secure desktop may be inaccessible from the normal user desktop. The executor must fail closed rather than attempting blind input.

### Local IPC impersonation

A local socket or named pipe without ACL and peer authentication can allow another local process to issue requests. The Coordinator must authenticate the UI and helper.

### Prompt injection

The current origin model is a good start, but the future system must preserve it across:

- screenshots;
- OCR;
- UI text;
- browser content;
- provider/model output;
- clipboard;
- voice transcription;
- imported documents.

Observed content must remain data, never authority.

---

# 10. Deployment and release requirements

## 10.1 Required release artifacts

For the current Python core:

- wheel;
- source distribution;
- package metadata;
- version consistency;
- clean-environment installation test;
- test report;
- coverage report.

For a Windows product:

- signed installer;
- signed native helper;
- signed application binaries;
- release manifest;
- checksums;
- supported Windows versions;
- supported Python/runtime strategy;
- migration procedure;
- rollback procedure;
- uninstall behavior;
- privacy notice;
- security contact;
- release notes;
- known limitations.

## 10.2 Versioning

The current mismatch between `0.2.1` in `pyproject.toml` and `0.2.0` in the checklist must be resolved.

Recommended versioning:

- package version;
- protocol version;
- database schema version;
- helper version;
- capability revision;
- policy revision;
- UI version.

Do not use one version string for all independently evolving contracts.

## 10.3 Main branch governance

The repository metadata reports that `main` is not protected.

Before production work:

- protect `main`;
- require CI;
- require review;
- prevent force pushes;
- enable dependency update automation;
- define release permissions;
- consider signed commits or signed tags;
- document whether unsigned commits are acceptable.

The repository metadata reports secret-scanning push protection enabled, which is positive, but this does not replace dependency or release governance.

---

# 11. Risks and likely failure points

## Highest risks

### 1. Treating typed authorization as execution

The current core returns a typed action but does not execute it. Any caller that assumes `consume()` means success would violate the documented boundary.

### 2. In-memory permit replay after restart

A restart loses consumed and active permit state. This is unacceptable for real desktop mutation.

### 3. Event/state inconsistency

The current coordinator mutates memory and appends events, but there is no single transaction containing durable state and event. A failure between those operations can create ambiguous state.

### 4. Windows session mismatch

A correctly authorized action may be sent to the wrong desktop/session if identity checks are missing.

### 5. DPI and monitor changes

Coordinate actions can target the wrong location after topology or scaling changes.

### 6. Unknown executor results

A crash after input injection but before the response creates an unknown outcome. Retrying blindly can duplicate an action.

### 7. UI Automation variability

Different applications expose different control patterns and properties. “Works with Notepad” does not imply general Windows UI support.

### 8. Packaging mismatch

The project is currently a Python library, not an installable Windows application. Packaging it as an app requires new runtime, installer, and signing decisions.

### 9. Dependency drift

The project has version ranges but no lock file. CI may test different dependency versions over time.

### 10. False confidence from Linux CI

Portable tests cannot verify Windows desktop behavior, UI Automation, DPI, sessions, input injection, or installer operation.

---

# 12. Missing information and unresolved questions

## Explicit unknowns

1. Is the actual intended task truly “None,” or should the builder instruction be treated as the requested Windows-app objective?
2. Is Electron required, or merely mentioned in planning material?
3. Should the app be per-user or per-machine?
4. Should the Coordinator be a desktop process, Windows service, or both?
5. Is physical input required, or should UI Automation be the preferred mechanism?
6. Which Windows versions are supported?
7. Which Python packaging strategy is expected?
8. Is Python bundled or installed separately?
9. Which installer technology is preferred?
10. Is code signing available?
11. What is the supported application matrix?
12. Is browser automation in scope?
13. Is voice in scope?
14. Are credentials ever entered or stored?
15. What is the threat model for other local users/processes?
16. What is the required recovery behavior after an unknown result?
17. What are the retention requirements for screenshots and audit artifacts?
18. Is the repository intended to be a library, an internal application, or a distributable product?
19. What does “ready to install” mean: internal test installer, signed beta, or production release?
20. What acceptance workflow should the Windows app demonstrate?

## NO DATA statements

- **NO DATA: no explicit user feature requirements were supplied.**
- **NO DATA: no issue or pull request defining the requested change was available in the inspected repository context.**
- **NO DATA: no Windows installer configuration exists in the repository tree.**
- **NO DATA: no Electron project exists in the repository tree.**
- **NO DATA: no Windows-native helper exists in the repository tree.**
- **NO DATA: no Windows acceptance test suite exists in the repository tree.**
- **NO DATA: no lock file exists in the repository tree.**
- **NO DATA: no independently reproduced test run was performed during this investigation.**
- **NO DATA: no independently verified GitHub Actions run was inspected.**
- **NO DATA: no current package publication or release artifact was verified.**

---

# 13. Recommended implementation sequence

## Phase 0: Resolve scope

Before writing code:

1. Confirm whether the task remains “None.”
2. If Windows delivery is intended, write acceptance criteria.
3. Define supported Windows versions.
4. Decide whether Electron is required.
5. Decide whether physical input is in scope.
6. Define the supported application matrix.
7. Define the threat model and release level.

## Phase 1: Freeze and harden the portable core

1. Correct version documentation.
2. Add protocol/schema version fields.
3. Add canonical serialization tests.
4. Make event-store internals private.
5. Add event payload and event-type limits.
6. Add reopen, corruption, and backup tests.
7. Add idempotency tests.
8. Add concurrent issue/consume tests.
9. Add explicit expiry/replay tests.
10. Add clean wheel-install tests.
11. Add a reproducibility strategy.

## Phase 2: Add durable coordinator state

1. Introduce schema migrations.
2. Add runs, actions, permits, leases, and idempotency tables.
3. Move consume into an atomic SQLite transaction.
4. Persist action and run state.
5. Add optimistic concurrency revisions.
6. Add durable active-mutation ownership.
7. Add restart recovery.
8. Add safe mode after corruption or ambiguous state.
9. Add watchdog and heartbeat.
10. Add checkpoint and backup handling.

## Phase 3: Define executor protocol

1. Define request/response schemas.
2. Add protocol version.
3. Add request IDs.
4. Add deadlines and cancellation.
5. Add capability revisions.
6. Define `RETURNED`, `FAILED`, and `UNKNOWN`.
7. Define crash-point behavior.
8. Build a fake executor first.
9. Test duplicate requests and unknown outcomes.

## Phase 4: Implement Windows observations

1. Capture user/session identity.
2. Capture input desktop.
3. Capture foreground window/process.
4. Capture process creation identity.
5. Capture monitor topology.
6. Capture DPI.
7. Define coordinate-space IDs.
8. Capture screenshots and metadata.
9. Implement invalidation on topology/session changes.
10. Run on an interactive Windows test machine.

## Phase 5: Implement Windows executor

1. Build observation adapter.
2. Build UI Automation adapter.
3. Run UIA on an appropriate COM MTA thread.
4. Add allowlisted process launch.
5. Add window focus with identity checks.
6. Add semantic UIA actions.
7. Add physical input only where explicitly permitted.
8. Add cancellation and emergency stop.
9. Add pre-dispatch checks.
10. Add structured executor results.

## Phase 6: Implement verification and evidence

1. Add post-observation capture.
2. Add independent verifiers.
3. Add evidence manifests.
4. Add artifact retention policy.
5. Add unknown-result reconciliation.
6. Ensure every mutation has a durable trace.
7. Test false-positive and false-negative verification behavior.

## Phase 7: Add local UI and IPC

1. Select UI technology.
2. Implement authenticated local IPC.
3. Keep UI non-authoritative.
4. Add run/action/permit visibility.
5. Add confirmation workflow.
6. Add cancellation and safe mode.
7. Add audit display.
8. Add UI security hardening.
9. Test process restart and IPC failures.

## Phase 8: Package and release

1. Select installer technology.
2. Bundle required runtimes.
3. Add migrations on upgrade.
4. Add signed binaries.
5. Add signed installer.
6. Test install, upgrade, downgrade, uninstall.
7. Test clean Windows profiles.
8. Test locked and disconnected sessions.
9. Publish supported capability labels.
10. Release only tested capabilities.

---

# 14. Final determination

## What exists now

The repository currently contains a small, well-bounded Python prototype implementing:

- strict typed protocol models;
- typed action unions;
- observation/action binding;
- in-process expiring permits;
- single-use consumption;
- an in-process mutation boundary;
- lifecycle transition tables;
- a SQLite tamper-evident event journal;
- portable invariant tests;
- Python packaging and CI.

## What does not exist now

It is not currently:

- a Windows application;
- a desktop automation product;
- an Electron app;
- a Windows-native helper;
- a UI Automation client;
- an input executor;
- a browser automation system;
- a voice application;
- a durable coordinator;
- a restart-recoverable action system;
- an installer;
- a signed release;
- a postcondition-verifying computer-use agent.

## Builder recommendation

If the intended deliverable is only the stated task, no code change is required because the task is `None`.

If the intended deliverable is the repository instruction to create a tested, installable Windows app, the work must begin with durable state and an executor protocol—not with Electron or physical input. The safety-critical implementation order is:

```text
durable state
→ atomic permits
→ idempotency and recovery
→ executor protocol
→ Windows observations
→ identity checks
→ UI Automation
→ physical input
→ verification
→ authenticated IPC
→ UI
→ installer and signing
```

The current honest product label remains:

> **Compuse portable safety-first coordination core; Windows computer-use application not yet implemented.**

----------

# Compuse Windows Application Implementation Plan

## Quick Start

### Scope status

**Fact:** The supplied task is `None`. The repository contains a builder instruction in `plan.md` requesting a tested and verified installable Windows application, but that instruction is repository content rather than an explicit user requirement.

**Decision:** Do not claim that a Windows application implementation is authorized or complete. This plan defines the work required if the intended objective is to turn the existing coordination core into a Windows application.

The implementation must begin with scope confirmation. Do not begin UI, installer, or physical input work until the following are answered:

1. Is Windows application delivery the intended task?
2. Which Windows versions are supported?
3. Is the application per-user or per-machine?
4. Is Electron required?
5. Is physical mouse/keyboard injection required?
6. Which applications must be supported?
7. Is unattended operation allowed?
8. What does “ready to install” mean: internal test installer, signed beta, or production release?

### Existing portable-core setup

The current repository declares Python `>=3.11`, Pydantic `>=2.7,<3`, Hatchling `>=1.25`, pytest `>=8`, and pytest-cov `>=5`.

From the repository root:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -e ".[test]"

pytest --cov=compuse --cov-report=term-missing
python -m build
```

**Verification limitation:** These commands are prescribed from repository configuration and findings. They were not executed during the research task. Do not report them as passing until they have run successfully in the target environment.

### Implementation order

Build in this order:

```text
scope confirmation
→ portable-core hardening
→ durable coordinator state
→ atomic permits and recovery
→ executor protocol
→ Windows observation provider
→ Windows executor
→ postcondition verification
→ authenticated local IPC
→ desktop UI
→ installer and signing
→ Windows acceptance testing
```

Do not reverse this order by building a UI around the existing in-memory coordinator. The current coordinator is not restart-safe and does not execute actions.

---

## Requirements

### Verified repository requirements

The current package requires:

```text
Python >= 3.11
pydantic >= 2.7, < 3
```

The current test and build configuration uses:

```text
hatchling >= 1.25
pytest >= 8
pytest-cov >= 5
```

The package is named `compuse` and currently reports version `0.2.1` in `pyproject.toml`.

### Required product requirements if Windows delivery is approved

The Windows application must provide, at minimum:

- durable run and action state;
- restart recovery;
- one-use, expiring permits;
- atomic permit consumption;
- request idempotency;
- authenticated local IPC;
- Windows session and desktop identity checks;
- observation capture;
- coordinate-space and DPI binding;
- an executor with explicit capabilities;
- independent postcondition verification;
- explicit `UNKNOWN` handling;
- cancellation and emergency stop;
- tamper-evident event journaling;
- installer and upgrade behavior;
- Windows-native acceptance tests;
- reproducible release artifacts.

### Non-requirements unless separately approved

The following are not currently present or authorized by repository evidence:

- browser automation;
- voice control;
- credential storage;
- unattended operation;
- arbitrary application launch;
- unrestricted physical input;
- cloud services;
- remote control;
- Electron;
- a Windows service;
- an auto-update mechanism.

Do not add any of these without an explicit scope decision.

### Acceptance criteria

The implementation is not complete until all applicable criteria below are satisfied:

1. A fresh Windows installation can start the application.
2. The Coordinator persists state across process restart.
3. A consumed permit cannot be reused after restart.
4. Concurrent consumers cannot consume one permit twice.
5. A stale observation cannot authorize a coordinate action.
6. A changed session, desktop, process, window, monitor topology, or DPI invalidates the action where relevant.
7. The executor cannot self-authorize an action.
8. Executor crashes produce a durable `UNKNOWN` state rather than an automatic retry.
9. Every dispatched action receives a postcondition result of `VERIFIED`, `FAILED`, `UNKNOWN`, or `REQUIRES_USER_INTERVENTION`.
10. Local IPC rejects unauthenticated or malformed clients.
11. The UI cannot directly access the executor or SQLite database.
12. The event chain detects tampering and sequence gaps.
13. Install, upgrade, rollback, and uninstall behavior are tested.
14. Release artifacts are version-consistent and, if production distribution is intended, signed.

---

## Current State

### Repository structure

The verified repository tree is:

```text
.github/
  workflows/
    test.yml

LICENSE
README.md

compuse/
  __init__.py
  coordinator/
    __init__.py
    core.py
    states.py
  protocol/
    __init__.py
    models.py
  storage/
    __init__.py
    events.py

docs/
  final-execution-checklist.md
  protocol.md
  security.md
  supported-capabilities.md
  test-matrix.md
  windows-development.md

plan.md
pyproject.toml

tests/
  test_core.py
  test_states.py
  test_storage.py
```

There are no verified Electron, frontend, Windows-native helper, installer, migration, IPC, or Windows integration-test files.

### Existing protocol

`compuse/protocol/models.py` contains strict Pydantic models using:

```python
class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
```

The protocol includes:

- trusted and untrusted origins;
- observation models;
- action proposals;
- permits;
- typed actions;
- action hashing;
- process, session, window, tool, capability, launch, and browser metadata fields.

The current action union includes:

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

These are protocol models only. They do not perform those actions.

### Existing coordinator

`compuse/coordinator/core.py` currently supports:

```python
Coordinator.issue(...)
Coordinator.consume(...)
Coordinator.release(...)
Coordinator.cleanup(...)
```

The coordinator validates:

- positive permit TTL;
- maximum permit TTL of 300 seconds;
- trusted proposal origin;
- matching run IDs;
- matching observation revision;
- matching coordinate-space ID;
- current policy revision;
- action digest;
- single active mutation;
- permit expiry;
- permit replay.

The state is held in memory:

```python
self._permits = {}
self._active_permit = None
```

Consequences:

- permits disappear on restart;
- consumed state disappears on restart;
- active mutation ownership disappears on restart;
- an event record does not prevent permit replay;
- there is no durable idempotency;
- there is no durable lease;
- there is no crash recovery.

This is the primary blocker to real desktop execution.

### Existing state model

`compuse/coordinator/states.py` defines run and action state tables, including:

```text
IDLE
TASK_ACCEPTED
OBSERVING
PLANNING
WAITING_FOR_CONFIRMATION
READY_TO_EXECUTE
ACTION_EXECUTING
VERIFYING
RECOVERY
PAUSED
COMPLETED
CANCELLED
ABORTED
```

and:

```text
PROPOSED
PERMIT_PENDING
PERMITTED
DISPATCHING
DISPATCHED
EXECUTOR_RETURNED
VERIFICATION_PENDING
VERIFIED
FAILED
UNKNOWN
RECONCILING
RECONCILED_SUCCESS
RECONCILED_FAILURE
CANCELLED
ABORTED
```

The transition tables fail closed, but they are not durable. The implementation must preserve these state names unless a documented state-model change is approved.

### Existing event journal

`compuse/storage/events.py` provides a SQLite event store with:

- one SQLite connection per store;
- `RLock`;
- foreign keys;
- busy timeout;
- `synchronous=FULL`;
- WAL for file-backed databases;
- explicit `BEGIN IMMEDIATE`;
- per-run sequence numbers;
- SHA-256 hash chaining;
- canonical JSON payloads;
- chain verification;
- tamper and sequence-gap detection.

The current public database attribute is used by white-box tests for tampering. The production API should make the connection private and expose controlled transaction APIs.

### Existing CI

`.github/workflows/test.yml` tests Python:

```yaml
["3.11", "3.12", "3.13"]
```

It installs `.[test]` and runs:

```bash
pytest --cov=compuse --cov-report=term-missing --cov-fail-under=80
```

The workflow is portable Python CI. It does not test Windows input, UI Automation, sessions, DPI, installers, or application behavior.

### Version mismatch

`pyproject.toml` declares version `0.2.1`, while `docs/final-execution-checklist.md` documents `0.2.0` artifacts:

```text
compuse-0.2.0-py3-none-any.whl
compuse-0.2.0.tar.gz
```

Resolve this before release automation. The package version, documentation, artifact names, and release metadata must agree.

---

## Implementation Design

### Architecture

The target architecture is:

```text
Desktop UI
    |
    | authenticated local IPC
    v
Python Coordinator
    |
    +-- durable SQLite state
    +-- policy and authority checks
    +-- permit manager
    +-- lifecycle state machine
    +-- recovery/watchdog
    +-- evidence/artifact manager
    |
    | authenticated restricted IPC
    v
Windows Executor
    |
    +-- observation provider
    +-- UI Automation adapter
    +-- screenshot provider
    +-- input dispatcher
    +-- allowlisted launcher
    +-- cancellation and emergency stop
```

The Coordinator is the only component allowed to:

- accept user intent;
- decide whether a proposal is trusted;
- issue permits;
- consume permits;
- transition authoritative state;
- classify executor results;
- declare verification outcomes.

The executor is a capability-limited worker. It must never infer authorization from a screenshot, UI text, provider output, or its own request payload.

### Component responsibilities

#### Coordinator

The Coordinator owns:

- run lifecycle;
- action lifecycle;
- policy revision;
- permit creation and consumption;
- durable idempotency;
- lease ownership;
- current observation binding;
- executor request creation;
- result classification;
- verification scheduling;
- recovery and safe mode.

#### Observation provider

The observation provider captures:

- timestamp;
- run and observation revision;
- foreground window;
- process ID;
- process identity;
- Windows session ID;
- input desktop;
- monitor topology;
- DPI snapshot;
- coordinate-space identity;
- screenshot metadata;
- UI Automation target identity where applicable.

#### Executor

The executor receives a Coordinator-issued request and validates:

- protocol version;
- permit ID;
- action ID;
- request ID;
- run ID;
- capability revision;
- observation revision;
- coordinate-space ID;
- session ID;
- input desktop;
- target process/window identity;
- expiry;
- cancellation status.

It returns a structured result. It does not declare semantic success.

#### Verifier

The verifier captures a new observation and evaluates an explicit postcondition. It must return one of:

```text
VERIFIED
FAILED
UNKNOWN
REQUIRES_USER_INTERVENTION
```

A successful Win32 or UI Automation API call is not sufficient to return `VERIFIED`.

#### Desktop UI

The UI displays state and requests operations through IPC. It must not:

- access the SQLite file directly;
- invoke executor operations directly;
- hold signing keys or policy authority;
- interpret screenshots as authorization;
- bypass confirmation or permit expiry.

### Durable state model

Use SQLite initially because the repository already uses SQLite and the current deployment is local-first.

Add durable tables for:

```text
schema_migrations
runs
actions
permits
leases
idempotency_keys
observations
executor_requests
executor_results
verifications
artifacts
confirmations
```

Recommended fields:

```text
runs:
  run_id
  state
  state_revision
  created_at
  updated_at
  owner_instance_id
  recovery_required

actions:
  action_id
  run_id
  request_id
  state
  state_revision
  action_kind
  action_json
  action_hash
  observation_revision
  policy_revision
  capability_hash
  created_at
  updated_at

permits:
  permit_id
  action_id
  run_id
  status
  issued_at
  expires_at
  consumed_at
  consumed_by
  action_hash
  permit_version

leases:
  lease_name
  owner_id
  acquired_at
  expires_at
  heartbeat_at

idempotency_keys:
  request_id
  operation
  request_hash
  response_json
  created_at
  expires_at
```

Use migrations with a schema version. Do not silently create or alter production tables outside the migration mechanism.

### Atomic state and event updates

State updates and corresponding events must commit in the same SQLite transaction.

Recommended abstraction:

```python
from contextlib import contextmanager
from collections.abc import Iterator
import sqlite3

class Database:
    def __init__(self, path: str) -> None:
        self._db = sqlite3.connect(
            path,
            isolation_level=None,
            check_same_thread=False,
        )
        self._db.execute("PRAGMA foreign_keys = ON")
        self._db.execute("PRAGMA busy_timeout = 10000")
        self._db.execute("PRAGMA synchronous = FULL")
        self._db.execute("PRAGMA journal_mode = WAL")

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        self._db.execute("BEGIN IMMEDIATE")
        try:
            yield self._db
        except BaseException:
            self._db.rollback()
            raise
        else:
            self._db.commit()
```

The actual implementation must account for SQLite setup behavior, connection lifecycle, corruption, and shutdown. This snippet is an implementation pattern, not a claim about current repository code.

### Durable permit consumption

Permit consumption must be conditional and atomic:

```python
def consume_permit(
    conn: sqlite3.Connection,
    *,
    permit_id: str,
    request_id: str,
    now_iso: str,
) -> None:
    row = conn.execute(
        """
        SELECT status, expires_at, run_id, action_hash
        FROM permits
        WHERE permit_id = ?
        """,
        (permit_id,),
    ).fetchone()

    if row is None:
        raise PermitError("permit does not exist")

    status, expires_at, run_id, action_hash = row

    if status != "ISSUED":
        raise PermitError("permit is not consumable")

    if expires_at <= now_iso:
        raise PermitError("permit is expired")

    cursor = conn.execute(
        """
        UPDATE permits
        SET status = 'CONSUMED',
            consumed_at = ?,
            consumed_by = ?
        WHERE permit_id = ?
          AND status = 'ISSUED'
        """,
        (now_iso, request_id, permit_id),
    )

    if cursor.rowcount != 1:
        raise PermitError("permit was concurrently consumed")

    # Append the permit_consumed event in this same transaction.
```

The final implementation must also verify the proposal digest, run, observation, policy, capability, session, window, process, and coordinate-space bindings before committing.

### Optimistic concurrency

Every durable run and action record should have a revision number.

Transition API:

```python
def transition_action(
    conn: sqlite3.Connection,
    *,
    action_id: str,
    expected_revision: int,
    expected_state: str,
    target_state: str,
    updated_at: str,
) -> None:
    cursor = conn.execute(
        """
        UPDATE actions
        SET state = ?,
            state_revision = state_revision + 1,
            updated_at = ?
        WHERE action_id = ?
          AND state = ?
          AND state_revision = ?
        """,
        (
            target_state,
            updated_at,
            action_id,
            expected_state,
            expected_revision,
        ),
    )

    if cursor.rowcount != 1:
        raise ConcurrentStateError(
            "action state changed before transition completed"
        )
```

This prevents stale workers from overwriting newer state.

### Idempotency

Distinguish request identity from action identity.

Required behavior:

```text
same request_id + same request_hash
    → return the previously committed response

same request_id + different request_hash
    → reject as conflicting reuse

new request_id
    → process once and persist the result

retry after process crash
    → return the committed response if the transaction completed
```

Idempotency records must be written in the same transaction as the operation they describe.

### Recovery

On startup:

1. Open the database.
2. Apply migrations.
3. Verify event-chain integrity.
4. Verify required tables and indexes.
5. Check for expired permits and leases.
6. Find actions in non-terminal states.
7. Mark potentially in-flight executor operations as `UNKNOWN`.
8. Require reconciliation rather than retrying automatically.
9. Enter safe mode if integrity verification fails.
10. Emit a startup/recovery event.

Do not resume physical input automatically after a process restart.

### Observation identity

Extend the observation model with explicit identity fields:

```python
class Observation(StrictModel):
    observation_id: str
    run_id: str
    revision: int
    captured_at: datetime
    coordinate_space_id: str
    display_topology_hash: str
    dpi_snapshot_hash: str
    foreground_window: str | None
    process_id: int | None
    session_id: int | None
    input_desktop: str | None
```

A coordinate action must require matching:

```text
proposal.observation_revision
proposal.coordinate_space_id
proposal.display_topology_hash
proposal.dpi_snapshot_hash
```

Any monitor, scaling, DPI, session, or desktop change invalidates the relevant permit.

### Executor result model

Use structured result variants:

```python
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict

class ExecutorResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

class ExecutorReturned(ExecutorResult):
    kind: Literal["returned"] = "returned"
    request_id: str
    started_at: datetime
    finished_at: datetime
    api_result: dict[str, object]

class ExecutorFailed(ExecutorResult):
    kind: Literal["failed"] = "failed"
    request_id: str
    error_code: str
    message: str

class ExecutorUnknown(ExecutorResult):
    kind: Literal["unknown"] = "unknown"
    request_id: str
    reason: str
    retry_allowed: bool = False
```

The result must include enough information for durable reconciliation. Do not treat `ExecutorReturned` as `VERIFIED`.

---

## File and Change Map

### Existing files to modify

#### `pyproject.toml`

Modify only after scope approval:

- resolve the version mismatch;
- retain Python `>=3.11`;
- retain Pydantic `>=2.7,<3`;
- add only dependencies selected for the approved implementation;
- add application entry points only when an actual runtime entry point exists;
- add test, lint, type-check, and Windows-specific optional groups only if adopted.

Do not add Electron dependencies to Python configuration.

#### `compuse/protocol/models.py`

Add, in separate reviewable changes:

- protocol version;
- schema version;
- request IDs;
- observation identity fields;
- display topology and DPI hashes;
- executor request/result models;
- verification result models;
- explicit action and capability revisions;
- stricter validation for hashes and identifiers.

Preserve `extra="forbid"` and strict validation.

#### `compuse/coordinator/core.py`

Refactor the current in-memory permit implementation behind a durable repository/service boundary.

Do not remove existing invariant checks. Move them into reusable validation functions so both issue and consume paths use the same rules.

#### `compuse/coordinator/states.py`

Retain existing state names unless acceptance criteria require a change. Add:

- durable transition validation integration;
- terminal-state helpers;
- recovery-state helpers;
- explicit unknown-result transitions;
- optimistic revision handling.

#### `compuse/storage/events.py`

Modify to:

- make the SQLite connection private;
- add transaction context management;
- support appending within an existing transaction;
- enforce event-size limits;
- store event schema versions;
- provide startup verification;
- provide backup/checkpoint APIs;
- define corruption behavior.

#### `tests/test_core.py`

Add:

- expiry and replay tests;
- concurrent consume tests;
- restart tests;
- idempotency tests;
- action digest stability tests;
- changed identity-binding tests.

#### `tests/test_storage.py`

Add:

- reopen tests;
- rollback tests;
- WAL recovery tests;
- backup/restore tests;
- corruption tests;
- concurrent process tests;
- event-size and invalid-event tests.

#### `docs/protocol.md`

Document:

- protocol version;
- canonical serialization;
- digest scope;
- request and action identity;
- executor result semantics;
- `UNKNOWN` behavior;
- compatibility rules.

#### `docs/security.md`

Document:

- local IPC threat model;
- Windows integrity levels;
- session and input-desktop checks;
- DPI and coordinate risks;
- executor isolation;
- recovery behavior;
- artifact retention;
- safe mode.

#### `docs/supported-capabilities.md`

Label each capability accurately:

```text
protocol-only
implemented-portable
implemented-windows
tested-windows
release-supported
```

Do not label typed action models as executable capabilities.

#### `docs/test-matrix.md`

Add a Windows matrix covering:

- interactive session;
- locked session;
- disconnected RDP;
- wrong session;
- wrong input desktop;
- foreground-window changes;
- process restart;
- process ID reuse;
- window handle reuse;
- DPI changes;
- multi-monitor changes;
- UAC/secure desktop;
- executor crash;
- helper timeout;
- unknown dispatch result.

#### `.github/workflows/test.yml`

Keep the existing Python matrix. Add only portable checks that can run reliably in GitHub-hosted CI.

Windows desktop integration tests require a Windows runner with an interactive desktop. Do not assume ordinary CI runners can provide this.

### New recommended Python files

These are recommendations, not existing files:

```text
compuse/
  coordinator/
    core.py
    states.py
    runtime.py
    policy.py
    permits.py
    recovery.py
    leases.py
    idempotency.py
  protocol/
    models.py
    executor.py
    verification.py
  storage/
    events.py
    database.py
    migrations.py
  windows/
    __init__.py
    observation.py
    identity.py
    coordinates.py
    executor_client.py
  verification/
    __init__.py
    predicates.py
    service.py
```

### New database files

Recommended:

```text
compuse/storage/migrations/
  001_initial.sql
  002_durable_permits.sql
  003_idempotency.sql
  004_executor_results.sql
```

Migration filenames and contents must be added only after the schema is agreed. Do not claim these files exist currently.

### New Windows helper

The repository currently contains no helper. Choose one implementation after evaluating packaging and COM behavior:

```text
windows-helper/
  ...
```

Possible technologies include:

- Python with `ctypes`;
- `pywin32`;
- `comtypes`;
- C#;
- C++;
- Rust.

The selected technology must be recorded in the architecture decision record. The helper must expose a narrow protocol and must not receive arbitrary commands.

### New UI

Only if approved:

```text
desktop/
  package.json
  electron/
    main.ts
    preload.ts
    ipc.ts
  renderer/
    ...
```

No UI framework or Electron version can be specified as verified because none exists in the repository.

### New installer configuration

Add only after selecting a packaging technology:

```text
installer/
  ...
```

The release must document:

- runtime bundling;
- install scope;
- ACLs;
- helper placement;
- database location;
- migration behavior;
- code-signing process;
- uninstall behavior.

---

## Step-by-Step Build Plan

### Step 0: Confirm scope and acceptance criteria

Before code changes:

1. Confirm whether the task is still `None`.
2. If Windows delivery is intended, create an issue or approved requirements document.
3. Select supported Windows versions.
4. Select per-user or per-machine installation.
5. Decide whether Electron is required.
6. Decide whether physical input is required.
7. Define the supported application matrix.
8. Define whether unattended operation is forbidden.
9. Define expected installer type.
10. Define release signing requirements.

**Exit condition:** An approved scope exists. If scope remains `None`, stop after documenting the audit; do not implement unrelated features.

### Step 1: Correct package and documentation inconsistencies

1. Choose the authoritative package version.
2. Update `pyproject.toml`.
3. Update `docs/final-execution-checklist.md`.
4. Update README installation instructions if they mention the old version.
5. Build wheel and sdist.
6. Verify artifact names match the selected version.
7. Install the wheel into a clean Python 3.11 environment.

Commands:

```powershell
Remove-Item -Recurse -Force .\dist -ErrorAction SilentlyContinue
python -m build
python -m pip install --force-reinstall .\dist\*.whl
```

Do not record success until the commands complete.

### Step 2: Freeze the portable protocol

1. Add protocol and schema version fields.
2. Define canonical serialization rules.
3. Define whether Unicode normalization is used.
4. Define digest coverage.
5. Add tests for digest stability.
6. Add tests for strict nested validation.
7. Add tests for malformed UUIDs, hashes, timestamps, identifiers, and action kinds.
8. Document compatibility behavior.

Digest tests should verify that semantically identical serialized actions produce the same digest and that any permit-relevant mutation changes it.

### Step 3: Harden the event store

1. Make the database connection private.
2. Add a transaction context manager.
3. Add `append_in_transaction`.
4. Add event type and payload size limits.
5. Add event schema version.
6. Add reopen tests.
7. Add rollback tests.
8. Add backup and restore tests.
9. Add startup integrity verification.
10. Define behavior for corruption and disk-full errors.

Required failure behavior:

```text
event append failure
→ transaction rollback
→ authoritative state unchanged
→ error recorded if possible
→ safe mode if consistency cannot be established
```

### Step 4: Add migrations and durable state

1. Create the migration runner.
2. Create the initial durable schema.
3. Add runs, actions, permits, leases, and idempotency records.
4. Add indexes for run ID, action ID, permit ID, request ID, and state.
5. Add schema migration tests.
6. Test upgrade from an empty database.
7. Test upgrade from each prior schema version once versions exist.

Do not modify the database directly from application code outside the migration and repository layers.

### Step 5: Replace in-memory permit authority

1. Persist permit issue operations.
2. Persist permit status.
3. Persist expiry.
4. Persist consumed timestamp and consumer identity.
5. Persist the action digest.
6. Perform consume using `BEGIN IMMEDIATE`.
7. Append the consume event in the same transaction.
8. Add conditional update checks.
9. Add restart tests.
10. Add two-process or two-thread race tests.

Required invariant:

```text
one permit
→ zero or one successful consume
→ never two successful consumes
```

### Step 6: Add idempotency and recovery

1. Add request IDs to protocol models.
2. Persist request hashes and responses.
3. Return prior responses for identical retries.
4. Reject conflicting request reuse.
5. Mark in-flight executor work as `UNKNOWN` on restart.
6. Never automatically repeat an uncertain mutation.
7. Add explicit reconciliation commands or UI actions.
8. Add safe mode when integrity checks fail.

### Step 7: Define the executor protocol

1. Define executor request and result models.
2. Include protocol version.
3. Include request ID, action ID, permit ID, and run ID.
4. Include deadline and cancellation fields.
5. Include capability revision.
6. Define `RETURNED`, `FAILED`, and `UNKNOWN`.
7. Define error codes.
8. Build a fake executor.
9. Test timeout, crash, duplicate request, cancellation, and malformed response cases.

The fake executor must be used for coordinator tests before Windows APIs are introduced.

### Step 8: Implement Windows observation

1. Implement interactive-session detection.
2. Capture session ID.
3. Capture input desktop.
4. Capture foreground window and process.
5. Capture process creation identity where possible.
6. Capture monitor topology.
7. Capture DPI information.
8. Generate a coordinate-space ID.
9. Capture screenshot metadata.
10. Add invalidation when identity or geometry changes.

Observation acquisition must fail closed when required fields cannot be obtained.

### Step 9: Implement UI Automation

1. Choose the Windows API binding or native helper.
2. Define the COM threading model.
3. Implement UI tree lookup.
4. Implement element identity capture.
5. Revalidate elements before dispatch.
6. Support only explicitly implemented control patterns.
7. Return structured unsupported-capability errors.
8. Test against the approved application matrix.
9. Test applications with different UI Automation providers.

Do not treat an element reference captured in an old observation as permanently valid.

### Step 10: Implement physical input only if approved

1. Define allowed capabilities.
2. Validate session and input desktop.
3. Validate foreground process/window.
4. Validate coordinate-space ID.
5. Validate DPI and monitor topology.
6. Validate permit expiry.
7. Dispatch through the selected Windows API.
8. Record the API result.
9. Capture a post-dispatch observation.
10. Verify the postcondition.
11. Classify blocked or ambiguous results as `FAILED` or `UNKNOWN`.

Do not equate a successful `SendInput` return count with successful application behavior.

### Step 11: Implement verification

1. Define predicates for each supported action.
2. Capture before and after observations.
3. Store verification inputs and outputs.
4. Store artifact references rather than embedding large binary data in events.
5. Return explicit verification categories.
6. Add negative tests where dispatch succeeds but the desired state does not change.
7. Add unknown-result tests.
8. Add user-reconciliation flow.

### Step 12: Add authenticated local IPC

1. Select a local transport.
2. Define peer authentication and ACL behavior.
3. Define request and response envelopes.
4. Enforce protocol version.
5. Enforce maximum message size.
6. Enforce deadlines and cancellation.
7. Reject unknown fields.
8. Add request IDs and idempotency.
9. Test unauthorized local clients.
10. Test malformed, oversized, replayed, and concurrent requests.

The UI must communicate with the Coordinator, not the executor.

### Step 13: Add UI only after the backend is durable

1. Display run and action state.
2. Display observation age.
3. Display current target identity.
4. Display permit expiry.
5. Display executor result.
6. Display verification result.
7. Display safe mode and recovery requirements.
8. Add confirmation controls.
9. Add cancellation and emergency stop.
10. Add audit-event viewing.
11. Test UI behavior across Coordinator restarts.
12. Harden renderer and preload boundaries if Electron is selected.

### Step 14: Package and install

1. Select installer technology.
2. Decide whether Python is bundled.
3. Bundle the Coordinator, UI, and helper.
4. Define database and log directories.
5. Define install scope and ACLs.
6. Add migration-on-upgrade.
7. Add rollback behavior.
8. Add clean-install tests.
9. Add upgrade tests.
10. Add uninstall tests.
11. Sign binaries and installer if required.
12. Produce checksums and release manifest.

### Step 15: Windows acceptance testing

Run on a real Windows interactive desktop:

- normal unlocked session;
- locked workstation;
- disconnected RDP;
- multiple monitors;
- DPI scaling changes;
- monitor docking/undocking;
- foreground-window changes;
- process restart;
- helper crash;
- Coordinator restart;
- wrong session;
- wrong input desktop;
- UAC or secure desktop;
- stale permit;
- expired permit;
- duplicate request;
- unknown executor result;
- emergency stop;
- database corruption;
- disk-full simulation;
- install, upgrade, rollback, and uninstall.

No Linux-only or ordinary portable CI result can substitute for these tests.

---

## Technical Details

### Canonical action digest

The current pattern is:

```python
from hashlib import sha256
import json

def digest_action(action) -> str:
    encoded = json.dumps(
        action.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()
```

Before production use, document:

- canonical encoding version;
- UTF-8 encoding;
- Unicode normalization policy;
- numeric representation;
- schema version inclusion;
- exact fields included;
- whether the digest covers only the action or also permit metadata.

A SHA-256 digest detects changes to a trusted value. It does not authenticate an untrusted IPC caller. Authentication must be provided separately.

### Timestamp handling

The current observation timestamp requires timezone awareness and normalizes to UTC.

Preserve this behavior. Add tests for:

- UTC timestamps;
- non-UTC offsets;
- naive timestamps;
- daylight-saving transitions;
- expired permits at exact boundary times;
- clock skew policy.

Use an injectable clock in coordinator tests so expiry behavior is deterministic.

### SQLite behavior

The current use of:

```sql
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 10000;
PRAGMA synchronous = FULL;
PRAGMA journal_mode = WAL;
```

is consistent with the existing local SQLite design.

Document:

- database location;
- WAL and shared-memory file handling;
- backup procedure;
- retention;
- recovery after abnormal termination;
- disk-full behavior;
- corruption response;
- whether multiple Coordinator processes are supported.

If only one Coordinator process is supported, enforce that with a durable lease or process lock. Do not rely only on convention.

### Lease ownership

A process or instance lease should include:

```text
lease_name
owner_id
acquired_at
heartbeat_at
expires_at
```

Rules:

- only one active Coordinator owns the mutation lease;
- lease acquisition is transactional;
- heartbeat is periodic;
- expired leases require recovery review;
- a new owner cannot resume uncertain physical input automatically;
- lease loss forces safe mode.

### Windows identity

Bind actions to more than a process ID or window handle. Where available, include:

- session ID;
- input desktop;
- process ID;
- process creation time;
- executable path;
- executable identity;
- window handle;
- window class;
- UI Automation runtime ID;
- observation revision.

Process IDs and window handles can be reused. Revalidate immediately before dispatch.

### UI Automation

Use UI Automation for semantic operations where the target application exposes appropriate controls.

Expected adapter responsibilities:

```python
class UiaAdapter:
    def locate(self, locator, observation):
        ...

    def invoke(self, element):
        ...

    def set_value(self, element, value):
        ...

    def select(self, element):
        ...
```

The final implementation must define actual types and error behavior. The adapter must report unsupported controls instead of falling back silently to blind coordinates.

### DPI and coordinates

Every coordinate action must include:

```text
coordinate_space_id
observation_revision
display_topology_hash
dpi_snapshot_hash
```

Reject the action if any current value differs.

The implementation must explicitly distinguish:

- logical coordinates;
- physical screen coordinates;
- monitor-relative coordinates;
- virtual desktop coordinates.

Test:

- 100%, 125%, 150%, and other supported scales;
- multiple monitors;
- monitors with different scales;
- docking and undocking;
- RDP scaling;
- topology changes during a pending permit.

### Error taxonomy

Define stable error codes, for example:

```text
INVALID_REQUEST
UNTRUSTED_ORIGIN
STALE_OBSERVATION
COORDINATE_SPACE_MISMATCH
POLICY_REVISION_MISMATCH
PERMIT_EXPIRED
PERMIT_CONSUMED
PERMIT_NOT_FOUND
ACTIVE_MUTATION_EXISTS
SESSION_MISMATCH
INPUT_DESKTOP_MISMATCH
WINDOW_MISMATCH
PROCESS_MISMATCH
CAPABILITY_UNSUPPORTED
EXECUTOR_TIMEOUT
EXECUTOR_CRASHED
EXECUTOR_UNKNOWN
VERIFICATION_FAILED
DATABASE_CORRUPTION
SAFE_MODE
```

Error messages may be human-readable, but machine behavior must use stable codes.

### Logging and artifacts

Logs must not contain:

- credentials;
- full typed text when sensitive;
- arbitrary clipboard contents;
- unredacted screenshots unless explicitly allowed;
- secrets in exception messages.

Events should contain references to artifacts rather than large screenshots. Define:

- artifact directory;
- retention period;
- redaction policy;
- access permissions;
- deletion behavior;
- encryption requirements, if needed.

The current repository does not define these policies. They are required before production deployment.

---

## Testing and Verification

### Portable unit tests

Run:

```powershell
python -m pytest -ra --cov=compuse --cov-report=term-missing --cov-fail-under=80
```

Add coverage for:

- strict model behavior;
- canonical digest;
- trusted-origin enforcement;
- stale observation rejection;
- permit expiry;
- permit replay;
- single active mutation;
- release and cleanup;
- state transitions;
- durable transactions;
- idempotency;
- restart recovery;
- event tampering;
- sequence gaps;
- rollback.

Coverage percentage is a quality signal, not proof of safety. Critical invariants require direct tests.

### Property-based tests

**Recommendation:** Add Hypothesis only if the project accepts another test dependency.

Generate:

- malformed action payloads;
- unknown fields;
- boundary coordinate values;
- TTL values;
- timestamps;
- concurrent state transition sequences;
- action mutations.

Properties:

```text
unknown fields are rejected
untrusted origins never receive permits
one permit cannot be consumed twice
changing any digest-covered field changes the digest
stale revisions are rejected
invalid transitions never succeed
```

### Concurrency tests

Test:

- simultaneous issue calls;
- simultaneous consume calls;
- simultaneous release and consume;
- two Coordinator instances;
- SQLite writer contention;
- event sequence allocation;
- lease acquisition races.

Use barriers to force races instead of relying on timing.

### Restart tests

For each durable operation:

1. Start Coordinator.
2. Issue or consume a permit.
3. Terminate the process at controlled points.
4. Reopen the database.
5. Verify state and event consistency.
6. Verify uncertain executor work becomes `UNKNOWN`.
7. Verify no automatic duplicate input occurs.

Controlled crash points should include:

```text
before database transaction
after state update before event append
after event append before commit
after commit before response
after executor dispatch before result
```

### Event-store tests

Add tests for:

- tampered payload;
- tampered hash;
- missing sequence;
- duplicate sequence;
- invalid previous hash;
- malformed timestamp;
- oversized payload;
- failed transaction;
- database reopen;
- WAL files;
- backup while active;
- restore to a new database;
- corruption and safe mode.

### Windows integration tests

These require a Windows environment with an interactive desktop and should be segregated from portable CI.

Test:

- observation capture;
- foreground-window identity;
- process/session identity;
- input desktop;
- UI Automation lookup;
- UI Automation action;
- `SendInput` error handling if physical input is approved;
- DPI and monitor topology;
- locked session;
- secure desktop;
- RDP disconnect;
- helper crash;
- cancellation;
- emergency stop;
- verification predicates.

### Installer tests

Test on clean Windows machines or clean virtual machines:

- fresh install;
- first launch;
- normal shutdown;
- restart;
- upgrade;
- failed upgrade;
- rollback;
- uninstall;
- data retention;
- permissions;
- missing runtime;
- missing helper;
- corrupted database;
- user profile with non-ASCII path;
- spaces in installation path.

### Verification evidence

Each test run must record:

- commit identifier;
- package version;
- protocol version;
- schema version;
- OS version;
- Python/runtime version;
- dependency versions;
- test command;
- pass/fail result;
- logs;
- installer checksum where relevant.

Do not describe repository-documented historical results as newly verified.

---

## Security and Reliability

### Authority boundaries

Maintain the current rule:

```text
environment content and provider output are data, not authority
```

This rule must hold across:

- screenshots;
- OCR;
- UI Automation text;
- browser content;
- clipboard;
- voice transcription;
- model output;
- imported documents.

Only trusted Coordinator logic may authorize actions.

### Process boundaries

The UI, Coordinator, and executor should be separate authority domains:

- UI requests;
- Coordinator authorizes;
- executor dispatches;
- verifier evaluates.

The executor must not accept arbitrary commands from the UI.

### Local IPC security

The selected IPC transport must provide:

- local-only binding;
- authenticated peer identity;
- access control;
- request size limits;
- schema validation;
- protocol versioning;
- request IDs;
- deadlines;
- cancellation;
- replay resistance where required;
- safe handling of client disconnects.

A local transport without peer authentication is insufficient for an input-capable application.

### Least privilege

Run components with the minimum required privileges.

Do not elevate the entire application merely because one target application may run at a higher integrity level. If elevated targets are in scope, define a separate, narrowly controlled mechanism and document the security impact.

### Safe mode

Enter safe mode on:

- event-chain verification failure;
- database corruption;
- lost Coordinator lease;
- uncertain physical dispatch;
- session mismatch;
- input-desktop mismatch;
- unsupported secure desktop;
- helper authentication failure;
- repeated executor crashes;
- migration failure.

Safe mode must prevent new mutations while allowing diagnostics, export, and controlled recovery.

### Recovery policy

Never automatically retry an action when the executor result is unknown. A retry may duplicate:

- clicks;
- keypresses;
- text entry;
- launches;
- destructive commands.

Require reconciliation or user intervention.

### Secrets and sensitive data

The current repository has no credential or secret-management implementation. Until one is designed and approved:

- do not store credentials;
- do not log typed sensitive text;
- do not retain unrestricted screenshots;
- do not use clipboard contents as an implicit secret channel;
- do not claim browser or credential support.

### Supply-chain and release security

Before production distribution:

- pin or otherwise control dependency resolution;
- audit dependencies;
- protect the release branch;
- require CI;
- use signed release artifacts where required;
- publish checksums;
- document provenance;
- define update and rollback behavior.

The repository reports secret-scanning push protection, but that does not replace dependency, installer, or signing controls.

---

## Deployment and Operations

### Runtime layout

The final deployment must define locations for:

```text
application binaries
configuration
SQLite database
WAL/SHM files
logs
artifacts
backups
crash dumps
```

Do not place mutable database state inside a read-only installation directory.

### Per-user versus per-machine

This is unresolved and must be decided before packaging.

For desktop input, a per-user interactive process is generally easier to align with the user’s session and input desktop. A service running in Session 0 must not be assumed to control the interactive desktop.

If both service and per-user processes are used:

- define their authority separately;
- authenticate their IPC;
- define installation ACLs;
- define startup and shutdown ordering;
- define recovery behavior.

### Startup

Startup sequence:

```text
load configuration
→ validate configuration
→ open database
→ apply migrations
→ verify event chain
→ acquire Coordinator lease
→ inspect incomplete actions
→ enter safe mode or recovery as required
→ start IPC
→ start observation provider
→ expose ready state
```

Do not expose the application as ready before database and lease checks complete.

### Backups

Implement:

- scheduled local backups;
- backup integrity verification;
- retention;
- restore procedure;
- handling of WAL and SHM files;
- backup encryption if sensitive artifacts are included.

A hash chain detects tampering or loss but is not a backup system.

### Monitoring

Monitor:

- Coordinator heartbeat;
- executor heartbeat;
- IPC authentication failures;
- permit expiration;
- unknown-result count;
- verification failures;
- database size;
- event-chain verification;
- migration status;
- safe-mode entry;
- crash frequency;
- artifact storage usage.

### Release artifacts

For the Python core:

```text
wheel
source distribution
checksums
test report
coverage report
version metadata
```

For the Windows application:

```text
installer
signed binaries where required
native helper
release manifest
checksums
supported Windows versions
migration notes
rollback instructions
known limitations
```

### Versioning

Track independently:

```text
package version
protocol version
database schema version
helper version
capability revision
policy revision
UI version
```

Do not use one version field for all contracts.

---

## Gaps and Unknowns

### Blocking unknowns

1. The explicit task is `None`.
2. It is unknown whether the repository instruction should be treated as the actual requested objective.
3. No supported Windows version is specified.
4. No installer technology is selected.
5. No UI technology is selected.
6. No Python bundling strategy is selected.
7. No native-helper technology is selected.
8. No per-user/per-machine deployment decision exists.
9. No physical-input decision exists.
10. No application support matrix exists.
11. No threat model for other local processes/users exists.
12. No recovery policy for unknown mutations has been approved.
13. No screenshot or artifact retention policy exists.
14. No code-signing availability is documented.
15. No independently reproduced test run was performed during research.
16. No GitHub Actions execution was independently inspected.
17. No installer or Windows-native implementation exists.
18. No dependency lock file exists.

### Repository facts that must not be assumed

- The typed actions are executable.
- The current permit system is restart-safe.
- The current event journal alone prevents replay.
- Portable CI proves Windows behavior.
- Historical checklist results are current.
- `0.2.0` artifacts are authoritative.
- Electron is required.
- Windows UI Automation is implemented.
- Any installer is available.
- The application is production-ready.

### Explicit stop conditions

Stop implementation and request clarification if:

- the intended task remains `None`;
- requirements conflict with the safety model;
- physical input is requested without a session/desktop identity design;
- unattended execution is requested without a reviewed threat model;
- installer signing is required but signing ownership is unavailable;
- the target applications do not expose testable postconditions;
- the team cannot provide an interactive Windows test environment.

---

## Builder Handoff

### Immediate action

The builder must first obtain explicit scope approval. The current repository evidence does not authorize a Windows application implementation because the task is `None`.

If Windows delivery is approved, implement the following first:

1. Resolve version inconsistency.
2. Harden protocol and digest contracts.
3. Make the event store transaction-safe and private.
4. Add schema migrations.
5. Persist runs, actions, permits, leases, and idempotency.
6. Make permit consumption atomic and restart-safe.
7. Add recovery and safe mode.
8. Define and test the executor protocol.
9. Build a fake executor.
10. Implement Windows observation identity.
11. Add Windows execution only for explicitly approved capabilities.
12. Add independent verification.
13. Add authenticated IPC.
14. Add UI.
15. Package, sign, and test the installer.

### Required builder reporting

For every implementation phase, report:

```text
files changed
database/schema changes
new dependencies and exact versions
commands run
tests run
test results
Windows environment details
known failures
security implications
remaining gaps
```

Do not report “tested and verified” unless the relevant commands and Windows acceptance tests were actually executed.

### Definition of honest current status

Until the above work is completed and verified, the product status must remain:

> Compuse is a portable safety-first coordination core. It is not yet a Windows computer-use application, executor, desktop UI, installer, or signed release.