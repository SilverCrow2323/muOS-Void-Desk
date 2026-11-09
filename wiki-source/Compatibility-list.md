# Compatibility and validation matrix

**Evidence snapshot: 2026-11-09 (CI runs #42637030192 and #42637211232)**  
**Development line:** v10.5.4-NEXUS  
**Latest published handheld package:** v10.2.0

This page distinguishes a declared target from automated CI coverage and from real hardware validation. A green screenshot job is not a compatibility certification.

## Status definitions

| Status | Meaning |
|---|---|
| **Target** | The project is being developed for this environment, but no complete hardware acceptance record is attached here |
| **CI checked** | The named source/build/test path completed in GitHub Actions; this does not prove operation on a handheld |
| **Experimental** | The feature exists but is incomplete, has limited coverage or is not recommended for daily use |
| **Pending hardware** | Source-level or CI work exists, but the required physical-device test has not been recorded |
| **Not claimed** | No compatibility promise is made for this combination |

## Device and firmware matrix

| Device / platform | Firmware or OS | Status | Evidence and limitation |
|---|---|---|---|
| Anbernic RG35XX-H / Allwinner H700 | MustardOS / muOS 2606.0 Andromeda | **Target · Pending hardware** | Declared primary target in the README. The current evidence snapshot contains no complete physical acceptance record for startup, controls, power-off, APT, Tailscale, Syncthing and upgrade/rollback on this exact combination |
| Other Allwinner H700 handhelds | MustardOS / muOS 2606.0 Andromeda | **Target family · Pending hardware** | Shared SoC family does not prove identical display, buttons, storage, Wi-Fi, Bluetooth or firmware behaviour. Verify each exact model |
| H700 handhelds on older muOS releases | Older firmware | **Not claimed** | No release-level compatibility record is maintained here |
| ROCKNIX | Any build | **Not claimed** | No current end-to-end installation and hardware acceptance record |
| KNULLI | Any build | **Not claimed** | No current end-to-end installation and hardware acceptance record |
| Linux desktop PC | Linux distribution with Python 3, Tkinter and a supported GUI session | **Companion target · CI checked** | BaseStation has a standalone PC build path; PR [#12](https://github.com/SilverCrow2323/Void-Desk-Project/pull/12) passed all 7 CI jobs, including Python checks and reproducible PC archive packaging (run [#42637030192](https://github.com/SilverCrow2323/Void-Desk-Project/actions/runs/42637030192)). Remote input and remote display are not yet implemented |

## Frontend evidence

| Component | Current evidence | Remaining limitation |
|---|---|---|
| Python / Pygame | CI visual capture renders 103/103 declared states (five home styles plus 98 non-home state branches). The capture job passed in [run #42637030192](https://github.com/SilverCrow2323/Void-Desk-Project/actions/runs/42637030192) | State rendering does not prove route reachability, correct actions, controller edge cases or physical display/input behaviour |
| LÖVE | CI visual capture covers 23/23 registered scenes and passed in [run #42565176588](https://github.com/SilverCrow2323/Void-Desk-Project/actions/runs/42565176588) | LÖVE remains experimental and is not feature-equivalent to Pygame; service/action gaps remain |
| NEXUS navigation | Static route/placeholder checks cover selected hubs, including Session, Forge, Workshop and Toolbox | Full action-driven navigation coverage across every hub and physical controller QA remain release gates |

## Service and feature evidence

| Feature | Current implementation / CI evidence | Not yet demonstrated |
|---|---|---|
| .muxapp packaging | The reproducible package and structural validator passed in [run #42565176588](https://github.com/SilverCrow2323/Void-Desk-Project/actions/runs/42565176588); the workflow emitted a package artifact | Install, upgrade, permissions, rollback and uninstall on a physical muOS device |
| APT manager | Native frontend/service path and an allowlisted job manager exist; unit and packaging coverage was added to the development line | Search/install/remove/update/clean against the actual VoidDesk Debian/Ubuntu image on the handheld, including mount recovery and low-storage behaviour |
| Rt:Tailscale-M | Native VoidDesk service adapter and Uplink UI delegate to the pinned upstream manager. The upstream static/model/QR/UI suite, arm64 binary build and QEMU daemon/watchdog/boot/web-panel checks passed in run #42637030192 | Physical muOS installation, identity migration, login, reboot, reconnect, exit-node, Taildrop and upgrade/uninstall |
| Syncthing | Existing Andromeda Web Service discovery uses local API port 7070. Native panels list folders/devices and support pause/resume, rescan, confirmed override and device pause/resume | Add/remove folder/device flows, conflict/versioning UX and real API validation on the target handheld |
| VoidCast | Launcher hand-off and configuration preflight are present; LÖVE hand-off and evdev-related checks are in the test suite | Actual IPTV playback, audio/video compatibility, controller operation and long-session testing on target hardware |
| SPDW Device Agent | Service-owned gateway, pairing and authenticated request flows have dedicated source and test coverage | Live port inventory, pairing/revocation and upload/download testing on physical muOS hardware |
| BaseStation / PC Link | PC companion source and browser dashboard are present; the package workflow was added. PR #12 is fixing the latest CI blockers | Latest Python and companion-package CI passed in run [#42637030192](https://github.com/SilverCrow2323/Void-Desk-Project/actions/runs/42637030192); PC Link uses HTTP and must remain on trusted LAN/Tailscale paths, never directly exposed to the public internet. Remote keyboard/mouse and Remote View remain future work |
| RT Stream / Sunshine | Port-family registry model and source-audit notes exist | Actual daemon source, lifecycle ownership and current port contract remain source-audit-pending; do not treat streaming as available merely because ports are listed |

## Network exposure policy

- PC Link on TCP 8420 currently uses HTTP with an authentication token. Keep it on a trusted LAN or an authenticated encrypted Tailscale path.
- Do not expose PC Link or legacy management panels directly to the public internet.
- Do not treat a port registry entry as proof that the corresponding daemon is installed, running or safely configured.
- Confirm bind address, authentication and firewall policy on the actual host before enabling remote access.

## Recording a hardware result

A compatibility claim requires a reproducible record with:

1. Exact handheld model and hardware revision, if known.
2. Exact firmware name/build and installation method.
3. VoidDesk version or commit SHA and selected frontend.
4. Test date, power/battery state and network conditions where relevant.
5. Each tested journey: install/launch, controller navigation, display, sound, Wi-Fi, Bluetooth, storage, shutdown, and the feature-specific actions being claimed.
6. Result per journey (**pass**, **fail**, **blocked**, or **not tested**) plus relevant redacted logs or screenshots.

Do not publish Wi-Fi credentials, API keys, Tailscale identity/state, pairing tokens, private IPs or personal file names. A model is considered hardware-verified only after the record is reviewed and added to this matrix.

## Release rule

No device/firmware combination becomes **Hardware verified** from source inspection, unit tests, QEMU, screenshots or a successful .muxapp build alone. Physical installation, normal operation, upgrade and rollback must be tested on the exact combination being claimed.
