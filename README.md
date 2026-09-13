# Compuse

Compuse is a local-first desktop computer-use runtime with an explicit
authorization and audit boundary. It now includes a first NeuralAgent-style
Windows vertical slice: headed screen observation, typed physical input, an
OpenAI-compatible vision planner, and a dual-lobe speculative handoff loop.

## Dual-lobe runtime

Lobe A plans the active batch. While that batch is executing, A predicts a
possible next batch and Lobe B independently prepares and checks the next
handoff from A's predicted end state. B's batch is executed only after a fresh
observation confirms its checkable anchors. Any mismatch, failure, or unknown
result discards speculation and causes a replan from reality.

This overlaps model planning with physical execution, but physical input stays
serialized through the Coordinator. It is bounded speculation, not blind
parallel clicking.

## Install and run on Windows

```powershell
python -m pip install -e ".[desktop]"
$env:COMPUSE_LLM_BASE_URL = "https://api.example.com/v1"
$env:COMPUSE_LLM_API_KEY = "your-key"
$env:COMPUSE_LLM_MODEL = "your-vision-model"
compuse-agent "Open Chrome and navigate to example.com" --live
```

Use `--live` only after reviewing the task. Without it, the desktop adapter
refuses mouse, keyboard, launch, file, and browser mutations.

## Portable core

The original coordination core remains available and provides:

- strict Pydantic v2 action models;
- observation/action binding;
- one-use expiring permits;
- SQLite WAL event journaling with a SHA-256 hash chain;
- fail-closed lifecycle transition tables.

```powershell
python -m pip install -e ".[test]"
python -m pytest -ra
```

The portable tests do not prove Windows behavior. The live adapter is a first
vertical slice and still needs UI Automation/OCR grounding, independent
postcondition verification, durable permit state, cancellation, crash
recovery, and interactive Windows acceptance tests before unattended use.

See [`docs/dual-lobe.md`](docs/dual-lobe.md) for the runtime contract and
[`docs/windows-development.md`](docs/windows-development.md) for the Windows
boundary.
