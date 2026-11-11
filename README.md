<div align="center">

<img src="resources/vdlogo.png" alt="VoidDesk" width="170">

# VOIDDESK — NEXUS

**A handheld-first Linux desktop hub for H700 devices.**

[![CI](https://github.com/SilverCrow2323/Void-Desk-Project/actions/workflows/ci.yml/badge.svg)](https://github.com/SilverCrow2323/Void-Desk-Project/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/SilverCrow2323/Void-Desk-Project?label=release)](https://github.com/SilverCrow2323/Void-Desk-Project/releases)

*The void does not stare back. It compiles.*

</div>

VoidDesk turns a Linux handheld into a controller-first workstation. It combines a native framebuffer interface, system utilities, media tools, connectivity panels, diagnostics and an optional Linux desktop running in an isolated image.

## At a glance

| | |
|---|---|
| Project line | **10.5.4-NEXUS** (release candidate in `main`; see CHANGELOG.md) |
| Latest published package | **v10.2.0** (published 2026-08-11; v10.5.4 is not yet downloadable) |
| Primary target | Anbernic RG35XX-H / Allwinner H700 |
| Primary firmware path | muOS application launcher |
| Native UI | Python + Pygame framebuffer frontend |
| Experimental UI | LÖVE 2D prototype; incomplete and not feature-equivalent to Pygame |
| Desktop session | XFCE in an Ubuntu image; optional tooling is device-dependent |
| Configuration | data/desk_config.json |
| Device entry point | mux_launch.sh |
| PC/development launcher | voiddesk.py |
| License | Not declared in this repository; see note below |

> **Compatibility:** The current packaging target is MustardOS / muOS 2606.0 Andromeda on compatible Allwinner H700 handhelds. Hardware-specific behaviour still requires device-level verification on each model. Older firmware releases and other distributions are not claimed as supported.

## What VoidDesk includes

### NEXUS — the home interface

An animated, orbit-based hub selector designed for D-pad navigation. The UI supports themes, layout choices, sound, transitions, overlays and display effects.

<img src="resources/nexus-menu.png" alt="VoidDesk NEXUS home screen" width="720">

### The hubs

| Hub | Purpose | Representative tools |
|---|---|---|
| **START SESSION** | Start or repair the optional desktop | XFCE image bootstrap and session hand-off |
| **THE FORGE** | Manage components and packages | Status, install/remove, update and cleanup |
| **UPLINK** | Connectivity and device links | Wi-Fi, hotspot, Bluetooth, Tailscale, PC uplink, BaseStation, controllers |
| **MEDIA VAULT** | Audio and video | Internet radio, VoidCast, media library, background audio |
| **WORKSHOP** | Maintenance and diagnostics | System stats, logs, storage, monitoring, backup, CHD, duplicate-file tools |
| **RT:TOOLBOX** | Everyday utilities | Calculator, clock, calendar, notes, RSS, weather, file manager, FTP, sync, terminal, editor |
| **MUOS APPS** | Discover handheld applications | App grid, glyph and controller utilities |
| **SETTINGS** | Personalize the interface | Theme, language, font scale, home style, VFX, status bar, controls |
| **INFO & ABOUT** | Project documentation | About, manual, quick controls, update information |
| **END SESSION** | Leave or restart the session | App restart, reboot, power-off |

Tool availability depends on host firmware, installed packages, hardware and permissions. A listed feature is not a guarantee that it is available on every device.

### Visual system

The interface uses a dark industrial aesthetic, custom artwork, planet-like hub nodes, CRT effects and multiple colour themes. Artwork is stored mainly in resources/, assets/ and love/assets/.

<img src="resources/forge-menu.png" alt="The Forge" width="48%">
<img src="resources/uplink-hub.png" alt="Uplink" width="48%">

<img src="resources/media_vault.png" alt="Media Vault" width="48%">
<img src="resources/workshop.png" alt="Workshop" width="48%">

## Components and entry points

- **Python frontend:** main implementation in desk/; entry point is desk/main.py.
- **LÖVE frontend (experimental):** incomplete prototype in love/; it is not feature-equivalent to Pygame and is not the recommended daily-use engine.
- **Local service:** service/voiddesk_service.py provides the backend used by frontend panels and session actions.
- **VoidCast:** standalone IPTV/media application under outdesk/VoidCast/voidcast/.
- **External tools:** optional applications and integrations under outdesk/.
- **Device launcher:** mux_launch.sh starts the local service, chooses the engine and handles session hand-off.
- **PC launcher:** voiddesk.py provides a terminal menu and direct launch options for development and desktop testing.

See [Architecture](docs/ARCHITECTURE.md) for execution flow.

## Installation on the handheld

> **Release status (2026-11-08):** the latest published handheld package is `VoidDesk_v10.2.0.muxapp` (release `v10.2.0`, published 2026-08-11). The `main` branch has advanced to the `v10.5.4-NEXUS` release candidate, but that candidate has **not** been published as a `.muxapp` package yet. The v10.2.0 download therefore does not include the v10.5.4 changes listed in the changelog.

1. Open [GitHub Releases](https://github.com/SilverCrow2323/Void-Desk-Project/releases) and download the latest **published `.muxapp` asset**. Check the release tag before installing; the source-code ZIP is not a replacement for the muOS application package.
2. Copy the `.muxapp` file to the SD1 `ARCHIVE/` folder.
3. On the handheld, open **Applications → Archive Manager** and install the package.
4. Launch VoidDesk from Applications and follow the on-screen setup/repair flow for the optional desktop image.

### First-run checklist

- Keep the device connected to reliable Wi-Fi during downloads.
- Keep at least **1.5–2 GB free storage** for the desktop image, as stated by the original installation guide. Actual requirements vary with selected components.
- Keep the device powered while an image or package installation is running.
- Back up important saves and configuration before updating firmware or replacing the package.
- If setup is interrupted, inspect the log before repeating storage-intensive operations.

**Pygame is the recommended frontend.** LÖVE is included for ongoing development and testing only; several hubs and actions remain incomplete in that engine. The Pygame frontend can bootstrap its runtime on demand. The improved bootstrap validates HTTPS certificates, verifies the published PyPI SHA-256 digest, checks archive paths and tests the import before replacing the active runtime. The desktop image bootstrap is separate.

## Web browsers on muOS

VoidDesk exposes optional desktop browsers through the **XFCE environment**. NetSurf (`netsurf-gtk`), Falkon (`falkon`) and Dillo (`dillo`) are package choices for the Ubuntu desktop image; they are not browser binaries installed directly into the muOS host.

To use one:

1. Install and start the optional XFCE desktop from **START SESSION**.
2. Open **THE FORGE → BROWSER / RETE** and install the browser into the desktop image.
3. Launch it from the XFCE application menu or an XFCE terminal.

The separate `qtWebBrowser` entry in EthoStore is a third-party muOS application. It is not the same component as the XFCE browsers above and is not bundled or maintained by VoidDesk.

### Browser launch errors

An `Input/output error` is not specific enough to identify one cause. Record which browser was selected, whether it was launched from XFCE or from the muOS application grid, and the complete error text. Useful logs are:

- `data/xfce_session.log` — XFCE session output.
- `data/session_xfce.log` — X/desktop startup output.
- `data/voiddesk.log` — VoidDesk launcher and session hand-off output.

Installing a browser inside the XFCE image does not make it executable from the muOS host; those are separate environments.

## Controls

| Input | Default action |
|---|---|
| D-pad | Navigate |
| A | Confirm / open |
| B | Back / cancel |
| X | Context or secondary action (varies by panel) |
| Y | Cycle view or secondary list action |
| L1 / R1 | Change tab or category |
| START | Panel-specific action / dialog confirmation |
| SELECT | Refresh or rescan where supported |

Use the in-app quick guide when a panel defines different shortcuts.

## Desktop and development launch

The root-level voiddesk.py is a convenience launcher for a Linux PC. It is not the muOS package installer and does not make every handheld-only operation available on a desktop.

Prerequisites: Linux, Python 3 and a terminal. The LÖVE frontend needs a system love executable (Debian/Ubuntu: sudo apt install love). The Pygame launcher creates .venv_desktop and installs pygame and psutil on first use.

~~~bash
git clone --recurse-submodules https://github.com/SilverCrow2323/Void-Desk-Project.git
cd Void-Desk-Project

python3 voiddesk.py
python3 voiddesk.py --love
python3 voiddesk.py --py
python3 voiddesk.py --engine love
python3 voiddesk.py --engine py
python3 voiddesk.py --repair
python3 voiddesk.py --help

# Build the muOS package (requires the pinned submodule above)
python3 tools/build_muxapp.py
~~~

The bundled LÖVE binary is architecture-specific; on a PC the launcher prefers the system installation.

The Rt:Tailscale-M service is included as a pinned Git submodule. If you cloned without `--recurse-submodules`, run `git submodule update --init --recursive` before building or packaging Void Desk. The builder copies only the upstream service manager, watchdog, CLI wrapper and PIN-protected panel into `Void-Desk/external/rt-tailscale-m/app/RtTailscale`; the standalone upstream UI is not launched. Tailscale's official arm64 binaries are installed on first service start with upstream checksum verification.

See the [visual capture workflow](docs/visual/README.md) to capture every LÖVE scene automatically, take F12 screenshots in either frontend, and generate the asset catalogue and visual galleries.

## Configuration and generated data

| Path | Role |
|---|---|
| data/desk_config.json | Main user configuration |
| data/iptv_config.json | IPTV configuration |
| data/voiddesk.log | Device launcher and session log |
| data/logs/ | Additional runtime logs |
| data/.pygame_ready | Pygame bootstrap completion marker |
| data/visual-captures/ | Local F12 screenshots and JSON metadata; ignored by Git |
| data/sdl_path.txt | Detected SDL library path |
| runtime/ | Downloaded Pygame runtime; ignored by Git |
| data/xfce.img | Optional desktop image |

Back up personal configuration and media/list files before reinstalling. Generated runtime directories and logs are excluded from version control.

## Repository map

~~~text
.
├── .github/workflows/   # Continuous integration
├── assets/              # Fonts, sounds, glyphs and platform assets
├── bin/                 # Bootstrap, diagnostics and session scripts
├── data/                # Configuration and local runtime state
├── desk/                # Python framebuffer application and hubs
│   ├── hubs/            # Feature panels
│   └── utils/           # Safe I/O, extraction, cache and calculation helpers
├── lib/                 # Runtime libraries and framebuffer helpers
├── love/                # LÖVE frontend, scenes, widgets and themes
├── outdesk/             # Standalone applications and integrations
├── resources/           # Artwork and screenshots
├── service/             # Local backend service
├── tests/               # Focused automated tests
├── tools/               # Visual asset and screenshot inventory tools
├── wiki-source/         # Source pages for the GitHub Wiki
├── voidcast_addons/     # VoidCast add-ons
├── BUILDCHECK.py        # Repository integrity checks
├── mux_launch.sh        # muOS device entry point
└── voiddesk.py          # PC/development launcher
~~~

## Development and quality checks

The repository includes focused tests for atomic file writes, safe calculation and archive extraction.

~~~bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install pytest ruff

python -m compileall -q BUILDCHECK.py voiddesk.py bin desk service outdesk voidcast_addons assets
pytest -q
python BUILDCHECK.py
~~~

The optional headless smoke test requires Pygame: python BUILDCHECK.py --smoke.

GitHub Actions checks Python compilation, focused tests, critical Ruff diagnostics, shell syntax and LuaJIT bytecode compilation. A green result does not replace testing on the target handheld. See [Development](docs/DEVELOPMENT.md).

## Troubleshooting

| Symptom | First checks |
|---|---|
| Black screen or immediate exit | data/voiddesk.log, engine choice, framebuffer permissions, free storage |
| Pygame engine fails | Device clock, CA certificates and bootstrap logs; do not disable TLS verification |
| LÖVE missing on PC | Install the PC build of LÖVE and retry python3 voiddesk.py --love |
| Desktop session does not start | data/voiddesk.log, desktop-image readiness, free storage |
| A hub reports a missing tool | Install the optional dependency, then re-run diagnostics |
| Controls stop responding | Return to the parent panel, reconnect the controller, inspect diagnostics |
| Update or repair fails | Preserve logs and open an issue with device/firmware details |

Bug reports should include version, device, firmware, selected engine, reproduction steps and a short relevant log excerpt. Redact usernames, network names, IP addresses, tokens and private data.

### Device power-off

When VoidDesk is started as a muOS application, the power-off action returns control to `mux_launch.sh`. The launcher stops the local companion service, syncs pending filesystem writes, then requests a forced power-off, with kernel power-off fallbacks if the first command returns. This is separate from **END SESSION → Close**, which only exits VoidDesk.

If the device does not power off, preserve `data/voiddesk.log` and report the device model, muOS build and whether the screen/LED state changed. Avoid repeated hard resets while storage writes may still be in progress.

## Security and responsible use

VoidDesk can interact with the host system, install packages, manage network interfaces and expose local services.

- Review commands and package operations before confirming them.
- Use network tools only on devices and networks you own or are explicitly authorized to administer.
- Do not expose BaseStation or other local services to untrusted networks.
- Do not publish configuration files, logs or screenshots containing credentials or private network information.
- Keep firmware, packages and the device clock up to date.
- Treat third-party playlists, add-ons, archives and downloads as untrusted input.

See [SECURITY.md](SECURITY.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

## Credits and license

VoidDesk is credited in the project materials to **Sir Pips / SPDW Factory**. The repository also acknowledges Pygame, LÖVE, muOS, Debian/Ubuntu, iptv-org, Open-Meteo and Radio Browser, alongside contributors listed in CHANGELOG.md.

The repository currently has no root-level LICENSE file, even though older README content displayed an MIT badge. The badge has been removed rather than making an unsupported legal claim. The maintainer should add the intended license text before redistribution under a specific open-source license.

<div align="center">

**VOIDDESK NEXUS · built for the void, by the void.**

[Releases](https://github.com/SilverCrow2323/Void-Desk-Project/releases) · [Issues](https://github.com/SilverCrow2323/Void-Desk-Project/issues) · [Source](https://github.com/SilverCrow2323/Void-Desk-Project)

</div>
