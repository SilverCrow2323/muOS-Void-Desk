# 🖥️ Frontends — Pygame and LÖVE

Void Desk currently contains two frontend implementations. They do not yet provide feature parity.

## Pygame — reference frontend

Pygame is the primary handheld implementation and the recommended frontend for normal muOS use.

- Entry point: `desk/main.py`
- Hub screens: `desk/hubs/`
- Shared constants and routing: `desk/`
- Device launcher: `mux_launch.sh`
- Runtime bootstrap: `bin/bootstrap_lite.py`

The Pygame implementation is the reference for current user-visible behaviour. Individual actions still need feature-level tests and physical-device validation.

## LÖVE — experimental frontend

The LÖVE frontend is an active development target, not a feature-equivalent production alternative.

- Entry point: `love/main.lua`
- Scenes: `love/scenes/`
- Shared renderer and widgets: `love/core/`
- Themes: `love/theme/`
- Local service bridge: `love/core/bridge.lua` and `service/voiddesk_service.py`

A scene rendering in CI does not prove that its routes, services, controller focus or actions work. Missing features must be presented as unavailable rather than simulated as success.

> [!WARNING]
> Do not choose LÖVE as the default handheld frontend until the matching ARM64 runtime is packaged, the complete target scope is implemented, and the same user journeys have been tested on the actual H700 device.

## Shared direction

The v12 architecture aims to share the UI composition contract, semantic actions, focus/navigation model, theme tokens and capability APIs. Each frontend remains a renderer/adapter; privileged host operations belong to the service layer.

The long-term engine choice should be made after performance, accessibility and feature coverage have been measured. Avoid permanent divergence between two independent versions of the product.

## Visual verification

- Pygame smoke captures: `python3 tools/capture_pygame_screenshots.py --all-states`
- LÖVE scene captures: `python3 tools/capture_love_screenshots.py`
- Asset and screenshot inventory: `python3 tools/visual_capture.py --check`

See [Visual capture and assets](Visual-capture-and-assets). Renderer coverage is not an end-to-end hardware test.
