# VoidDesk architecture

This note maps the source tree and main runtime paths. It does not imply that every optional integration is available on every firmware.

## Runtime overview

On the handheld, mux_launch.sh is the package entry point. It loads muOS launcher helpers, establishes the application environment, starts service/voiddesk_service.py and runs the selected frontend.

~~~text
muOS Apps
   |
   v
mux_launch.sh
   |-- local Python service (service/voiddesk_service.py)
   |
   |-- engine = py   -> desk/main.py + runtime/ (Pygame wheel)
   |
   '-- engine = love -> lib/love love/
           |
           '-- session hand-off -> bin/xfce_launch.sh
                                  -> return to VoidDesk
~~~

The launcher re-reads the configured engine before each run. If the Pygame runtime is not ready, it calls bin/bootstrap_lite.py. If setup or the Pygame frontend fails, the launcher falls back to LÖVE and records the event in data/voiddesk.log.

The PC launcher, voiddesk.py, is a separate development convenience. It checks for a system LÖVE binary on PC and can create .venv_desktop for the Pygame path. It is not the handheld package entry point.

## Main subsystems

| Path | Responsibility |
|---|---|
| desk/main.py | Python/Pygame application, state and rendering |
| desk/const.py | Shared dimensions, palettes, menu metadata and version |
| desk/hubs/ | Feature-specific panels and hub actions |
| desk/utils/ | Atomic I/O, cache/performance helpers, safe calculation and archive extraction |
| love/main.lua | LÖVE frontend entry point |
| love/core/ | Layout, input, scenes, jobs, notifications, shell bridge, widgets and rendering |
| love/scenes/ | Individual hub and tool screens |
| love/theme/ | Theme palettes and loading |
| service/voiddesk_service.py | Local HTTP/service bridge and background tasks |
| service/iptv_module.py | IPTV-related service integration |
| outdesk/ | Standalone applications and optional integrations |
| voidcast_addons/ | Add-ons for VoidCast |
| bin/ | Bootstrap, desktop launch, diagnostics and platform scripts |
| assets/, resources/ | Fonts, audio, glyphs, artwork and UI assets |

## Configuration and generated state

data/desk_config.json is the main user configuration. The app merges defaults in code with this file, allowing new settings without rewriting every existing config.

Generated paths that should not be committed:
- runtime/: unpacked Pygame wheel.
- data/.pygame_ready: runtime-ready marker.
- data/pygame.whl and partial download: temporary wheel download.
- data/logs/ and data/voiddesk.log: diagnostics.
- data/xfce.img and data/xfce_mnt/: optional desktop image and mount point.

## Engine boundaries

### Pygame

The device bootstrap discovers a compatible manylinux wheel from PyPI. It verifies the wheel's SHA-256 digest from PyPI metadata, checks ZIP entries before extraction, extracts to a staging directory and verifies import pygame before replacing runtime/. A failed validation should leave the previous runtime available.

### LÖVE

The handheld package includes lib/love and the project under love/. The PC launcher prefers a system love executable because the bundled binary is target-architecture-specific. LÖVE syntax is validated in CI with LuaJIT.

## Service and hand-off

The local service provides the bridge used by frontends for system information, network state, media state, jobs and desktop session actions. The launcher uses data/.pending_session as a hand-off marker: the frontend exits, the shell launcher starts the requested session after the display has been released, and VoidDesk is launched again when that session ends.

Treat the service and any local web/file integrations as privileged surfaces. Do not expose them to untrusted networks.

## Extension points

- Add a Python panel under desk/hubs/ and connect it through the hub/menu router.
- Add a LÖVE scene under love/scenes/ and register it with the scene/menu system.
- Add a VoidCast add-on under its add-on directory with a matching metadata file.
- Keep optional external programs behind dependency checks and show clear diagnostics when unavailable.

Before adding a cross-engine feature, decide whether it belongs in both frontends or is intentionally engine-specific. Document that choice and test shared logic where feasible.
