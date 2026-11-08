# Visual capture and asset catalogue

## Capture

Both graphical frontends support F12.

- Pygame: F12 via Linux evdev key code 88.
- LÖVE: F12 queues a frame capture after the current frame is drawn.

PNG files and JSON metadata sidecars are written under data/visual-captures/.

## Generate the catalogue

~~~bash
python3 tools/visual_capture.py
python3 tools/visual_capture.py --check
~~~

The dependency-free script scans images and fonts in assets/, resources/, love/assets/ and glyph/. It records size, dimensions where available and SHA-256, verifies images referenced by active LÖVE NEXUS nodes and indexes screenshots.

Generated reports: docs/visual/ASSET_CATALOG.md, docs/visual/SCREENSHOT_CHECKLIST.md and docs/visual/visual-inventory.json.

## Publish selected images

Captures are ignored by Git by default. They may reveal SSIDs, IP addresses, hostnames, personal media names or other private data. Inspect every screenshot before publishing.

~~~bash
python3 tools/visual_capture.py --export-public
~~~

This copies reviewed screenshots into docs/visual/captures/.
