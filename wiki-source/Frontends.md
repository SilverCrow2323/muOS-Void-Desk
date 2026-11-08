# Frontends — Pygame and LÖVE

## Pygame (recommended)

Pygame is the main and more complete VoidDesk frontend.

- Entry point: desk/main.py
- Shared constants and menu metadata: desk/const.py
- Feature panels: desk/hubs/
- Runtime bootstrap: bin/bootstrap_lite.py
- Device launcher: mux_launch.sh

The Pygame UI is the reference implementation for user-visible features and expected behaviour.

## LÖVE (experimental)

The LÖVE frontend under love/ is an incomplete prototype. It is included for active development and testing, not as a feature-equivalent production option.

- Entry point: love/main.lua
- Scenes: love/scenes/
- Shared renderer/widgets: love/core/
- Theme palettes: love/theme/
- Python service bridge: love/core/bridge.lua and service/voiddesk_service.py

Some screens exist, but several actions are placeholders or do not yet have a working backend path. The toolbox, workshop, media and repair flows still have incomplete actions. The UI must report unavailable functionality honestly instead of pretending an operation succeeded.

## Known current limitations

- Toolbox utilities such as Notes, RSS and Weather are not all implemented in LÖVE.
- Workshop diagnostics, live monitor, logs and cleanup are incomplete.
- Media Library and Radio flows need parity work.
- Desktop repair is a placeholder.
- Some Forge actions call service commands that are not yet implemented.
- Tool-specific UI and confirmation/error states still need validation on handheld hardware.

The Settings screen can change the configured engine. The choice is applied after restarting the application. Use Pygame for normal use; switch to LÖVE only when deliberately testing the prototype.
