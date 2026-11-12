![Void Desk field manual](assets/voiddesk-docs-banner.svg)

# 🪐 Void Desk — QWASAR-Env handheld field manual

**A controller-first Linux handheld environment.**  
*BORN IN THE VOID. BUILT BEYOND THE FIRMWARE.*

> [!IMPORTANT]
> **v12 is a blueprint, not a published release.** The latest published package is v10.2.0 (11 August 2026). PR #66 remains a draft. Install from [GitHub Releases](https://github.com/SilverCrow2323/Void-Desk-Project/releases), not from the source ZIP.

> [!NOTE]
> Pygame is the reference frontend. LÖVE is experimental and not feature-equivalent. muOS 2606.0 Andromeda is the current packaging target; compatibility is not implied for every device.

## Choose your path

| Goal | Page |
|---|---|
| Install Void Desk | [Installation — muOS Andromeda](Installation-muOS-Andromeda) |
| Learn controls | [Controls & navigation](Controls-and-navigation) |
| Understand workspace ownership | [Hubs & features](Hubs-and-features) |
| Compare frontends | [Pygame and LÖVE](Frontends) |
| Explore the v12 architecture | [Void Desk v12 blueprint](Void-Desk-v12-Blueprint) |
| Check firmware/controller mappings | [muOS firmware compatibility](muOS-Firmware-Compatibility) |
| Understand host integration | [Symbiotic Layer](Symbiotic-Layer) |
| Fix a problem | [Troubleshooting](Troubleshooting) |
| Develop and test | [Development](Development) |
| Write or review docs | [Documentation style](Documentation-Style-Guide) |
| Inspect images and captures | [Visual assets](Visual-capture-and-assets) |

## The system map

![QWASAR-Env system map](assets/qwasar-system-map.svg)

The host firmware remains responsible for boot, native navigation and recovery. Void Desk runs inside the supported application lifecycle and uses a local service bridge for selected device capabilities.

## NEXUS — v12 destination map

![NEXUS v12 navigation](assets/nexus-v12-navigation.svg)

The v12 proposal groups eight destinations by user intent. RT:WORKSHOP has two satellites: **SYSTEMS** (device health/maintenance) and **TOOLS** (user/developer utilities). This diagram shows the target architecture, not a screenshot of the current UI.

## Firmware and controller resolution

![Firmware/controller profile resolution](assets/muos-profile-resolution.svg)

| muOS line | Policy |
|---|---|
| 2606.0 Andromeda | Current packaging target; validate each device/GUID profile |
| 2601.0 Jacaranda | Legacy profile family |
| 2601.1 Funky Jacaranda | Keep separate until equivalence is proven |
| 2612 Supernova | In development on 12 Nov 2026; preview only |
| Other / unknown | Generic safe fallback plus calibration |

See [official muOS releases](https://muos.dev/release) and [release progress](https://muos.dev/release/progress).

<details>
<summary>📷 Earlier interface screenshots (historical references)</summary>

These PNGs show earlier UI work. They do not demonstrate v12 completion or feature parity.

<img src="https://raw.githubusercontent.com/SilverCrow2323/Void-Desk-Project/main/resources/nexus-menu.png" alt="Earlier NEXUS menu" width="48%" />
<img src="https://raw.githubusercontent.com/SilverCrow2323/Void-Desk-Project/main/resources/uplink-hub.png" alt="Earlier Uplink screen" width="48%" />

</details>

## Project links

- [Repository](https://github.com/SilverCrow2323/Void-Desk-Project)
- [Releases](https://github.com/SilverCrow2323/Void-Desk-Project/releases)
- [Issues](https://github.com/SilverCrow2323/Void-Desk-Project/issues)
- [Technical docs](https://github.com/SilverCrow2323/Void-Desk-Project/tree/main/docs)
- [v12 blueprint](https://github.com/SilverCrow2323/Void-Desk-Project/blob/main/docs/V12_BLUEPRINT.md)

When reporting an issue, include exact device model, firmware, frontend, steps and relevant redacted logs. Remove Wi-Fi names, IPs, tokens, hostnames and personal filenames.
