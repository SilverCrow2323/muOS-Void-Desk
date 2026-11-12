# QWASAR-Env — Product Ecosystem and Device Map

**Status:** working architecture baseline  
**Scope:** product naming, device responsibilities, repository boundaries, trust model, and the Void Desk LÖVE completion plan  
**Current implementation anchor:** `SilverCrow2323/Void-Desk-Project`  
**Rule:** this document describes the intended system. A planned component is not an implemented or supported product until it has code, tests, packaging, and device evidence.

---

## 1. Product identity and naming

The ecosystem should have one umbrella identity and clearly separated products. Names describe responsibility, not merely technology.

| Name | Role | Status |
|---|---|---|
| **QWASAR-Env** | Umbrella name for the cross-device environment, shared contracts, integrations, and product family | Recommended ecosystem name |
| **Void Desk** | The classic controller-first handheld application. It owns the NEXUS interface, local tools, frontend engines, and handheld lifecycle | Current product; first delivery priority |
| **Rt:QWASAR** | Reserved name for a future shared runtime/device-agent layer and its platform adapters | Reserved; not a separate product or repository yet |
| **QWASAR Hub** | Optional server/API service for device registry, pairing, profile/catalog distribution, and sync coordination | Planned; not deployed |
| **QWASAR Studio** | One browser/PWA product containing Module Forge, Layout Designer, Release Composer, and Community Library | Existing design direction; implementation is not deployed |
| **QWASAR Link** | Native PC companion/agent for secure device pairing, transfers, telemetry, remote input, and remote display | Planned; legacy BaseStation is only a prototype reference |
| **Void Desk AppBuilder engine** | Local/reproducible build and validation engine for `.muxapp` flavours | Existing `build-packages.sh` and `tools/build_muxapp.py` are the foundation; the module-aware engine is future work |

### Naming rules

- Use **QWASAR-Env** when referring to the ecosystem as a whole.
- Use **Void Desk** when referring to the classic handheld application. Do not rename its installed paths, package identifiers, or repository slug in the same change as a branding update.
- Use **QWASAR Studio** for one unified browser experience: Module Forge, Layout Designer, Release Composer and Community Library. Use **QWASAR Hub** for its optional server/API.
- Use **QWASAR Link** for the PC companion. It is not the same thing as the browser interface.
- Reserve **Rt:QWASAR** for the shared runtime/device-agent layer. Do not use the `Rt:` prefix as the public umbrella name; it is better suited to a runtime component.
- Keep the AppBuilder engine inside the Void Desk repository; Studio is its user-facing web workbench, not a second builder application.

The name QWASAR-Env does not imply a new firmware distribution or a monolithic operating system. It is a coordinated environment assembled from independently installable applications and services.

---


## 1A. Void Desk as a modular environment

Void Desk is a multifunctional handheld hub whose sections are assembled from replaceable modules. The user can rearrange, rename, hide, disable, replace and create contributions in stable NEXUS/workspace slots. Modules declare compatibility, dependencies, typed capabilities, permissions, UI contributions and optional XFCE APT package requirements. Profiles describe layout only; they never execute code. APT packages are installed only inside the optional Debian/Ubuntu desktop image, never on the muOS Buildroot host.

The precise proposed bundle structure, manifest, slot model, permission contract, community trust tiers and Full/Essential/Slim package flavours are specified in [Void Desk Modules](MODULE_SYSTEM.md). This is a proposed contract: module execution, community publishing, signing and custom builds must not be described as implemented until those systems exist.

QWASAR Studio remains one web app with four workbenches:

- **Module Forge:** create, document and validate a module.
- **Layout Designer:** compose Void Desk sections and tiles like LEGO blocks.
- **Release Composer:** select Full, Essential, Slim or a custom first-party module set and request a reproducible package build.
- **Community Library:** discover and share profiles and, after the trust infrastructure exists, reviewed executable modules.

The current AppBuilder scripts are the local build engine. Studio will become the visual front-end to that engine and to a controlled remote build pipeline; it is not a separate fifth product.

## 2. Device-by-device responsibility map

### Device A — H700 handheld running muOS / MustardOS

**Priority:** P0 — finish this first.

**Product:** Void Desk  
**Current device target:** Anbernic RG35XX-H and compatible H700 devices  
**Current firmware target:** muOS / MustardOS Andromeda  
**Frontend status:** Pygame is the reference implementation; LÖVE is the active alternative frontend to complete.

Responsibilities:

- Launch as a normal muOS application through the supported application runner, then offer a reversible pre-frontend selector for installed Void Desk instances, Full/Essential/Slim/Custom flavour, available engine and user profile.
- Provide NEXUS navigation and controller-first workspaces whose shell, header, footer, side panels, menus and widgets are defined by the engine-neutral QWASAR UI contract.
- Run the local Python service and expose typed, allowlisted capabilities to Pygame/LÖVE adapters.
- START SESSION launches separate desktop or terminal sessions; UPLINK owns online services and PC pairing; THE FORGE owns package/module lifecycle; MEDIA VAULT owns multimedia; RT:TOOLBOX owns installed tools, diagnostics and utilities.
- RT:TOOLBOX is composed of Everyday Tools, Files & Storage, System & Diagnostics, and Developer & Terminal.
- Keep local features working offline; network-only functions must show an explicit offline state.
- Allow profiles to rearrange, hide or disable registered contributions without uninstalling them; use QWASAR Inspector for validation and QWASAR Switchboard for activation state.
- Compose sections from built-in/installed modules, export/import portable layout profiles, and later pair with Studio/Link without requiring either to use the local privileged service directly.

Platform boundary:

- muOS is the host firmware and remains responsible for boot, recovery, and the native frontend.
- Do not run APT against the muOS Buildroot host. APT operations belong inside the optional Debian/Ubuntu image only.
- No bootloader replacement, destructive init modifications, or irreversible firmware changes. GRUB is not used on muOS/H700; its boot selector is the muxapp launcher plus the reversible pre-frontend selector.
- The local service remains loopback-only and privileged. It must not become an internet-facing API.

**P0 acceptance:** complete Void Desk's declared LÖVE journeys and validate them on the RG35XX-H before expanding to other firmwares.

### Device B — Other H700 handheld models running muOS

**Priority:** P1 — after the RG35XX-H baseline is stable.

Reuse the Void Desk product and shared H700 adapter where possible. Validate each model independently:

- display dimensions, safe margins, orientation and scaling;
- gamepad names, D-pad, analog axes, shoulder buttons and hotkeys;
- battery, Wi-Fi, Bluetooth, audio, storage and power-off behaviour;
- SD1/SD2 mount paths and available storage;
- firmware-specific launcher metadata and lifecycle.

A shared SoC does not prove that every device has identical controls, storage layout, firmware version, or hardware support.

### Device C — KNULLI handhelds

**Priority:** P2 — new platform adapter, not a compatibility flag.

Needs:

- KNULLI application/package lifecycle adapter;
- filesystem and storage discovery;
- service startup/shutdown and permission model;
- controller/display profile;
- feature capability map (which integrations exist on that firmware);
- packaging and upgrade/uninstall tests on real hardware.

Void Desk's UI and shared logic may be reusable, but muOS-specific scripts and assumptions must not be copied unchanged.

### Device D — ROCKNIX handhelds

**Priority:** P2 — separate platform adapter and validation track.

Needs the same explicit adapter contract as KNULLI, plus ROCKNIX-specific package, service, display, input, and storage tests. Do not claim support merely because a Linux binary starts.

### Device E — Other/custom Linux handhelds

**Priority:** P3 — capability-based support after at least two concrete platform adapters exist.

The shared runtime must discover capabilities instead of assuming one firmware layout. Unsupported hardware operations must be absent or disabled with a reason. A platform adapter may expose only a safe subset of the full feature catalogue.

### Device F — Linux PC

**Products:** Void Desk desktop build for the classic frontend; QWASAR Link for the PC companion role.

Current foundation:

- `voiddesk.py` is the PC/development launcher.
- `build-packages.sh` builds a portable muOS `.muxapp` and a Debian `.deb`.
- The PC package currently launches the Pygame frontend and is not yet the complete QWASAR Link companion. The future launcher selects the installed Void Desk instance/flavour/engine after Linux has booted; it is independent of any GRUB OS selection.

QWASAR Link responsibilities:

- pair and manage handheld devices;
- display device status, battery, storage, connectivity and service health;
- transfer files to explicitly selected destinations;
- request screenshots/log bundles with user consent;
- provide an easy setup/pairing wizard for a software-KVM backend such as Input Leap where supported; its input-sharing feature does not carry video;
- forward remote input through an authenticated, narrow and revocable capability;
- provide a separate remote-view window with latency, resolution, bitrate and reconnect controls;
- manage pairing revocation and device trust.

Input Leap is a candidate keyboard/mouse sharing backend, not the remote-display implementation. Its endpoint must be available on both participating machines; the QWASAR Link wizard must probe platform support and offer a QWASAR-owned fallback rather than assuming a compatible handheld binary exists.

The old VOID BaseStation code is a prototype, not the security foundation for QWASAR Link. Its current defaults and SSH trust model require a full security redesign before reuse or exposure. Do not expose its embedded daemon as a production service.

Optional PC-only integrations:
- **GRUB2:** a separate bootloader adapter may preview and generate entries for complete bootable OS/rootfs installations, with mandatory backup, explicit consent and rollback. It never selects Pygame versus LÖVE inside the running Linux system and is never modified by ordinary Void Desk package installation.
- **VirtualBox:** an optional session provider for compatible PC hosts, initially Linux x86-64. QWASAR Link may expose a VM console remotely, but the H700 does not host VirtualBox natively. Oracle's VirtualBox 7.2 guide lists Linux x86-64 host packages, not Linux ARM64 in its supported host package matrix. See [installation](https://docs.oracle.com/en/virtualization/virtualbox/7.2/user/installation.html) and [host/guest combinations](https://docs.oracle.com/en/virtualization/virtualbox/7.2/user/Introduction.html).

### Device G — Browser, tablet, and phone

**Product:** QWASAR Studio (responsive web app/PWA).

Initial responsibilities:

- **Module Forge:** create a module from templates, define its manifest, add frontend adapters/assets/docs and inspect permissions;
- **Layout Designer:** rearrange NEXUS nodes, workspace sections, tiles and widgets like LEGO blocks;
- **Release Composer:** select Full/Essential/Slim or a custom safe module set, validate dependencies and request a reproducible build;
- **Community Library:** inspect, share and review portable profiles and, after trust infrastructure exists, executable modules;
- import/export and validate portable profiles locally, without requiring QWASAR Hub.

Mobile/tablet browsers are clients of Studio, not privileged device agents. They must never receive unrestricted shell, filesystem, or host-control access.

The first Studio milestone should work without accounts or cloud services through local profile editing, module-manifest validation and JSON import/export. Online publishing, device sync and controlled remote builds are opt-in and require QWASAR Hub or a dedicated build service.

### Device H — Optional QWASAR Hub host (PC, NAS, or server)

**Product:** QWASAR Hub  
**Status:** planned, not deployed.

Responsibilities:

- authenticate devices and manage revocable pairing credentials;
- store versioned, portable profiles and official catalogue metadata;
- coordinate device-initiated sync jobs;
- publish immutable profile/catalog revisions and integrity digests;
- provide an API for Studio and approved Link clients;
- retain audit events without collecting secrets or private device data.

Hub is optional. Void Desk remains useful without a Hub, Studio, account, or internet connection.

---

## 3. System layers and data flow

~~~text
                     QWASAR-ENV ECOSYSTEM
                              |
            +-----------------+------------------+
            |                 |                  |
        VOID DESK         QWASAR LINK        QWASAR STUDIO
     handheld frontend     PC companion       browser / PWA
       Pygame / LÖVE       PC agent + UI       profile editor
            |                 |                  |
            |                 +---------+--------+
            |                           |
    local capability API          authenticated HTTPS
            |                           |
    platform adapter                  QWASAR HUB
       muOS / H700              pairing / profiles / catalog
            |                    sync coordination / API
      host services
~~~

### Runtime layers

1. **Boot/launch layer:** optional PC bootloader selection for complete operating systems, then QWASAR pre-frontend selection of installed Void Desk instance, build flavour, engine, profile and session target.
2. **Frontend layer:** Pygame and LÖVE today; Qt 6, LVGL and Web are future adapters to the same QWASAR UI manifest.
3. **Void Desk local service:** owns local jobs and narrow privileged host operations. Frontends submit typed commands; they do not construct arbitrary shell commands.
4. **Platform adapter:** translates a capability request into the correct firmware/host-specific operation.
5. **QWASAR Hub:** optional remote control plane for identity, profile/catalog distribution, and sync coordination.
6. **QWASAR Studio / Link:** independent clients of Hub and approved device APIs; neither bypasses the trust boundary.

### Network and trust rules

- Local privileged APIs bind to loopback by default.
- Never expose the current Void Desk service directly to the public internet.
- Remote sync is device-initiated over authenticated HTTPS with revocable credentials and bounded jobs.
- LAN pairing, when implemented, requires explicit user confirmation, short-lived codes, origin checks, transport protection, rate limits, and revocation.
- A profile is declarative data only. It cannot contain shell commands, scripts, executable paths, arbitrary launch URLs, credentials, or privileged operations.
- Remote input and file transfer are separate capabilities and must be individually granted and revocable.
- Tailscale remains an optional connectivity integration, not the identity/security model for the whole ecosystem.

---

## 4. Repository boundaries and when to split

Do not create a repository for every screen or every device. Split when a component has an independent API, owner, build/test pipeline, and release lifecycle.

| Repository | Contents | Decision |
|---|---|---|
| `Void-Desk-Project` | Void Desk app, Pygame/LÖVE frontends, local service, schemas, device packaging, AppBuilder foundation | Keep as the active P0 repository |
| `muOS-Rt-Tailscale` | Independent Tailscale service manager and upstream lifecycle | Keep separate; consume as a pinned integration |
| `qwasar-studio` | Browser/PWA application | Create when Studio implementation starts |
| `qwasar-hub` | Server/API and device registry | Create when backend deployment starts |
| `qwasar-link` | PC companion and authenticated transport | Create when the legacy BaseStation prototype is replaced with a secure design |
| `qwasar-env` | Ecosystem-level index, version matrix, architecture links and cross-repository release metadata | Optional later; not needed to continue development now |
| `qwasar-runtime` | Shared runtime and platform adapter contracts | Do not split yet. First stabilise the contract inside Void Desk and prove reuse across two platform adapters |

### AppBuilder boundary

Keep Void Desk AppBuilder in the current repository while it builds and validates Void Desk packages. Extract it only when it can independently build more than one product/platform, has a stable input/output manifest, and no longer depends on private Void Desk internals.

The AppBuilder must eventually support:

- declarative application manifests and permissions;
- target-specific packaging (muOS first, then KNULLI/ROCKNIX after adapter validation);
- static validation and dependency checks;
- reproducible builds and SHA-256 manifests;
- signing/provenance before third-party distribution;
- safe install, upgrade, rollback and uninstall tests.

---

## 5. Void Desk LÖVE — current baseline

LÖVE is the next engineering focus. Pygame remains the behavioural reference, but LÖVE must become a genuinely usable alternative for the release scope rather than a screenshot-only prototype.

### What exists now

- LÖVE entry point: `love/main.lua`.
- NEXUS node metadata: `love/core/nodes.lua`.
- Scene modules: `love/scenes/`.
- Shared rendering, input, scene management, job state and file bridge: `love/core/`.
- Palette system: `love/theme/`.
- Python local service bridge: `love/core/bridge.lua` ↔ `service/voiddesk_service.py`.
- Current NEXUS catalogue contains 10 visible nodes, including End Session.
- Automated LÖVE capture currently enumerates 25 scenes. This proves that those scenes can be entered and rendered in the capture environment; it does not prove every action works or that hardware-specific behaviour is correct.
- The current action audit checks all static scene routes and visible NEXUS destinations, checks the service registration of bridge commands, and has focused action checks for Session, Forge, Workshop, Toolbox and MUOS APPS. It is not yet a complete semantic audit of every selectable row in every hub.
- A source-based, node-by-node status register is maintained in [LÖVE Frontend Gap Register](LOVE_FRONTEND_GAP_REGISTER.md).

### Verified gaps and boundaries

- MEDIA VAULT now has dedicated `void_radio` and `media_library` LÖVE scenes, already referenced by `hub_media.lua`. Void Radio calls the registered `radio_search`, `radio_favorites`, `radio_favorite_toggle`, `radio_play`, `radio_action` and `radio_status` handlers; Media Library calls `media_list`, `media_play` and `media_stop`. Mainline service tests cover bounded station data, catalogue IDs, player arguments, fixed media roots, supported extensions, symlink rejection and path traversal. CI scene/bridge checks do not yet certify controller interaction, radio network access or actual `mpv` audio/video playback on muOS/H700; those remain device acceptance gates.
- MUOS APPS now has service handlers for discovery and launch. Static tests verify that the scene calls both handlers and that the shell launcher validates the hand-off path. Real RG35XX-H testing is still required.
- INFO and FORGE use the registered `gh_fetch_releases` handler. The handler performs a bounded public release lookup and returns explicit errors; network/offline behaviour still needs device testing.
- IPTV has service handlers for playlist, EPG, play, stop and status. The LÖVE scene implements channel selection, group filtering and favourites. Playback still depends on the media player being installed and available on the target device.
- Workshop routes to Diagnostics, Monitor, APT system maintenance and Jobs. Forge exposes APT manager, desktop install/launch, shell and package jobs. Static route and bridge-registration tests pass; privileged operations require real-image/device tests.
- The screenshot batch currently enumerates 25 scenes, including Diagnostics and Monitor. Screenshot success is not an interaction or hardware test.
- The static audit covers route resolution and bridge registration globally, but only selected hubs have row-level action assertions. Extend row-level coverage to every visible NEXUS node before calling LÖVE feature-complete.
- Several INFO rows are informational status messages rather than navigable documentation pages. They should be labelled as such or connected to real content during the INFO pass.

These gaps are source-verified, not hardware-certified. For every missing operation choose one of: implement a safe backend handler, route to an existing verified implementation, or disable/hide the action with an explicit reason. Never report success before the backend confirms it.

---

## 6. LÖVE completion plan — execute in this order

### L0 — Build the action and capability registry

Create one machine-readable registry for all visible NEXUS nodes, child scenes and selectable actions.

Each entry must record:

- stable node/action ID and source scene;
- destination route (if any);
- service command / capability owner;
- firmware and dependency requirements;
- request schema and response fields;
- timeout, cancellation and busy-state behaviour;
- confirmation requirement for destructive operations;
- error/unavailable state;
- automated test and capture reference;
- physical-device validation result.

Extend the action audit beyond the four currently covered hubs. Include every visible node and all actions reachable from it.

**Exit:** no unknown routes, no silent no-ops, no success-shaped failures, and no visible placeholder actions.

### L1 — NEXUS, navigation, and controller contract

- Verify every visible node and child scene opens and returns correctly.
- Test scene-stack push/back/switch, focus restoration, repeated input, and pending-job cleanup.
- Test D-pad, A/B/X/Y, L1/R1, Start/Select, analog edge/deadzone behaviour, and keyboard fallback.
- Confirm text clipping, safe margins and readable focus at the handheld's target resolution.
- Provide a consistent busy/progress/error notification model across scenes.

**Exit:** complete NEXUS navigation can be performed with the handheld controls without a dead end.

### L2 — UPLINK

Complete and test:

- Wi-Fi status, scan, connect/disconnect and clear credential handling;
- Bluetooth status, scan and supported actions;
- hotspot enable/disable and dependency checks;
- Tailscale lifecycle, authentication QR, peers, exit nodes, Taildrop, autostart and recovery;
- Syncthing status, devices, folders, pause/resume, scan and confirmation flows;
- PC link status and clear disconnected/unpaired states.

Preserve single-daemon ownership and never expose keys/tokens in the UI, logs, exports or screenshots.

**Exit:** each operation has a validated service command, explicit result, and physical muOS test.

### L3 — THE FORGE and APT

- Search, installed packages, package details and version state;
- install/remove with dependency and disk-space review;
- update/upgrade/clean/autoremove with explicit confirmation where needed;
- serialized nonblocking jobs, progress, logs, cancellation and exit code;
- offline, absent chroot, unmounted image, read-only image and out-of-space states.

All APT operations must remain inside the optional Debian/Ubuntu image. Never run APT on muOS itself.

**Exit:** package operations pass in the real chroot on the H700 device; CI alone is not sufficient.

### L4 — START SESSION and RT:TOOLBOX

- Session launch/return hand-off for XFCE and supported desktop sessions;
- diagnostics and system monitor refresh without blocking input/render loops;
- storage, mount health, logs, cleanup, backup/restore and recovery guidance;
- shell via the existing bounded PTY service, not arbitrary command interpolation;
- calculator, clock, calendar and supported file tools;
- truthful state for unavailable tools and optional dependencies.

**Exit:** common maintenance journeys complete without leaving stale services or mounts.

### L5 — MEDIA VAULT, MUOS APPS, INFO, and external tools

- Media Library: safe browsing and launch of supported local media;
- Radio: playlist source, playback state, error recovery and volume controls;
- IPTV: playlist, EPG, group filtering, favourites and playback lifecycle;
- MUOS app discovery and launch through the supported firmware mechanism;
- update/release feed with timeout, cache and offline state;
- External Tools: signed/allowlisted registry entries, dependency checks and accurate install state.

**Exit:** no row implies functionality that is not available on the device.

### L6 — SETTINGS, visual system, accessibility and performance

- Theme/style and palette settings must be persisted and restored.
- Verify all visual styles implemented by LÖVE; do not claim a style based only on a palette name.
- Consistent typography, readable hierarchy, focus rings, disabled states and confirmation dialogs.
- Measure frame pacing, memory, startup, scene transitions and background-service polling on H700.
- Ensure screenshot/diagnostic capture redacts sensitive content.

**Exit:** LÖVE remains responsive and readable on the target hardware with effects enabled and disabled.

### L7 — Release and physical QA

- Unit tests for the scene manager, bridge, input model, service commands and schemas.
- Route/action registry test for all visible actions.
- Automated capture for every user-facing scene, with failure manifest.
- Pygame/LÖVE comparison for the declared feature set.
- Install, in-place upgrade, rollback and uninstall validation of the `.muxapp`.
- Physical tests on the RG35XX-H/muOS: cold boot, repeated launch/exit, sleep/resume, network loss, storage pressure, power-off, and service cleanup.
- Publish a compatibility table with exact device, firmware, app version, frontend and test date.

**Definition of done:** a user can complete every declared Void Desk journey in LÖVE on the RG35XX-H without encountering a placeholder, dead route, fake success, or unrecoverable state.

---

## 7. Cross-device roadmap after Void Desk

1. **Finish Void Desk first:** complete LÖVE, preserve Pygame stability, validate the package on H700/muOS.
2. **Freeze shared contracts:** define capability IDs, platform adapter interface, profile versioning, error model, pairing and sync protocol.
3. **QWASAR Hub foundation:** device registry, revocable credentials, profiles, immutable revisions, catalog metadata and audit events.
4. **QWASAR Studio v1:** local import/export and profile editor first; Hub-backed pairing/sync later.
5. **QWASAR Link:** replace the legacy BaseStation design with secure pairing, file transfer, telemetry and remote input. Add remote display only after latency and privacy requirements are met.
6. **Platform adapters:** KNULLI, ROCKNIX and custom Linux targets, each with its own hardware/firmware evidence.
7. **Runtime extraction:** extract Rt:QWASAR/shared runtime only when two or more adapters consume a proven stable contract.

Do not make the cross-device backend a prerequisite for the handheld application. Void Desk must remain independently usable.

---

## 7A. QWASAR Studio Store hosting

The selected v1 hosting direction is GitHub Pages for one static QWASAR Studio PWA. QWASAR Store, Module Forge, Layout Designer and Release Composer are workbenches in the same web application. The public JSON catalogue is static and generated from reviewed immutable release metadata; module/profile/package binaries are distributed from GitHub Releases. GitHub Actions validates and deploys the PWA. Pages is not the account, upload, moderation, device-pairing or remote-build backend. Those functions remain future QWASAR Hub responsibilities. See [QWASAR Store Portal Architecture](QWASAR_STORE_PORTAL.md).

## 8. Immediate next engineering increments

The first implementation work after this map should stay inside `Void-Desk-Project`:

1. Add LÖVE Diagnostics and Monitor to the automated scene capture set; deliberately exclude the generic stub from normal user-facing capture.
2. Expand the action/route audit from Session, Forge, Workshop and Toolbox to every visible NEXUS node.
3. Verify the live service handler table against every `bridge.call` made by LÖVE scenes.
4. Complete LÖVE Media Vault end-to-end and physical acceptance: route/action flow, radio online/offline, player availability, media start/stop and controller navigation; do not call it hardware-validated until tested on H700.
5. Complete the highest-priority UPLINK and Forge user journeys, testing each backend operation as it is connected.
6. Start the physical H700 acceptance checklist before declaring LÖVE complete.

No QWASAR Hub, Studio, Link, or runtime repository needs to be created to do this work. Keep the module contract and built-in registry in Void-Desk-Project while Void Desk LÖVE is completed.


## 9. Definitive launch, PC and tool-management model

### Boot and install selector

Do not conflate bootloader selection with renderer selection:

- GRUB2, when explicitly enabled on a compatible PC, chooses complete bootable OS/rootfs installations.
- QWASAR's pre-frontend selector runs after the host OS/firmware starts and chooses an installed Void Desk instance, Full/Essential/Slim/Custom flavour, frontend engine, profile and session target.
- muOS/H700 uses the existing muxapp launcher and never changes the handheld bootloader.
- Multiple Void Desk instances use unique IDs and isolated executable/package roots; they may coexist without overwriting one another. User data sharing requires explicit versioned migration.

### START SESSION

START SESSION launches independent environments, not individual utilities: graphical desktop environments, standalone terminal sessions, a paired PC workstation through QWASAR Link, and registered VirtualBox VMs on supported PC hosts. VirtualBox dependency installation/configuration lives in THE FORGE; VM selection/launch lives here.

### UPLINK and PC input

UPLINK owns online and inter-device connectivity. QWASAR Link on PC supplies the easy pairing/setup surface. Input Leap may be selected as a software-KVM backend when both endpoints and the display/input stacks support it; keyboard/mouse sharing is separate from video, remote desktop, file transfer and telemetry.

### THE FORGE vs RT:TOOLBOX

- THE FORGE installs, updates and removes APT packages, Void Desk package instances, QMOD modules, external tools and engine runtimes.
- RT:TOOLBOX uses and organizes tools already installed. It has exactly four categories: Everyday Tools; Files & Storage; System & Diagnostics; Developer & Terminal.
- QWASAR Inspector validates the installed structure in read-only mode.
- QWASAR Switchboard enables/disables modules, workspaces, sections, widgets, menu entries and global panels at profile level. Disable is not uninstall.

The detailed UI tree, component slots, engine adapter contract, menu entry format and manifest are in [QWASAR GUI System](QWASAR_GUI_SYSTEM.md). The current repository has the architecture/schema baseline only; dynamic composition and Switchboard/Inspector runtime commands are future implementation work.

