# Visual capture and asset workflow

VoidDesk has two graphical frontends. Capture each engine separately; a Pygame screenshot is not proof that the LÖVE prototype works, and vice versa.

## Capture all LÖVE scenes automatically

On a Linux development PC with LÖVE 11.5 installed:

~~~bash
python3 tools/capture_love_screenshots.py
~~~

The script starts the local Python companion service, launches the LÖVE frontend in a window (or under Xvfb when no display is available), then visits the scene list in love/core/visual_capture.lua. Each scene is allowed to settle before a PNG and JSON sidecar are written. The final manifest is:

data/visual-captures/love-batch-manifest.json

Logs are written beside the captures. A failed scene is recorded in the manifest and does not prevent the remaining scenes from being captured.

Options:

~~~bash
python3 tools/capture_love_screenshots.py --love-bin /path/to/love
python3 tools/capture_love_screenshots.py --settle 1.2 --timeout 300
python3 tools/capture_love_screenshots.py --no-service
~~~

This is a software-rendered desktop capture pass, not a substitute for screenshots from a physical handheld.

## Capture a single screen on-device

Press **F12** on either frontend to save the current composed frame. Pygame uses the Linux evdev F12 key code; LÖVE queues a screenshot after the current draw frame. Both create PNG files and JSON sidecars under data/visual-captures/.

The sidecar records engine, screen, UTC timestamp, resolution, capture mode and app version.

## Generate the asset catalogue and visual galleries

Run from the repository root:

~~~bash
python3 tools/visual_capture.py
python3 tools/visual_capture.py --check
~~~

The script uses only the Python standard library. It inventories images and fonts under assets/, resources/, love/assets/ and glyph/; records file sizes, image dimensions and SHA-256 hashes; checks active LÖVE NEXUS planet-image references; and indexes local screenshots.

Generated reports:

- docs/visual/ASSET_CATALOG.md
- docs/visual/SCREENSHOT_CHECKLIST.md
- docs/visual/visual-inventory.json
- docs/visual/ASSET_GALLERY.html — browse existing graphical assets in a local browser.
- docs/visual/SCREENSHOT_GALLERY.html — browse captured UI screens in a local browser.

## Publishing selected screenshots

Screenshots are ignored by Git by default. Review each capture for SSIDs, IP addresses, hostnames, personal media names or other private details before publishing.

~~~bash
python3 tools/visual_capture.py --export-public
~~~

This copies reviewed screenshots into docs/visual/captures/ and points the gallery at those approved copies. Only commit/export images after the privacy review.
