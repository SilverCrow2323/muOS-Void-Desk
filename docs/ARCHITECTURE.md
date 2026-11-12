# Void Desk architecture

This note maps the Void Desk source tree and main runtime paths. It does not imply that every optional integration is available on every firmware.

For the wider cross-device product structure, naming rules, platform matrix, repository boundaries and LÖVE completion plan, see [QWASAR-Env Product Ecosystem Map](PRODUCT_ECOSYSTEM_MAP.md).

## Runtime overview

On the handheld, mux_launch.sh is the package entry point. It loads muOS launcher helpers, establishes the application environment, starts the local service and runs the selected frontend. The target architecture adds a pre-frontend QWASAR Launch Selector to choose among installed Void Desk instances, build flavours, supported engines, profiles and session targets. It does not replace the muOS firmware bootloader.

~~~text
muOS Apps
   |
   v
mux_launch.sh
   |-- local Python service (service/voiddesk_service.py)
   |
   '-- engine = py   -> desk/main.py + runtime/ (bundled ARM64 Pygame)
 
LÖVE is an experimental, opt-in frontend. The current muOS package does not
include its complete ARM64 runtime, so the device launcher must not select it.
           |
           '-- session hand-off -> bin/xfce_launch.sh
                                  -> return to QWASAR Desk
~~~

The launcher re-reads the configured engine before each run and defaults to Pygame on muOS. If the Pygame runtime is not ready, it extracts the bundled CPython 3.11/aarch64 archives from assets/runtime_archives into a staging directory, verifies imports and then activates runtime/. This first boot works without network access. A PyPI wheel is only a fallback if the bundled ABI cannot be used. Pygame is the reference handheld frontend; LÖVE is experimental and may only be selected when its complete matching ARM64 shared-library set is packaged.

The PC launcher, voiddesk.py, is currently a development convenience. The target PC launcher will provide the same pre-frontend instance/engine selector and session catalogue. Optional GRUB2 integration is separate and only selects complete bootable OS installations; it never changes the renderer inside an already running OS.

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

The source tree contains an experimental aarch64 LÖVE executable and Lua project, but the muOS package must not treat that binary alone as a usable runtime: it also needs the matching liblove-11.5.so and its dependent shared libraries. Until that full runtime is included and validated, the muOS launcher defaults to Pygame and refuses an incomplete LÖVE selection. Some LÖVE routes and actions are still placeholders; it is not at Pygame feature parity.

## LÖVE-to-Python service bridge

The LÖVE bridge serializes requests through the single request/response file pair: only one request is published at a time, each response is matched by request ID, and the service claims requests with an atomic rename before writing an atomic response. This avoids overwriting simultaneous requests on SD filesystems.

## Non-blocking host status

The Pygame frontend reads header indicators through `App.status_snapshot()`. This method is a cache read only. A `StatusPoller` worker refreshes battery, Wi-Fi, Bluetooth, volume, USB and hotspot state at a bounded interval. Slow commands such as `hciconfig` and `bluetoothctl show` therefore cannot suspend the NEXUS render/input loop. Only one refresh is allowed at a time; a failed probe leaves the last known snapshot available and permits a later retry.

## Device power-off sequence

For the muOS package launcher, the Pygame frontend writes `data/.pending_poweroff` and exits normally. The shell launcher detects the marker, stops and waits for `service/voiddesk_service.py`, synchronizes filesystem writes, and invokes the forced power-off command with fallbacks. This avoids leaving the QWASAR Desk companion service running while the system is asked to power down.

The direct power-off fallback in the standalone/PC path is separate from the device hand-off. Neither path can be certified by headless CI; final behaviour must be checked on the target hardware.

## Service and hand-off

The local service provides the bridge used by frontends for system information, network state, media state, jobs and desktop session actions. The launcher uses data/.pending_session as a hand-off marker: the frontend exits, the shell launcher starts the requested session after the display has been released, and QWASAR Desk is launched again when that session ends.

Treat the service and any local web/file integrations as privileged surfaces. Do not expose them to untrusted networks.

## Visual capture and asset inventory

Both frontends support F12 screenshot capture. PNG images and JSON metadata are saved locally under data/visual-captures/. The dependency-free tools/visual_capture.py script indexes captures, scans images and fonts, records file dimensions and SHA-256 hashes, and checks that active LÖVE NEXUS nodes have their referenced textures. Captures are excluded from Git by default; review them for private network and device information before exporting selected images.

## Extension points

- Add a Python panel under desk/hubs/ and connect it through the hub/menu router.
- Add a LÖVE scene under love/scenes/ and register it with the scene/menu system.
- Add a VoidCast add-on under its add-on directory with a matching metadata file.
- Keep optional external programs behind dependency checks and show clear diagnostics when unavailable.

Before adding a cross-engine feature, decide whether it belongs in both frontends or is intentionally engine-specific. Document that choice and test shared logic where feasible.

## Tool catalog and visual system

The current source-grounded tool inventory and proposed workspace/category model are documented in [Tool Catalog](TOOL_CATALOG.md), with a machine-readable starting index in `data/tool_catalog.json`.

The visual identity direction, including the Megastructure, Manga Ink, Industrial, Terminal, Neon Noir and Minimal styles, is documented in [Visual Identity](VISUAL_IDENTITY.md). Style (layout/render treatment) and palette (colours) are separate concepts.


## QWASAR Symbiotic Layer

The long-term host integration strategy is documented in [SYMBIOTIC_LAYER.md](SYMBIOTIC_LAYER.md). It prioritises the official muOS application runner, data-driven extension points, explicit service ownership, SD1/SD2-safe paths and reversible integration. It does not authorise bootloader replacement, protected frontend patching or destructive changes to host init scripts.

## QWASAR Studio companion

The browser companion, portable profile format, official-only plugin trust model, and planned device-sync boundary are specified in [QWASAR Studio — Technical Architecture](STUDIO_ARCHITECTURE.md). That document is the source of truth for profile/schema contracts and staged Studio rollout. Studio does not replace the existing handheld launcher or local service, and it does not make the local service internet-facing.



## QWASAR GUI and launch contracts

The engine-neutral UI composition baseline is defined by:
- docs/QWASAR_GUI_SYSTEM.md
- schemas/qwasar-ui.schema.json
- data/qwasar_ui_manifest.json

The local side-by-side installation inventory is defined by schemas/qwasar-installations.schema.json. The example file is not a live device inventory.

Pygame and LÖVE are the first UI adapters. Qt 6, LVGL and Web are reserved future adapters. Both current frontends must progressively consume the same shell/workspace/menu/widget contracts rather than duplicating application structure.

QWASAR Inspector and QWASAR Switchboard are planned host tools: Inspector audits structure without modifying it; Switchboard applies validated profile-level enable/disable, hide/show and ordering changes. Neither is a substitute for THE FORGE package installation/removal.

See docs/QWASAR_BOOT_AND_SESSION_MODEL.md for the separation between GRUB/OS boot, pre-frontend engine selection, multiple installation flavours, START SESSION, Input Leap/QWASAR Link and optional PC VirtualBox support.

