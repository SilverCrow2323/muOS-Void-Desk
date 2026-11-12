# 🧬 Symbiotic Layer — Void Desk and muOS

## The idea

The **Symbiotic Layer** is the long-term integration model for Void Desk: richer system capabilities and a custom handheld experience built around the host firmware, without taking control away from the firmware itself.

It is an architecture direction, not a claim that Void Desk currently replaces the muOS frontend or firmware.

![QWASAR-Env system boundaries](assets/qwasar-system-map.svg)

## Host boundary

The current target is MustardOS / muOS **2606.0 Andromeda** on compatible H700 devices. Void Desk is installed and launched as a normal muOS application through the supported application lifecycle.

The official developer references describe the application runner, launching and extension mechanisms:

- [Application Runner](https://community.muos.dev/t/application-runner/1282)
- [Extending MustardOS](https://muos.dev/docs/infrastructure/extending)
- [Frontend and Launching](https://muos.dev/docs/infrastructure/launching)

## Integration principles

1. Preserve the official app runner and its startup/cleanup lifecycle.
2. Use resolved runtime paths where the host provides them; avoid hard-coded SD mount assumptions.
3. Keep QWASAR state namespaced and separate from firmware-owned configuration.
4. Use atomic writes, migrations and backups for persistent state.
5. Give every service one clear owner and stop it cleanly on exit/failure.
6. Do not spawn a duplicate instance of a host service that is already active.
7. Keep privileged listeners local by default; remote pairing requires a separate authenticated design.
8. Require backup, rollback and uninstall paths for deeper integration.

## Integration levels

| Level | Goal | Status |
|---|---|---|
| 0 — Application | Launch as a normal muOS application | Current baseline |
| 1 — Services | QWASAR-owned services with lifecycle and health checks | In progress |
| 2 — Capabilities | Typed APIs for device, network, storage and media | Planned / partial |
| 3 — Experience | NEXUS, profiles, themes and global panels | Partial / in progress |
| 4 — Ecosystem | KNULLI, ROCKNIX and other adapters | Planned; no blanket support claim |
| 5 — Deeper integration | Optional, reversible hooks | Research only |

## What it does not mean

- No bootloader replacement.
- No destructive init-script changes.
- No protected firmware binary patching as a shortcut.
- No disabling native firmware recovery or safe mode.
- No mandatory cloud dependency for normal handheld launch.
- No host mutation without explicit user-facing status and rollback.

> [!CAUTION]
> The device must remain bootable and recoverable when Void Desk is disabled, uninstalled or fails to start.

## Recovery contract

Before deeper integration is enabled, the system must back up affected state, stage the change, health-check it, roll back a failed activation and remove only QWASAR-owned files/services. Each claimed device/firmware combination needs install, update, rollback and uninstall evidence.

For the detailed v12 target, see [docs/V12_BLUEPRINT.md](https://github.com/SilverCrow2323/Void-Desk-Project/blob/main/docs/V12_BLUEPRINT.md).
