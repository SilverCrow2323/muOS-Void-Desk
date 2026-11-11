# Issue Triage

This document defines a consistent, low-noise taxonomy for VoidDesk issues. Apply labels from different dimensions together rather than inventing a single label for every combination.

## Label dimensions

### Type

| Label | Use |
|---|---|
| `[Type] Bug` | Existing behaviour is broken or unsafe |
| `[Type] Feature` | New capability request |
| `[Type] Enhancement` | Improvement to an existing capability |
| `[Type] Documentation` | README, wiki, guides or developer documentation |
| `[Type] Question` | Help or clarification |
| `[Type] Compatibility` | Device, firmware, architecture or distribution compatibility |

### Scope

Keep the existing `[Scope] muOS` label. Add these only when the repository label set is provisioned:

- `[Scope] ROCKNIX`
- `[Scope] KNULLI`
- `[Scope] Linux PC`
- `[Scope] Cross-platform`

### Area

Use one or more component labels:

- `[Area] NEXUS UI`
- `[Area] Browser`
- `[Area] XFCE`
- `[Area] Bluetooth`
- `[Area] Power Management`
- `[Area] UPLINK`
- `[Area] Media`
- `[Area] Packaging`
- `[Area] QWASAR Studio`
- `[Area] Build and CI`
- `[Area] Documentation`

### Priority

| Label | Meaning |
|---|---|
| `[Priority] P0 Critical` | Data loss, security exposure, or widespread device failure |
| `[Priority] P1 High` | Core workflow broken or device cannot safely complete a system action |
| `[Priority] P2 Normal` | Important defect with a workaround or limited impact |
| `[Priority] P3 Low` | Cosmetic, minor or non-blocking improvement |

### Status

- `[Status] Needs Triage` — not yet classified.
- `[Status] Needs Info` — maintainer needs reproduction details or logs.
- `[Status] Needs Hardware Test` — code-side work exists, but physical validation is outstanding.
- `[Status] Blocked` — cannot proceed until a dependency is resolved.
- `[Status] Ready` — sufficiently specified and ready for implementation.

Do not use a status label as a substitute for closing a resolved issue.

## Triage rules

1. Every issue should have exactly one Type label.
2. Add one or more Area labels where the affected component is known.
3. Add a Scope label only when the affected platform is evidenced by the report or reproduction.
4. Assign a Priority based on impact, not how recently the issue was reported.
5. Use Needs Info when the report cannot be reproduced. Use Needs Hardware Test when software changes are merged but device validation is still outstanding.
6. Do not close a hardware-dependent issue solely because CI is green.
7. Keep one issue focused on one independently verifiable outcome. Split issues only when separate fixes or validation results can be tracked independently.

## Current open issue triage

### #1 — Browser launch fails with an Input/output error on muOS

- Existing labels: `[Type] Bug`, `[Scope] muOS`.
- Suggested additions: `[Area] Browser`, `[Priority] P2 Normal`, `[Status] Needs Info`.
- Reason: the report only says “output input error”; browser identity, launch path and logs are still missing.

### #2 — RG35XXSP: power-off leaves device running after LED extinguishes

- Existing labels: `[Type] Bug`, `[Scope] muOS`.
- Suggested additions: `[Area] Power Management`, `[Priority] P1 High`, `[Status] Needs Hardware Test`.
- Reason: the shutdown hand-off has been merged, but the reporter's RG35XXSP still needs a physical full power-off check.

### #42 — RG35XXSP: verify Bluetooth responsiveness after background-probe fix

- Existing labels: `[Type] Bug`, `[Scope] muOS`.
- Suggested additions: `[Area] Bluetooth`, `[Priority] P2 Normal`, `[Status] Needs Hardware Test`.
- Reason: PR #5 moved Bluetooth status probes off the UI path; verify smooth NEXUS animation and D-pad response on the actual RG35XXSP with Bluetooth initially enabled and disabled.

## Provisioning

The existing repository labels are bracketed (for example, `[Type] Bug` and `[Scope] muOS`). Create any new label names in GitHub's repository Labels settings before applying them to issues. This file is the taxonomy source of truth; do not apply misspelled or ad-hoc variants.
