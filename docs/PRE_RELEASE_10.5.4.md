# v10.5.4-NEXUS — Pre-release completion plan

This document is the acceptance contract for the next public pre-release. It deliberately separates source-level tests, desktop smoke tests and real handheld validation. A green CI run is necessary, never sufficient.

## Release objective

Deliver VoidDesk as a self-contained, controller-first control centre for MustardOS / muOS 2606.0 Andromeda on supported H700 handhelds:

- Pygame remains the reference frontend and receives usability, reliability and workflow improvements.
- LÖVE becomes a supported, feature-complete alternative for the declared v10.5.4 scope. It must not expose dead actions or "coming soon" controls as if they worked.
- Every visible NEXUS node and every child action has a verified route, backend operation, error state and test.
- APT package discovery and management are available from VoidDesk without launching XFCE.
- Tailscale and Syncthing are first-class UPLINK services.
- A Linux PC companion can pair with the handheld for remote input, file exchange, telemetry and a low-latency remote display mode.
- The distributable .muxapp contains exactly one top-level Void-Desk/ directory and all required runtime/integration assets.

## Current baseline — do not overstate it

| Area | Verified evidence | What it does not prove |
|---|---|---|
| Pygame visual capture | CI renders 103/103 declared render states | Navigation reachability, correct actions, controller edge cases or device compatibility |
| LÖVE visual capture | CI captures 20/20 registered scenes | Feature parity, service correctness or hardware operation |
| LÖVE Shell | Local service PTY endpoints and tests exist on the PR branch | Real muOS terminal usability, keyboard layout and lifecycle on handheld |
| External tools | Registry-based discovery/launch and missing-tool reporting | Bundled submodule content is present in the final .muxapp |
| APT | Native LÖVE APT Manager now provides Search, Installed, Jobs and System operations through a safe XFCE-image manager; CI baseline passed | Real muOS chroot search/install/remove/update/clean validation and failure recovery on hardware |
| Tailscale | Native LÖVE and Pygame panels now use the pinned Rt:Tailscale-M service manager; QR encoder, peer/exit-node controls, Taildrop inventory and autostart are implemented; first-run install is delegated to rt install/start | Post-change CI, reproducible package test, identity migration and physical muOS lifecycle validation |
| Syncthing | Native Pygame REST panel now lists folders/devices, connection and completion state, and supports folder pause/resume, scan, override and device pause/resume; Andromeda discovery and no-duplicate-daemon safeguards are retained | Add/remove flows, disabled-service UX refinements and real-device tests |
| PC link | BaseStation/PcClient already exchange telemetry, notifications and screenshots | Remote keyboard/mouse, virtual display, secure pairing lifecycle and latency budgets |

## Workstream 1 — NEXUS node and action audit

Create a machine-readable feature registry for every node and action:

- stable node/action ID and owning frontend scene/state;
- implementation owner (native UI, Python service, muOS API, optional external tool);
- availability requirements and explicit unavailable reason;
- action input schema and expected result;
- error/timeout handling and cancellation semantics;
- automated test and screenshot references;
- physical-device test result and supported hardware/firmware.

Release gate:

1. Every visible node resolves to a real screen.
2. Every selectable row has a real action or is visibly disabled with a reason.
3. No placeholder, coming-soon, silent no-op or success-shaped failure remains in the release UI.
4. Back navigation, focus restoration, controller repeat/edge behaviour and small-screen text clipping are tested.
5. Pygame and LÖVE feature matrices agree on the declared supported scope.

Visual state enumeration remains a smoke test; add action-driven navigation tests for the critical paths.

## Workstream 2 — LÖVE completion

Prioritise parity by user journey, not by adding isolated screens:

1. NEXUS → every hub → every child view → return path.
2. THE FORGE: searchable APT catalogue, package details, installed state, install/remove queue, update/clean, progress/logs and confirmation for destructive actions.
3. UPLINK: Wi-Fi, Bluetooth, hotspot, PC link, Tailscale and Syncthing.
4. RT:TOOLBOX: Shell, Calculator, Clock, Calendar, Notes, RSS, Weather, file manager, FTP and sync.
5. WORKSHOP: diagnostics, storage, logs, monitoring, backup/restore and maintenance actions.
6. MEDIA VAULT, MUOS APPS, SETTINGS, INFO and END SESSION.
7. Controller mapping, analog input, on-screen keyboard, focus and accessibility pass.

Every screen must use the shared bridge and job model; no scene may shell out with arbitrary interpolated commands.

## Workstream 3 — APT without launching XFCE

Important platform boundary: muOS Andromeda is Buildroot-based, not Debian/Ubuntu. Do not run apt against the muOS host and do not write into its read-only system paths.

The existing VoidDesk Debian/Ubuntu chroot is the package target. VoidDesk should mount and operate on that rootfs from its native frontend; the user does not need to launch XFCE or enter a desktop session.

Required catalogue features:

- apt-get update state, cache timestamp and stale-cache warning;
- apt-cache search with query, category/section and installed/available filters;
- package detail: version, section, description, installed size and dependencies;
- installed package list and upgradeable packages;
- multi-select install/remove with a dependency and disk-space summary;
- non-blocking job queue with progress, output, cancellation and final exit status;
- clean cache and autoremove with a review/confirmation step;
- clear state when the chroot is absent, unmounted, read-only, out of space or offline.

Security and reliability:

- never accept a shell command from the UI;
- validate package names and invoke apt-get with argument arrays;
- keep package operations inside the known chroot root;
- mount only the resources required and unmount only mounts created by the operation;
- serialize package-manager mutations to prevent concurrent dpkg locks;
- never disable TLS verification for repository downloads;
- log exact package names, exit code and bounded output.

The catalogue is available in VoidDesk even when XFCE is not running. If the optional chroot is not installed, offer its installation/repair flow; do not pretend host APT exists.

## Workstream 4 — Rt:Tailscale-M as a first-class service

Source project: https://github.com/SilverCrow2323/muOS-Rt-Tailscale.

Do not merely launch the standalone app from an external-tools list. Reuse and integrate its service layer with a VoidDesk-native interface.

Preserve the mature service capabilities:

- official arm64 tailscale and tailscaled binaries, downloaded from the official stable feed and SHA-256 verified;
- daemon lifecycle, process identity checks, watchdog and logs;
- kernel TUN detection and userspace-networking fallback;
- QR-based login, logout and identity migration/adoption;
- peers, online state, ping, exit-node selection and preferences;
- Taildrop send/receive;
- start-at-boot through muOS User Init Scripts, with explicit status and safe disable;
- service diagnostics, update and recovery;
- optional PIN-protected web panel, bound and exposed deliberately.

Integration requirements:

- one daemon owner only; detect an existing Tailscale process/socket before starting;
- preserve the node identity across VoidDesk upgrades and support explicit migration from existing Rt:Tailscale/Shin installs;
- keep state and keys private (permissions, no UI/log disclosure, no screenshots of secrets);
- pin source/runtime inputs and verify binary hashes;
- include MIT/BSD third-party notices and upstream attribution;
- show a clear distinction between daemon installed, daemon running, logged in, connected and tailnet reachable.

The reproducible builder is now implemented as tools/build_muxapp.py. It refuses to build when the pinned Rt:Tailscale-M submodule is missing, then vendors only the upstream service manager, watchdog, CLI wrapper, web-panel assets, version and license notices under Void-Desk/external/rt-tailscale-m/app/RtTailscale. It does not include the standalone upstream LÖVE UI or any state/identity files; official arm64 binaries are installed on first service start through the upstream checksum-verifying installer. The builder still needs its new CI tests and a real muOS package install/upgrade test. The separate muos-prototypes gitlink had no .gitmodules URL and its commit could not be resolved; its pointer was removed from this PR branch. File-GD X remains unavailable until its source is recovered or replaced.

## Workstream 5 — Syncthing as a native UPLINK service

MustardOS Andromeda documents Syncthing as an optional Web Service, enabled in Configuration → Connectivity → Web Services, with its local UI/API on port 7070.

VoidDesk must manage that existing service, not start a second daemon with a second database.

Required native panel:

- detect service enabled/running and show the correct local endpoint;
- discover API credentials from the active MUOS storage config without displaying or logging the API key;
- device ID, connection state, remote devices and last-seen status;
- folders, paths, completion %, send/receive mode and folder errors;
- pause/resume, rescan and safely add/remove a folder or device;
- show disk usage and conflict/versioning warnings;
- guide the user to enable the muOS Web Service when it is disabled;
- provide a connection test and bounded diagnostics.

Do not assume inotify works on exFAT. Explain scheduled scanning and versioning before enabling bidirectional save sync.

## Workstream 6 — Linux PC companion and remote workspace

Build on the existing BaseStation/PcClient protocol rather than creating an unrelated second protocol.

Phase A — secure pairing and useful remote control:
- explicit pairing code / rotating token, revoke and forget device;
- authenticated, rate-limited commands; no arbitrary shell execution;
- keyboard and mouse input forwarded to VoidDesk's own input dispatcher;
- clipboard and file transfer with destination confirmation;
- PC/device status, battery, storage, network and notifications;
- screenshot request and remote logs with user consent.

Phase B — remote display:
- low-latency H.264/MJPEG stream with configurable resolution, bitrate and frame rate;
- a handheld Remote View scene with fit/crop, latency indicator and reconnect;
- optional input return channel;
- adaptive low-bandwidth mode for Wi-Fi.

Phase C — true secondary display (experimental until tested):
- separate X11 virtual output / Wayland virtual monitor on the PC;
- select a window or virtual output to stream;
- document the PC compositor/driver requirements;
- do not call screen mirroring an extended monitor.

Security: pairing is explicit, secrets are stored with restrictive permissions, traffic is authenticated, file paths are confined to chosen shares, and remote input can be disabled immediately on either endpoint.

## Workstream 7 — Pygame evolution

Pygame remains the reference implementation. Improve rather than replace its mature workflows:

- unify service status and job notifications across hubs;
- modernise the Forge catalogue and package operation review;
- finish Tailscale and Syncthing native management;
- add PC pairing, remote keyboard/mouse and Remote View;
- improve search, filtering, focus, controller feedback and empty/error states;
- remove duplicate legacy paths only after parity tests prove the replacement.

## Workstream 8 — Wiki and release packaging

The wiki-source Markdown is maintained with the source repository. The actual GitHub Wiki still needs its first Home page saved in the GitHub UI; only then can tools/publish_wiki.sh publish the remaining pages.

Before publishing the pre-release:

- Wiki pages match the shipped feature set and label experimental functions honestly;
- compatibility list records tested device + firmware + frontend + known limitations;
- build is reproducible and emits a SHA-256 manifest;
- .muxapp has exactly one top-level Void-Desk/ directory;
- no external gitlink is empty or silently omitted;
- no secrets, user config, Syncthing API keys, Tailscale state or runtime logs are packaged;
- install, in-place upgrade, rollback and uninstall are tested.

## Release gates

A v10.5.4 pre-release is ready only when all gates pass:

- [ ] Pygame critical journeys pass on real Andromeda hardware.
- [ ] LÖVE critical journeys pass on real Andromeda hardware.
- [ ] Every NEXUS node/action has a registry entry and a verified result.
- [ ] APT search/install/remove/update/clean work from VoidDesk without launching XFCE.
- [ ] Tailscale install/login/reboot/reconnect/exit-node/Taildrop/update/uninstall pass.
- [ ] Syncthing detection, pairing, folder sync, pause/rescan and recovery pass.
- [ ] PC pairing, remote input and Remote View pass on a Linux PC.
- [ ] .muxapp structure, permissions, size and checksum pass.
- [ ] Upgrade from the last published release preserves user data and service identities.
- [ ] Wiki and compatibility list reflect actual hardware test results.

CI is the first gate, not the last. Features requiring muOS, network, Wi-Fi, TUN, controller or compositor behaviour must be tested on physical devices.
