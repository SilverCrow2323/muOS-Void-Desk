# QWASAR Desk Frontends — Pygame and LÖVE

## Pygame (recommended)

Pygame is the main and more complete QWASAR Desk frontend.

- Entry point: desk/main.py
- Shared constants and menu metadata: desk/const.py
- Feature panels: desk/hubs/
- Runtime bootstrap: bin/bootstrap_lite.py
- Device launcher: mux_launch.sh

The Pygame UI is the reference implementation for user-visible features and expected behaviour.

### Pygame visual verification

- F12 saves the current composed frame to `data/visual-captures/`.
- `python3 tools/capture_pygame_screenshots.py --all-states` renders all five supported home styles (BLAME, HUD, Terminal, Orbit and NEXUS) and smoke-renders every branch declared in `App.render_state()`.
- CI publishes the generated screenshots and manifest as the `voiddesk-pygame-visual-captures` artifact.

The CI currently renders 103/103 screens (five home styles plus 98 non-home state branches). Direct state rendering does not prove navigation reachability, working actions, controller behaviour or handheld hardware certification.

## LÖVE (experimental)

The LÖVE frontend under love/ is an incomplete prototype. It is included for active development and testing, not as a feature-equivalent production option.

- Entry point: love/main.lua
- Scenes: love/scenes/
- Shared renderer/widgets: love/core/
- Theme palettes: love/theme/
- Python service bridge: love/core/bridge.lua and service/voiddesk_service.py

Some screens exist, but several actions are placeholders or do not yet have a working backend path. The toolbox, workshop, media and repair flows still have incomplete actions. The UI must report unavailable functionality honestly instead of pretending an operation succeeded.

## Known current limitations

### Remaining LÖVE service gaps

These bridge endpoints are not implemented yet:

- muOS app discovery/launch: `list_muos_apps`, `launch_muos_app`
- GitHub release feed: `gh_fetch_releases`
- IPTV playlist and EPG loading: `iptv_load_playlist`, `iptv_load_epg`

A screen can render in CI while its service action remains unavailable. Keep these gaps separate from visual test coverage and report them honestly in the UI.


- LÖVE Toolbox links Calculator and Clock to existing scenes, reads Calendar events from the shared `data/calendar.json` store, and displays live note/text counts from the service. Notes, RSS and Weather remain incomplete.
- THE FORGE uses a process-backed job queue for package installation; arbitrary shell commands are rejected by the service allowlist.
- Shell uses a real nonblocking PTY through the local service (`shell_start`, `shell_poll`, `shell_send`, `shell_kill`).
- External Tools reads the shared `external/tools.json` registry, reports whether each launcher is actually present, and starts only registered launchers. Missing optional submodules are shown as not installed rather than being treated as successful launches.
- Pygame Syncthing discovery now checks the Andromeda storage configuration, defaults to the documented local API port 7070, and never spawns a second daemon on muOS. The service must be enabled in Configuration → Connectivity → Web Services → Syncthing. The panel still needs full device/folder management and hardware validation.
- Rt:Tailscale-M is pinned as a source submodule and its upstream static/UI tests plus 21 QEMU service checks run in CI. Its service is not yet embedded as a native QWASAR Desk feature; the final .muxapp builder must vendor the pinned service files rather than rely on a gitlink.
- Workshop diagnostics, live monitor, logs and cleanup are incomplete.
- Media Library and Radio flows need parity work.
- Desktop repair is a placeholder.
- Some Forge actions call service commands that are not yet implemented.
- Tool-specific UI and confirmation/error states still need validation on handheld hardware.

The Settings screen can change the configured engine. The choice is applied after restarting the application. Use Pygame for normal use; switch to LÖVE only when deliberately testing the prototype.


## Visual styles and palettes

QWASAR separates visual composition from colour palettes. The direction set includes Megastructure, Manga Ink, Industrial, Terminal, Neon Noir and Minimal. Pygame remains the reference UI; LÖVE palette work is in progress and does not yet imply full style or feature parity. Read [Visual Identity](https://github.com/SilverCrow2323/Void-Desk-Project/blob/main/docs/VISUAL_IDENTITY.md).
