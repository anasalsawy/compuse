# Windows development

Windows functionality is planned but not present in this repository.

The first native milestone is a model-free Notepad vertical slice: approved logical launch, process/window identity, UI Automation observation, exact text-control resolution, semantic `ValuePattern` assignment, post-action verification, cancellation, and fail-closed recovery.

A future implementation must choose a native-helper language and typed IPC protocol before adding native code. It must be tested on an unlocked interactive Windows desktop. Headless Linux CI and fake executors cannot prove UI Automation, input-desktop identity, DPI behavior, or Notepad behavior.

Do not add arbitrary shell execution or arbitrary executable paths as a shortcut to the native boundary.