# Void Desk — Symbiotic Layer

**Product identity:** Void Desk, the classic handheld application in QWASAR-Env  
**Current implementation:** a muOS-launched application with Pygame as the reference frontend and LÖVE as an experimental frontend.  
**Long-term direction:** a deeply integrated handheld environment that remains reversible and respects the host firmware.

## Product principle

Void Desk should feel like an environment growing inside the handheld, not an unrelated app. The "symbiosis" is architectural: Void Desk reuses host facilities, contributes its own tools and presentation layer, and returns control cleanly to the original firmware.

The metaphor of parasitizing muOS describes the ambition to integrate deeply. It is not a technical instruction to compromise the host. QWASAR must never make the device unbootable, hide recovery paths, or require destructive system patches.

## Supported integration boundary

The current target is MustardOS / muOS 2606.0 Andromeda on compatible H700 handhelds. The following are documented integration points and must be verified on each supported firmware/device pair.

### Application lifecycle

Use the official muOS application runner, not a parallel launcher that bypasses it. The runner is responsible for CPU governor handling, SDL environment, HOME assignment, SD1/SD2-aware storage mounting, foreground process tracking and cleanup. Its launcher metadata is also parsed by the frontend.

Developer reference: https://community.muos.dev/t/application-runner/1282

Implementation rules:
- Keep the shared `/opt/muos/script/var/func.sh` integration where required by the runner.
- Use `GET_VAR` / `SET_VAR` and `SETUP_APP` for the documented application setup flow.
- Set stable launcher metadata (`HELP`, `ICON`, `GRID`) and provide language metadata where appropriate.
- Use the runtime bind-mounted application path `/run/muos/storage/application/<app>`; never hardcode `/mnt/mmc` or `/mnt/sdcard` where the runner provides a resolved path.
- Restore temporary environment changes and release foreground/session resources on every exit path.
- Keep session hand-off in the launcher lifecycle so the frontend releases the display before a desktop session starts.

### Storage and state

MustardOS documents three distinct location classes:
- `/run/muos`: transient coordination/runtime state; cleared on restart.
- `MUOS`: persistent user choices, saves and content on selected storage.
- `/opt/muos`: read-only firmware resources and programs.

QWASAR-owned data must be clearly namespaced and must not overwrite firmware-owned state. Persistent writes should be atomic, validate input and retain backups for migrations. Never assume SD1-only storage.

### Services and capabilities

QWASAR-managed services must have:
- explicit start/stop ownership and bounded shutdown;
- health/status reporting and useful logs;
- narrow typed operations instead of arbitrary shell passthrough;
- loopback-only local listeners by default;
- explicit permission and confirmation for changes to network, package, mount, power or user files;
- startup failure isolation so the NEXUS UI and muOS remain usable.

Prefer existing muOS Web Services and supported APIs where they provide the needed capability. Do not launch duplicate daemons (for example, Syncthing or Tailscale) when the host service is already active.

### Themes and frontend extensions

Explore data-driven integration first: stable IDs, manifests, launcher metadata, glyphs, language files, themes and optional overlay hooks. QWASAR-specific artwork must remain separate from muOS-owned theme files unless the user explicitly installs an integration package.

MustardOS documents manifests, theme packages, external software launchers, task scripts and the Web Dashboard API as extension paths. They are preferred over direct frontend binary patches.

Developer reference: https://muos.dev/docs/infrastructure/extending

## Integration levels

| Level | Description | Status |
|---|---|---|
| 0 — App | QWASAR launches as a normal muOS application | Current baseline |
| 1 — Services | QWASAR-owned services and host-service adapters with clean lifecycle | In progress |
| 2 — Capabilities | One typed device API shared by Pygame, LÖVE and Studio | Planned |
| 3 — Experience | Optional QWASAR home, profiles, themes and cross-tool navigation | Planned |
| 4 — Ecosystem | Platform adapters for KNULLI, ROCKNIX and custom firmware | Planned; no blanket support claim |
| 5 — Deep integration | Optional user-selected integration through documented host extension points | Research only |

## Recovery and uninstall contract

Every deeper integration must include:
1. A pre-change backup and a manifest of files owned by QWASAR.
2. A staged update that validates before activation.
3. A way to disable QWASAR integration and return to the native muOS frontend.
4. An uninstall path that removes only QWASAR-owned files and services.
5. A rollback path when startup health checks fail.
6. A clear report of what cannot be reverted automatically.

Do not modify bootloader partitions, replace init scripts, patch protected frontend binaries, or overwrite firmware configuration as a shortcut. Do not disable muOS safe-mode or recovery behaviour. No deeper takeover is approved until an official, reversible integration route is documented and tested.

## Milestones

### Phase A — reliable application
- Preserve the official muOS runner lifecycle.
- Fix session/service cleanup and storage path assumptions.
- Keep Pygame as reference and LÖVE clearly marked experimental.

### Phase B — capability layer
- Inventory each host operation and its privilege.
- Add capability IDs, availability checks and typed service handlers.
- Share capability snapshots across frontends to avoid duplicate polling.

### Phase C — QWASAR experience
- Introduce menu/profile registry and theme adapters.
- Permit optional home/navigation customisation while preserving native muOS access.
- Add recovery-mode entry and safe defaults.

### Phase D — Studio and ecosystem
- Sync portable profiles with explicit pairing.
- Ship official signed plugins only.
- Add KNULLI/ROCKNIX/custom adapters one at a time with hardware evidence.

## Acceptance criteria for deeper integration

- A failed QWASAR launch returns to the native host without reboot loops.
- Removing QWASAR restores the original app launcher path.
- No QWASAR service binds to an untrusted interface by default.
- No profile, theme or plugin import can run arbitrary host commands.
- SD1/SD2 layouts are handled without hardcoded storage assumptions.
- Every supported device/firmware combination has installation, update, rollback and uninstall test evidence.
