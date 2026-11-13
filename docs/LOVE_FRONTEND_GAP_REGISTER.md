# Void Desk LÖVE Frontend — Gap Register

**Scope:** current LÖVE frontend in `love/`, local service in `service/voiddesk_service.py`, and muOS launcher hand-off.
**Baseline:** `fix/love-experience-overhaul` (draft PR work, November 13, 2026). CI #774 passed on `cb7d9c64` for compile, tests, packaging and 28 scene captures; manual review invalidated the visual-capture evidence. The new pixel-level capture guard is pending CI.
**Evidence rule:** source checks and automated screenshots are not hardware certification. Status below distinguishes implemented code from device validation.

## Current shape

- 10 visible NEXUS destinations: START SESSION, THE FORGE, UPLINK, MEDIA VAULT, WORKSHOP, TOOLBOX, MUOS APPS, SETTINGS, INFO and END NODE.
- 5 additional NEXUS entries are currently hidden: GAMES, DEVELOP, COMMUNITY, OUTERDESK and LEGACY.
- The automated LÖVE capture batch enumerates 28 scenes, including Notes, Void Radio and Media Library. Manual review of the CI #774 artifact found a capture false positive: onboarding remained above the scene manager, so all 28 screenshots showed the identity screen. The 28/28 count is therefore not accepted as visual proof. A follow-up now disables onboarding only in isolated capture mode and compares decoded 32×24 pixel samples to detect near-identical frames; the new CI run must validate this guard before the visual gate is reopened. Scene captures still prove rendering only, not full interaction.
- Global tests check scene-route resolution, visible NEXUS destination resolution and registration of bridge commands used by LÖVE.
- Row-level action tests currently concentrate on Session, Forge, Workshop, Toolbox and MUOS APPS.

## Visible destination register

| NEXUS destination | Current LÖVE scope | Source-verified state | Remaining proof/work |
|---|---|---|---|
| START SESSION | Dedicated XFCE, IceWM and LXDE cards; supervised install; update checks; confirmed environment removal; launch hand-off | LÖVE cards, service handlers and job overlay are implemented. XFCE removal clearly warns that shared IceWM/LXDE content is also removed | Test free-space failure, install, update simulation, remove, launch, display release, return and cleanup on RG35XX-H |
| THE FORGE | APT manager, XFCE install/launch, package jobs, shell, release lookup | Scene routes exist; bridge calls are registered; CI audits Forge actions | Exercise package operations inside the optional Debian/Ubuntu image; never on muOS host |
| UPLINK | Network status, Tailscale, Syncthing and related connectivity panels | Scene family exists and is included in capture | Audit every selectable action and test daemon ownership, credentials, offline/error states on device |
| MEDIA VAULT | IPTV, Void Radio and local media library | IPTV/Radio and local media service handlers exist. System Tablet can pause, resume, stop and adjust volume for local MPV, radio and IPTV streams | Test player IPC, audio routing, video hand-off, dependency errors and shutdown on hardware; finish media library browsing states |
| WORKSHOP | Diagnostics, monitor, APT maintenance and jobs/logs | Routes to Diagnostics, Monitor and APT tabs resolve; scene captures exist | Validate polling remains non-blocking; exercise jobs, cancellation, logs and low-storage cases |
| TOOLBOX | Calculator, clock, calendar, PTY shell, Python REPL, File-GD X, System Monitor, Diagnostics, local Notes, Syncthing/Tailscale/Uplink shortcuts, muOS Apps, Media Vault and external tools | Notes has bounded local CRUD and a controller-driven on-screen keyboard; Python REPL uses the supervised PTY; native routes are present. The legacy VOID Edit screen is still a prototype, and RSS/Weather/FTP parity is incomplete | Exercise notes save/reopen/delete, text input, REPL, File-GD X hand-off and every cross-hub shortcut on device; finish RSS, Weather, FTP and a persistent general-purpose editor |
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
- RT:Toolbox: new Notes workspace with allowlisted filenames, fixed `data/notes` storage, 32 KB limit, atomic writes and delete confirmation; text input is now routed to the active scene.

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

1. Implement Void Radio with a bounded station catalogue, explicit player dependency checks, play/stop/status and clear error states.
2. Implement Media Library using fixed, validated media roots and a bounded extension allowlist; never accept arbitrary filesystem paths from the frontend.
3. Keep IPTV as its own scene and preserve its existing playlist/EPG/favourites flow.
4. Add service tests, Lua interaction tests where practical, and capture states for empty, loading, playing and unavailable cases.

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
- Automated route/action tests and all 25 scene captures pass.
- The complete controller-driven journeys pass on real RG35XX-H hardware.
- The package keeps Pygame as the reference frontend and treats LÖVE as selectable only after parity for the declared release scope is demonstrated.
