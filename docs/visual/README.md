# Visual capture and asset workflow

VoidDesk has two graphical frontends. Capture each engine separately; a Pygame screenshot is not proof that the LÖVE prototype works, and vice versa.

## F12 screenshot shortcut

- **Pygame:** press F12 on a keyboard connected to the device/host. Linux evdev key code 88 maps to the SCREENSHOT action.
- **LÖVE:** press F12. LÖVE captures the composed frame after the current draw callback.

Both frontends save PNG files and JSON sidecars under data/visual-captures/. The sidecar records engine, scene, UTC timestamp, resolution and app version.

## Generate the asset catalogue and screenshot checklist

Run from the repository root:

~~~bash
python3 tools/visual_capture.py
python3 tools/visual_capture.py --check
~~~

The script uses only the Python standard library. It inventories images and fonts under assets/, resources/, love/assets/ and glyph/, records file sizes, image dimensions and SHA-256 hashes, checks active LÖVE NEXUS planet-image references and indexes local screenshots.

Generated reports:
- docs/visual/ASSET_CATALOG.md
- docs/visual/SCREENSHOT_CHECKLIST.md
- docs/visual/visual-inventory.json

## Publishing screenshots

Screenshots are ignored by Git by default. Review each capture for SSIDs, IP addresses, hostnames, personal media names or other private details before publishing.

~~~bash
python3 tools/visual_capture.py --export-public
~~~

This copies reviewed screenshots into docs/visual/captures/.
