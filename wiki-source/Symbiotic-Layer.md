# Symbiotic Layer — QWASAR Desk and muOS

## Vision

QWASAR Desk (formerly Void Desk) aims to grow from a launched application into a deeply integrated handheld environment. "Symbiotic Layer" is the technical name for that direction: QWASAR should use and extend the host firmware through supported interfaces while leaving its native boot and recovery mechanisms intact.

This is an architectural roadmap, not a claim that QWASAR currently replaces the muOS frontend or firmware.

## Current host boundary

The current target is MustardOS / muOS 2606.0 Andromeda on compatible H700 hardware. QWASAR is packaged and launched as a normal muOS application.

MustardOS documents a standard Application Runner. It prepares the CPU governor, SDL environment, HOME directory, SD1/SD2-aware storage, foreground process tracking and cleanup. Its launcher metadata is parsed by the native frontend.

Developer references:
- [Application Runner](https://community.muos.dev/t/application-runner/1282)
- [Extending MustardOS](https://muos.dev/docs/infrastructure/extending)
- [Frontend and Launching](https://muos.dev/docs/infrastructure/launching)
- [Boot and Services](https://muos.dev/docs/infrastructure/boot)

## Integration rules

1. Keep the official application runner as the entry and exit boundary.
2. Use the documented shared helper functions and setup flow; do not remove the shared function library.
3. Use the bind-mounted runtime application path where provided; do not hardcode SD1 or SD2 mount paths.
4. Keep QWASAR state namespaced and separate from muOS-owned configuration.
5. Use atomic writes, migrations and backups for persistent files.
6. Own every service QWASAR starts and stop it cleanly on exit, power-off and failure.
7. Prefer documented manifests, themes, launcher metadata, task scripts and Web Dashboard APIs over patching native binaries.
8. Keep local service listeners loopback-only unless a separately reviewed, authenticated interface is deliberately enabled.
9. Do not spawn a second instance of a host service that is already running.
10. Every deeper integration needs an uninstall and recovery path.

## Integration levels

| Level | Goal | Status |
|---|---|---|
| 0 — App | QWASAR runs as a normal muOS application | Current baseline |
| 1 — Services | QWASAR-managed services have health checks and clean lifecycle | In progress |
| 2 — Capabilities | One typed API for device, network, storage and media features | Planned |
| 3 — Experience | Optional QWASAR navigation, profiles, themes and dashboards | Planned |
| 4 — Ecosystem | KNULLI, ROCKNIX and custom platform adapters | Planned; no blanket support claim |
| 5 — Deep integration | User-selected integration through documented reversible hooks | Research only |

## What deeper integration does not mean

- No bootloader replacement.
- No destructive init-script changes.
- No patching protected muOS frontend binaries as a shortcut.
- No disabling firmware recovery or safe-mode mechanisms.
- No overwriting firmware-owned data without explicit user approval.
- No hidden dependency that prevents muOS from launching when QWASAR fails.

The native muOS frontend must remain available. Users must be able to disable or uninstall QWASAR and return to a normal host experience.

## Recovery contract

Before a deeper integration is enabled, QWASAR must be able to back up the affected state, stage the change, health-check it, roll back a failed activation, and remove only QWASAR-owned files/services. Every supported device/firmware combination needs install, update, rollback and uninstall evidence.

## Roadmap

- Stabilise the current Pygame application and service lifecycle.
- Complete the capability inventory and service adapters.
- Share tool and capability metadata across Pygame, LÖVE and Studio.
- Add optional, profile-driven navigation and visual customisation.
- Pair Studio securely with a device for opt-in profile sync.
- Add platform adapters only after firmware-specific research and hardware testing.
