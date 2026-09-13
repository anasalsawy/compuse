# Supported capabilities

| Capability | Status | Evidence |
|---|---|---|
| Strict typed protocol | Implemented | `compuse/protocol/models.py` |
| Single-use expiring in-process permits | Implemented | `compuse/coordinator/core.py` |
| Explicit lifecycle transition validation | Implemented | `compuse/coordinator/states.py`, `tests/test_states.py` |
| Tamper-evident SQLite event journal | Implemented | `compuse/storage/events.py`, `tests/test_storage.py` |
| Windows native helper/UI Automation | Not implemented | None |
| Durable run/action/permit state and restart recovery | Not implemented | None |
| Course scheduling/import/calendar export | Not implemented | None |

Implemented entries describe the portable foundation only; they do not imply desktop execution or success verification.
