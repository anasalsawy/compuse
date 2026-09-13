# Test matrix

## Executed baseline

| Command | Environment | Result |
|---|---|---|
| `python -m pip install -e '.[test]'` | E2B Linux sandbox, Python 3.11.6 | exit 0 |
| `python -m pytest -ra` | E2B Linux sandbox, pytest 9.1.1 | 7 passed, exit 0 |

## Not verified

The Windows host command runner was unavailable (`Invalid MCP token`). Consequently these remain unverified:

- Windows dependency installation.
- Native helper build.
- Interactive desktop access.
- Notepad launch and UI Automation.
- Process/window identity, DPI, session, and input-desktop checks.
- Windows integration tests, packaging, signing, and crash recovery.

No Windows capability is claimed until those checks execute successfully on an interactive Windows host.