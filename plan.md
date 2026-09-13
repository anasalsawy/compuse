# Implementation Research Report: `anasalsawy/compuse`

## 1. Task interpretation and exact requirements

### Task status

The supplied task is explicitly:

> **None**

Therefore, there is no feature request, bug report, integration request, or acceptance criterion to implement.

### Verified interpretation

The repository itself is the only available implementation context. The appropriate deliverable is therefore an implementation-readiness audit:

- establish the current repository baseline;
- identify what is already implemented;
- distinguish implementation from documented future work;
- identify the repository’s explicit boundaries;
- determine what would need to be built if the intended next step is to advance the project;
- identify testing, security, deployment, and integration constraints;
- avoid treating the existing prototype as a desktop automation product.

### Important conclusion

No code change can be specified as mandatory because no requested change exists.

The repository does, however, document a clear future direction: a safety-first coordination core that may eventually support Windows observation, controlled execution, postcondition verification, and recovery. Those capabilities are **not currently implemented** and should not be inferred as part of the current task.

---

## 2. Existing repository state and relevant file paths

### Repository metadata

Verified from GitHub:

- Repository: `anasalsawy/compuse`
- Visibility: public
- Default branch: `main`
- Current repository language: Python
- Repository created: 2026-09-12
- Latest observed commit: `cfd5bb157e24da4c720a6409784ecb62f8541b94`
- Latest commit message: `fix: harden event journal concurrency and packaging checks`
- Only listed branch: `main`
- `main` is not protected
- Open issues: 0
- Repository is not archived
- GitHub Pages: disabled
- Dependabot security updates: disabled
- Secret scanning: enabled
- Secret-scanning push protection: enabled

The latest commit is unsigned according to the GitHub metadata returned by the repository API. That is not itself a code defect, but it is relevant if signed commits are required for a production security or compliance workflow.

### Repository tree

The current tree contains:

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

### README-described product boundary

The README describes Compuse as:

- a safety-first;
- local-first;
- coordination core;
- intended for future computer-use systems;
- currently a portable authorization and audit prototype.

The README says the current release:

- validates typed actions;
- binds actions to observations;
- issues one-use permits;
- records tamper-evident events.

The README explicitly says it is **not** a Windows automation product. It does not:

- launch applications;
- control input;
- implement UI Automation;
- claim that an authorized action succeeded.

The README also states that the repository currently does not provide:

- a native Windows helper;
- UI Automation;
- Notepad workflow support;
- process/window/session identity checks;
- physical input;
- durable run/action/permit state;
- restart recovery;
- leases;
- idempotency;
- executor dispatch;
- postcondition verification;
- unknown-result reconciliation.

It also excludes:

- course scheduling;
- course import;
- scheduling conflicts;
- calendar export.

### `pyproject.toml`

Verified configuration:

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

Verified implications:

- Python 3.11 or newer is required.
- Runtime dependency is Pydantic 2.x.
- Test dependencies are optional extras.
- Hatchling is the build backend.
- The package is built from `compuse`.
- Pytest is configured through `pyproject.toml`.
- Coverage is not configured here; it is enforced in CI.

The Python Packaging User Guide confirms that using `[build-system]` and `[project]` in `pyproject.toml` is the standard current packaging approach. This repository follows that model.

### `compuse/protocol/models.py`

The protocol layer contains strict Pydantic models.

#### Strict base model

The repository defines a base model equivalent to:

```python
class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
```

This means:

- unknown fields are rejected;
- Pydantic coercion is disabled through strict mode;
- models form a deliberately narrow protocol boundary.

Pydantic’s official documentation confirms that strict mode prevents ordinary type coercion and that type annotations and constraints define validation and serialization behavior.

#### Origins

The protocol defines:

```text
USER_INTENT
SYSTEM_POLICY
STRATEGIST_INSTRUCTION
EXECUTOR_INSTRUCTION
ENVIRONMENT_CONTENT
PROVIDER_OUTPUT
```

The coordinator rejects proposals originating from:

- `ENVIRONMENT_CONTENT`
- `PROVIDER_OUTPUT`

This is an important prompt-injection and authority-boundary control: content observed from the environment or returned by a provider cannot independently authorize a mutating action.

#### Action kinds

The current action enum includes:

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

Implemented action models include:

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

Actions are represented as a discriminated union using the `kind` field.

The model constraints include:

- bounded wait duration;
- bounded coordinates;
- bounded text length;
- bounded key-combination length;
- required nonempty identifiers;
- bounded target and window identifiers.

#### Observation model

The observation model includes:

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

The `captured_at` validator:

- requires a timezone-aware timestamp;
- normalizes the timestamp to UTC.

Observations therefore provide the data needed for stale-state and coordinate-space checks, although the repository does not yet acquire observations from Windows.

#### Action proposal model

The proposal binds an action to:

- action ID;
- run ID;
- action origin;
- observation revision;
- coordinate-space ID;
- policy revision;
- tool;
- optional capability hash;
- optional launch/browser/window/process/session identity;
- optional confirmation ID.

#### Permit model

Permits include:

- UUID permit ID;
- run ID;
- action ID;
- deterministic action hash;
- observation revision;
- coordinate-space ID;
- policy revision;
- expiration timestamp;
- consumed flag;
- optional capability and identity bindings.

#### Hashing

The repository exposes:

```python
def digest_action(action: Action) -> str:
    ...
```

It canonicalizes the action using JSON with sorted keys and compact separators, then calculates SHA-256.

This creates a stable binding between the proposed action and the permit.

### `compuse/coordinator/core.py`

The coordinator is the authorization boundary.

Relevant public methods:

```python
Coordinator(
    store=None,
    policy_revision="policy-1",
)
```

```python
Coordinator.issue(
    proposal: ActionProposal,
    observation: Observation,
    ttl: float = 30,
) -> Permit
```

```python
Coordinator.consume(
    permit_id,
    proposal: ActionProposal,
    observation: Observation,
)
```

```python
Coordinator.release(
    permit_id,
)
```

```python
Coordinator.cleanup()
```

#### `issue()` behavior

The method rejects:

- TTLs that are not greater than zero;
- TTLs greater than 300 seconds;
- untrusted origins;
- mismatched run IDs;
- stale observation revisions;
- mismatched coordinate spaces;
- stale policy revisions.

It creates a one-use permit with a default 30-second lifetime.

It records a `permit_issued` event.

#### `consume()` behavior

The method rejects:

- concurrent mutation attempts;
- unavailable permits;
- expired permits;
- already consumed permits;
- mismatched proposal identity;
- untrusted origins;
- policy or coordinate-space mismatches;
- stale observations;
- action-hash mismatches.

It records a `permit_consumed` event and returns the validated action.

The method does **not**:

- dispatch mouse or keyboard input;
- launch a process;
- inspect a real desktop;
- verify a postcondition;
- reconcile an unknown executor result.

That separation is deliberate and must be preserved if execution is added later.

#### Concurrency

The coordinator uses:

```python
threading.RLock
```

The in-process `_active_permit` field prevents multiple mutation operations from being active within one coordinator instance.

This does not constitute durable multi-process coordination. The README and capability documentation correctly identify durable state, leases, restart recovery, and executor dispatch as future work.

### `compuse/coordinator/states.py`

The repository defines two explicit state machines.

#### Run states

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

#### Action states

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

The module provides:

```python
can_transition(current, target) -> bool
```

and:

```python
transition(current, target)
```

Invalid transitions raise `ValueError`.

The state definitions are fail-closed: terminal states have no outgoing transitions unless explicitly represented through another state.

### `compuse/storage/events.py`

The event store is a SQLite-backed, hash-chained journal.

Public API:

```python
EventStore(path=":memory:")
```

```python
append(
    run_id: str,
    event_type: str,
    payload: Any,
    timestamp: str,
) -> int
```

```python
verify(run_id: str) -> bool
```

```python
assert_integrity(run_id: str) -> None
```

```python
events(run_id: str) -> list[sqlite3.Row]
```

```python
close() -> None
```

#### Storage properties

The journal:

- uses SQLite;
- creates the events table automatically;
- enables foreign keys;
- enables a 10-second busy timeout;
- enables `synchronous=FULL`;
- enables WAL mode for file-backed stores;
- serializes operations per instance with `RLock`;
- uses `BEGIN IMMEDIATE`;
- assigns per-run sequence numbers;
- stores previous event hashes;
- stores current event hashes;
- computes SHA-256 over the canonical event components;
- detects missing, reordered, modified, or invalid events.

The table schema is effectively:

```sql
CREATE TABLE IF NOT EXISTS events (
    run_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    type TEXT NOT NULL,
    payload TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    previous_event_hash TEXT NOT NULL,
    event_hash TEXT NOT NULL,
    PRIMARY KEY (run_id, seq),
    UNIQUE (event_hash)
);
```

The latest repository history shows two commits specifically hardening event-journal transactions, concurrency, and packaging checks. That indicates storage integrity is an active design concern.

### Tests

The repository contains:

- `tests/test_core.py`
- `tests/test_states.py`
- `tests/test_storage.py`

The workflow runs:

```powershell
pip install -e '.[test]'
pytest --cov=compuse --cov-report=term-missing --cov-fail-under=80
```

The GitHub Actions matrix covers:

- Python 3.11
- Python 3.12
- Python 3.13

No test execution was performed by this investigation. The repository contents and CI configuration were inspected, but a local interpreter was not available through the supplied tools.

### CI workflow

`.github/workflows/test.yml`:

- runs on pushes and pull requests;
- grants `contents: read`;
- uses `ubuntu-latest`;
- checks out with `actions/checkout@v4`;
- installs Python with `actions/setup-python@v5`;
- enables pip caching;
- installs the package with test extras;
- runs pytest with coverage;
- enforces 80% minimum coverage.

This is a portable CI suite. It does not test Windows native integrations because those are not implemented.

---

## 3. Recommended architecture and implementation boundaries

Because the task is `None`, the recommendation is not to implement a feature blindly. The next builder should first choose one of the documented future workstreams.

### Recommended architectural layers

#### Layer 1: Protocol and validation

Existing location:

```text
compuse/protocol/
```

Responsibilities:

- typed actions;
- observations;
- proposals;
- permits;
- identity and capability bindings;
- canonical hashing;
- schema validation.

This layer should remain free of:

- Windows API calls;
- UI Automation calls;
- input injection;
- browser automation;
- provider/model SDKs;
- persistent workflow orchestration.

#### Layer 2: Coordination and lifecycle

Existing location:

```text
compuse/coordinator/
```

Responsibilities:

- policy checks;
- stale-state checks;
- permit issuance and consumption;
- lifecycle transitions;
- run/action ownership;
- cancellation;
- recovery decisions.

The coordinator should remain the only component allowed to authorize mutation.

#### Layer 3: Durable state and audit

Existing location:

```text
compuse/storage/
```

Responsibilities:

- durable run/action/permit records;
- leases;
- event journal;
- integrity verification;
- recovery after process restart;
- idempotency records.

The current event journal is not sufficient by itself for durable permit state. A future implementation should add explicit durable tables rather than relying only on the in-memory `_permits` dictionary.

#### Layer 4: Observation adapters

Recommended new area:

```text
compuse/platform/
  windows/
    observation.py
    identity.py
    coordinates.py
```

Responsibilities:

- capture foreground window;
- capture process ID;
- capture session ID;
- capture input desktop;
- identify coordinate space;
- capture screenshot metadata;
- produce a normalized `Observation`.

This layer should not authorize actions or execute them.

#### Layer 5: Executor adapter

Recommended new area:

```text
compuse/executor/
  interface.py
  result.py
  portable.py
  windows.py
```

Possible interface:

```python
class Executor(Protocol):
    def dispatch(
        self,
        *,
        permit: Permit,
        action: Action,
        observation: Observation,
    ) -> ExecutorResult:
        ...
```

The executor must:

- require a valid consumed permit;
- check identity and coordinate bindings immediately before dispatch;
- return explicit results;
- distinguish confirmed success, confirmed failure, and unknown outcomes;
- never claim success merely because input was sent.

#### Layer 6: Verification

Recommended new area:

```text
compuse/verification/
  interface.py
  postconditions.py
```

Possible interface:

```python
class Verifier(Protocol):
    def verify(
        self,
        *,
        action: Action,
        before: Observation,
        after: Observation,
    ) -> VerificationResult:
        ...
```

The verifier must independently observe the target state after dispatch.

#### Layer 7: Workflow integration

Only after the lower layers are implemented should the project add:

- a Windows helper;
- UI Automation;
- a Notepad vertical slice;
- browser integration;
- model/provider integration;
- installer or service packaging.

These should be adapters around the coordination core, not direct calls from a model or UI.

### Recommended initial future milestone

If the intent is to advance the repository, the most defensible next milestone is:

> Implement a Windows observation and verification vertical slice without unattended mutation.

That milestone should begin with:

1. Windows identity observation;
2. a controlled read-only target;
3. explicit observation normalization;
4. durable state modeling;
5. testable fake executor/verifier interfaces;
6. no physical input until identity and postcondition checks are proven.

The repository’s own documentation says that the current portable suite does not prove Windows behavior, so this would be a meaningful but bounded next step.

---

## 4. Required APIs, libraries, SDKs, tools, versions, and environment variables

### Verified current dependencies

Runtime:

```text
Python >= 3.11
pydantic >= 2.7, < 3
```

Build:

```text
hatchling >= 1.25
```

Testing:

```text
pytest >= 8
pytest-cov >= 5
```

CI actions:

```text
actions/checkout@v4
actions/setup-python@v5
```

### No external service integration exists

There is currently no verified integration with:

- OpenAI;
- Anthropic;
- browser providers;
- Microsoft APIs;
- Windows UI Automation;
- Electron;
- cloud storage;
- external databases;
- authentication providers;
- queues;
- service managers.

Therefore:

- no API keys are currently required;
- no service endpoints are configured;
- no runtime environment variables are documented as required;
- no SDK version can be specified for an absent integration.

### Recommended additions for Windows implementation

These are recommendations, not current repository facts.

#### Windows identity and observation

A future Windows adapter may need documented Win32 APIs such as:

- foreground-window lookup;
- window process-ID lookup;
- session-ID lookup;
- desktop/input-desktop inspection;
- process and window identity checks;
- screen and coordinate-space queries.

The implementation should choose either:

- a small native helper, likely in C/C++ or Rust; or
- a carefully bounded Python Windows API layer.

The repository explicitly anticipates a native Windows helper. The final choice must be made before implementation because the current package has no Windows-specific dependency set.

#### UI Automation

If UI Automation is added, the project must define:

- supported control types;
- locator policy;
- identity and stale-element behavior;
- whether UIA actions are considered mutation;
- postcondition rules;
- fallback behavior when an element disappears.

No UI Automation library is currently present.

#### Durable database

SQLite is already used and is an appropriate initial database for a local-first prototype.

Recommended future tables:

```sql
runs
actions
permits
observations
leases
executor_results
verifications
events
```

Example conceptual fields:

```sql
runs(
    run_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    policy_revision TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

actions(
    action_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    state TEXT NOT NULL,
    action_json TEXT NOT NULL,
    action_hash TEXT NOT NULL,
    observation_revision INTEGER NOT NULL,
    coordinate_space_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);

permits(
    permit_id TEXT PRIMARY KEY,
    action_id TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    consumed_at TEXT,
    revoked_at TEXT,
    state TEXT NOT NULL
);
```

These schemas are recommendations and are not present in the current repository.

### Environment variables

#### Verified

No environment variables are currently documented or required by the inspected files.

#### Recommended future variables

Only if deployment or external integrations are added:

```text
COMPUSE_DATA_DIR
COMPUSE_LOG_LEVEL
COMPUSE_POLICY_REVISION
COMPUSE_WINDOWS_HELPER_PATH
COMPUSE_EXECUTOR_TIMEOUT
```

If a model/provider is later integrated, provider-specific credentials must be injected through the deployment secret manager and never committed to the repository.

---

## 5. Concrete code patterns, function signatures, schemas, commands, and integration details

### Current installation and test commands

The README specifies:

```powershell
python -m pip install -e ".[test]"
python -m pytest -ra
```

Coverage:

```powershell
python -m pip install coverage
pytest --cov=compuse --cov-report=term-missing
```

CI adds:

```text
--cov-fail-under=80
```

### Current protocol usage pattern

Conceptually:

```python
from compuse.coordinator import Coordinator
from compuse.protocol import ActionProposal, Observation

coordinator = Coordinator(policy_revision="policy-1")

permit = coordinator.issue(
    proposal=proposal,
    observation=observation,
    ttl=30,
)

action = coordinator.consume(
    permit.permit_id,
    proposal,
    observation,
)
```

The returned `action` is authorized data only. It is not executed.

A future executor should be called only after `consume()` returns successfully:

```python
action = coordinator.consume(
    permit.permit_id,
    proposal,
    observation,
)

try:
    result = executor.dispatch(
        permit=permit,
        action=action,
        observation=observation,
    )
finally:
    coordinator.release(permit.permit_id)
```

That pattern is illustrative. The repository currently has no executor interface or implementation.

### Recommended executor result schema

A future result should be explicit rather than Boolean-only:

```python
class ExecutorOutcome(StrEnum):
    DISPATCHED = "DISPATCHED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
```

```python
class ExecutorResult(StrictModel):
    action_id: str
    permit_id: UUID
    outcome: ExecutorOutcome
    started_at: datetime
    finished_at: datetime
    helper_version: str
    capability_hash: str
    error_code: str | None = None
    error_message: str | None = None
    correlation_id: str
```

The `UNKNOWN` outcome is essential for crashes, timeouts, transport failures, or uncertain input delivery.

### Recommended verification result schema

```python
class VerificationOutcome(StrEnum):
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
```

```python
class VerificationResult(StrictModel):
    action_id: str
    outcome: VerificationOutcome
    observed_revision: int
    observed_at: datetime
    reason: str | None = None
```

### Recommended observation adapter interface

```python
class Observer(Protocol):
    def capture(self, *, run_id: str) -> Observation:
        ...
```

The observer should normalize all platform-specific data into the existing `Observation` model.

### Recommended durable lease interface

```python
class LeaseStore(Protocol):
    def acquire(
        self,
        *,
        run_id: str,
        owner_id: str,
        ttl_seconds: int,
    ) -> Lease:
        ...

    def renew(
        self,
        *,
        lease_id: str,
        owner_id: str,
    ) -> Lease:
        ...

    def release(
        self,
        *,
        lease_id: str,
        owner_id: str,
    ) -> None:
        ...
```

A lease must be durable and checked by the coordinator, not only represented by an in-memory lock.

### Recommended idempotency key

For action dispatch:

```text
idempotency_key = run_id + ":" + action_id + ":" + permit_id
```

This should be recorded before dispatch and associated with an executor correlation ID.

The exact format is a recommendation, not a current repository behavior.

### Recommended command sequence for builders

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
python -m pytest -ra
python -m pytest --cov=compuse --cov-report=term-missing --cov-fail-under=80
python -m build
```

`build` is not currently declared as a test dependency, so it would need to be installed separately if used:

```powershell
python -m pip install build
```

The final command is recommended validation, not an existing repository command.

---

## 6. Testing, validation, error handling, security, and deployment requirements

### Existing testing requirements

CI requires:

- Python 3.11, 3.12, and 3.13;
- editable package installation;
- all pytest tests;
- at least 80% coverage.

Existing tests are organized around:

- coordinator behavior;
- lifecycle states;
- event storage.

### Required tests for any future changes

#### Protocol tests

Add tests for:

- unknown fields;
- strict type failures;
- invalid discriminator values;
- out-of-range coordinates;
- excessive text;
- excessive key-combination length;
- naïve timestamps;
- UTC normalization;
- deterministic action hashes;
- serialization round trips.

#### Coordinator tests

Add tests for:

- stale proposal rejection;
- stale observation rejection;
- coordinate-space mismatch;
- policy revision mismatch;
- untrusted origin rejection;
- expired permits;
- permit reuse;
- incorrect action hash;
- concurrent consumption;
- release ownership;
- cleanup behavior.

#### Storage tests

Add tests for:

- sequence ordering;
- independent chains per run;
- tampering detection;
- missing event detection;
- rollback after append failure;
- concurrent writers;
- file-backed WAL behavior;
- restart and reopen behavior;
- corrupted database handling.

#### Durable state tests

If persistence is added:

- restart recovery;
- permits not becoming reusable after process restart;
- expired permit cleanup;
- lease expiration;
- lease renewal;
- ownership checks;
- duplicate dispatch suppression;
- event/state consistency.

#### Windows tests

Windows-specific tests must not be replaced by portable unit tests.

At minimum:

- foreground-window identity;
- process identity;
- session identity;
- input-desktop identity;
- coordinate-space stability;
- helper version compatibility;
- helper timeout;
- helper crash;
- unknown dispatch result;
- postcondition verification;
- secure desktop and lock-screen behavior.

The repository’s documentation explicitly warns that the portable suite does not prove Windows behavior.

### Error handling principles

The implementation should remain fail-closed:

- invalid protocol data must be rejected;
- stale observations must prevent mutation;
- mismatched identity must prevent mutation;
- expired permits must not be accepted;
- consumed permits must not be reusable;
- unknown executor results must not be treated as failures or successes automatically;
- process restart must not silently recreate authority;
- event integrity failures must stop trust in the affected run;
- executor timeouts must transition to `UNKNOWN` or recovery;
- postcondition failures must be recorded as verification failures.

### Security requirements

#### Authority separation

The current origin model is a good foundation. Future components must preserve the distinction between:

- user intent;
- policy;
- planner/provider output;
- environment content.

Environment content and provider output must remain data, not authorization.

#### Sensitive data

The current `TypeText` model permits arbitrary text up to 10,000 characters. A future desktop executor must decide whether text may contain:

- passwords;
- access tokens;
- payment information;
- personal data.

Recommended controls:

- avoid logging raw typed text;
- redact or hash sensitive payloads in event logs;
- make credential entry a separately gated capability;
- require explicit user confirmation for sensitive actions;
- never place credentials in action hashes or audit logs in plaintext.

#### Native helper trust

A Windows helper must have:

- authenticated request/response correlation;
- version reporting;
- capability reporting;
- explicit cancellation;
- bounded timeouts;
- crash detection;
- secure installation;
- integrity verification;
- least privilege;
- no arbitrary command execution interface.

#### Unattended execution

The repository is not safe to connect directly to unattended desktop mutation. Before any such deployment, the project needs:

- target identity checks;
- pre-dispatch observation;
- post-dispatch observation;
- explicit verification;
- unknown-result reconciliation;
- durable permits;
- leases;
- recovery behavior;
- audit integrity checks.

### Deployment requirements

#### Current repository

No deployment target is currently implemented.

The project is a Python library/prototype rather than:

- a web service;
- a desktop application;
- a Windows service;
- an installer;
- a CLI product;
- a hosted API.

#### Recommended future deployment stages

1. **Portable library release**
   - build wheel and source distribution;
   - validate metadata;
   - publish only after tests and security review.

2. **Windows development helper**
   - developer-only;
   - explicit local invocation;
   - no unattended operation;
   - Windows-specific CI or manual validation.

3. **Controlled vertical slice**
   - signed or integrity-checked helper;
   - local durable database;
   - explicit user confirmation;
   - test target application;
   - kill switch and recovery.

4. **Production deployment**
   - only after executor, verification, recovery, and security boundaries are implemented;
   - require operational logging and incident procedures;
   - define upgrade compatibility for protocol and helper versions.

No actual deployment configuration is present in the repository.

---

## 7. Risks, compatibility concerns, and likely failure points

### Task ambiguity

The largest issue is that the task is `None`. Any implementation effort beyond an audit would be assumption-driven.

### Repository maturity

The repository was created very recently and has a small, focused codebase. It should be treated as an early prototype, not as a production automation framework.

### In-memory permit state

`Coordinator` stores permits in an in-memory dictionary. Consequences:

- permits disappear on restart;
- permits cannot be coordinated across processes;
- a crash can leave action state ambiguous;
- durable replay/recovery is not implemented.

### In-process mutation lock

The `_active_permit` lock is local to one coordinator instance. It does not protect:

- multiple processes;
- multiple machines;
- multiple coordinator instances sharing a database;
- executor processes.

### Event journal scope

The event journal is tamper-evident against ordinary modifications, but it is not a complete security system.

Potential concerns:

- the database file itself is not protected against deletion or replacement;
- there is no external trust anchor;
- no key-based signatures are used;
- there is no retention or archival policy;
- event payload privacy is not separately addressed;
- state records are not yet persisted alongside events.

### Time semantics

Permits use wall-clock UTC timestamps. Potential future concerns:

- system clock changes;
- suspend/resume;
- clock skew between helper and coordinator;
- expiry evaluation during long-running operations.

A future design should consider monotonic timing for local TTL enforcement while retaining UTC timestamps for audit.

### Action hash limitations

The action hash protects the action payload but does not alone bind:

- the real target window;
- the physical desktop;
- the current process identity;
- helper capability version;
- current screen layout;
- current UI element identity.

Those bindings must be captured and checked before dispatch.

### Coordinate-space risk

Mouse actions use integer coordinates and an observation coordinate-space ID, but no current implementation obtains or verifies actual screen geometry. Risks include:

- display changes;
- DPI scaling;
- monitor reordering;
- remote desktop sessions;
- virtual desktops;
- secure desktops;
- window movement;
- stale screenshots.

### `ApplicationLaunch` risk

The protocol includes application launch actions, but there is no launch policy enforcement or Windows implementation. A future implementation must not treat `target_id` as an arbitrary executable path or shell command.

### No postcondition verification

The current coordinator can authorize and consume an action but cannot establish that it succeeded. This is especially dangerous for:

- clicks;
- text entry;
- application launch;
- window focus;
- drag-and-drop;
- key combinations.

### Unknown outcomes

The state machine includes `UNKNOWN` and reconciliation states, but there is no executor or reconciliation implementation. A timeout or crash must not be represented as ordinary failure without checking the target state.

### CI platform gap

CI runs on Ubuntu. The configured matrix tests Python compatibility, not Windows behavior.

### Unpinned dependency ranges

Dependencies are bounded but not fully locked:

- `pydantic>=2.7,<3`
- `pytest>=8`
- `pytest-cov>=5`
- `hatchling>=1.25`

This is normal for a library, but release reproducibility would benefit from tested lock files or a documented dependency update policy.

### Unprotected main branch

The `main` branch is not protected. For a security-sensitive project, recommended controls include:

- required CI checks;
- pull-request review;
- signed commits if required;
- restricted direct pushes;
- dependency review;
- release tagging policy.

### Unsigned commits

The GitHub metadata marks observed commits as unsigned. If provenance matters, commit signing and verified-release artifacts should be considered.

### Missing security documentation retrieval

The direct GitHub raw-content fetch for `docs/security.md` returned an HTTP error through the available URL-reading path.

Therefore:

> **NO DATA: `docs/security.md` content was not retrievable through the attempted raw-file fetch.**

The README references the document, but the complete content was not independently verified in this investigation.

### Missing test-matrix retrieval

The direct raw-content fetch for `docs/test-matrix.md` also returned an HTTP error.

Therefore:

> **NO DATA: `docs/test-matrix.md` content was not retrievable through the attempted raw-file fetch.**

The repository tree verifies that the file exists, but its complete contents were not independently read.

### No local test execution

No local shell or test runner was available through the supplied tools.

Therefore:

> **NO DATA: actual pytest results were not obtained.**

The report describes configured tests, not successful execution.

---

## 8. Missing information, assumptions, unresolved questions, and unknowns

### Missing task requirements

There is no feature description, issue number, acceptance criterion, target user, deadline, or deployment requirement.

This prevents determining:

- which code must change;
- whether the expected work is bug fixing, feature development, documentation, or deployment;
- whether Windows support is desired now;
- whether external model/provider integration is desired;
- whether the task is intentionally a baseline audit.

### Assumptions used in this report

1. The requested activity is a repository investigation rather than implementation.
2. `main` is the relevant baseline.
3. The latest observed commit is the intended current state.
4. Existing documentation describes the intended product boundaries.
5. Future recommendations should preserve the current safety-first separation between authorization, execution, and verification.

### Unresolved product questions

Before implementation begins, the owner should answer:

1. What is the next concrete capability?
2. Is the intended product a library, service, desktop agent, or all three?
3. Is Windows support required immediately?
4. Is physical input injection in scope?
5. Is UI Automation in scope?
6. Is a native helper acceptable?
7. Is model/provider integration in scope?
8. What actions require user confirmation?
9. What data may be stored in the event journal?
10. What is the threat model?
11. Must permits survive restarts?
12. Must multiple processes coordinate?
13. What is the supported Windows version range?
14. Is an installer required?
15. What release artifact and signing policy are required?
16. What constitutes verified success for each action kind?
17. How should unknown outcomes be reconciled?
18. Is course scheduling genuinely excluded permanently, or merely excluded from this milestone?

### Unknown technical details

The following were not established:

- actual test pass/fail status;
- complete `plan.md` contents;
- complete `docs/final-execution-checklist.md` contents;
- complete `docs/security.md` contents;
- complete `docs/test-matrix.md` contents;
- Windows API implementation choice;
- native helper language;
- persistence schema beyond the event journal;
- release hosting;
- package publication workflow;
- signing infrastructure;
- operational monitoring.

---

## 9. Practical sequence of implementation work for builders

Because no task was supplied, the sequence below is a recommended roadmap rather than a direct implementation plan.

### Phase 0: Clarify scope

Create a concrete issue containing:

- feature name;
- user story;
- supported platform;
- security boundary;
- acceptance criteria;
- expected files;
- test requirements;
- deployment target.

Do not begin Windows input automation until this is defined.

### Phase 1: Establish and verify the baseline

Run locally:

```powershell
python -m pip install -e ".[test]"
python -m pytest -ra
python -m pytest --cov=compuse --cov-report=term-missing --cov-fail-under=80
```

Also validate packaging:

```powershell
python -m pip install build
python -m build
```

Record:

- Python version;
- dependency versions;
- test count;
- coverage;
- wheel contents;
- source distribution contents.

### Phase 2: Define the next boundary

Choose one:

- durable coordination;
- Windows observation;
- executor protocol;
- postcondition verification;
- Notepad vertical slice;
- native helper;
- installer;
- model/provider integration.

Do not combine all of these in one change.

### Phase 3: Add durable state before real execution

If permits or actions must survive restarts:

- add durable run/action/permit records;
- add leases;
- add state-transition persistence;
- record idempotency keys;
- define crash recovery;
- test reopening the database;
- preserve event-chain integrity.

The in-memory coordinator should not be extended directly into production execution without this phase.

### Phase 4: Implement observation

Add an observer that produces the existing `Observation` model.

Validate:

- process identity;
- window identity;
- session identity;
- input desktop;
- coordinate space;
- capture timestamp;
- monotonic revision.

Add Windows-specific tests and document unsupported environments.

### Phase 5: Implement a fake executor first

Before dispatching real input, implement a deterministic fake executor:

```python
class FakeExecutor:
    def dispatch(...):
        ...
```

Use it to test:

- permit ownership;
- lifecycle transitions;
- result persistence;
- timeout behavior;
- unknown outcomes;
- cancellation;
- verification.

### Phase 6: Implement verification

Define postconditions for each supported action.

Examples:

- `window.focus`: expected foreground-window identity;
- `application.launch`: expected process/window identity;
- `type`: expected UI value or controlled target-state change;
- `click`: expected target-state transition;
- `screenshot`: expected observation event, not mutation success.

Never mark an action `VERIFIED` solely because dispatch returned.

### Phase 7: Implement the narrowest Windows vertical slice

Use a controlled test application, not arbitrary desktop automation.

Suggested scope:

- observe one known window;
- focus it only after identity validation;
- perform one narrowly defined action;
- capture an after-observation;
- verify one explicit postcondition;
- record all state transitions and outcomes.

Keep it opt-in and user-confirmed.

### Phase 8: Harden the helper boundary

Add:

- helper version;
- capability hash;
- request correlation ID;
- timeout;
- cancellation;
- crash handling;
- authenticated local IPC;
- explicit `UNKNOWN` results;
- integrity checks;
- least privilege.

### Phase 9: Expand tests and CI

Add:

- Windows CI or documented manual test jobs;
- integration tests with a controlled target;
- restart recovery tests;
- tamper tests;
- concurrency tests;
- security regression tests;
- dependency and packaging checks.

Require CI status before merges. Consider protecting `main`.

### Phase 10: Release and deployment

Only after the above:

- define versioning;
- build signed artifacts if needed;
- publish package metadata;
- package the helper;
- document installation;
- define rollback;
- define data-retention and incident procedures;
- publish a threat model and support matrix.

---

# Final assessment

There is no implementation request because the task is `None`.

The repository currently contains a coherent, safety-oriented Python authorization and audit prototype. The implemented boundary is limited to:

- strict typed protocol models;
- observation/action binding;
- one-use in-process permits;
- lifecycle transition tables;
- SQLite hash-chained event storage;
- portable tests and CI.

The repository does **not** currently contain:

- Windows automation;
- a native helper;
- UI Automation;
- physical input dispatch;
- durable coordinator state;
- restart recovery;
- leases;
- idempotency;
- postcondition verification;
- unknown-result reconciliation;
- deployment packaging.

The correct immediate action is therefore not to modify code, but to obtain a concrete task definition. If the intended next step is inferred from the repository roadmap, durable state and a controlled Windows observation/verification vertical slice should precede any real executor or unattended desktop mutation.

----------

# Compuse Implementation Plan

## Plan Status

**Task status:** No implementation task was supplied. The original task is explicitly `None`.

**Implementation consequence:** No feature, bug fix, integration, or acceptance criterion can be identified as mandatory. This plan therefore defines:

1. the verified repository baseline;
2. the actions required to clarify scope;
3. the guarded implementation roadmap for the repository’s documented future capabilities;
4. the boundaries that must not be crossed without an explicit task.

**Fact:** The current repository is a safety-first, local-first authorization and audit prototype.

**Recommendation:** Do not implement Windows input dispatch, UI Automation, model integration, or deployment packaging until the project owner supplies a concrete task and acceptance criteria.

---

# Quick Start

A builder should take these actions in order.

## 1. Confirm the task scope before changing code

Obtain a written task containing at least:

- the desired capability or defect;
- target platform;
- supported Python versions;
- whether Windows integration is required;
- whether physical input dispatch is in scope;
- whether UI Automation is in scope;
- required confirmation behavior;
- persistence and restart requirements;
- acceptance criteria;
- deployment target;
- required artifacts.

Do not infer a feature from the repository roadmap.

## 2. Establish the repository baseline

From the repository root, create a Python 3.11-or-newer environment and install the existing test dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
```

Run the configured test suite:

```powershell
python -m pytest -ra
```

Run the CI-equivalent coverage check:

```powershell
python -m pytest --cov=compuse --cov-report=term-missing --cov-fail-under=80
```

These commands are planned verification commands. No test execution was performed during research.

## 3. Validate packaging

Install the build frontend if necessary:

```powershell
python -m pip install build
python -m build
```

Record:

- Python version;
- installed dependency versions;
- test result;
- coverage percentage;
- generated wheel;
- generated source distribution;
- package contents.

## 4. Read the implementation boundary before selecting a workstream

Review:

```text
README.md
compuse/protocol/models.py
compuse/coordinator/core.py
compuse/coordinator/states.py
compuse/storage/events.py
docs/supported-capabilities.md
docs/windows-development.md
docs/final-execution-checklist.md
docs/security.md
docs/test-matrix.md
```

The complete contents of `docs/security.md` and `docs/test-matrix.md` were not independently retrieved during research and must be reviewed locally before relying on them.

## 5. Select exactly one initial workstream

Choose one of the following:

- durable coordination state;
- Windows observation;
- executor protocol;
- postcondition verification;
- controlled Windows vertical slice;
- native helper;
- installer or deployment packaging;
- model/provider integration.

Do not combine all future workstreams into one change.

## 6. Preserve the current safety boundary

Any future implementation must preserve these separations:

- protocol validation must not perform desktop operations;
- the coordinator must remain the authorization boundary;
- environment content and provider output must not independently authorize actions;
- executors must not be called before successful permit consumption;
- dispatch success must not automatically mean task success;
- unknown outcomes must remain distinguishable from confirmed failure;
- verification must observe the target state independently.

---

# Requirements

## Functional Requirements

### R1. Scope clarification is required

Before implementation begins, the project owner must define the requested behavior because the current task is `None`.

The task definition must identify:

- what the system should do;
- what it must not do;
- which action kinds are involved;
- whether behavior is portable or Windows-specific;
- what constitutes success;
- what constitutes failure;
- how uncertain outcomes are handled.

### R2. Preserve the existing protocol boundary

The protocol layer must continue to provide strict, typed models for:

- actions;
- observations;
- proposals;
- permits;
- origins;
- action hashing.

Unknown fields must remain rejected through the existing strict Pydantic model configuration.

### R3. Preserve authority restrictions

The coordinator must continue rejecting proposals originating from:

- `ENVIRONMENT_CONTENT`;
- `PROVIDER_OUTPUT`.

Observed environment content and provider output must remain data rather than authorization.

### R4. Preserve stale-state protections

Any implementation that issues or consumes permits must continue validating:

- run identity;
- observation revision;
- coordinate-space identity;
- policy revision;
- action identity;
- action hash;
- permit expiration;
- permit consumption state.

### R5. Preserve one-use permit behavior

A permit must not be reusable after consumption.

If permits become durable, the persisted representation must preserve the same one-use behavior across:

- process restarts;
- multiple coordinator instances;
- concurrent processes;
- crashes during dispatch.

### R6. Do not treat authorization as execution

`Coordinator.consume()` currently returns authorized action data. It does not execute the action.

Future code must not imply that successful permit consumption means:

- mouse input was sent;
- keyboard input was sent;
- a process was launched;
- a window was focused;
- a UI state changed;
- a postcondition was satisfied.

### R7. Add durable state before production execution

If the selected task requires process restart recovery, multi-process coordination, or real execution, add durable records for at least the relevant:

- runs;
- actions;
- permits;
- leases;
- executor results;
- verification results;
- idempotency records.

The existing event journal alone is not a replacement for durable operational state.

### R8. Require explicit executor outcomes

Any future executor must distinguish at least:

- confirmed dispatch or success;
- confirmed failure;
- unknown outcome.

A timeout, process crash, or transport failure must not be converted automatically into ordinary failure or success.

### R9. Require independent verification

Any action that mutates a desktop or application must define a postcondition and verify it using a subsequent observation.

An executor return value alone is insufficient to mark an action verified.

### R10. Keep Windows integration isolated

Windows APIs, UI Automation, input injection, process launch, and desktop observation must not be added directly to:

```text
compuse/protocol/
compuse/coordinator/
```

They must be isolated behind platform or executor adapters.

### R11. Maintain portable test coverage

Changes must continue to pass the configured Python matrix:

- Python 3.11;
- Python 3.12;
- Python 3.13.

The CI coverage threshold remains 80% unless a separately approved task changes it.

## Technical Requirements

- Python `>=3.11`.
- Runtime dependency: `pydantic>=2.7,<3`.
- Build backend: `hatchling>=1.25`.
- Test dependencies: `pytest>=8`, `pytest-cov>=5`.
- Package name: `compuse`.
- Package source directory: `compuse`.
- Test configuration is in `pyproject.toml`.
- CI must continue to use the existing test command unless the task explicitly changes it.
- New dependencies must be justified and added to `pyproject.toml` using the existing packaging pattern.
- New Windows-specific dependencies must not become mandatory for the portable core without an explicit compatibility decision.

## Operational Requirements

If future work introduces a runnable service, helper, or agent, the implementation must document:

- startup command;
- shutdown behavior;
- data directory;
- logging;
- timeout behavior;
- persistence;
- upgrade compatibility;
- rollback procedure;
- supported operating systems;
- required permissions;
- recovery from crashes.

No such service currently exists.

## Acceptance Requirements for the Current Task

Because no implementation task exists, there are no feature-specific acceptance criteria.

The minimum acceptable deliverable for the current state is:

- no unrequested code change;
- a verified or explicitly unverified repository baseline;
- a documented scope decision;
- preservation of the current authorization and audit boundaries;
- clear reporting of unresolved requirements.

---

# Current State

## Repository Metadata

Verified repository facts:

- Repository: `anasalsawy/compuse`
- Default branch: `main`
- Repository language: Python
- Repository is public.
- Repository is not archived.
- Only `main` was listed.
- Open issues: 0.
- GitHub Pages is disabled.
- Dependabot security updates are disabled.
- Secret scanning is enabled.
- Secret-scanning push protection is enabled.
- `main` is not protected.
- The latest observed commit is `cfd5bb157e24da4c720a6409784ecb62f8541b94`.
- The latest observed commit message is `fix: harden event journal concurrency and packaging checks`.
- The observed latest commit is unsigned according to GitHub metadata.

## Existing Repository Layout

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

## Implemented Capabilities

The repository currently implements:

- strict Pydantic protocol models;
- action discriminated unions;
- action origin validation;
- observations with revision and identity metadata;
- action proposals;
- one-use permits;
- deterministic SHA-256 action hashing;
- policy revision binding;
- coordinate-space binding;
- stale observation checks;
- permit expiration;
- permit consumption;
- explicit lifecycle state machines;
- a SQLite-backed hash-chained event journal;
- portable tests;
- GitHub Actions CI for Python 3.11, 3.12, and 3.13.

## Current Product Boundary

The README describes the project as a portable authorization and audit prototype, not as a desktop automation product.

The repository does not currently:

- launch applications;
- control mouse or keyboard input;
- implement Windows UI Automation;
- acquire observations from a real Windows desktop;
- verify that an authorized action succeeded;
- persist run, action, or permit state durably;
- recover state after restart;
- implement leases;
- implement idempotency;
- dispatch executor operations;
- reconcile unknown results;
- provide a native Windows helper;
- provide Notepad workflow support;
- provide browser automation;
- provide model/provider integrations;
- provide course scheduling or calendar features.

## Coordinator State

`Coordinator` currently uses an in-process `threading.RLock` and an in-memory permit collection.

The active permit guard only coordinates operations within one coordinator instance. It does not coordinate:

- multiple processes;
- multiple coordinator instances;
- multiple machines;
- executor processes;
- restart recovery.

This behavior must be preserved for the current prototype and replaced with durable coordination only as part of an explicitly scoped future task.

## Event Journal State

The event journal:

- uses SQLite;
- creates its schema automatically;
- enables foreign keys;
- uses a 10-second busy timeout;
- uses `synchronous=FULL`;
- enables WAL mode for file-backed stores;
- serializes operations per store instance;
- uses `BEGIN IMMEDIATE`;
- maintains per-run sequence numbers;
- stores previous and current event hashes;
- verifies chain integrity.

The journal is tamper-evident against ordinary modification, but it is not an external trust system. It does not currently provide:

- signed event chains;
- deletion protection;
- retention policy;
- archival;
- separate event confidentiality;
- durable coordinator state.

## Existing CI

`.github/workflows/test.yml`:

- runs on pushes and pull requests;
- grants `contents: read`;
- uses `ubuntu-latest`;
- uses `actions/checkout@v4`;
- uses `actions/setup-python@v5`;
- enables pip caching;
- installs `.[test]`;
- runs pytest with coverage;
- requires at least 80% coverage;
- tests Python 3.11, 3.12, and 3.13.

The workflow does not validate Windows behavior.

## What Must Be Preserved

Unless a specific task authorizes a change, preserve:

- strict model validation;
- rejection of unknown fields;
- origin restrictions;
- action hashing;
- observation revision checks;
- coordinate-space checks;
- policy revision checks;
- permit expiration;
- one-use permits;
- hash-chained event storage;
- explicit action and run state machines;
- the distinction between authorization, execution, and verification;
- the portable Python package structure;
- the current CI coverage requirement.

---

# Implementation Design

Because no concrete task exists, the architecture below is a gated design for future work rather than an instruction to implement all components immediately.

## Architectural Layers

### 1. Protocol and Validation

Existing location:

```text
compuse/protocol/
```

Responsibilities:

- validate action payloads;
- validate observations;
- validate proposals;
- validate permits;
- represent origins;
- calculate canonical action hashes;
- serialize and deserialize protocol data.

Must not contain:

- Win32 calls;
- UI Automation calls;
- input injection;
- process launching;
- provider SDK calls;
- workflow orchestration.

### 2. Coordination and Lifecycle

Existing location:

```text
compuse/coordinator/
```

Responsibilities:

- enforce policy revision;
- compare proposal and observation bindings;
- issue permits;
- consume permits;
- reject stale or invalid requests;
- manage run and action lifecycle;
- coordinate cancellation and recovery decisions.

The coordinator remains the only component that authorizes mutation.

### 3. Durable State and Audit

Existing location:

```text
compuse/storage/
```

Responsibilities for a future durable-state workstream:

- persist runs;
- persist actions;
- persist permits;
- persist leases;
- persist executor results;
- persist verification results;
- preserve event journal integrity;
- support restart recovery;
- support idempotency checks.

The event journal and operational state should not be conflated.

### 4. Observation Adapters

Recommended future location:

```text
compuse/platform/
  __init__.py
  windows/
    __init__.py
    observation.py
    identity.py
    coordinates.py
```

Responsibilities:

- capture foreground window;
- capture process identity;
- capture session identity;
- capture input desktop;
- identify coordinate space;
- capture timestamps;
- increment observation revisions;
- normalize platform data into the existing `Observation` model.

Observation adapters must not issue permits or execute actions.

### 5. Executor Adapter

Recommended future location:

```text
compuse/executor/
  __init__.py
  interface.py
  result.py
  fake.py
  windows.py
```

Responsibilities:

- accept only authorized actions;
- validate permit and identity bindings immediately before dispatch;
- issue a bounded dispatch request;
- return a structured result;
- distinguish confirmed, failed, and unknown outcomes;
- expose correlation information for recovery.

Suggested interface:

```python
class Executor(Protocol):
    def dispatch(
        self,
        *,
        permit: Permit,
        action: Action,
        observation: Observation,
    ) -> ExecutorResult:
        ...
```

This interface is a recommendation. It does not currently exist.

### 6. Verification

Recommended future location:

```text
compuse/verification/
  __init__.py
  interface.py
  result.py
  postconditions.py
```

Suggested interface:

```python
class Verifier(Protocol):
    def verify(
        self,
        *,
        action: Action,
        before: Observation,
        after: Observation,
    ) -> VerificationResult:
        ...
```

Verification must occur after dispatch and must use a fresh observation.

### 7. Workflow Integration

Only after durable state, observation, execution, and verification boundaries are defined should the project add:

- a Windows helper;
- UI Automation;
- a controlled Notepad vertical slice;
- browser integration;
- model/provider integration;
- installer or service packaging.

These components must call the coordination core through explicit interfaces rather than bypassing it.

## Recommended Data Flow

For a future controlled execution flow:

1. An authorized source produces an `ActionProposal`.
2. An observer captures an `Observation`.
3. The coordinator validates the proposal and observation.
4. The coordinator issues a one-use `Permit`.
5. The permit issuance is recorded in durable state and the event journal.
6. The coordinator consumes the permit.
7. The executor rechecks identity and capability bindings.
8. The executor returns a structured result.
9. The observer captures a fresh post-dispatch observation.
10. The verifier evaluates the postcondition.
11. The coordinator transitions the action to:
    - verified;
    - failed;
    - unknown;
    - reconciliation-required.
12. All state transitions and outcomes are journaled.

The current repository implements only the protocol, permit, coordination, and event-journal portions of this flow.

## State Design

Existing run states:

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

Existing action states:

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

Future code must use the existing transition functions rather than assigning states arbitrarily.

## Recommended Result Models

These models are proposed for a future executor implementation and are not current repository APIs.

```python
class ExecutorOutcome(StrEnum):
    DISPATCHED = "DISPATCHED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
```

```python
class ExecutorResult(StrictModel):
    action_id: str
    permit_id: UUID
    outcome: ExecutorOutcome
    started_at: datetime
    finished_at: datetime
    helper_version: str
    capability_hash: str
    error_code: str | None = None
    error_message: str | None = None
    correlation_id: str
```

```python
class VerificationOutcome(StrEnum):
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
```

```python
class VerificationResult(StrictModel):
    action_id: str
    outcome: VerificationOutcome
    observed_revision: int
    observed_at: datetime
    reason: str | None = None
```

## Recommended Observer Interface

```python
class Observer(Protocol):
    def capture(self, *, run_id: str) -> Observation:
        ...
```

The adapter must populate the existing observation fields:

- `run_id`;
- `revision`;
- `captured_at`;
- `coordinate_space_id`;
- `foreground_window`;
- `process_id`;
- `session_id`;
- `input_desktop`.

## Recommended Durable Lease Interface

```python
class LeaseStore(Protocol):
    def acquire(
        self,
        *,
        run_id: str,
        owner_id: str,
        ttl_seconds: int,
    ) -> Lease:
        ...

    def renew(
        self,
        *,
        lease_id: str,
        owner_id: str,
    ) -> Lease:
        ...

    def release(
        self,
        *,
        lease_id: str,
        owner_id: str,
    ) -> None:
        ...
```

The lease must be persisted and checked by the coordinator. An in-memory lock is insufficient for multi-process coordination.

## Recommended Persistence Entities

These are proposed entities, not current schema objects:

```text
runs
actions
permits
observations
leases
executor_results
verifications
events
```

Conceptual fields include:

```sql
runs(
    run_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    policy_revision TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

actions(
    action_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    state TEXT NOT NULL,
    action_json TEXT NOT NULL,
    action_hash TEXT NOT NULL,
    observation_revision INTEGER NOT NULL,
    coordinate_space_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);

permits(
    permit_id TEXT PRIMARY KEY,
    action_id TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    consumed_at TEXT,
    revoked_at TEXT,
    state TEXT NOT NULL
);
```

The final schema must be defined only after the specific durable-state requirements are approved.

## Integration Boundaries

### External services

No external services currently exist.

There is no verified integration with:

- OpenAI;
- Anthropic;
- Microsoft APIs;
- browser providers;
- cloud storage;
- queues;
- external databases;
- authentication providers.

### Windows

Windows support is not implemented. A future implementation must select one of:

- a native helper;
- a bounded Python Windows API layer;
- another explicitly approved adapter.

The language, IPC method, supported Windows versions, and dependency set are unresolved.

### Authentication

The current repository has no user authentication, service authentication, or external identity provider.

A future helper boundary must define request authentication and correlation before production use.

---

# File and Change Map

## Current Files to Preserve

### `pyproject.toml`

Preserve:

- Python requirement `>=3.11`;
- package name and version unless the task requires a release change;
- Pydantic dependency range;
- Hatchling build configuration;
- pytest configuration;
- 80% coverage enforcement remains in CI.

Modify only when a scoped task requires:

- a new dependency;
- a new optional extra;
- a version change;
- package inclusion changes;
- additional test configuration.

### `compuse/protocol/models.py`

Preserve:

- strict Pydantic model configuration;
- action discriminated union;
- origin definitions;
- action constraints;
- observation validation and UTC normalization;
- proposal bindings;
- permit fields;
- deterministic action hashing.

Potential future modifications must be narrowly scoped to approved protocol requirements.

### `compuse/coordinator/core.py`

Preserve:

- authorization responsibility;
- stale observation checks;
- policy checks;
- origin checks;
- one-use permit behavior;
- action-hash validation;
- explicit release and cleanup behavior.

If durable state is added, modify this file only through a deliberate persistence abstraction. Do not embed platform-specific execution here.

### `compuse/coordinator/states.py`

Preserve existing states and transition validation.

Add states only if a concrete workflow requires them and the transition semantics are documented and tested.

### `compuse/storage/events.py`

Preserve:

- SQLite usage;
- hash chaining;
- transaction boundaries;
- integrity verification;
- per-run sequencing;
- concurrency protections.

If durable operational state is added, either extend storage through separate modules or clearly separate state tables from the existing event journal.

### `tests/test_core.py`

Preserve existing coordinator coverage.

Add tests for any changed coordinator behavior, especially:

- persistence;
- restart recovery;
- concurrency;
- lease ownership;
- idempotency;
- unknown outcomes.

### `tests/test_states.py`

Preserve coverage for all existing valid and invalid transitions.

Add transition tests only for approved new states.

### `tests/test_storage.py`

Preserve event-chain integrity and concurrency tests.

Add tests for:

- reopen behavior;
- transaction rollback;
- durable state;
- corruption;
- concurrent writers;
- migration behavior if migrations are introduced.

### `.github/workflows/test.yml`

Preserve:

- Python 3.11–3.13 matrix;
- editable install with test extras;
- coverage threshold;
- read-only repository permissions.

Modify only to add approved platform-specific jobs, packaging checks, or security checks.

### `README.md`

Preserve the explicit statement that the current project is not a Windows automation product.

Update only after an implemented capability is tested and supported. Do not document future work as current functionality.

### `docs/protocol.md`

Update when protocol models, bindings, or state semantics change.

### `docs/supported-capabilities.md`

Update whenever a capability moves from planned to implemented and tested.

### `docs/windows-development.md`

Update only when Windows development or helper requirements are concretely selected.

### `docs/final-execution-checklist.md`

Update when execution, verification, recovery, or deployment requirements are implemented.

### `docs/security.md`

Must be reviewed locally before relying on its contents. Any future security boundary, helper, credential handling, or deployment change must update this document.

### `docs/test-matrix.md`

Must be reviewed locally before changing test strategy. Any Windows-specific validation must be added explicitly because current CI runs on Ubuntu.

### `plan.md`

The current file exists, but its complete contents were not independently verified.

Before replacing it, inspect it locally and preserve any useful repository-specific decisions. This implementation plan may replace it only after the project owner confirms that a plan update is desired.

## Conditional Files to Create

These files are recommendations for specific future workstreams and must not be created solely because the current task is `None`.

### Durable state workstream

Potential files:

```text
compuse/storage/state.py
compuse/storage/schema.py
compuse/storage/migrations.py
tests/test_state.py
tests/test_recovery.py
```

Responsibilities:

- durable runs, actions, permits, and leases;
- schema initialization or migrations;
- restart recovery;
- ownership checks;
- idempotency records.

### Windows observation workstream

Potential files:

```text
compuse/platform/__init__.py
compuse/platform/windows/__init__.py
compuse/platform/windows/observation.py
compuse/platform/windows/identity.py
compuse/platform/windows/coordinates.py
tests/windows/test_observation.py
```

Responsibilities:

- capture and normalize Windows observations;
- validate foreground window;
- validate process/session identity;
- identify input desktop;
- identify coordinate space.

### Executor workstream

Potential files:

```text
compuse/executor/__init__.py
compuse/executor/interface.py
compuse/executor/result.py
compuse/executor/fake.py
compuse/executor/windows.py
tests/test_executor.py
tests/test_executor_recovery.py
```

Responsibilities:

- executor protocol;
- explicit outcomes;
- fake executor for portable tests;
- Windows adapter only when platform support is approved.

### Verification workstream

Potential files:

```text
compuse/verification/__init__.py
compuse/verification/interface.py
compuse/verification/result.py
compuse/verification/postconditions.py
tests/test_verification.py
```

Responsibilities:

- postcondition definitions;
- verification result handling;
- unknown verification outcomes;
- transition into recovery or reconciliation.

### Native helper workstream

Potential files are not yet determinable.

The helper language, project layout, IPC protocol, build system, signing process, and packaging format are unresolved. Do not invent these files before those decisions are made.

## Files Not to Create Without Scope Approval

Do not create:

- provider SDK integrations;
- browser automation adapters;
- arbitrary shell execution;
- Windows input injection;
- a native helper;
- an installer;
- a service manager configuration;
- authentication middleware;
- cloud deployment configuration;
- course scheduling features.

---

# Step-by-Step Build Plan

The following steps are ordered. Steps after scope clarification are conditional on the selected workstream.

## Step 1: Obtain a concrete task definition

**Input**

- The current repository.
- The fact that the supplied task is `None`.

**Action**

Create or obtain an issue containing:

- user-visible behavior;
- technical scope;
- supported platforms;
- action kinds;
- security requirements;
- persistence requirements;
- acceptance criteria;
- deployment expectations.

**Expected result**

A bounded implementation target exists.

**Dependencies**

None.

---

## Step 2: Inspect the complete local baseline

**Input**

- Repository at the selected commit or current `main`.

**Action**

Read:

```text
README.md
pyproject.toml
compuse/protocol/models.py
compuse/coordinator/core.py
compuse/coordinator/states.py
compuse/storage/events.py
docs/*.md
tests/*.py
.github/workflows/test.yml
```

Pay particular attention to the locally available contents of:

```text
docs/security.md
docs/test-matrix.md
plan.md
```

**Expected result**

The builder has verified the current implementation and documentation boundaries rather than relying only on the research summary.

**Dependencies**

Step 1 is recommended first, but this inspection can begin before scope is finalized.

---

## Step 3: Run and record the baseline tests

**Input**

- A Python 3.11-or-newer environment.
- Existing `pyproject.toml`.

**Action**

Run:

```powershell
python -m pip install -e ".[test]"
python -m pytest -ra
python -m pytest --cov=compuse --cov-report=term-missing --cov-fail-under=80
```

**Expected result**

A recorded baseline containing:

- pass/fail status;
- test count;
- coverage;
- Python version;
- dependency versions;
- failures and tracebacks if any.

**Dependencies**

Step 2.

**Verification status**

Not executed by the research task.

---

## Step 4: Run packaging validation

**Input**

- Existing Hatchling configuration.

**Action**

Run:

```powershell
python -m pip install build
python -m build
```

Inspect the generated artifacts.

**Expected result**

The package builds successfully, or packaging failures are recorded as baseline defects.

**Dependencies**

Step 3 is recommended but not technically required.

**Verification status**

Not executed by the research task.

---

## Step 5: Select one implementation workstream

**Input**

- Scope decision from Step 1.
- Baseline results from Steps 2–4.

**Action**

Select exactly one initial workstream:

- durable state;
- Windows observation;
- executor interface;
- verification;
- controlled vertical slice;
- helper;
- packaging/deployment;
- another explicitly defined task.

Document why the selected workstream is first and what is deliberately excluded.

**Expected result**

A small, reviewable implementation boundary exists.

**Dependencies**

Steps 1–4.

---

## Step 6: Define interfaces and failure states before implementation

**Input**

- Selected workstream.

**Action**

Document:

- input and output types;
- ownership;
- timeout behavior;
- error behavior;
- state transitions;
- persistence requirements;
- logging requirements;
- security boundary;
- test strategy.

If execution is involved, define explicit outcomes for:

- confirmed dispatch;
- confirmed failure;
- unknown result.

**Expected result**

Implementation contracts exist before code is written.

**Dependencies**

Step 5.

---

## Step 7: Implement portable fakes before platform mutation

**Input**

- Approved interfaces.

**Action**

If the workstream involves execution or verification, implement deterministic fake components first.

Use them to exercise:

- permit consumption;
- lifecycle transitions;
- result persistence;
- timeout handling;
- unknown outcomes;
- verification failure;
- cancellation;
- recovery.

**Expected result**

The coordination behavior is testable without Windows APIs or real input injection.

**Dependencies**

Step 6.

---

## Step 8: Implement durable state if restart or multi-process behavior is required

**Input**

- Persistence requirements from Step 1.
- Existing `EventStore`.

**Action**

Add durable records for the entities required by the task.

At minimum, define behavior for:

- state initialization;
- permit consumption persistence;
- expiration;
- ownership;
- restart recovery;
- transaction rollback;
- event/state consistency;
- lease handling if multiple workers exist;
- idempotency if dispatch may be retried.

**Expected result**

A process restart cannot silently recreate or duplicate authority.

**Dependencies**

Steps 5–7 if execution is involved.

---

## Step 9: Implement observation adapters if Windows state is required

**Input**

- Approved Windows scope.
- Existing `Observation` model.

**Action**

Add a Windows observer that normalizes:

- foreground window;
- process ID;
- session ID;
- input desktop;
- coordinate-space ID;
- capture timestamp;
- observation revision.

Define behavior for:

- missing foreground window;
- secure desktop;
- locked workstation;
- process exit;
- changed display configuration;
- stale coordinate space.

**Expected result**

The coordinator receives structured, current observations rather than fabricated or incomplete state.

**Dependencies**

Steps 5–8 where persistence is required.

---

## Step 10: Implement execution only after authorization and observation are proven

**Input**

- Valid consumed permit.
- Current observation.
- Approved executor interface.
- Approved platform boundary.

**Action**

Implement the smallest permitted executor behavior.

Immediately before dispatch:

- recheck target identity;
- recheck coordinate space;
- recheck capability bindings;
- validate timeout;
- generate a correlation ID;
- record the intended dispatch.

Return an explicit structured result.

**Expected result**

The executor cannot be called as an unrestricted action runner and does not claim verified success.

**Dependencies**

Steps 6–9.

---

## Step 11: Implement postcondition verification

**Input**

- Action;
- pre-dispatch observation;
- executor result;
- post-dispatch observation.

**Action**

Define and implement an explicit postcondition for each supported action.

Examples:

- focus requires the expected foreground window;
- launch requires expected process/window identity;
- typing requires a controlled observable state change;
- clicking requires a defined target-state change;
- screenshot requires an observation event rather than mutation success.

**Expected result**

Actions reach `VERIFIED` only when the target state is independently observed.

**Dependencies**

Steps 9 and 10.

---

## Step 12: Add failure and recovery paths

**Input**

- Executor and verifier outcomes.

**Action**

Implement handling for:

- expired permits;
- stale observations;
- identity mismatch;
- helper timeout;
- helper crash;
- transport failure;
- unknown dispatch result;
- failed postcondition;
- database failure;
- event integrity failure;
- process restart.

Use existing `UNKNOWN`, `RECONCILING`, `RECOVERY`, `FAILED`, `CANCELLED`, and `ABORTED` concepts where appropriate.

**Expected result**

Uncertain operations stop safely and do not become false successes.

**Dependencies**

Steps 8–11.

---

## Step 13: Add tests for the selected workstream

**Input**

- Implemented code.
- Baseline tests.

**Action**

Add unit and integration tests covering:

- valid behavior;
- invalid inputs;
- concurrency;
- persistence;
- restart behavior;
- stale state;
- security boundaries;
- timeouts;
- unknown outcomes;
- recovery.

For Windows behavior, add Windows-specific tests or explicitly document manual-only validation.

**Expected result**

The new behavior is covered without weakening current tests.

**Dependencies**

Steps 7–12.

---

## Step 14: Update documentation

**Input**

- Implemented and tested behavior.

**Action**

Update only the documentation that reflects actual supported behavior:

- `README.md`;
- `docs/protocol.md`;
- `docs/supported-capabilities.md`;
- `docs/windows-development.md`;
- `docs/security.md`;
- `docs/test-matrix.md`;
- `docs/final-execution-checklist.md`.

Clearly distinguish:

- implemented;
- tested;
- manually verified;
- planned;
- unsupported.

**Expected result**

Documentation does not overclaim support.

**Dependencies**

Step 13.

---

## Step 15: Run all validation and report unverified work

**Input**

- Completed implementation and documentation.

**Action**

Run:

```powershell
python -m pytest -ra
python -m pytest --cov=compuse --cov-report=term-missing --cov-fail-under=80
python -m build
```

Run platform-specific validation if applicable.

Record:

- commands;
- environment;
- results;
- failures;
- skipped tests;
- unavailable services or credentials;
- unverified behavior.

**Expected result**

The builder can distinguish actual results from planned checks.

**Dependencies**

Steps 13–14.

---

# Technical Details

## Current Public APIs

### Coordinator construction

```python
Coordinator(
    store=None,
    policy_revision="policy-1",
)
```

### Permit issuance

```python
Coordinator.issue(
    proposal: ActionProposal,
    observation: Observation,
    ttl: float = 30,
) -> Permit
```

Current documented constraints:

- TTL must be greater than zero;
- TTL must not exceed 300 seconds;
- default TTL is 30 seconds;
- origin must be trusted;
- run ID must match;
- observation revision must not be stale;
- coordinate-space ID must match;
- policy revision must match.

### Permit consumption

```python
Coordinator.consume(
    permit_id,
    proposal: ActionProposal,
    observation: Observation,
)
```

The method validates the permit and returns authorized action data. It does not execute the action.

### Permit release

```python
Coordinator.release(
    permit_id,
)
```

### Cleanup

```python
Coordinator.cleanup()
```

### Action hashing

```python
def digest_action(action: Action) -> str:
    ...
```

The current implementation canonicalizes the action using compact JSON with sorted keys and calculates a SHA-256 digest.

### Event store

```python
EventStore(path=":memory:")
```

```python
EventStore.append(
    run_id: str,
    event_type: str,
    payload: Any,
    timestamp: str,
) -> int
```

```python
EventStore.verify(run_id: str) -> bool
```

```python
EventStore.assert_integrity(run_id: str) -> None
```

```python
EventStore.events(run_id: str) -> list[sqlite3.Row]
```

```python
EventStore.close() -> None
```

## Current Protocol Values

### Origins

```text
USER_INTENT
SYSTEM_POLICY
STRATEGIST_INSTRUCTION
EXECUTOR_INSTRUCTION
ENVIRONMENT_CONTENT
PROVIDER_OUTPUT
```

The coordinator rejects `ENVIRONMENT_CONTENT` and `PROVIDER_OUTPUT` as independent authorization sources.

### Action kinds

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

## Current Dependencies

```text
Python >= 3.11
pydantic >= 2.7, < 3
hatchling >= 1.25
pytest >= 8
pytest-cov >= 5
```

The test dependencies are provided through the `test` optional extra.

## Current Commands

```powershell
python -m pip install -e ".[test]"
python -m pytest -ra
```

Coverage:

```powershell
python -m pip install coverage
pytest --cov=compuse --cov-report=term-missing
```

CI-equivalent coverage:

```powershell
pytest --cov=compuse --cov-report=term-missing --cov-fail-under=80
```

Packaging validation:

```powershell
python -m pip install build
python -m build
```

The packaging command is recommended validation and is not currently part of the existing CI workflow.

## Database Behavior

The current event journal schema is effectively:

```sql
CREATE TABLE IF NOT EXISTS events (
    run_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    type TEXT NOT NULL,
    payload TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    previous_event_hash TEXT NOT NULL,
    event_hash TEXT NOT NULL,
    PRIMARY KEY (run_id, seq),
    UNIQUE (event_hash)
);
```

The journal uses:

- SQLite;
- foreign keys;
- 10-second busy timeout;
- `synchronous=FULL`;
- WAL for file-backed stores;
- `RLock` per store instance;
- `BEGIN IMMEDIATE`;
- SHA-256 event hashes.

## Recommended Idempotency Key

For a future executor:

```text
run_id + ":" + action_id + ":" + permit_id
```

This is a recommendation only. The current repository does not implement idempotency.

## Time Compatibility

Current permits use wall-clock UTC timestamps.

A future implementation must assess:

- system clock changes;
- suspend/resume;
- helper/coordinator clock differences;
- long-running dispatch;
- expiry during execution.

A possible future approach is to use monotonic time for local TTL enforcement while retaining UTC timestamps for audit. This is a design recommendation, not an existing behavior.

## Environment Variables

No environment variables are currently documented or required.

Potential future variables, only if approved and implemented:

```text
COMPUSE_DATA_DIR
COMPUSE_LOG_LEVEL
COMPUSE_POLICY_REVISION
COMPUSE_WINDOWS_HELPER_PATH
COMPUSE_EXECUTOR_TIMEOUT
```

Do not add these variables until their behavior and defaults are defined.

---

# Testing and Verification

## Verification Status

The research task inspected repository contents and CI configuration but did not execute tests.

Therefore:

- no local pytest result is verified;
- no coverage result is verified;
- no package build result is verified;
- no Windows behavior is verified;
- no runtime behavior beyond source inspection is verified.

## Required Baseline Checks

Run:

```powershell
python -m pytest -ra
```

Expected planned check:

- all existing tests pass.

Run:

```powershell
python -m pytest --cov=compuse --cov-report=term-missing --cov-fail-under=80
```

Expected planned check:

- coverage is at least 80%.

Run:

```powershell
python -m build
```

Expected planned check:

- wheel and source distribution build successfully.

## Unit Tests

### Protocol

Test:

- unknown fields are rejected;
- strict types are enforced;
- invalid action discriminators are rejected;
- coordinates respect bounds;
- text length limits are enforced;
- key-combination length limits are enforced;
- required identifiers cannot be empty;
- naïve timestamps are rejected;
- timezone-aware timestamps are normalized to UTC;
- action hashes are deterministic;
- serialization round trips preserve meaning.

### Coordinator

Test:

- untrusted origins are rejected;
- mismatched run IDs are rejected;
- stale observation revisions are rejected;
- coordinate-space mismatch is rejected;
- policy mismatch is rejected;
- invalid TTLs are rejected;
- expired permits are rejected;
- consumed permits cannot be reused;
- action-hash mismatches are rejected;
- concurrent consumption is handled safely;
- release behavior is correct;
- cleanup removes or handles expired state as documented.

### State machines

Test:

- every valid transition;
- every invalid transition;
- terminal-state behavior;
- any newly added transitions;
- cancellation and abort behavior;
- recovery and reconciliation behavior.

### Storage

Test:

- sequence numbers are ordered;
- separate runs have separate chains;
- modified payloads are detected;
- deleted events are detected;
- reordered events are detected;
- previous hashes are validated;
- failed appends roll back;
- concurrent writers behave correctly;
- file-backed WAL behavior is correct;
- reopening a database preserves expected state;
- corrupted databases fail safely.

## Future Durable-State Tests

If persistence is implemented, test:

- permits remain consumed after restart;
- permits do not become reusable after a crash;
- expired permits are handled deterministically;
- lease acquisition is exclusive;
- lease renewal requires ownership;
- lease release requires ownership;
- expired leases can be recovered safely;
- duplicate dispatch requests are suppressed or reconciled;
- state and event journal remain consistent;
- migration behavior is tested.

## Future Windows Tests

Windows-specific validation must test:

- foreground-window identity;
- process identity;
- session identity;
- input-desktop identity;
- coordinate-space stability;
- display and DPI changes;
- locked workstation behavior;
- secure desktop behavior;
- helper version compatibility;
- helper timeout;
- helper crash;
- IPC failure;
- unknown dispatch outcomes;
- postcondition verification;
- process/window disappearance;
- cancellation.

Portable tests do not prove Windows behavior.

## Integration Tests

For a controlled future vertical slice, test:

1. capture a pre-action observation;
2. create a proposal;
3. issue a permit;
4. consume the permit;
5. dispatch through a fake executor;
6. capture a post-action observation;
7. verify the postcondition;
8. persist all state transitions;
9. inspect the event chain;
10. simulate restart and recovery.

## Manual Checks

If Windows support is implemented, document manual checks for:

- supported Windows versions;
- display configurations;
- DPI scaling;
- multiple monitors;
- remote desktop;
- locked workstation;
- secure desktop;
- helper installation;
- helper upgrade;
- helper removal;
- process crash;
- timeout;
- cancellation;
- recovery.

## Acceptance Criteria for a Future Execution Workstream

A future executor workstream is not complete unless:

- only valid consumed permits can reach the executor;
- target identity is checked before dispatch;
- capability and coordinate bindings are checked;
- outcomes distinguish success, failure, and unknown;
- postconditions are independently verified;
- unknown outcomes enter reconciliation or recovery;
- state survives restart if restart safety is in scope;
- tests cover failure and concurrency;
- documentation accurately states supported behavior;
- CI remains green with at least 80% coverage.

---

# Security and Reliability

## Authority Separation

Maintain the existing distinction between:

- user intent;
- system policy;
- strategist instructions;
- executor instructions;
- environment content;
- provider output.

Environment content and provider output must not independently issue permits.

## Input Validation

Continue using strict Pydantic models with:

```python
ConfigDict(extra="forbid", strict=True)
```

Validate:

- action discriminator;
- identifiers;
- numeric ranges;
- text limits;
- timestamps;
- revisions;
- coordinate spaces;
- policy revisions;
- capability bindings.

Do not accept arbitrary extra fields at protocol boundaries.

## Permit Security

Permits must be:

- bound to a run;
- bound to an action;
- bound to an action hash;
- bound to an observation revision;
- bound to a coordinate space;
- bound to a policy revision;
- time-limited;
- one-use;
- rejected after expiration;
- rejected after consumption.

If persisted, permit state must be transactionally updated.

## Secrets and Sensitive Data

The current `TypeText` action allows arbitrary text up to 10,000 characters.

A future executor must decide how to handle sensitive text such as:

- passwords;
- access tokens;
- payment information;
- personal data.

Minimum requirements:

- do not log raw typed text by default;
- redact or hash sensitive payloads in audit records;
- separate credential entry from ordinary text entry;
- require explicit confirmation where appropriate;
- never store credentials in plaintext in events;
- avoid including sensitive payloads in logs, exceptions, or telemetry.

## Native Helper Security

A future helper must have:

- authenticated request and response correlation;
- version reporting;
- capability reporting;
- bounded request timeouts;
- cancellation;
- crash detection;
- least privilege;
- secure installation;
- integrity verification;
- no unrestricted shell or command execution interface.

The helper language and IPC design are unresolved and require an explicit decision.

## Logging

Logging requirements for future components:

- log correlation IDs;
- log run and action IDs;
- log state transitions;
- log failure codes;
- avoid raw sensitive text;
- avoid logging credentials;
- include enough context to diagnose stale-state and identity failures;
- do not log a successful mutation unless the result and verification state are accurately represented.

No logging configuration currently exists as a documented runtime contract.

## Timeouts and Retries

Future executor and helper boundaries must define:

- connection timeout;
- dispatch timeout;
- verification timeout;
- retry policy;
- retry safety;
- behavior after timeout.

Do not retry a potentially delivered mutation unless idempotency and reconciliation behavior are defined.

## Safe Failure

The system must fail closed when:

- an observation is stale;
- the target identity changes;
- the coordinate space changes;
- a permit expires;
- a permit has already been consumed;
- event integrity fails;
- the helper cannot be authenticated;
- a timeout creates uncertainty;
- verification cannot determine the result.

Unknown outcomes must not be silently converted to success or ordinary failure.

## Event Journal Reliability

The current journal’s hash chain should be preserved.

Future work must consider:

- database replacement;
- database deletion;
- external trust anchors;
- retention;
- archival;
- access permissions;
- privacy of event payloads;
- backup and restore;
- integrity verification during startup.

## Repository Security Controls

Current repository facts:

- secret scanning is enabled;
- secret-scanning push protection is enabled;
- `main` is not protected;
- Dependabot security updates are disabled;
- observed latest commit is unsigned.

Recommended future controls:

- required CI checks;
- pull-request review;
- restricted direct pushes;
- dependency review;
- dependency update policy;
- signed commits or signed release artifacts if required;
- protected release tags.

---

# Deployment and Operations

## Current Deployment State

No deployment target is implemented.

The repository is currently a Python library/prototype, not:

- a hosted service;
- a CLI product;
- a Windows service;
- a desktop application;
- an installer;
- a cloud workload.

## Current Runtime Configuration

No runtime environment variables are documented as required.

No external service credentials are required by the current code.

## Recommended Deployment Stages

### Stage 1: Portable library

Required work:

- build wheel and source distribution;
- validate package metadata;
- run the supported Python matrix;
- document installation;
- define versioning;
- define release artifacts.

### Stage 2: Windows development helper

Requirements:

- developer-only execution;
- explicit local invocation;
- no unattended operation;
- Windows-specific validation;
- helper version reporting;
- documented installation and removal;
- no arbitrary command execution.

### Stage 3: Controlled vertical slice

Requirements:

- local durable database;
- explicit user confirmation;
- controlled target application;
- identity validation;
- postcondition verification;
- kill switch;
- recovery behavior;
- audit logging;
- helper integrity checks.

### Stage 4: Production deployment

Do not proceed until the project has:

- durable permits;
- leases where needed;
- restart recovery;
- idempotency;
- executor outcomes;
- postcondition verification;
- unknown-result reconciliation;
- security review;
- supported-platform definition;
- operational logging;
- rollback procedure;
- release integrity policy.

## Startup and Shutdown

No current startup command exists beyond importing the Python package.

Future services or helpers must document:

- startup command;
- shutdown command;
- signal handling;
- database initialization;
- lock acquisition;
- recovery on startup;
- cleanup on shutdown;
- behavior after an interrupted dispatch.

## Data and Database Setup

The current `EventStore` creates its SQLite schema automatically.

If durable operational state is added, define:

- database location;
- schema initialization;
- migration strategy;
- backup strategy;
- corruption handling;
- file permissions;
- retention;
- restore validation.

## Monitoring

No monitoring system currently exists.

A future deployment should define monitoring for:

- startup failures;
- event integrity failures;
- permit rejection rates;
- stale observations;
- helper crashes;
- timeout frequency;
- unknown outcomes;
- verification failures;
- database lock errors;
- recovery attempts.

## Rollback

A future release must define:

- how to stop the helper or service;
- how to preserve the audit database;
- how to downgrade protocol versions;
- how to handle incompatible persisted state;
- how to revoke or invalidate permits;
- how to restore the prior package or helper;
- how to prevent partially completed actions from being retried unsafely.

---

# Gaps and Unknowns

## Task and Product Gaps

- No feature request exists.
- No bug report exists.
- No acceptance criteria exist.
- No target user is specified.
- No deadline is specified.
- No deployment target is specified.
- It is unknown whether the intended next step is implementation, documentation, or audit.
- It is unknown whether Windows support is required now.
- It is unknown whether physical input injection is in scope.
- It is unknown whether UI Automation is in scope.
- It is unknown whether a native helper is acceptable.
- It is unknown whether provider or model integration is in scope.
- It is unknown whether course scheduling is permanently excluded or only excluded from the current milestone.

## Technical Unknowns

- The Windows API implementation choice is unresolved.
- The native helper language is unresolved.
- The IPC mechanism is unresolved.
- The supported Windows version range is unresolved.
- The persistence schema is not implemented.
- The migration strategy is not implemented.
- The lease design is not implemented.
- The idempotency design is not implemented.
- The executor protocol is not implemented.
- The postcondition model is not implemented.
- The unknown-result reconciliation process is not implemented.
- The helper signing and integrity process is not defined.
- The release hosting location is not defined.
- The package publication workflow is not defined.
- The monitoring system is not defined.
- The rollback procedure is not defined.

## Verification Gaps

- Local tests were not executed during research.
- Actual test pass/fail status is unknown.
- Actual coverage is unknown.
- Package build status is unknown.
- Wheel contents were not verified.
- Source distribution contents were not verified.
- Windows behavior is unverified.
- Native helper behavior is unverified because no helper exists.
- Complete `docs/security.md` content was not independently retrieved.
- Complete `docs/test-matrix.md` content was not independently retrieved.
- Complete `plan.md` content was not independently retrieved.
- Complete `docs/final-execution-checklist.md` content was not independently retrieved.

## Security Gaps

- No external trust anchor exists for the event journal.
- Database deletion or replacement is not addressed.
- Event retention is not defined.
- Event payload privacy is not separately addressed.
- No user authentication exists.
- No service authentication exists.
- No helper authentication exists.
- No credential-entry policy exists.
- No release-signing policy exists.
- `main` is not protected.
- Dependabot security updates are disabled.
- Observed commits are unsigned.

## Assumptions

This plan assumes:

1. `main` and the latest observed commit represent the intended baseline.
2. The repository documentation describes the intended product boundary.
3. Future work should preserve the current safety-first separation.
4. No implementation should be selected without a concrete task.
5. The existing portable test and packaging patterns should be preserved unless a task justifies changing them.

---

# Builder Handoff

The builder must deliver the following.

## Required for the Current Task

- Do not make unrequested product or code changes.
- Obtain a concrete task definition before implementation.
- Inspect the local contents of all relevant files, including `plan.md`, `docs/security.md`, and `docs/test-matrix.md`.
- Run and record the baseline test commands.
- Run and record packaging validation.
- Report actual results separately from planned checks.
- Preserve the current authorization, validation, state, and audit boundaries.

## Required if a Future Workstream Is Approved

- Define the workstream and exclusions.
- Add only the files required for that workstream.
- Preserve strict protocol validation.
- Preserve origin restrictions.
- Preserve stale-state and action-hash checks.
- Preserve one-use permit semantics.
- Add durable state before production execution.
- Add explicit executor outcomes.
- Treat uncertain results as `UNKNOWN`.
- Verify postconditions independently.
- Add unit, integration, concurrency, persistence, and failure tests.
- Update documentation only for implemented and verified behavior.
- Keep portable CI passing on Python 3.11, 3.12, and 3.13.
- Maintain at least 80% coverage unless explicitly changed.
- Document platform-specific tests and any manual-only verification.
- Document secrets, permissions, timeouts, retries, logging, and rollback.

## Incomplete or Unverified Work Reporting

The builder must report:

- every command executed;
- the exact environment used;
- test and coverage results;
- package build results;
- skipped tests and why they were skipped;
- unavailable operating systems or tools;
- missing credentials;
- unverified API behavior;
- incomplete integrations;
- known security limitations;
- remaining implementation gaps;
- whether any behavior is only planned rather than implemented.

No builder report may claim that the system works, is production-ready, or supports Windows automation unless that behavior has been implemented and verified with the required tests and operational checks.