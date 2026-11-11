# Contributing to VoidDesk

VoidDesk spans a handheld framebuffer UI, a LÖVE frontend, a local service and optional desktop utilities. Small, testable changes are easier to review than broad rewrites.

## Before opening an issue

Include:
- VoidDesk version and commit/release used.
- Device model, firmware and architecture.
- Selected frontend (love or py) and the exact screen/action involved.
- Steps to reproduce and expected versus actual behaviour.
- A short relevant log excerpt, with credentials, IPs, SSIDs and personal paths redacted.

## Pull requests

1. Keep each PR focused on one fix or feature.
2. Explain user-visible effects and compatibility implications.
3. Add or update tests for bug fixes where practical.
4. Keep optional dependencies optional; handle their absence gracefully.
5. Do not suppress failing checks with "|| true" or equivalent.
6. Do not commit generated runtime directories, personal config, logs, backups or downloaded desktop images.
7. Describe what you tested and on which hardware/firmware.

## Local checks

~~~bash
python3 -m pip install pytest ruff
python -m compileall -q BUILDCHECK.py voiddesk.py bin desk service outdesk voidcast_addons assets
python -m pytest -q
python BUILDCHECK.py
~~~

CI additionally validates selected Ruff diagnostics, shell scripts and Lua files with LuaJIT. The optional headless smoke test requires Pygame: python BUILDCHECK.py --smoke.

## Project conventions

- Prefer the standard library in bootstrap and recovery paths.
- Avoid network calls, package installation or blocking system commands in render/update loops.
- Validate downloaded archive paths and verify published checksums before use.
- Write configuration atomically where possible.
- Preserve the last known-good runtime if bootstrap fails.
- Document device-only features as device-only; do not imply PC or non-muOS support without testing.


## Issue triage and pull request workflow

- Use the structured issue forms for defects, feature proposals and device-specific validation.
- Follow [Issue Triage](docs/ISSUE_TRIAGE.md) for the repository's label dimensions and priority definitions.
- Work on a topic branch and open a pull request against `main`; do not push routine development changes directly to `main`.
- A green CI run is necessary but does not replace physical handheld validation. Mark device-only checks explicitly in the PR and keep hardware-dependent issues open until evidence is available.
- Resolve review conversations and include concise test evidence before requesting integration.
