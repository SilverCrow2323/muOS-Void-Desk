# ◈ VoidDesk

**The definitive desktop layer for muOS.**
*A real Linux machine lives inside your handheld. VoidDesk is how you drive it.*

<div align="center">

![Void-DESK](https://i.ibb.co/27cw4TZt/muos-20260725-175855.png)

[![muOS](https://img.shields.io/badge/muOS-Compatible-7B68EE?style=flat-square)](#)
[![Device](https://img.shields.io/badge/Device-RG35XX--H-FF6F00?style=flat-square)](#)
[![Python](https://img.shields.io/badge/Python-3-3776AB?style=flat-square&logo=python&logoColor=white)](#)
[![Pygame](https://img.shields.io/badge/Pygame-Framebuffer-90EE90?style=flat-square)](#)
[![Chroot](https://img.shields.io/badge/Desktop-Ubuntu%20chroot-E95420?style=flat-square&logo=ubuntu&logoColor=white)](#)
[![Version](https://img.shields.io/badge/Version-10.0.0--pre--release-FF6B6B?style=flat-square)](#)
[![SPDW Factory](https://img.shields.io/badge/SPDW_Factory_Lab-00FFCC?style=for-the-badge)](#)

</div>

---

## 📖 Table of Contents

- [Overview](#-overview)
- [What's New in v10.0.0](#-whats-new-in-v1000)
- [Key Features](#-key-features)
- [Controls](#-controls)
- [Installation](#-installation)
- [Project Structure](#-project-structure)
- [Under the Hood](#-under-the-hood)
- [Troubleshooting](#-troubleshooting)
- [Roadmap](#-roadmap)
- [Credits](#-credits--philosophy)

---

## 📖 Overview

Stock firmware gets you emulators and stops there. **VoidDesk** starts from a different premise: a handheld with an ARM SoC and a screen is a *computer*, and deserves to be treated like one.

Under the hood, VoidDesk bootstraps and manages real Linux desktop environments — **XFCE, IceWM, LXDE** — each living in its own self-contained Ubuntu chroot, launched on demand, never getting in the way of the rest of the system. On top of that, VoidDesk *is itself* a complete native interface: its own menu system, its own file manager and text editor, its own real terminal, its own networking suite, all drawn from scratch straight to `/dev/fb0` — no X server for the shell itself, no compositor, just a game loop and a framebuffer, running comfortably on hardware with no GPU to speak of.

Everything is built for a d-pad first. Nothing about this app assumes you have a mouse, a keyboard, or patience for either.

---

## 🚀 What's New in v10.0.0

### **Net-Sphere** — A 3D Planetarium Menu

The home menu has been completely reimagined. **Nexus** is now a navigable solar system:

- **🌌 Dual orbit system** — Inner ring (START SESSION) and outer ring (all other hubs) with independent rotation
- **🌍 Orbital mechanics** — Nodes drift in real-time; each planet has its own speed, size, and colour signature
- **🎯 Dynamic focus** — The selection zone remains fixed while the entire scene pans and zooms to your chosen destination
- **🌀 Smooth transitions** — Rotate between nodes on an orbit, or switch orbits entirely, with continuous camera movement
- **💫 Procedural nebula** — A soft, colour-shifting nebula pulses behind the scene, keyed to the selected node

![Nexus Menu](resources/nexus-menu.png)

---

## 🚀 Key Features

### 🖥️ Desktop Environments

| | |
|---|---|
| 🐧 **Three real desktops** | XFCE, IceWM (*Turbo*), and LXDE (*Light*) — install, launch, or remove each independently |
| 🗂️ **One chroot, zero clutter** | Everything lives in a single ext4 disk image; nothing touches your SD card's root filesystem |
| 🪟 **Tabbed environment manager** | Cycle between environments with **L1/R1**, see status, launch, repair, or update from one screen |
| 🩹 **One-tap repair** | A stuck or half-configured session gets fixed without a full reinstall |
| 🎬 **Per-environment boot animation** | Toggle it independently for each desktop |
| 📜 **Session logging** | Every desktop session logs to its own file, browsable from the Log Registry |

![XFCE Environment](https://i.ibb.co/fzGVBrZT/muos-20260725-175947.png)
![Live menu of the Desktop Sessions](https://i.ibb.co/nMDqSVyH/muos-20260725-180006.png)
![Desktop Sessions](resources/sessions-menu.png)

### 📦 Void Installer

| | |
|---|---|
| 🗃️ **Full package catalogue** | Every installable component, live install status, at a glance |
| 📂 **Expandable categories** | Collapse what you don't need — MX-style, not a 200-item wall of scrolling |
| ☑️ **Multi-select install/remove** | Batch operations with live progress, never silent, never surprising |
| ⚠️ **Confirms before it acts** | Destructive operations always show what they're about to do first |

![FORGE menu](resources/forge-menu.png)

### 💻 CLI Arsenal & Real Terminal

| | |
|---|---|
| ⌨️ **A real terminal** | Actual `xterm` on a minimal X session — not a fake shell drawn in pygame |
| 🎮 **Gamepad-native typing** | On-screen keyboard tuned specifically for d-pad navigation, no physical keyboard assumed |
| 🐍 **Curated CLI catalogue** | `cmatrix`, `nyancat`, `ani-cli`, terminal games, utilities — browsable and installable like an app store |
| 🎥 **Anime streaming from a terminal** | `ani-cli` integration, because why not |
| 🛠️ **Dedicated Live Panel** | Terminal-specific troubleshooting menu — Ctrl+C, core task health check, keyboard settings, all without leaving the session |
| 🔄 **True in-place restart** | Restart the current CLI tool without bouncing back to the main menu |

### 🌐 Networking

| | |
|---|---|
| 📶 **Wi-Fi manager** | Saved networks, signal strength, forget/reconnect, out-of-range detection |
| 🔵 **Bluetooth manager** | Pair, trust, connect, forget — full device lifecycle |
| 📡 **Hotspot** | Native hotspot with hostapd+dnsmasq — 2.4GHz or 5GHz, custom SSID/password |
| 🔁 **Syncthing panel** | Native REST API integration, not a shortcut to a web UI |
| 🔒 **Tailscale integration** | Peer list, exit nodes, Taildrop, QR login — built in |

![Uplink Hub](resources/uplink-hub.png)

### 🧰 Native Tool Suite (*Rt:TOOLBOX*)

| | |
|---|---|
| 📁 **Void Files** | File manager with clipboard, script execution, image preview |
| 📝 **Void Edit** | A text editor that doesn't fight the d-pad |
| 🗓️ **Calendar** | Real month-grid view plus a week view with full day names |
| 🕐 **Clock** | Six distinct faces — classic, minimal, segmented, analog (with a live seconds sub-dial), skeleton, and pilot |
| 🗞️ **RSS Reader** | Follow feeds without a browser |
| ☁️ **Weather** | Multi-city, glanceable |
| 📌 **Notes** | Sticky-note board, because sometimes you just need to jot something down |
| 🔌 **FTP client** | With profile management and live transfer progress |
| 🐍 **Python REPL** | A persistent Python shell on the host, for when you need to poke at something directly |

![Rt:Toolbox set](resources/toolbox-set.png)

### 📊 System Diagnostics

| | |
|---|---|
| 📈 **Void Stats** | The full system picture — kernel, uptime, memory, storage, network, in one screen |
| 🩺 **Void Diag** | Image and session health checks |
| 📉 **Void Monitor** | Live CPU / RAM / temp / network graphs |
| ⚡ **Void Boost** | CPU governor and swap control, per-app if you want it |
| 🗃️ **Log Registry** | Every log VoidDesk writes, in one place, with one-tap archive-to-SD |

![Workshop Hub](resources/workshop.png)

### 🎨 Customization & Visual Identity

| | |
|---|---|
| 🧭 **Five home menu styles** | Cycle with **Y** — a dense grid, a HUD, a green-phosphor terminal, a slow radial orbit, and **Nexus**, the new 3D planetarium view |
| 🌈 **Colour themes** | Multiple accent palettes, applied consistently across the whole app |
| 🎚️ **VFX detail sliders** | Background animation, transitions, and screen effects each get their own 0–5 dial — tune it down for a weaker device, crank it up for the full experience |
| 🔤 **Adjustable text size** | Four scales, because not every screen and not every user wants the same density |
| 🏭 **A living background** | A seamless animated megastructure — grid, gears, a fan, status LEDs, the occasional glitch — running behind almost every screen, not just the home menu |
| 🌀 **Real transitions, not cuts** | Window open/close has actual weight to it — a slight mechanical overshoot, not a flat fade |
| ✨ **A boot sequence with an ending** | Custom animated intro, closing on a rotating light-wipe that reveals the menu underneath it |

---

## 🎮 Controls

| Input | Action |
|---|---|
| **D-Pad** | Navigate menus |
| **A** | Confirm / open |
| **B** | Back / cancel |
| **X** | Secondary actions — mark for multi-select, open a detail card, context options (consistent across the whole app) |
| **Y** | Cycle home menu style · select-all in list screens |
| **L1 / R1** | Switch tabs — environments, installer mode, category jump |
| **START** | Collapse/expand a category · confirm in dialogs |
| **SELECT** | Rescan / refresh |

### Nexus Menu Controls (v10.0.0)

| Input | Action |
|---|---|
| **UP / DOWN** | Rotate the current orbit (previous/next planet) |
| **LEFT / RIGHT** | Switch between inner and outer orbit |
| **A** | Open the selected hub |

Full reference lives in-app: **INFO & ABOUT → Quick guide**.

![Info menu](resources/info.png)

---

## 📥 Installation

| Step | |
|---|---|
| **1. Download** | Grab the latest `VoidDesk_v10_XX.muxapp` from [Releases](https://github.com/SilverCrow2323/muOS-Void-Desk/releases) |
| **2. Copy** | Place it in `mnt/mmc/MUOS/application/` |
| **3. Launch** | Open it from **MuOS Apps** on the device |
| **4. First run** | Pick a desktop environment to bootstrap — this downloads a real desktop, budget a few minutes and a stable connection |

### Requirements

- Anbernic **RG35XX-H**
- **muOS**, developed and tested against the 2601 *JACARANDA* release line
- Free SD space for whichever environments you install — budget ~1.5–2GB each

---

## 📂 Project Structure

```
VoidDesk/
├── desk/                              # Core application modules
│   ├── main.py                        # The application itself — every screen, every render path
│   ├── intro.py                       # The boot animation
│   ├── icons.py                       # Procedural glyph set
│   ├── rtshell.py                     # Native terminal with PTY and ANSI emulation
│   ├── qrgen.py                       # Pure Python QR code generator
│   ├── controllers.py                 # HID/MIDI device reading
│   ├── sysinfo.py                     # System state (battery, network, audio, etc.)
│   ├── imgmount.py                    # chroot image mount/unmount handling
│   ├── fbdisplay.py                   # Framebuffer output without SDL video driver
│   ├── pcuplink.py                    # PC Basestation client
│   ├── evinput.py                     # Direct /dev/input/event* reading
│   └── jsmap.py                       # evdev ↔ QJoyPad mapping
│
├── bin/                               # Host-side scripts: mount, install, launch, network setup
│   ├── vd_loader.py                   # Loading indicator with progress bar
│   ├── vd_panel.py                    # LIVE panel (START+SELECT)
│   ├── vd_hotkey.py                   # System key daemon
│   ├── vd_bootanim.py                 # Environment boot animation
│   ├── vd_boost.sh                    # System optimizations (swap, CPU governor)
│   ├── xfce_launch.sh                 # Desktop launch script
│   ├── xfce_bootstrap.py              # Initial XFCE chroot installation
│   ├── xfce_install.py                # Package install/removal
│   ├── xfce_update.py                 # System update
│   ├── bootstrap_lite.py              # Pygame runtime bootstrapping
│   ├── gen_layout.py                  # QJoyPad layout generator
│   ├── vd_xterm_launch.sh             # Real terminal (xterm) launcher
│   ├── vd_chdman_run.sh               # CHD conversion runner
│   └── vd_hotspot_*.sh                # Hotspot scripts (hostapd + dnsmasq)
│
├── assets/                            # Resources (fonts, images, configurations)
│   ├── brand/                         # SPDW Factory artwork, symbols
│   ├── basestation/                   # PC companion (basestation.py)
│   ├── bgm/                           # Boot animation audio
│   ├── glyphs/                        # 22×22 app icon set
│   ├── xfce/                          # XFCE configuration files
│   └── DejaVuSans.ttf                 # System font
│
├── lib/                               # Support libraries
│   ├── fbtext.py                      # Text on framebuffer (no pygame)
│   ├── fbmsg.py                       # Framebuffer messaging
│   └── glyph_install.sh               # Glyph installation in muOS theme
│
├── data/                              # Runtime state, logs, config, user data (created on first run)
│   ├── desk_config.json               # Main configuration file
│   ├── *.log                          # Application logs
│   └── xfce.img                       # Desktop environment disk image (~4GB)
│
└── mux_launch.sh                      # muOS entry point

```
## ⚙️ Under the Hood

VoidDesk's own interface is a single pygame application drawing directly to `/dev/fb0`. The desktop environments it manages are a different animal entirely: a real Ubuntu chroot in an ext4 disk image, bootstrapped with `debootstrap`, mounted and launched through a minimal X session only when you ask for it. The two worlds meet at a small, deliberate seam — a handful of shell scripts that mount, launch, and clean up, and a config file both sides read.

No GPU, no compositor, no wasted cycles. Every animation you see is software-rendered on hardware that was never meant to run a desktop at all.

### Key Technical Details

- **Pygame runtime**: Bootstrapped on first run from PyPI — no pre-installed dependencies required
- **Framebuffer output**: Direct `/dev/fb0` writing with RGB565 or XRGB8888 conversion
- **Event input**: Direct `/dev/input/event*` reading — no X11 event loop
- **Chroot management**: Loop-mounted ext4 image with bind mounts for /dev, /proc, /sys, and SD cards
- **Swap management**: zram first, fallback to swapfile inside the image
- **Hotspot**: Native hostapd + dnsmasq, auto-detects the best wireless interface
- **Companion PC**: HTTP/JSON daemon (`basestation.py`) that runs on your PC

---

## 💡 Troubleshooting

- **Blank screen after launch** — check `data/voiddesk.log` first; most launch failures leave a clear trace there
- **A desktop session won't start** — use the environment's **Repair** action before reinstalling; it fixes the vast majority of stuck states
- **CLI tool says "not found" after installing** — open **Log Registry**, archive the logs, and check `deps_check.log` and `post_install_check.log` for the actual failure
- **Wi-Fi/Bluetooth not refreshing** — leave and re-enter the panel; if it persists, check the specific log
- **Out of space inside the image** — clean apt cache in **WORKSHOP**, or remove software you don't use from **FORGE**

Every subsystem that can fail writes its own log. If something's wrong, the **Log Registry** is always the first stop.

---

## 🗺️ Roadmap

VoidDesk is under active, genuinely relentless development. Core functionality is stable and in daily use; the visual layer is being reworked screen by screen, and several larger features are in progress:

- **v10.0.0** — Nexus 3D planetarium menu *(current)*
- **v10.1.0** — Enhanced package installer with dependency resolution
- **v10.2.0** — App drawer redesign
- **v10.3.0** — Deeper networking detail views

See [`ROADMAP.md`](ROADMAP.md) for the current state of things in detail.

---

## ⚖️ Credits & Philosophy

**Part of the SPDW Factory ecosystem** — built alongside `VoidCast` (IPTV/PVR) and `VoidDiag` (zero-dependency diagnostics), somewhere in the ß universe.

> *anon@ß-relay has established a connection. we don't know who's reading this. but if you made it this far — you're one of us. keep up the sbrobbing.*

**Designed and built by Sir Pips** — SPDW Factory.

Symbol design, brand identity, and the whole visual language are original SPDW Factory work.

### Third-Party Acknowledgments

- **Debian/Ubuntu** — The base system powering the desktop environments
- **Pygame** — The framework that makes the native interface possible
- **muOS** — The firmware that made this project viable
- **iptv-org** — Free IPTV playlists
- **open-meteo.com** — Weather data and geocoding
- **nvcuong1312** — Bluetooth bring-up (bltMuos) and hotspot inspiration
- **amosjerbi** — Wi-Fi detection and reconnect fallback

---

<div align="center">

*continua a smontare le cose.*

[⬆ Back to top](#--voiddesk)

</div>
