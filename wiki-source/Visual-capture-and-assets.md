# QWASAR Desk — Visual capture and asset catalogue

## Capture every LÖVE scene

On a Linux development PC with LÖVE 11.5 installed:

~~~bash
python3 tools/capture_love_screenshots.py
~~~

The script starts the Python companion service, runs the LÖVE frontend, switches through its scene catalogue and captures each rendered screen. When no display is available it uses Xvfb. The capture summary is saved as data/visual-captures/love-batch-manifest.json.

This pass verifies that scenes can be opened and rendered in the desktop runtime. GitHub Actions uploads a `voiddesk-love-visual-captures` artifact from each run (screenshots, JSON sidecars, manifest and logs; 30-day retention). Open the workflow run and download it from **Artifacts**. Synthetic system/network status is used for this test, not live host data. It is not hardware validation for muOS or a claim that all LÖVE actions are complete.

## Automated Pygame home-style smoke capture

On Linux/CI, run:

~~~bash
python3 tools/capture_pygame_screenshots.py --all-states
~~~

The harness boots the real Pygame application with an isolated temporary config and SDL's dummy video/audio drivers, renders the five supported home styles (BLAME, HUD, Terminal, Orbit and NEXUS), then smoke-renders every state branch declared in `App.render_state()`. Each direct state render produces a PNG and JSON sidecar; the manifest is `data/visual-captures/pygame-home-manifest.json`.

GitHub Actions uploads these files as `voiddesk-pygame-visual-captures` (30-day retention). A failed style makes the command fail and is recorded in the manifest. Direct state rendering does not prove that a screen is reachable through normal navigation, that its actions work, or that controller/hardware flows are valid. Treat this as broad renderer coverage, not end-to-end feature validation.

## Capture one current screen

Both frontends support F12. PNG screenshots and JSON metadata sidecars are saved under data/visual-captures/.

## Generate the asset catalogue and galleries

~~~bash
python3 tools/visual_capture.py
python3 tools/visual_capture.py --check
~~~

The standard-library script scans images and fonts in assets/, resources/, love/assets/ and glyph/. It records size, dimensions where available and SHA-256, verifies active LÖVE NEXUS node textures and indexes screenshots.

Generated reports:

- docs/visual/ASSET_CATALOG.md
- docs/visual/SCREENSHOT_CHECKLIST.md
- docs/visual/visual-inventory.json
- docs/visual/ASSET_GALLERY.html
- docs/visual/SCREENSHOT_GALLERY.html

## Publish selected images

Captures are ignored by Git by default. They may reveal SSIDs, IP addresses, hostnames, personal media names or other private data. Inspect every screenshot before publishing.

~~~bash
python3 tools/visual_capture.py --export-public
~~~

This copies reviewed screenshots into docs/visual/captures/. Do not publish raw captures until they have been reviewed.
