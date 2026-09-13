# Compuse

Compuse is a safety-first, local-first coordination core for a future Windows computer-use agent. This repository intentionally ships a **portable, model-free foundation**, not a complete Windows automation product.

## Current status

Implemented and tested:

- Strict Pydantic protocol models and discriminated actions.
- Observation-, coordinate-space-, policy-, and action-bound permit validation.
- Single-use, expiring permits with an in-process mutation boundary.
- SQLite WAL event journaling with full synchronous mode and SHA-256 per-run hash chains.
- Automated Python tests.

Not implemented:

- Windows native helper, UI Automation, Notepad workflow, process/window identity, session/input-desktop checks, and physical input.
- Durable run/action/permit state, leases, restart recovery, and unknown-result reconciliation.
- Browser, voice, provider/model, Electron, screenshot, installer, and signing integrations.

This is not course-scheduling software and does not implement course import, scheduling, conflict detection, or calendar export.

## Installation and tests

Requires Python 3.11 or newer.

```bash
python -m pip install -e '.[test]'
python -m pytest -ra
```

The current test suite is portable and does not prove Windows behavior.

## Safety boundary

`Coordinator.consume()` authorizes a typed action; it does not execute input or prove success. A future Windows integration must capture post-action state, independently verify the intended result, and record failure or unknown outcomes. Do not use this prototype with production credentials or unattended desktop mutation.

See [`docs/supported-capabilities.md`](docs/supported-capabilities.md) for the conservative capability matrix and [`plan.md`](plan.md) for the broader design direction.

## License

See [`LICENSE`](LICENSE).
