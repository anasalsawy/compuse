# Compuse

Compuse is a safety-first, local-first coordination core for a future Windows computer-use agent. This repository intentionally ships a **portable model-free foundation**, not the complete Windows product described in `plan.md`.

## Current implementation

- Strict Pydantic protocol models and discriminated actions.
- Observation- and coordinate-space-bound, expiring, single-use permits.
- Coordinator-owned policy checks and thread-safe in-process mutation boundary.
- SQLite WAL event journal with FULL synchronous mode and SHA-256 per-run hash chains.
- Explicit rejection of environment content and provider output as authority.

The coordinator authorizes and records actions; it does not inject input, launch programs, browse, use Electron, process voice, or claim verification. Those capabilities remain planned or unsupported.

## Development

Requires Python 3.11+.

```bash
python -m venv .venv
. .venv/bin/activate       # Windows: .venv\\Scripts\\Activate.ps1
python -m pip install -e '.[test]'
pytest -q
```

A minimal flow constructs an `Observation`, creates an `ActionProposal`, issues a permit, consumes it, dispatches the returned typed action through a separately implemented executor, then calls `release(permit_id)`.

## Safety boundary

`consume` is not execution and does not prove success. A real integration must capture post-action state, perform independent deterministic verification, and record recovery/unknown outcomes. Never use this prototype with production credentials or unattended desktop mutation.

See `plan.md` for the authoritative target architecture and `docs/supported-capabilities.md` for the current capability matrix.
