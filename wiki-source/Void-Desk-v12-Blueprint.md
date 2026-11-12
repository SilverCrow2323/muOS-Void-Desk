![Void Desk field manual](assets/voiddesk-docs-banner.svg)

# 🪐 Void Desk v12 — product blueprint

> [!IMPORTANT]
> This page describes the **target architecture** for v12. It is not a feature list for the current downloadable package. Current implementation status remains documented in [Frontends](Frontends) and [Release testing](Release-testing).

## The NEXUS destination map

![NEXUS v12 proposed navigation](assets/nexus-v12-navigation.svg)

| Destination | Role | Main content |
|---|---|---|
| **START SESSION** | Launch a standalone environment | Desktop sessions, terminal sessions, PC/VM hand-off where supported |
| **THE FORGE** | Build and maintain software | Packages, runtimes, Void Desk builds, verified modules |
| **UPLINK** | Connectivity and remote operations | Network Probe, BaseStation, Tailscale, Syncthing, FTP |
| **MEDIA VAULT** | Media experience | Local library, radio, IPTV, playlists and playback |
| **RT:WORKSHOP** | System tools and maintenance | Two satellites: SYSTEMS and TOOLS |
| **SETTINGS** | Device and QWASAR cockpit | General, Appearance, Controls, Display, Connectivity, Identity, Device/OS, QWASAR, Privacy |
| **MUOS APPS** | Native application hand-off | Discovery and validated launch of installed muOS applications |
| **END NODE** | Exit and recovery | Close, restart, reboot and power-off flows |

### RT:WORKSHOP — two satellites

<details>
<summary>🛰️ SYSTEMS — device health</summary>

- Device and OS diagnostics
- CPU, temperature, memory and storage status
- Logs, support bundles and maintenance history
- Safe cleanup, backup and repair operations

</details>

<details>
<summary>🛰️ TOOLS — user utilities</summary>

- RT:Shell and isolated Python execution
- Calculator, clock, calendar and notes
- File operations and developer utilities
- QWASAR Inspector and Switchboard when implemented

</details>

## UPLINK becomes one coherent control room

![QWASAR-Env system map](assets/qwasar-system-map.svg)

Network Probe belongs to UPLINK and presents a structured, timestamped diagnostic report: interfaces, routes, DNS, gateway, connectivity tests, performance, Tailnet and services. Each value must show whether it is detected, unavailable, stale or not tested; the UI must not invent missing telemetry.

BaseStation unifies the PC companion and local file bridge into one screen, but keeps their health states separate. A running file bridge must not be presented as proof that a PC client is connected. Syncthing gets its own dedicated screen and uses the existing host service; Void Desk must not start a second daemon.

## Global operation overlay

Long-running tasks share one job presentation:

1. Queued / preparing
2. Running, with a real progress value when available
3. Current phase and elapsed time
4. Expandable log output
5. Completed, failed or cancelled outcome
6. Retry or open report where safe

An indeterminate operation must use an indeterminate progress treatment, not a fabricated percentage. Cancellation is shown only when the backend can actually stop the operation.

## Settings cockpit

| Area | Responsibilities |
|---|---|
| General | Language, startup and interaction defaults |
| Appearance | Style, palette, typography, effects and reduced motion |
| Controls & Input | Semantic bindings, release/device profiles and calibration |
| Display & Performance | Resolution, scaling, frame budget and low-power mode |
| Connectivity | Network integrations and service policy |
| Identity | Local username/avatar and non-secret Device ID |
| Device & OS | Detected model, firmware, profile confidence and diagnostics |
| QWASAR | Profile, module and ecosystem preferences |
| Privacy & Security | Pairing, permissions, exported-data review and revocation |
| Documentation | Manual, changelog, credits and about |

A stable local Device ID is not a credential. Pairing tokens must be separate, revocable, short-lived and excluded from screenshots and public QR codes.

## Architecture rules

- One capability/service API is the authority for each host function; frontends are adapters, not duplicate implementations.
- The UI remains responsive: slow commands run as jobs, never in the render/input loop.
- Python scripts run outside the frontend process with timeout, output limits and process controls. Process separation alone is **not** a security sandbox.
- RT:Shell is a PTY utility; it does not inherently require XFCE or a desktop window manager.
- The official muOS application lifecycle remains the entry/exit boundary. Deeper integration must be reversible and recoverable.
- Do not remove legacy code or assets until static references, dynamic loading and packaged runtime usage have been audited.

## Delivery gates

| Stage | Focus | Exit condition |
|---|---|---|
| M0 | Docs, contracts and platform detection | Explicit release/device/controller identity and tests |
| M1 | Service and lifecycle stability | No known frontend-blocking host operation |
| M2 | NEXUS and operation overlay | Navigation and job outcomes verified end to end |
| M3 | UPLINK and RT:WORKSHOP | Services, diagnostics and failure states covered |
| M4 | Settings, identity and documentation | Safe persistence, pairing boundaries and readable UI |
| M5 | Frontend convergence and cleanup | Shared contracts, audited dead-code/assets removal |
| M6 | Release qualification | Package install/upgrade/rollback and physical H700 test matrix |

> [!TIP]
> Keep this page as a decision record. When the implementation changes, update the status and link the commit/PR that proves it; do not silently turn a roadmap sentence into a claim of availability.
