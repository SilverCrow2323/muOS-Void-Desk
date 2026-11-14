# Void Desk LÖVE Frontend — Gap Register

**Scope:** current LÖVE frontend in `love/`, local service in `service/voiddesk_service.py`, and muOS launcher hand-off.
**Baseline:** `fix/love-experience-overhaul` (draft PR work, November 13, 2026). CI #830 passed on `6202e27f` (November 13, 2026): Python 266 tests, repository audit/lint, `.muxapp/.deb`, Lua/LÖVE, 37 scene captures (37/37 visually distinct), Rt:Tailscale-M AArch64 and QEMU (21 passed, 0 failed).
**Evidence rule:** source checks and automated screenshots are not hardware certification. Status below distinguishes implemented code from device validation.

## Current shape

- 10 visible NEXUS destinations: START SESSION, THE FORGE, UPLINK, MEDIA VAULT, WORKSHOP, TOOLBOX, MUOS APPS, SETTINGS, INFO and END NODE.
- 5 additional NEXUS entries are currently hidden: GAMES, DEVELOP, COMMUNITY, OUTERDESK and LEGACY.
- The automated LÖVE capture batch enumerates 37 scenes, including Notes, Signal/RSS, Weather, Void Radio, Media Library, all six System Tablet pages and the operation overlay.
- The shell/REPL scene animates its PTY initialization for 1.4 seconds. CI, the local capture CLI and the LÖVE fallback now wait 1.6 seconds before capture, so the Shell image represents the ready terminal rather than a transient `INITIALIZING PTY` frame. This remains visual evidence, not a device PTY/controller test. CI #830 captured 37/37 scenes with zero failures and verified 37/37 visually distinct 32×24 samples. The runner bypasses onboarding only in isolated capture mode and compares decoded pixels to reject near-identical frames. The #824 artefact was inspected as a contact sheet and at full size: NEXUS, Start Session, Notes, RSS, Weather, six Tablet pages and the operation overlay. RSS, Weather, Notes and Activity use explicitly labelled local demo fixtures in capture mode only; no network fetch or persistent write is performed. Similar pairs remain distinct on full-size review. This verifies rendering, not full interaction or handheld controller behaviour.
- Global tests check scene-route resolution, visible NEXUS destination resolution and registration of bridge commands used by LÖVE.
- Row-level action tests currently concentrate on Session, Forge, Workshop, Toolbox and MUOS APPS.

## Visible destination register

| NEXUS destination | Current LÖVE scope | Source-verified state | Remaining proof/work |
|---|---|---|---|
| START SESSION | Dedicated XFCE, IceWM and LXDE cards; supervised install; update checks; confirmed environment removal; launch hand-off | LÖVE cards, service handlers and job overlay are implemented. XFCE removal clearly warns that shared IceWM/LXDE content is also removed | Test free-space failure, install, update simulation, remove, launch, display release, return and cleanup on RG35XX-H |
| THE FORGE | APT manager, XFCE install/launch, package jobs, shell, release lookup | Scene routes exist; bridge calls are registered; CI audits Forge actions | Exercise package operations inside the optional Debian/Ubuntu image; never on muOS host |
| UPLINK | Network status, Tailscale, Syncthing and related connectivity panels | Scene family exists and is included in capture | Audit every selectable action and test daemon ownership, credentials, offline/error states on device |
| MEDIA VAULT | IPTV, Void Radio and local media library | Radio Browser search/filter/favourites/playback handlers exist; local Media Library browses fixed SD roots with audio/video allowlists, skips symlinks, rejects external paths and launches MPV. Tablet can pause, resume, stop and adjust volume | Finish search and queue/playlist UX; validate empty/error/loading states, player IPC, audio routing, video hand-off and shutdown on hardware |
| WORKSHOP | Diagnostics, monitor, APT maintenance and jobs/logs | Routes to Diagnostics, Monitor and APT tabs resolve; scene captures exist | Validate polling remains non-blocking; exercise jobs, cancellation, logs and low-storage cases |
| TOOLBOX | Calculator, clock, calendar, PTY shell, Python REPL, File-GD X, System Monitor, Diagnostics, Notes, persistent VOID Edit, RSS, Weather, Syncthing/Tailscale/Uplink shortcuts, muOS Apps, Media Vault and external tools | Notes has bounded local CRUD; VOID Edit reads/writes allowlisted files in data/Texts with 128 KB cap, symlink/path protection, atomic save and controller OSK; RSS and Weather use supervised refresh jobs and bounded HTTPS/cache adapters; Python REPL uses supervised PTY | Verify first-run controller input, Notes/VOID Edit save/reopen/delete, RSS and Weather offline/refresh behavior, REPL, File-GD X and all cross-hub shortcuts on RG35XX-H; implement secure FTP/SFTP parity |
| MUOS APPS | Discover applications on supported SD1/SD2 roots and hand off to selected app | Service handlers and dynamic list are present; launcher validates paths in static tests | Test on muOS hardware with real SD1/SD2 layouts, malformed entries and app exit |
| SETTINGS | Theme, display, controls and application preferences | Scene and capture exist | Audit every setting for persistence, validation, reset and rollback |
| INFO | About, manual, controls, manifesto, update check, platform info, logs and credits | Release lookup and system-info routes exist | Replace status-only manual/log actions with real content or label as informational; verify offline release lookup |
| END NODE | Exit/power lifecycle | Built-in NEXUS quit destination | Test clean service shutdown and power-off behaviour on hardware |

## Recent implementation tranche (draft; not hardware-certified)

- First-boot identity: mandatory only when no completed profile exists; migrates a non-placeholder Pygame `termid_name` atomically so existing users are not prompted twice.
- Global System Tablet: overview, processes, system, network, media and activity pages; live job telemetry; media/radio/IPTV actions.
- Supervised operation overlay: operation name/icon, purpose, reason, phase, progress, recent log output and background/foreground handling.
- XFCE bootstrap: removes the competing `fbtext` framebuffer UI, publishes English structured progress, and reports storage/network/asset failures in the LÖVE overlay.
- Start Session: separate visual environment cards, dependency-aware IceWM/LXDE install, confirmed removal, update simulation and job tracking.
- NEXUS: wider orbit spacing within safe screen margins and hard three-tone cel-shaded planet lighting with ink outlines and directional highlights.
- RT:Toolbox: Notes and VOID Edit now have separate file stores and native LÖVE editors. Notes uses `data/notes` and 32 KB limits; VOID Edit reads/writes allowlisted text types in `data/Texts` with a 128 KB limit, path/symlink validation and atomic saves. Both support controller input and an on-screen keyboard; physical keyboard input is routed to the active scene.
- RT:Toolbox: RSS and Weather now have allowlisted HTTPS feeds/Open-Meteo adapters, bounded caches, supervised refresh jobs and visible progress; test their offline and network refresh behavior on device.

These changes are implemented on the draft branch only. Passing source tests or screenshots does not establish that they work correctly on RG35XX-H hardware.

## Hidden destinations

These entries exist in the NEXUS catalogue but are hidden and must not be advertised as active LÖVE features until their routes, scenes, capabilities, tests and captures are complete:

- GAMES
- DEVELOP
- COMMUNITY
- OUTERDESK
- LEGACY

## Immediate implementation order

### L0 — close the audit contract

1. Extend row-level assertions to every visible hub, not only selected scenes. This tranche adds route, service-handler and Notes CRUD checks; it does not yet cover every individual controller journey.
2. Record each action's stable ID, route or bridge command, required capability/dependency, confirmation requirement, error state and test.
3. Verify that unavailable operations are visibly disabled or explain why they cannot run.
4. Keep screenshot capture as a visual regression layer only.

### L1 — MEDIA VAULT

1. Void Radio is implemented with Radio Browser search, category/country filters, persistent favourites, playback and pause/volume/stop controls; finish network-error and device interaction validation.
2. Media Library already uses fixed `/mnt/mmc` and `/mnt/sdcard` roots, an audio/video extension allowlist, path/symlink guards and MPV playback. Complete local search plus queue/playlist controls and the remaining controller-driven browse/play states.
3. Keep IPTV as its own scene and preserve its existing playlist/EPG/favourites flow.
4. Extend service and scene tests for empty roots, missing mounts, media errors, queue operations and audio/video hand-off.

### L2 — finish each visible hub

Complete UPLINK, SETTINGS, TOOLBOX and INFO row-by-row. Do not count a row as complete merely because it has an action callback; verify the destination or service result.

### L3 — device validation

On the RG35XX-H / H700 running the target muOS release, validate:

- 640x480 layout, safe margins, clipping, focus and text input;
- D-pad, A/B/X/Y, L1/R1, Start/Select, repeat and back behaviour;
- SD1/SD2 discovery and bounded filesystem operations;
- Wi-Fi, Bluetooth, Tailscale and Syncthing availability/error states;
- XFCE image install, APT operations, session hand-off and return;
- IPTV/radio playback, audio controls and player shutdown;
- service startup, timeout, crash recovery, exit and power-off.

Only after the RG35XX-H baseline passes should other H700 models or firmwares be promoted to supported targets.

## Release gate

LÖVE is release-ready only when all of the following are true:

- Every visible NEXUS node resolves to a real feature or a documented built-in lifecycle action.
- Every visible row has a working destination or an explicit unavailable state; no "soon" placeholder remains.
- Every bridge command is registered, typed, bounded and covered by a service test.
- All destructive or privileged actions have confirmation and honest result reporting.
- Automated route/action tests and all 37 scene captures pass.
- The complete controller-driven journeys pass on real RG35XX-H hardware.
- The package keeps Pygame as the reference frontend and treats LÖVE as selectable only after parity for the declared release scope is demonstrated.
