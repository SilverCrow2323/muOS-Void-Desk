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

The launcher re-reads the configured engine before each run. If the Pygame runtime is not ready, it calls bin/bootstrap_lite.py. Pygame is the recommended, more complete frontend. If the Pygame process fails, the launcher can start LÖVE as an emergency fallback; that fallback is an experimental, incomplete prototype and is not feature-equivalent.

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

### LÖVE (experimental)

The handheld package includes lib/love and the project under love/. The PC launcher prefers a system love executable because the bundled binary is target-architecture-specific. LÖVE is incomplete and is not yet at Pygame feature parity. Some routes and actions are still placeholders; keep it opt-in for development and testing. CI validates Lua syntax with LuaJIT and selected core behaviour with focused tests.

## LÖVE-to-Python service bridge

The LÖVE bridge serializes requests through the single request/response file pair: only one request is published at a time, each response is matched by request ID, and the service claims requests with an atomic rename before writing an atomic response. This avoids overwriting simultaneous requests on SD filesystems.

## Non-blocking host status

The Pygame frontend reads header indicators through `App.status_snapshot()`. This method is a cache read only. A `StatusPoller` worker refreshes battery, Wi-Fi, Bluetooth, volume, USB and hotspot state at a bounded interval. Slow commands such as `hciconfig` and `bluetoothctl show` therefore cannot suspend the NEXUS render/input loop. Only one refresh is allowed at a time; a failed probe leaves the last known snapshot available and permits a later retry.

## Device power-off sequence

For the muOS package launcher, the Pygame frontend writes `data/.pending_poweroff` and exits normally. The shell launcher detects the marker, stops and waits for `service/voiddesk_service.py`, synchronizes filesystem writes, and invokes the forced power-off command with fallbacks. This avoids leaving the VoidDesk companion service running while the system is asked to power down.

The direct power-off fallback in the standalone/PC path is separate from the device hand-off. Neither path can be certified by headless CI; final behaviour must be checked on the target hardware.

## Service and hand-off

The local service provides the bridge used by frontends for system information, network state, media state, jobs and desktop session actions. The launcher uses data/.pending_session as a hand-off marker: the frontend exits, the shell launcher starts the requested session after the display has been released, and VoidDesk is launched again when that session ends.

Treat the service and any local web/file integrations as privileged surfaces. Do not expose them to untrusted networks.

## Visual capture and asset inventory

Both frontends support F12 screenshot capture. PNG images and JSON metadata are saved locally under data/visual-captures/. The dependency-free tools/visual_capture.py script indexes captures, scans images and fonts, records file dimensions and SHA-256 hashes, and checks that active LÖVE NEXUS nodes have their referenced textures. Captures are excluded from Git by default; review them for private network and device information before exporting selected images.

## Extension points

- Add a Python panel under desk/hubs/ and connect it through the hub/menu router.
- Add a LÖVE scene under love/scenes/ and register it with the scene/menu system.
- Add a VoidCast add-on under its add-on directory with a matching metadata file.
- Keep optional external programs behind dependency checks and show clear diagnostics when unavailable.

Before adding a cross-engine feature, decide whether it belongs in both frontends or is intentionally engine-specific. Document that choice and test shared logic where feasible.


## Void Desk Studio companion

The browser companion, portable profile format, official-only plugin trust model, and planned device-sync boundary are specified in [Void Desk Studio — Technical Architecture](STUDIO_ARCHITECTURE.md). That document is the source of truth for profile/schema contracts and staged Studio rollout. Studio does not replace the existing handheld launcher or local service, and it does not make the local service internet-facing.
