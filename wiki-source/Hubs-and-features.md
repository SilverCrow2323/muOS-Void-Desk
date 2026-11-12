# 🧭 Hubs and features

NEXUS is the main entry point to Void Desk. The current source tree contains several legacy hub names and routes; the v12 proposal reorganises those responsibilities without silently claiming that the new interface has shipped.

> [!NOTE]
> Tool availability depends on the frontend, firmware, installed dependencies, hardware and permissions. A visible menu item or a rendered screenshot is not proof that its action works.

## Current source inventory

| Existing area | Responsibilities found in the repository | Reality check |
|---|---|---|
| START SESSION | Optional desktop and terminal/session hand-off | Depends on device storage and available session images |
| THE FORGE | Package and component maintenance | Operations must be capability-checked and reported accurately |
| UPLINK | Wireless, network, remote access and sync entry points | Not every integration is enabled on every firmware |
| MEDIA VAULT | Radio, IPTV and media-related tools | Individual media paths have separate implementation status |
| WORKSHOP | Device checks, logs, storage and maintenance | Some engine actions remain incomplete |
| RT:TOOLBOX | Everyday tools, shell and utilities | Tool coverage differs across frontends |
| MUOS APPS | Discover and hand off to installed muOS apps | Requires valid app roots and launcher metadata |
| SETTINGS | Appearance, controls and app configuration | Some advanced categories are part of the v12 plan |
| INFO / ABOUT | Project and update information | Being folded into Settings / Documentation in the v12 proposal |
| END SESSION | Exit, return and power actions | Device power behaviour requires physical tests |

## Proposed v12 workspaces

![Proposed NEXUS structure](assets/nexus-v12-navigation.svg)

| Destination | Role |
|---|---|
| **START SESSION** | Desktop environments, terminal sessions and supported workspace hand-off |
| **THE FORGE** | Packages, runtimes, updates and registered modules |
| **UPLINK** | Network Probe, BaseStation, PC companion, Tailscale, Syncthing and FTP |
| **MEDIA VAULT** | Playback, library, radio, IPTV and playlists |
| **RT:WORKSHOP** | One maintenance/create area with SYSTEMS and TOOLS satellites |
| **SETTINGS** | General, appearance, controls, connectivity, identity, device/OS, QWASAR and privacy |
| **MUOS APPS** | Discover and launch native muOS applications |
| **END NODE** | Close, return, restart, reboot and safe power-off flows |

### RT:WORKSHOP satellites

- **SYSTEMS:** device health, temperature, storage, logs, backups and diagnostics.
- **TOOLS:** shell, Python executor, calculator, clock, calendar, notes and developer utilities.

### UPLINK sub-screens

- **BaseStation:** a unified panel with separate state for PC companion and local file-bridge services.
- **Network Probe:** scrollable diagnostic report with interfaces, routes, DNS, performance, tailnet and service state.
- **Syncthing:** dedicated themed device/folder screen using the existing host service rather than spawning a duplicate daemon.
- **Tailscale:** dedicated service view with explicit login, peers and action status.

## Source-grounded catalog

The deeper tool inventory and module taxonomy live in [docs/TOOL_CATALOG.md](https://github.com/SilverCrow2323/Void-Desk-Project/blob/main/docs/TOOL_CATALOG.md). The v12 target and release gates are in [docs/V12_BLUEPRINT.md](https://github.com/SilverCrow2323/Void-Desk-Project/blob/main/docs/V12_BLUEPRINT.md).
