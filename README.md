# Compuse

Safety-first coordination core for a local-first Windows computer-use agent. The delivered core provides strict typed actions, observation-bound single-use permits, untrusted-origin rejection, a global mutation boundary, and a tamper-evident SQLite event chain.

## Install and test

```bash
python -m venv .venv
python -m pip install -e '.[test]'
pytest
```

Native UI Automation, Electron, browser/CDP, voice, installer, and Windows-specific integrations are explicitly not implemented in this portable core. See `plan.md` and `docs/supported-capabilities.md`.
