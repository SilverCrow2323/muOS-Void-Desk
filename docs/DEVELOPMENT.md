# 🛠️ Void Desk — development and quality guide

> [!NOTE]
> This guide separates source checks, desktop smoke tests and physical handheld validation. Passing one level does not imply passing the next.

## Environment

~~~bash
git clone --recurse-submodules https://github.com/SilverCrow2323/Void-Desk-Project.git
cd Void-Desk-Project
git submodule update --init --recursive
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install pytest ruff
~~~

The desktop launcher may create its own <code>.venv_desktop</code>. Do not package a desktop virtual environment for muOS.

## Run

~~~bash
python3 voiddesk.py
python3 voiddesk.py --py
python3 voiddesk.py --love
python3 voiddesk.py --engine py
python3 voiddesk.py --engine love
python3 voiddesk.py --repair
~~~

| Entry point | Responsibility |
|---|---|
| <code>voiddesk.py</code> | PC/development launcher |
| <code>mux_launch.sh</code> | muOS entry point and lifecycle hand-off |
| <code>desk/main.py</code> | Pygame reference frontend |
| <code>love/main.lua</code> | Experimental LÖVE frontend |
| <code>service/voiddesk_service.py</code> | Local capability/service bridge |

## Fast checks

~~~bash
python -m compileall -q BUILDCHECK.py voiddesk.py bin desk service outdesk voidcast_addons assets
pytest -q
python BUILDCHECK.py
~~~

For shell edits, use <code>sh -n path/to/script.sh</code>. For Lua edits, use the repository's configured LuaJIT checks.

> [!IMPORTANT]
> Never hide a failing check with <code>|| true</code>. Fix it or document exactly why it could not run.

## Visual verification

### Pygame PNG capture

~~~bash
python3 tools/capture_pygame_screenshots.py --all-states
~~~

The harness writes PNGs, JSON sidecars and a manifest under <code>data/visual-captures/</code>. It exercises supported renderer states, not real host operations.

### LÖVE scene capture

On Linux with LÖVE 11.5 and Xvfb if no display is available:

~~~bash
python3 tools/capture_love_screenshots.py
~~~

Capture mode uses synthetic system/network values. This is a visual smoke test, not hardware certification.

### Asset inspection

~~~bash
python3 tools/visual_capture.py
python3 tools/visual_capture.py --check
~~~

F12 saves a screenshot in supported frontends. Inspect every PNG before sharing it: SSIDs, IPs, hostnames, device IDs and personal filenames may be visible.

See [Visual capture workflow](visual/README.md).

## Handheld qualification

| Evidence | Demonstrates | Does not demonstrate |
|---|---|---|
| Unit/static tests | Syntax and isolated logic | Controller or framebuffer behaviour |
| CI/QEMU | Paths exercised by that job | Physical hardware compatibility |
| Desktop run | Development-host behaviour | muOS package behaviour |
| Physical device test | Named device/firmware pair | Other untested combinations |

Record the exact handheld model, muOS release, controller name/GUID, frontend and selected input profile. Test cold launch, controls, edited feature, unavailable/error states, shutdown and return to muOS. For services, include stopped/offline/timeout/permission-denied cases.

## Pull request checklist

- Keep changes focused and preserve stable IDs unless a migration is included.
- Add regression tests for confirmed bugs where practical.
- Keep optional dependencies optional and report unavailable capabilities clearly.
- Keep slow host operations out of render/input callbacks.
- Use atomic configuration writes and preserve a valid previous copy.
- Redact secrets and private device/network information from logs and captures.
- Do not claim Pygame/LÖVE parity from a screenshot pass alone.
- Include device evidence for handheld-specific changes.

<details>
<summary>🔎 Related engineering references</summary>

- [Architecture](ARCHITECTURE.md)
- [QWASAR GUI contract](QWASAR_GUI_SYSTEM.md)
- [Profile resolver](QWASAR_PROFILE_RESOLVER.md)
- [Tool catalog](TOOL_CATALOG.md)
- [muOS compatibility](MUOS_FIRMWARE_COMPATIBILITY.md)
- [Contributing](../CONTRIBUTING.md)
- [Security](../SECURITY.md)

</details>
