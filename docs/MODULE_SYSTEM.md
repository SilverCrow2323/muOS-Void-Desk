# Void Desk Modules — Architecture, Packaging and Community Contract

**Product:** Void Desk, part of QWASAR-Env  
**Status:** architecture proposal for the next implementation phase  
**First platform target:** H700 / muOS Andromeda  
**Frontends:** Pygame (reference) and LÖVE (completion priority)  
**Purpose:** define what a Void Desk "building block" is before implementing a module manager or community publishing.

This document is a design contract, not a claim that dynamic third-party modules, online publishing, signing, or custom package builds already exist.

---

## 1. Core product model

Void Desk is a **modular handheld control environment**. Its interface is a host shell; its visible sections, tools, integrations, and desktop launchers are contributions registered by modules.

A user must be able to:

- enable or disable a section without breaking the rest of the environment;
- reorder, rename, regroup, hide, or replace its visible tiles;
- add a module from the local module library or QWASAR Studio;
- create a module from a guided template;
- bind a section to installed APT applications in the optional desktop environment;
- export a profile/layout and share it with the community;
- update or remove a module without resetting unrelated modules or user data.

**The LEGO rule:** a section is not a hard-coded list of actions. It is a stable container with named contribution slots. Modules declare the slots they can fill; profiles decide which compatible contribution is visible and where it appears.

NEXUS remains the recognizable Void Desk home and navigation metaphor. The module system changes what its nodes and workspaces contain without forcing a route or package-identifier rename.

---

## 2. Three things that must not be confused

### A. Profiles and layouts — declarative composition

A profile describes how already-installed capabilities and modules are arranged.

Examples:

- move Tailscale above Syncthing in UPLINK;
- hide MEDIA VAULT and place a local media tool in TOOLBOX;
- rename a section and change its icon or palette;
- create a developer-focused layout;
- select which optional modules should be enabled.

A profile is JSON data. It cannot contain executable code, shell commands, scripts, binary payloads, arbitrary URLs, credentials, or privileged operations.

Sharing a profile never silently installs a module.

Suggested portable extension: `.qprofile` (JSON document; extension is a proposal). Existing Void Desk profile JSON and schema v1 remain compatibility inputs during migration.

### B. Modules — functional building blocks

A module provides a feature, tool, integration, dashboard, widget, or group of related actions.

Examples:

- Wi-Fi manager;
- Tailscale panel;
- Syncthing panel;
- APT catalogue;
- diagnostics widget;
- file manager;
- radio/player tool;
- a desktop application launcher;
- a user-created developer workspace.

A module has a stable ID, version, manifest, supported target adapters, UI contribution, capability declarations, dependency list, permission list, settings schema, assets, documentation, tests, provenance, and (for executable packages) a verified signature.

Suggested package extension: `.qmod`, a deterministic ZIP-based module bundle containing `module.json` and the declared files. This is a proposed format and must be versioned before implementation.

### C. Desktop APT packages — applications installed in XFCE

APT packages are not Void Desk modules and are not installed into the muOS host.

Void Desk can discover, install, remove, update and launch packages **inside the optional Debian/Ubuntu desktop image**. A module may declare the APT packages it needs and the application launchers it contributes, but it must call the existing typed package/session service rather than run raw `apt` or shell commands.

Examples:

- install `htop` in the XFCE image and expose it as a desktop tool;
- install a browser in the image and create a launcher tile;
- declare a group of developer packages for the desktop environment.

The module's APT declaration is a package list/recipe with compatibility metadata, not an arbitrary pre-install or post-install script.

---

## 3. Modular interface model

The UI has a stable shell and replaceable contributions.

### Stable shell (owned by Void Desk)

- NEXUS home navigation and global input dispatcher;
- header/footer and shared visual tokens;
- workspace/container layout;
- notification, progress and error surfaces;
- profile selection and module manager;
- capability broker and local service bridge;
- safe recovery / return-to-muOS path.

The shell must remain operable even when a third-party module fails to load or is disabled.

### Contribution slots

A module may declare one or more supported contributions:

| Slot | Purpose | Example |
|---|---|---|
| nexus.node | A visible top-level NEXUS destination | MEDIA VAULT |
| workspace.section | A category within a workspace | RT:TOOLBOX / Files & Storage |
| shell.header.* / shell.footer.* | A composable global header/footer slot | Battery, profile and controller hints |
| home.left / home.right | A panel on either side of the NEXUS home | Favourites and telemetry |
| overlay.media | The global media panel opened with M | Shared now-playing controls |
| hub.panel | A panel or page inside a stable hub | Tailscale status |
| menu.tile | A selectable tool/action tile | Calculator |
| dashboard.widget | A bounded status/graph widget | Battery and storage |
| session.target | A standalone desktop/terminal/PC/VM target | XFCE or terminal session |
| `service.provider` | A typed capability implementation registered by the host | Media status provider |
| `desktop.launcher` | A launcher for an installed XFCE application | Browser |
| `theme.pack` | Palette, typography and visual assets | Manga Ink |
| `workflow.action` | A reviewed sequence of typed actions | Refresh package lists |

A contribution must declare its slot, stable contribution ID, display metadata, target route, required capabilities, and fallback state. It may only target slot types supported by the installed Void Desk version.

A profile can rearrange or hide a registered contribution. It cannot invent a new executable route or bypass the module registry.

### Layout composition

Each workspace has a stable ID and an ordered list of contribution slots. A profile stores:

- workspace visibility and ordering;
- section ordering and grouping;
- module/contribution references;
- labels, descriptions and icon overrides;
- enabled/disabled state;
- safe, schema-validated settings;
- conditions based on declared platform capabilities.

Stable IDs are independent from translated or user-edited labels. Removing a module leaves an unresolved reference that the manager can explain and repair; it must not redirect to an unrelated route.

---

## 4. Canonical module bundle structure

Proposed `.qmod` bundle layout:

~~~text
module-root/
├── module.json              # required manifest
├── README.md                # required user-facing documentation
├── LICENSE                  # required licence
├── CHANGELOG.md             # recommended
├── assets/
│   ├── icons/
│   ├── images/
│   └── audio/                # only when needed and licensed
├── locales/
│   └── en.json
├── ui/
│   ├── common/               # engine-neutral view metadata / resources
│   ├── pygame/               # optional Pygame adapter
│   └── love/                 # optional LÖVE adapter
├── adapters/
│   ├── muos/                 # optional platform-specific adapter metadata
│   ├── knulli/
│   ├── rocknix/
│   └── desktop/
├── schemas/
│   └── settings.schema.json # optional module settings schema
├── tests/
│   ├── manifest/
│   ├── contract/
│   └── fixtures/
└── provenance/
    └── build.json            # reproducible build/source metadata
~~~

Not every module needs every directory. The manifest must list all package files and their SHA-256 hashes. Bundles reject path traversal, symlinks, duplicate paths, unexpected executable bits, oversized assets, and undeclared files.

### Engine-neutral logic and frontend adapters

- Keep domain logic and data contracts separate from rendering.
- A module may provide a Pygame adapter, a LÖVE adapter, or both.
- A module without a compatible frontend adapter is not shown as installable for that engine.
- The module manager never assumes that a Pygame screen can run inside LÖVE or vice versa.
- Platform adapters are separate again: a UI may be available in LÖVE but a device operation may still be unsupported on KNULLI or ROCKNIX.

Feature availability is the intersection of module compatibility, frontend adapter, platform adapter, device capability, dependencies and user permissions.

---

## 5. Manifest contract

The proposed `module.json` is the source of truth for module identity and compatibility. A future `qwasar-module.schema.json` must validate it with a strict schema and reject unknown executable fields.

Required manifest fields:

| Field | Meaning |
|---|---|
| `manifestVersion` | Module manifest contract version |
| `id` | Stable reverse-DNS-like identifier, e.g. `community.network.wifi-manager` |
| `name`, `description` | Localisable display metadata |
| `version` | Semantic version |
| `publisher` | Stable publisher ID and display name |
| `license` | SPDX identifier or explicit reviewed licence reference |
| `compatibility` | Void Desk API range, engines, firmware targets, device families and architectures |
| `contributions` | Slot type, contribution ID, entry route and display metadata |
| `capabilities` | Typed APIs the module needs |
| `permissions` | User-visible permission requests mapped to capabilities |
| `dependencies` | Module IDs and compatible version ranges |
| `desktopPackages` | Optional APT package declarations for the XFCE image |
| `settingsSchema` | Schema for non-secret user settings |
| `files` | Package path, size and SHA-256 for every file |
| `entrypoints` | Approved engine-adapter entrypoints (when executable modules are enabled) |
| `tests` | Declared contract tests and supported validation command IDs |
| `artifact` | Immutable HTTPS artifact URI, digest and size |
| `signature` | Detached signature algorithm, key ID and signature |

Example manifest (illustrative v1 shape, not a currently installable module):

~~~json
{
  "manifestVersion": "1.0",
  "id": "community.network.wifi-dashboard",
  "name": "Wi-Fi Dashboard",
  "description": "A compact Wi-Fi status and scan panel.",
  "version": "1.2.0",
  "publisher": {
    "id": "community-example",
    "displayName": "Community Example"
  },
  "license": "MIT",
  "compatibility": {
    "minimumVoidDeskApi": "1.0",
    "engines": ["py", "love"],
    "platforms": ["muos"],
    "deviceFamilies": ["h700"],
    "architectures": ["aarch64"]
  },
  "contributions": [
    {
      "id": "wifi-dashboard.main",
      "slot": "hub.panel",
      "route": "community.network.wifi-dashboard.main",
      "label": "Wi-Fi",
      "icon": "assets/icons/wifi.svg"
    }
  ],
  "capabilities": ["network.read-status", "network.wifi.scan"],
  "permissions": ["read-network-status", "scan-wifi"],
  "dependencies": [],
  "desktopPackages": [],
  "settingsSchema": "schemas/settings.schema.json",
  "entrypoints": {
    "pygame": "ui/pygame/main.py",
    "love": "ui/love/main.lua"
  },
  "artifact": {
    "url": "https://example.invalid/wifi-dashboard-1.2.0.qmod",
    "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
    "sizeBytes": 42000
  },
  "signature": {
    "algorithm": "ed25519",
    "keyId": "community-example-2026",
    "value": "REPLACE_WITH_DETACHED_SIGNATURE"
  }
}
~~~

The example's URL and digest are placeholders. A real module cannot be installed until the artifact exists, its digest matches, its signature chains to a trusted publisher, and every requested capability is approved.

---

## 6. Capability and permission model

Modules do not call arbitrary shell commands, directly edit system files, or open arbitrary network listeners. They request typed capabilities from the Void Desk host.

Initial capability families:

| Capability family | Example IDs | Notes |
|---|---|---|
| Device read | `device.read-status`, `device.read-storage` | Read-only by default |
| Network | `network.read-status`, `network.wifi.scan`, `network.wifi.connect` | Credential entry remains in a trusted host UI |
| Connectivity services | `tailscale.read`, `tailscale.manage`, `syncthing.read`, `syncthing.manage` | Keys and service identity remain inside trusted service layer |
| Media | `media.read-state`, `media.playback.control` | Only registered media backends |
| Packages | `desktop.apt.search`, `desktop.apt.install`, `desktop.apt.remove` | XFCE image only; package names validated by host |
| Desktop session | `desktop.session.read`, `desktop.session.launch` | Session hand-off through launcher |
| Storage | `storage.user-data.read`, `storage.user-data.write` | App-private or explicitly chosen locations |
| UI | `ui.notification`, `ui.widget.register` | Cannot replace the system shell or steal global input |
| Remote link | `link.device.status`, `link.file-transfer`, `link.remote-input` | Separate opt-in and revocable permission |

### Permission levels

1. **Passive:** read public app metadata or local UI state.
2. **Read-only device:** status, diagnostics and storage metadata.
3. **User-mediated:** package install/remove, file selection, network connect and session launch.
4. **Sensitive remote:** file transfer, remote input and remote display; disabled until explicitly paired and granted.
5. **Forbidden to community modules:** arbitrary root shell, bootloader/init modification, unrestricted host filesystem, credential/key extraction, secret logging, internet-facing privileged API, or silent persistence.

Permissions are granted per module and can be revoked. Destructive actions require a host-owned confirmation dialog that shows the exact target. A module cannot draw a fake confirmation dialog and then call a hidden privileged operation.

---

## 7. APT and desktop integration contract

Void Desk owns the user experience; each platform package adapter owns its package database. On H700, APT operates only inside the optional Debian/Ubuntu desktop image. On a supported Linux PC, a separate host-APT adapter may operate on the PC host only after explicit user authorization. APT is never run against the muOS Buildroot host.

A module may declare a package set:

~~~json
{
  "desktopPackages": [
    {
      "name": "htop",
      "versionConstraint": ">=3.0",
      "architectures": ["arm64"],
      "required": false,
      "purpose": "Interactive process monitor inside XFCE"
    }
  ]
}
~~~

Rules:

- Package names are validated against a conservative package-name grammar.
- No `preinst`, `postinst`, arbitrary command, shell fragment or repository override is accepted from a community module.
- On H700, APT operations are submitted through the Void Desk service job manager and executed only inside the configured Debian/Ubuntu image.
- On PC, host package management is a separate, opt-in package adapter that requires an explicit host authorization/admin prompt and reports the target machine/package database before mutation.
- The package manager serializes mutations and reports progress, exit code and bounded logs.
- A missing desktop image is a clear dependency state. Void Desk offers the trusted desktop-image installer rather than attempting APT on muOS.
- Package management is never exposed as an arbitrary shell command to third-party modules.
- A desktop launcher is registered only after the application is confirmed installed.
- Removing a module does not automatically purge APT packages that may be shared with other modules. Show an orphan/dependency report and require explicit confirmation.
- The optional XFCE root filesystem is distributed/provisioned separately from the core `.muxapp` to avoid forcing every handheld user to download a multi-gigabyte desktop image. Full flavour includes all desktop integration modules and the installer, not necessarily the desktop image bytes.

This lets a user build a developer workstation-like section, a media section, or a maintenance workspace while preserving a clean package and trust boundary.

---

## 8. Community library and trust tiers

Community sharing has three different trust tiers.

### Tier 1 — Profiles and layout packs

- Declarative data only.
- No executable code.
- Validate locally and preview before applying.
- Safe to share broadly after schema and content checks.
- Never auto-installs missing modules.

### Tier 2 — Desktop package recipes and launch profiles

- Declarative APT package names, categories, and launcher metadata only.
- No scripts or arbitrary repositories.
- Host checks distro/image compatibility and asks before package operations.
- Recipes cannot silently remove or replace packages.

### Tier 3 — Executable feature modules

- Require publisher identity, immutable artifact digest and detached signature.
- Require capability declarations, permission review, code review and compatibility tests.
- Official modules are allowlisted by the signed official catalogue.
- Community executable modules remain disabled until a module runtime with process isolation/sandboxing, resource limits, revocation and update rollback exists.
- An imported unsigned module can be inspected as source but must not be executed merely because it was shared by another user.

A public module page should show publisher, source repository, version, licence, supported devices/firmware/engines, required capabilities, dependencies, digest, signature state, update date, review status and known issues.

Community uploads must never be able to replace an official publisher ID or masquerade as an official module.

---

## 9. Module lifecycle

1. **Discover:** Studio Library or local package index shows compatibility, version, publisher, permissions and dependencies.
2. **Inspect:** user opens manifest, source/provenance, licence, permissions, package list and change log.
3. **Resolve:** host checks Void Desk API, engine/platform adapter, device capabilities and dependency graph.
4. **Verify:** validate schema, archive paths, all file hashes, publisher signature, licence and trust tier.
5. **Review:** show exact capabilities and requested permissions; require user confirmation.
6. **Stage:** unpack into a temporary versioned directory, never overwrite the active module.
7. **Test:** run manifest/contract checks and adapter availability checks.
8. **Activate:** atomically switch the module registry/profile reference.
9. **Monitor:** capture bounded module health/error events; isolate failure and allow immediate disable.
10. **Update/rollback:** stage new version, preserve module data, migrate settings transactionally and keep the previous version.
11. **Remove:** disable contributions, stop owned jobs, release resources, preserve or explicitly delete namespaced data, and report shared APT packages.

The system shell and recovery path must never depend on a third-party module.

---

## 10. QWASAR Studio — one web app, four workbenches

Do not build a separate web app for each builder operation. QWASAR Studio is one responsive PWA; its navigation contains four related workbenches.

### Module Forge

- Create a module from templates: dashboard widget, tool tile, hub panel, service integration, desktop launcher, theme pack or APT recipe.
- Edit and validate `module.json`.
- Add translations, icons, documentation and engine adapters.
- Inspect capability and permission requests.
- Run schema/static checks and create a reproducible module bundle.
- Produce a source repository/pull request workflow for executable community modules.

### Layout Designer

- Build a Void Desk layout visually, like LEGO blocks.
- Add/remove/reorder NEXUS nodes, sections, tiles and widgets.
- Configure which installed modules contribute to each section.
- Edit labels, descriptions, icons, palettes and visual styles.
- See missing dependencies, unsupported engines and incompatible modules before export.
- Preview target resolutions and controller navigation order.

### Release Composer

- Choose Full, Essential, Slim or a custom set of first-party modules.
- Select target: H700/muOS first; other platforms only when adapters are validated.
- Inspect size estimate, dependency closure, APT desktop requirements and compatibility.
- Create a build manifest and invoke a controlled, reproducible build pipeline.
- Verify checksums and provenance; download the `.muxapp` and SHA-256 sidecar.
- Produce an installable official release only through the signed maintainer pipeline. Personal custom builds are clearly marked as custom and cannot claim official signatures.

### Community Library

- Search, sort, inspect, rate/report and follow modules and profiles.
- Distinguish official, reviewed community, unreviewed source, and incompatible/withdrawn entries.
- Show compatibility and permissions before download.
- Share profiles independently of module code.
- Link each executable module to its source, immutable release and trust status.

### Online/offline split

The first Studio release must work locally with import/export and profile editing even when QWASAR Hub is absent. Online community publishing, device sync, accounts and release builds are additive services, not prerequisites to customise Void Desk.

---

## 11. Void Desk release flavours

All official flavours use the same source revision, app version, API contract and build pipeline. The difference is the installed module set and optional content, not a forked application.

| Flavour | Intended user | Included content | Omitted / deferred |
|---|---|---|---|
| **Full** | Users who want the complete Void Desk experience | Core shell, all maintained first-party modules, all supported integrations, tools and desktop-management modules | Large optional desktop image remains a separately verified add-on/download |
| **Essential** | Daily use with a curated core | Core shell, session, settings, diagnostics, connectivity essentials, package manager and essential tools | Experimental, specialised and large optional tools |
| **Slim** | Minimal storage footprint / users building their own setup | Core launcher, shell, module manager, profile engine, basic settings and diagnostics | Optional integrations and most tools; install them later from Studio/module sources or trusted packages |

### Package contents and naming

Proposed release assets:

- `Void-Desk-<version>-Full.muxapp`
- `Void-Desk-<version>-Essential.muxapp`
- `Void-Desk-<version>-Slim.muxapp`
- matching `.sha256` files;
- a machine-readable build manifest and module lockfile for each flavour;
- optional desktop image/add-on as a separate asset with its own digest and compatibility note.

The exact package filenames can be changed before the first multi-flavour release. Keep one shared product version and one source commit; do not publish three divergent codebases.

Full means every maintained and compatible first-party module is bundled. It does not mean every optional third-party APT program or the entire desktop root filesystem is embedded in the handheld package.

### Release-page hand-off to Studio

Every GitHub Release should include a prominent link to **QWASAR Studio → Release Composer** so users can:

- compare Full / Essential / Slim;
- build a custom module selection/profile;
- inspect module manifests and dependency requirements;
- download official flavours or prepare a custom build when that service is available.

The Studio URL is not yet deployed, so do not put a fake URL in release notes. When the domain and production app exist, define one stable route (for example `/builder`) and retain it across Studio versions.

---

## 12. Repository and build boundaries

- Keep the current `Void-Desk-Project` repository as the source of Void Desk, built-in modules, platform adapters, module schemas and local package-build engine.
- Keep the current `build-packages.sh` / `tools/build_muxapp.py` path as the first AppBuilder engine. Add flavour selection only after the module registry and module lockfile exist.
- QWASAR Studio will later be its own web application/repository, but its four workbenches remain one product.
- QWASAR Hub can be a separate server/API repository when deployment begins.
- QWASAR Link can be a separate PC companion repository when its secure protocol is designed.
- Do not create an independent repository for every module. Modules may live in their own source repositories when independently maintained, or in a first-party monorepo with versioned release bundles.
- Do not extract Rt:QWASAR into a repository before at least two stable platform adapters consume the same proven capability contract.

---

## 13. Implementation sequence

### Phase 0 — documentation and contract

- Agree the slot, manifest, capability, permission, trust and release-flavour vocabulary.
- Map current hard-coded hubs and tools to stable module/contribution IDs.
- Inventory all operations that already call the service and verify each handler.

### Phase 1 — Void Desk built-in module registry

- Convert the current NEXUS/hub/tool catalogue into a machine-readable registry.
- Mark each built-in module as built-in, optional, unavailable or experimental.
- Make Pygame and LÖVE read the same registry where practical.
- Add module enable/disable, contribution ordering and profile persistence without executing downloaded code.

### Phase 2 — LÖVE frontend completion

- Finish all visible LÖVE user journeys against the capability registry.
- Remove placeholders and ensure every action has a handler, result, timeout and error state.
- Make every supported section configurable from the profile/layout model.
- Add controller-navigation and hardware acceptance tests.

### Phase 3 — safe module packages and AppBuilder

- Implement strict module schema, deterministic `.qmod` build and validation.
- Package first-party modules and verify digest/signature.
- Add atomic install/update/rollback and permission review.
- Add Full/Essential/Slim lockfiles and reproducible `.muxapp` flavours.

### Phase 4 — QWASAR Studio

- Ship local Layout Designer and Module Forge with profile import/export first.
- Add Release Composer for official flavour selection.
- Add Hub-backed library, publishing and sync only after trust and signing services are operational.

### Phase 5 — community executable modules and other devices

- Introduce a sandboxed module host and publisher review/revocation workflow.
- Validate platform-specific adapters for KNULLI, ROCKNIX and custom systems.
- Publish compatibility evidence per device/firmware/engine combination.

---

## 14. Non-negotiable acceptance rules

- A profile is data only; it never executes.
- A module cannot exceed its declared and granted capabilities.
- No community module executes arbitrary root shell or edits protected firmware paths.
- APT packages are installed only inside the optional Debian/Ubuntu desktop image.
- The XFCE image is optional and independently verifiable.
- A missing/incompatible module never makes the base shell or recovery path unusable.
- Official and community trust states are visually distinct.
- Install/update/rollback are atomic and leave user data intact.
- Full/Essential/Slim are reproducible variants of one source revision and one API contract.
- A green screenshot capture is not proof that a module action or device operation works.
- QWASAR Studio is one web app; Module Forge, Layout Designer, Release Composer and Community Library are workbenches, not four separate products.



## 15. QWASAR UI composition and engine adapters

The canonical interface contract is documented in [QWASAR GUI System](QWASAR_GUI_SYSTEM.md) and versioned by schemas/qwasar-ui.schema.json with the default data/qwasar_ui_manifest.json.

Pygame and LÖVE are the first rendering adapters. Qt 6, LVGL and Web are reserved future adapters. The engine adapter owns rendering and input translation only; business logic, menu definitions, widget data providers and privileged commands remain engine-neutral.

The shell is composable: header, footer, NEXUS side panels and global overlays are declared regions/slots, not engine-specific screens. The M shortcut is a semantic action that opens the shared media overlay without changing the current workspace.

A workspace selects a visual template. START SESSION is a session selector; THE FORGE is the package workbench; UPLINK is the network/online console; MEDIA VAULT is the media workbench; RT:TOOLBOX is a four-category tool workbench; SETTINGS is a schema-backed settings editor; INFO/COMMUNITY is a reference library; END NODE is the safe exit surface.

## 16. Tool inventory, verification and activation

The four RT:TOOLBOX categories are:

1. **Everyday Tools** — calculator, clock/timer, calendar, notes, text editor and quick utilities.
2. **Files & Storage** — file manager, File-GD X, archives, checksums, backup/restore and storage analysis.
3. **System & Diagnostics** — Void Diag, Void Monitor, service health, logs, cleanup and safe repair.
4. **Developer & Terminal** — bounded shell, Python console, builders, manifest tools and developer utilities.

THE FORGE installs, updates and removes packages, Void Desk builds, modules and runtimes. RT:TOOLBOX lists, launches, arranges and monitors the tools already installed. Disabling a tool or section does not uninstall its package.

Two host-owned utilities are required:

- **QWASAR Inspector:** read-only structure verification for schemas, manifests, component IDs, module files, menu/action/route/provider resolution, dependencies, engine/platform compatibility, permissions, assets, and package integrity. It produces a report and repair suggestions; no automatic destructive repair.
- **QWASAR Switchboard:** activate/deactivate modules, workspaces, sections, widgets, menu entries and global panels in the user profile. It previews the change, validates required dependencies, writes atomically and offers rollback to the last valid profile.

The state model distinguishes installed, enabled, visible, available, running, unavailable, incompatible and error. A profile may hide a contribution without disabling its provider. A disabled module must stop providers/jobs owned only by that module; shared dependencies remain active while still referenced. Core shell, launch selector and recovery surfaces are protected from user disablement.

The future CLI may expose read-only verification and profile-level controls, such as “voiddesk verify --all”, “voiddesk doctor” and “voiddesk feature enable/disable stable-id”. These are design targets, not existing command contracts until implemented and tested.

