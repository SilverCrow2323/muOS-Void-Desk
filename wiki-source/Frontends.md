# Frontends — Pygame and LÖVE

## Pygame (recommended)

Pygame is the main and more complete VoidDesk frontend.

- Entry point: desk/main.py
- Shared constants and menu metadata: desk/const.py
- Feature panels: desk/hubs/
- Runtime bootstrap: bin/bootstrap_lite.py
- Device launcher: mux_launch.sh

The Pygame UI is the reference implementation for user-visible features and expected behaviour.

### Pygame visual verification

- F12 saves the current composed frame to `data/visual-captures/`.
- `python3 tools/capture_pygame_screenshots.py` smoke-renders all five supported home styles (BLAME, HUD, Terminal, Orbit and NEXUS).
- CI publishes the generated screenshots and manifest as the `voiddesk-pygame-visual-captures` artifact.

The automated Pygame pass currently covers the home presentation variants only. It must not be interpreted as full hub/action coverage or handheld hardware certification.

## LÖVE (experimental)

The LÖVE frontend under love/ is an incomplete prototype. It is included for active development and testing, not as a feature-equivalent production option.

- Entry point: love/main.lua
- Scenes: love/scenes/
- Shared renderer/widgets: love/core/
- Theme palettes: love/theme/
- Python service bridge: love/core/bridge.lua and service/voiddesk_service.py

Some screens exist, but several actions are placeholders or do not yet have a working backend path. The toolbox, workshop, media and repair flows still have incomplete actions. The UI must report unavailable functionality honestly instead of pretending an operation succeeded.

## Known current limitations

- LÖVE Toolbox links Calculator and Clock to existing scenes, reads Calendar events from the shared `data/calendar.json` store, and displays live note/text counts from the service. Notes, RSS and Weather remain incomplete.
- THE FORGE uses a process-backed job queue for package installation; arbitrary shell commands are rejected by the service allowlist.
- Shell uses a real nonblocking PTY through the local service (`shell_start`, `shell_poll`, `shell_send`, `shell_kill`).
- External Tools reads the shared `external/tools.json` registry, reports whether each launcher is actually present, and starts only registered launchers. Missing optional submodules are shown as not installed rather than being treated as successful launches.
- Workshop diagnostics, live monitor, logs and cleanup are incomplete.
- Media Library and Radio flows need parity work.
- Desktop repair is a placeholder.
- Some Forge actions call service commands that are not yet implemented.
- Tool-specific UI and confirmation/error states still need validation on handheld hardware.

The Settings screen can change the configured engine. The choice is applied after restarting the application. Use Pygame for normal use; switch to LÖVE only when deliberately testing the prototype.
