# Void Desk LÖVE Frontend — Gap Register

**Scope:** current LÖVE frontend in `love/`, local service in `service/voiddesk_service.py`, and muOS launcher hand-off.
**Baseline:** main at the time of this register; CI run #503 passed the current automated suite.
**Evidence rule:** static source checks and CI captures are not hardware certification. Status below distinguishes implemented code from device validation.

## Current shape

- 10 visible NEXUS destinations: START SESSION, THE FORGE, UPLINK, MEDIA VAULT, WORKSHOP, TOOLBOX, MUOS APPS, SETTINGS, INFO and END NODE.
- 5 additional NEXUS entries are currently hidden: GAMES, DEVELOP, COMMUNITY, OUTERDESK and LEGACY.
- The automated LÖVE capture batch enumerates 25 scenes. It proves scene entry/rendering in CI, not full interaction.
- Global tests check scene-route resolution, visible NEXUS destination resolution and registration of bridge commands used by LÖVE.
- Row-level action tests currently concentrate on Session, Forge, Workshop, Toolbox and MUOS APPS.

## Visible destination register

| NEXUS destination | Current LÖVE scope | Source-verified state | Remaining proof/work |
|---|---|---|---|
| START SESSION | XFCE/IceWM install and launch; boot animation; session hand-off | Scene and service routes exist; launcher hand-off is covered by static tests | Test install, launch, display release, return and cleanup on RG35XX-H |
| THE FORGE | APT manager, XFCE install/launch, package jobs, shell, release lookup | Scene routes exist; bridge calls are registered; CI audits Forge actions | Exercise package operations inside the optional Debian/Ubuntu image; never on muOS host |
| UPLINK | Network status, Tailscale, Syncthing and related connectivity panels | Scene family exists and is included in capture | Audit every selectable action and test daemon ownership, credentials, offline/error states on device |
| MEDIA VAULT | IPTV, external BGM normalizer, Void Radio and local library entries | IPTV and external-tool routes exist; Void Radio now has a LÖVE scene and audio-only service commands | Implement Media Library; validate radio/stream playback and player shutdown on device |
| WORKSHOP | Diagnostics, monitor, APT maintenance and jobs/logs | Routes to Diagnostics, Monitor and APT tabs resolve; scene captures exist | Validate polling remains non-blocking; exercise jobs, cancellation, logs and low-storage cases |
| TOOLBOX | Calculator, clock, editor and file/tool entries | Calculator and clock routes are asserted; scene exists | Audit all remaining rows and keyboard/controller editing behaviour |
| MUOS APPS | Discover applications on supported SD1/SD2 roots and hand off to selected app | Service handlers and dynamic list are present; launcher validates paths in static tests | Test on muOS hardware with real SD1/SD2 layouts, malformed entries and app exit |
| SETTINGS | Theme, display, controls and application preferences | Scene and capture exist | Audit every setting for persistence, validation, reset and rollback |
| INFO | About, manual, controls, manifesto, update check, platform info, logs and credits | Release lookup and system-info routes exist | Replace status-only manual/log actions with real content or label as informational; verify offline release lookup |
| END NODE | Exit/power lifecycle | Built-in NEXUS quit destination | Test clean service shutdown and power-off behaviour on hardware |

## Hidden destinations

These entries exist in the NEXUS catalogue but are hidden and must not be advertised as active LÖVE features until their routes, scenes, capabilities, tests and captures are complete:

- GAMES
- DEVELOP
- COMMUNITY
- OUTERDESK
- LEGACY

## Immediate implementation order

### L0 — close the audit contract

1. Extend row-level assertions to every visible hub, not only selected scenes.
2. Record each action's stable ID, route or bridge command, required capability/dependency, confirmation requirement, error state and test.
3. Verify that unavailable operations are visibly disabled or explain why they cannot run.
4. Keep screenshot capture as a visual regression layer only.

### L1 — MEDIA VAULT

1. Void Radio now has a bounded built-in station catalogue, explicit mpv dependency checks, audio-only play/stop/status and error reporting. The new scene is included in visual capture; CI and device playback validation remain required.
2. Implement Media Library using fixed, validated media roots and a bounded extension allowlist; never accept arbitrary filesystem paths from the frontend.
3. Keep IPTV as its own scene and preserve its existing playlist/EPG/favourites flow.
4. Add/retain service tests, Lua interaction tests where practical, and capture states for empty, loading, playing and unavailable cases.

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
