# Test matrix

| Area | Portable test suite | Windows acceptance suite |
|---|---:|---:|
| Strict protocol validation | Yes | No |
| Permit binding and replay rejection | Yes | No |
| Lifecycle transition tables | Yes | No |
| SQLite event integrity | Yes | No |
| Concurrent journal appends | Yes | No |
| Native helper | No | Not implemented |
| UI Automation | No | Not implemented |
| Notepad workflow | No | Not implemented |
| Process/window/session identity | No | Not implemented |

Portable tests prove Python invariants only. No Windows-native result should be inferred until an interactive Windows acceptance suite exists.
