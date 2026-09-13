# Compuse

Compuse is a safety-first, local-first coordination core for future computer-use systems. The current release is a **portable authorization and audit prototype**: it validates typed actions, binds them to observations, issues one-use permits, and records tamper-evident events.

It is deliberately **not** a Windows automation product. It does not launch applications, control input, implement UI Automation, or claim that an authorized action succeeded.

## Implemented

- Strict Pydantic v2 protocol models with rejected unknown fields.
- Discriminated typed actions and bounded input values.
- Timezone-aware observations and action/observation binding.
- Trusted-origin checks and policy/capability revisions.
- Single-use, expiring permits with an in-process mutation boundary.
- SQLite WAL event journaling with full synchronization and SHA-256 hash chains.
- Explicit fail-closed run and action lifecycle transition tables.
- Portable Pytest coverage for positive and negative invariants.

## Explicitly out of scope

The repository does not currently provide a native Windows helper, UI Automation, Notepad workflow, process/window/session identity checks, physical input, durable run/action/permit state, restart recovery, leases, idempotency, executor dispatch, postcondition verification, or unknown-result reconciliation. Those features require a separate design and interactive Windows acceptance tests.

This project is not course-scheduling software and does not implement course import, scheduling, conflict detection, or calendar export.

## Installation and tests

Python 3.11 or newer is required:

```powershell
python -m pip install -e ".[test]"
python -m pytest -ra
```

For coverage:

```powershell
python -m pip install coverage
pytest --cov=compuse --cov-report=term-missing
```

The portable suite does not prove Windows behavior. Treat `Coordinator.consume()` as authorization only; it does not execute input or prove success.

## Safety boundary

Do not connect this prototype to unattended desktop mutation or production credentials. A future Windows implementation must independently observe the target after dispatch, verify the intended postcondition, and record failed or unknown outcomes.

See `docs/protocol.md`, `docs/security.md`, `docs/supported-capabilities.md`, and `docs/windows-development.md` for the documented boundaries.

## License

See [LICENSE](LICENSE).
