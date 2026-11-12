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

## 🧩 Navigation icon library

The small PNGs below are **menu/hub icons from `resources/`**, not screenshots of application screens.

| WORKSHOP | SETTINGS | THE FORGE | START SESSION | RT:TOOLBOX |
|---|---|---|---|---|
| <img src="assets/icons/workshop.png" width="72" alt="Workshop icon" /> | <img src="assets/icons/settings.png" width="72" alt="Settings icon" /> | <img src="assets/icons/the_forge.png" width="72" alt="The Forge icon" /> | <img src="assets/icons/start.png" width="72" alt="Start Session icon" /> | <img src="assets/icons/rt_toolbox.png" width="72" alt="RT Toolbox icon" /> |

| NETSPHERE / UPLINK | muOS APPS | MEDIA VAULT | INFO | END |
|---|---|---|---|---|
| <img src="assets/icons/net_sphere.png" width="72" alt="Netsphere icon" /> | <img src="assets/icons/muos.png" width="72" alt="muOS Apps icon" /> | <img src="assets/icons/media_vault.png" width="72" alt="Media Vault icon" /> | <img src="assets/icons/info.png" width="72" alt="Info icon" /> | <img src="assets/icons/end.png" width="72" alt="End icon" /> |



<div align="center"><img src="assets/brand/voiddesk_symbol.png" width="84" alt="Void Desk logo" /></div>

<details>
<summary>🖥️ Actual screen reference — THE FORGE</summary>

This is the **THE FORGE application screen**, not the hub icon:

<img src="assets/screens/forge-menu.png" alt="THE FORGE application screen" width="720" />

The separate `the_forge.png` in the navigation grid above is the **THE FORGE hub icon**.
</details>

## Project links

- [Repository](https://github.com/SilverCrow2323/Void-Desk-Project)
- [Releases](https://github.com/SilverCrow2323/Void-Desk-Project/releases)
- [Issues](https://github.com/SilverCrow2323/Void-Desk-Project/issues)
- [Technical docs](https://github.com/SilverCrow2323/Void-Desk-Project/tree/main/docs)
- [v12 blueprint](https://github.com/SilverCrow2323/Void-Desk-Project/blob/main/docs/V12_BLUEPRINT.md)

When reporting an issue, include exact device model, firmware, frontend, steps and relevant redacted logs. Remove Wi-Fi names, IPs, tokens, hostnames and personal filenames.
