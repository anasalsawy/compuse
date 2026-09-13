# Windows development

The current package is portable Python and has no native Windows helper. Windows-specific behavior is therefore **not implemented or verified**.

When native work begins, tests must run on an unlocked interactive Windows desktop and must report the Windows build, Python version, helper version, session, input desktop, foreground window, and process identity. CI on non-Windows hosts must not be presented as evidence of desktop safety.

Until that work exists, do not use this prototype for unattended desktop mutation, production credentials, or safety-critical workflows.
