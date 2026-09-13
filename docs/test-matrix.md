# Test matrix

| Area | Command/evidence | Status |
|---|---|---|
| Portable protocol/coordinator | `python -m pytest -ra` | Verified only when run in the current environment |
| Lifecycle transitions | `tests/test_states.py` | Portable |
| Event integrity and tamper detection | `tests/test_storage.py` | Portable |
| Windows UI Automation/native helper | Windows interactive test suite | Not implemented / blocked |

The portable suite does not prove Windows behavior, desktop identity, UI Automation, physical input, or post-action desktop verification.
