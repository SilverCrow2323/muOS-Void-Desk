# 🌌 VOIDDESK PROJECT

**Multifunctional AIO Desktop Hub & Cyberpunk Linux Operating Environment for H700 Handhelds**

```
  ▗▖  ▗▖▗▄▄▖ ▗▄▄▄▖▗▄▄▄▖▗▄▄▄▖ ▗▄▄▖ ▗▄▄▄▖ ▗▄▄▖▗▖  ▗▖
  ▐▌  ▐▌▐▌ ▐▌  █  ▐▌   ▐▌ ▐▌▐▌ ▐▌▐▌   ▐▌   ▐▌  ▐▌
  ▐▌  ▐▌▐▌ ▐▌  █  ▐▌   ▐▌ ▐▌▐▌ ▐▌▐▄▄▄▖ ▝▀▚▖▐▌  ▐▌
  ▐▌  ▐▌▐▌ ▐▌  █  ▐▌   ▐▌ ▐▌▐▌ ▐▌▐▌       ▐▌▐▌  ▐▌
   ▝▚▞▘ ▝▄▄▞▘▗▄▄▄▖▗▄▄▄▖▐▄▄▄▘ ▝▄▄▞▘▐▄▄▄▖▗▄▄➞▘▝▚▞▘ 

```

<div align="center">

[![GitHub Release](https://img.shields.io/github/v/release/SilverCrow2323/Void-Desk-Project?style=for-the-badge&color=7057ff&labelColor=0d1117)](https://github.com/SilverCrow2323/Void-Desk-Project/releases)
[![MIT License](https://img.shields.io/badge/License-MIT-07a2c2?style=for-the-badge&labelColor=0d1117)](LICENSE)
[![GitHub Discussions](https://img.shields.io/github/discussions/SilverCrow2323/Void-Desk-Project?style=for-the-badge&color=1f883d&labelColor=0d1117)](https://github.com/SilverCrow2323/Void-Desk-Project/discussions)
[![GitHub Issues](https://img.shields.io/github/issues/SilverCrow2323/Void-Desk-Project?style=for-the-badge&color=d9381e&labelColor=0d1117)](https://github.com/SilverCrow2323/Void-Desk-Project/issues)

---

![Supported Firmware](https://img.shields.io/badge/Firmware-muOS%20%7C%20ROCKNIX%20%7C%20Knulli-d4c5f9?style=flat-square)
![Target Architecture](https://img.shields.io/badge/SoC-Allwinner%20H700-a2eeef?style=flat-square)
![License](https://img.shields.io/badge/License-MIT%20(Nicola%20Santato)-07a2c2?style=flat-square)

</div>

---

### ⚡ Welcome to the Playground

A warm greeting to all the wretches, rogue hackers, and wanderers passing through Sector G1! This is the dark alley I’ve opened to communicate better with anyone who wants to know more about this project — which, I’ll admit, is pretty much my personal playground.

Today it might be an office suite tool or system automation utility; tomorrow, an IPTV player or a full-blown Debian desktop session. At the end of the day, that’s just who I am: picking something up and pushing it to the absolute limit, caring zero about *"you shouldn't do that"* or *"don't even try"*.

**We try anyway. And fuck your corporate ethos.**

---

## 🛠️ Architecture & Core Philosophy

VoidDesk starts from a single, unyielding axiom:

> **An ARM SoC with a display is a real computer. It deserves to be treated like one.**

Rather than stacking heavy, battery-draining desktop managers or complex display server configurations directly on top of limited embedded OS layers, VoidDesk renders its native shell UI straight to the Linux framebuffer (`/dev/fb0`) using Python and Pygame.

* **Zero GPU Acceleration Overhead:** Runs entirely within native software rendering pathways, saving memory and keeping thermal throttle limits under control.
* **Non-Invasive Architecture:** Leaves your host firmware system, retro gaming frontend, and core partition structures untouched.
* **Low Footprint, Maximum Output:** Starts in under 2 seconds, utilizing minimal RAM idle state.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        VOIDDESK SYSTEM STACK                                │
├─────────────────────────────────────────────────────────────────────────────┤
│   CUSTOM SHELL / INTERACTIVE LAUNCHER NODE (Pygame / SDL / Framebuffer)     │
├─────────────────────────────────────────────────────────────────────────────┤
│   MODULE CONTAINER LAYER                                                    │
│   ├── Network & Tailscale Suite   ├── PTY Framebuffer Terminal              │
│   ├── BGM Normalizer & Tools      ├── Debian Chroot Environment (XFCE/LXDE)│
├─────────────────────────────────────────────────────────────────────────────┤
│   INTEROPERABILITY HOOKS (JSON State Pipes & Shell Triggers)                 │
├─────────────────────────────────────────────────────────────────────────────┤
│   HOST LINUX FIRMWARE LAYER (muOS Jacaranda / ROCKNIX / Knulli)             │
├─────────────────────────────────────────────────────────────────────────────┤
│   HARDWARE LAYER (Allwinner H700 SoC - Quad Cortex-A53 @ 1.5GHz / 1GB RAM) │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Complete Features, Modules & Utilities Breakdown

VoidDesk is packed with a wide array of raw tools, system extensions, automation scripts, and sub-level features.

```
                          ┌──────────────────────────┐
                          │   VOIDDESK ENGINE CORE   │
                          └─────────────┬────────────┘
                                        │
     ┌──────────────────┬───────────────┼───────────────┬──────────────────┐
     ▼                  ▼               ▼               ▼                  ▼
┌──────────────┐ ┌───────────────┐ ┌─────────┐ ┌──────────────────┐ ┌───────────────┐
│ 🎛️ DUAL-RING │ │ 🖥️ CHROOT     │ │ 🌐 NET  │ │ 📟 PTY TERMINAL  │ │ 🛠️ UTILITY HUB│
│ ORBIT SYSTEM │ │ DESKTOP ENGINE│ │ SUITE   │ │ & SHELL EMULATOR │ │ & TOOL SUITE  │
└──────────────┘ └───────────────┘ └─────────┘ └──────────────────┘ └───────────────┘
```

### 🎛️ 1. Dual-Ring Orbital Launcher & Framebuffer Compositor
* **Orbital Node Navigation:** Dynamic 2D orbital menu rendered at 60 FPS directly over `/dev/fb0`.
* **Procedural Visual Backgrounds:** Real-time starfield/nebula particle rendering without GLX dependencies.
* **Aspect Ratio & Resolution Adaptation:** Native scaling for 640x480 (4:3) and 720x720 (1:1 aspect displays like RG CubeXX).
* **Analog & D-Pad Navigation Engine:** Full gamepad controller binding with customizable deadzones.

### 🖥️ 2. Isolated Debian Linux Desktop Environment (Chroot Engine)
* **XFCE4 / LXDE / Openbox Sessions:** Run a real Linux desktop session directly on your handheld.
* **LibreOffice Suite Integration:** Functional Writer (documents) and Calc (spreadsheets) for mobile productivity.
* **ARM64 Web Browsing Node:** Optimized Chromium/Firefox ESM configurations for low-memory footprint browsing.
* **Loop-Mount System Protection:** Containerized filesystem image (`xfce.img`) mounting; protects host partition integrity.
* **ALSA Audio Passthrough:** Direct ALSA device routing for containerized applications.

### 🌐 3. Network, Remote Management & Tailscale Suite
* **Native Wi-Fi Manager:** Interface for `wpa_supplicant` connection management, AP scanning, and reconnect routines.
* **Tailscale Mesh VPN Manager:** Direct deployment and status monitoring for secure remote access over cellular/home networks.
* **SSH Server Daemon Controller:** One-click toggle for embedded dropbear/OpenSSH background servers.
* **Network Traffic & Active Socket Monitor:** Real-time bandwidth usage meter and open connection inspector.
* **IPTV Player Engine:** Lightweight stream parser and player integration for IPTV network playlists.

### 📟 4. Framebuffer PTY Terminal & Command Shell
* **On-Device Terminal Multiplexer:** Run multi-tab command-line sessions without an external display or PC connection.
* **Custom On-Screen Keyboard (OSK):** Controller-driven virtual keyboard with touch and D-Pad key selection.
* **ANSI Color Compositor:** Native rendering for terminal colors, ASCII artwork, and htop/btop utilities.
* **Quick Script Execution Shortcuts:** Pre-configured macro bar for fast execution of standard Linux shell commands.

### 🛠️ 5. Extended Utility Hub & On-Device Script Automation
* **CHD Converter Engine:** Batch compression tool converting PS1, Saturn, Sega CD, and Dreamcast ISOs directly to `.chd`.
* **BGM Audio Normalizer:** Volume balancing tool for handheld background music tracks (`external/muOS-BGM-Normalizer`).
* **MIDI Mapping Engine:** Route external USB-MIDI devices directly to Linux software synths.
* **System Resource & Thermal Monitor:** Live readings for Allwinner H700 CPU frequency, thermal throttling, and RAM usage.
* **Power & CPU Governor Tweaker:** Switch between `performance`, `schedutil`, and `powersave` scaling governors on the fly.
* **Automated Log & Clean-up Utility:** One-click cache flushing, temp file purging, and orphaned loop mount recovery.

---

## 🐍 Module Developer API Guide (Python IPC Engine)

VoidDesk exposes an internal Python API allowing developers to create custom modules, custom UI widgets, and hardware automation tools.

### 1. Module File Structure

All custom modules must reside inside the `modules/` directory:

```
modules/
└── my_custom_module/
    ├── __init__.py
    ├── manifest.json      # Metadata & launch parameters
    └── main.py            # Primary Python entrypoint
```

### 2. Module Manifest (`manifest.json`)

```json
{
  "id": "my_custom_module",
  "name": "Custom Hardware Diagnostic",
  "author": "SectorG1_Hacker",
  "version": "1.0.0",
  "category": "Diagnostics",
  "icon": "icon.png",
  "entrypoint": "main.py",
  "requires_root": false
}
```

### 3. Writing a Native Module (`main.py`)

Every VoidDesk module inherits from `VoidBaseModule` and hooks into the IPC bus and framebuffer event loop:

```python
import sys
import json
from voiddesk.core import VoidBaseModule, IPCBridge

class CustomDiagnosticModule(VoidBaseModule):
    def __init__(self):
        super().__init__(name="DiagnosticNode")
        self.ipc = IPCBridge(pipe_path="/tmp/voiddesk_ipc.json")

    def on_init(self):
        self.logger.info("Custom Diagnostic Module initialized in Sector G1")

    def render_overlay(self, surface):
        """Called directly inside the Pygame framebuffer loop."""
        # Custom drawing code targeting 640x480 or 720x720 canvas
        pass

    def on_event(self, event):
        """Handle gamepad buttons, D-Pad, or touch inputs."""
        if event.type == self.BUTTON_A:
            self.ipc.send_command("CPU_GET_TEMP")

    def on_ipc_message(self, data):
        """Process background telemetry from voiddesk_service.py."""
        if data.get("type") == "TELEMETRY_UPDATE":
            cpu_temp = data.get("payload", {}).get("cpu_temp")
            self.logger.info(f"Current CPU Temp: {cpu_temp}°C")

if __name__ == "__main__":
    module = CustomDiagnosticModule()
    module.run()
```

### 4. IPC JSON Pipe Protocol (`/tmp/voiddesk_ipc.json`)

Communication between Python modules and host daemons uses structured JSON packets:

```json
{
  "sender": "my_custom_module",
  "target": "voiddesk_service",
  "action": "EXEC_SHELL",
  "payload": {
    "command": "cat /sys/class/thermal/thermal_zone0/temp"
  }
}
```

---

## 📦 Installation & Quick Start Guide

### System Prerequisites
* **Target Handheld:** Allwinner H700 Device (RG35XX series, RG40XX series, RG CubeXX).
* **Firmware:** muOS (Jacaranda or newer), ROCKNIX, or Knulli.
* **Storage Footprint:**
  * Core Installation: **~150 MB**
  * Full Desktop Suite + Debian Chroot (`xfce.img`): **~2.5 GB free space recommended** on SD card.

### Step-by-Step Setup

1. **Download Release Package:** Get the latest build from [VoidDesk Releases](https://github.com/SilverCrow2323/Void-Desk-Project/releases).
2. **Extract to Target OS Directory:**
   * **muOS:** `/mnt/sdcard/MUOS/application/VoidDesk/`
   * **ROCKNIX:** `/storage/roms/ports/VoidDesk/`
   * **Knulli:** `/userdata/roms/ports/VoidDesk/`
3. **Set Execution Permissions:**
   ```bash
   chmod +x /mnt/sdcard/MUOS/application/VoidDesk/VoidDesk.sh
   ```
4. **Launch:** Open **Applications** (muOS) or **Ports** (ROCKNIX/Knulli) on your device and launch **VoidDesk**.

---

## 🔍 Troubleshooting & Recovery

* **Display Driver Conflict (`/dev/fb0` locked):** Ensure no other emulator or background frontend process is holding exclusive lock on the framebuffer.
* **muOS Environment Overrides:** Verify that `VoidDesk.sh` sets `export SDL_VIDEODRIVER=framebuffer` or `mali`.
* **Orphaned Loop Mount Cleanup:** If a chroot session crashes abruptly, run:
  ```bash
  sudo umount -l /mnt/chroot
  ```

---

## 💬 Community & Underground Hub

Because official updates and experimental builds cannot be distributed through standard third-party platform channels:

**[ This GitHub Repository is the Unsanctioned Headquarters ]**

* **💡 [Ideas & Proposals](https://github.com/SilverCrow2323/Void-Desk-Project/discussions/categories/ideas):** Drop module concepts or feature requests under Ideas.
* **💬 [General Terminal (VOID-555)](https://github.com/SilverCrow2323/Void-Desk-Project/discussions/categories/general):** Share custom setups, scripts, or Linux tweaks.
* **🐛 [Complaints & Gendarmeria Desk](https://github.com/SilverCrow2323/Void-Desk-Project/issues/new/choose):** Found a crash, bug, or script error? Open an issue report.

---

## 📜 License & Copyright

**VoidDesk Project** is open-source software distributed under the terms of the [**MIT License**](LICENSE).

```
MIT License

Copyright (c) 2026 Nicola Santato (SilverCrow2323)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

**Designed, coded, and tested with sweat, shell hacks, and pure Rintrompo energy in Sector G1.**

*★ VoidDesk is an independent project and is not officially affiliated with Anbernic, muOS, ROCKNIX, or Knulli teams. All trademarks belong to their respective owners. ★*