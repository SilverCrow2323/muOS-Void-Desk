# QWASAR Studio — Technical Architecture

**Product:** QWASAR Studio, the browser companion for QWASAR-Env  
**Status:** accepted product direction; foundation specification  
**Scope:** unified web workbench for module authoring, LEGO-style layout composition, release building, community library, portable profiles, and device sync  
**Initial runtime targets:** Pygame (py) and LÖVE (love). Qt 6 and LVGL are future adapters, not currently supported runtimes.

## Product decisions

- Studio is a responsive web app/PWA companion. The handheld remains usable without Studio or internet access.
- Users can export/import profiles and share declarative layout packs without an account.
- Module authoring and release composition are integrated into this same Studio application; there is no separate web AppBuilder product.
- Profile/layout sharing is data-only. Executable module publishing uses separate trust tiers and is disabled until signing, review, capability enforcement, and sandboxing are operational.
- Official executable modules are allowlisted by the signed catalogue. Community executable modules require review and must not execute simply because they were uploaded.
- Profiles are declarative data: NEXUS/workspace composition, menu ordering, labels, descriptions, icons, contribution references, supported feature toggles, safe module settings, and visibility conditions.
- Profiles cannot contain shell commands, scripts, executable paths, arbitrary launch URLs, credentials, or privileged operations.
- One engine-neutral profile format is consumed by all frontend adapters.

## System context

~~~text
Browser / PWA --HTTPS--> Studio API (planned)
     |                         |
     | import/export           +--> profile store / signed official catalog
     |
     +---- local JSON profile
                |
                v
       Void Desk local service
                |
                +--> validator + migration
                +--> Configuration Engine
                |      +--> Pygame adapter (current)
                |      +--> LÖVE adapter (current; parity incomplete)
                |      +--> Qt 6 adapter (future)
                |      '--> LVGL adapter (future)
                '--> official plugin manager
~~~

The hosted Studio API is a future component; this repository defines its contracts and data formats, not a deployed cloud service. The local service remains authoritative when applying settings.

## Device connectivity and trust boundaries

The existing local service performs privileged host operations. Keep it bound to loopback by default and do not expose it to the internet or an untrusted LAN. For future remote sync, prefer a device-initiated outbound HTTPS connection using a revocable device token and short-lived jobs. Do not require inbound ports on the handheld. Any LAN pairing mode needs a separate security design, explicit confirmation, short-lived pairing codes, origin checks, and transport protection.

Portable JSON import/export is the v1 baseline and must work without an account or cloud service. Cloud sync is opt-in and additive.

## Components

### Studio web companion

- Layout Designer: compose NEXUS nodes, workspaces, sections, tiles and widgets; reorder/hide/replace registered contributions and preview controller navigation.
- Profile library: local profiles/layout packs, import/export, validation, migration and duplicate detection.
- Module Library: inspect module manifests, source, dependencies, compatibility, permissions, licence, digest and trust state.
- Device view: display paired-device metadata and supported engines only after explicit pairing.
- Sharing: publish declarative profiles independently from executable module packages; the latter require the separate review/signing policy.

The initial client should be a static, progressively enhanced PWA. Do not place device credentials in exported profiles or browser storage without a dedicated credential design.

## One Studio application, four workbenches

QWASAR Studio is one responsive PWA. The following are workbenches inside it, not separate products or repositories:

### Module Forge

- Guided templates for a widget, menu tile, hub panel, service integration, desktop launcher, theme pack or APT recipe.
- Manifest editor and strict schema/static validation.
- Engine adapters for Pygame and LÖVE, plus platform compatibility declarations.
- Capability and permission inspector, dependency resolver, asset/localisation manager and reproducible `.qmod` export.
- Source/review workflow for executable community modules.

### Layout Designer

- LEGO-style canvas for NEXUS nodes, workspace sections, menu tiles and dashboard widgets.
- Drag/reorder, hide/disable, rename, regroup and replace registered contributions.
- Device/engine preview, missing-module warnings and compatibility/dependency report.
- Export a declarative `.qprofile`; never embeds executable code or silently installs referenced modules.

### Release Composer

- Select Full, Essential, Slim, or a custom permitted set of first-party modules.
- Show module closure, target platform, package-size estimate, desktop image requirements and compatibility.
- Generate a build manifest and invoke a controlled/reproducible build pipeline.
- Verify build provenance and SHA-256 outputs.
- Official release signing is maintainer-controlled. A personal custom package must be visibly labelled custom and must not impersonate an official signed release.

### Community Library

- Search and inspect profiles, layout packs, desktop package recipes and (when enabled) executable modules.
- Show publisher/source, licence, compatibility, capabilities, permissions, digest, signature and review state.
- Distinguish official, reviewed community, source-only/unreviewed, incompatible and withdrawn content.
- Publishing/review is not the same permission as sharing a data-only profile.

The local Studio milestone must provide profile import/export, layout editing and module-manifest validation without login or cloud access. Hub-backed community publishing and remote builds are later, optional services.

## Profile format and Configuration Engine

Canonical versioned JSON Schemas live under schemas/. A profile contains stable identity and metadata, compatibility constraints, an engine preference, a declarative menu/workspace composition, typed visibility conditions, and references to installed module contributions with non-secret settings.

The engine validates and migrates a profile before applying it. It merges profile overrides with built-in defaults and does not rewrite the user's base configuration. Activation is transactional: validate, stage, back up the current selection, atomically activate, and retain rollback. Unknown executable/action fields are rejected.

The existing data/desk_config.json remains the legacy runtime configuration during migration. Do not replace it wholesale. A future compatibility adapter maps only supported settings into the canonical model and writes through existing safe I/O helpers.

### Version 1 compatibility identifiers

The classic handheld application is **Void Desk**, the browser companion is **QWASAR Studio**, and both are components of **QWASAR-Env**. Version 1 of the profile and plugin contracts deliberately keeps its original technical identifiers so existing drafts, tools and future importers do not need a silent breaking rename:

- Schema filenames and profile IDs such as `voiddesk-starter` remain stable.
- The profile compatibility property `minimumVoidDeskVersion` keeps its v1 spelling even though it refers to the minimum **Void Desk** runtime version.
- The official plugin publisher ID `voiddesk-official` and display name `Void Desk Official` remain reserved v1 compatibility values. Do not change them independently: a public publisher-identity migration requires a new manifest/schema version and an explicit migration path.
- These identifiers are not the displayed product brand and must not be used for new user-facing copy.

## Menu and condition model

Menu array order determines presentation order. Stable item IDs are independent of labels. Routes must resolve to entries registered by the installed Void Desk build.

Visibility conditions use a closed vocabulary and are evaluated locally:
- key_sequence: bounded sequence of known controller keys.
- device_family: known platform/device family.
- feature_available: registered capability identifier.

Cheat-code sequences are easter-egg/discovery controls only. They are not authentication, authorization, encryption, or a security boundary. A hidden entry must never grant capabilities or bypass permission checks. Sequences have length/time bounds and reset on focus loss or timeout.

### Module runtime and official/community module manager

The module bundle and capability contract is defined in [Void Desk Modules](MODULE_SYSTEM.md) in the Void Desk repository. A profile can reference installed module IDs but cannot install code. The runtime verifies manifest, digest, signature, compatibility and permissions before staging/activation. Community executable modules remain disabled until a sandboxed module host, resource limits, revocation and rollback are implemented.

### Module manager

Executable modules are separately versioned bundles with a manifest, compatibility range, declared capabilities, immutable artifact digest and detached signature.

- The legacy v1 `voiddesk-plugin` contract remains official-publisher-only for compatibility. Do not silently broaden its fixed publisher ID.
- The proposed `.qmod` contract can support reviewed community publishers only after signing, source review, capability enforcement and sandboxing exist.
- Verify signature, digest, schema, compatibility and permissions before installation.
- No arbitrary shell execution. Privileged integrations require reviewed host-side capabilities with narrow typed APIs.
- Install, update, disable and remove are explicit actions. Updates are staged and rollback-capable.
- Profiles may reference module IDs and configure schema-approved non-secret options. Sharing a profile never silently installs a module. Missing modules are reported and can be resolved separately through the module library.

The manifest schema is not proof that signing/distribution already exists. Key management, rotation, revocation, publisher review and the sandboxed runtime must be implemented before community executable module installation is enabled.

### Multi-engine and multi-version

Profiles are engine-neutral. Each frontend adapter advertises supported routes, controls and capabilities. Pygame is the primary current frontend; LÖVE exists but is not feature-equivalent. Qt 6 and LVGL remain future adapters until implemented and tested.

Runtime version management is separate from profile management. Profiles may declare a minimum Void Desk version and preferred engine, but cannot install or switch binaries. Multi-version installation, boot selection, update channels and rollback belong to a separate package/boot manager.

## Planned API contract (not deployed)

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /v1/catalog/modules | Signed module index and trust state |
| GET | /v1/modules/{module_id}/versions/{version} | Immutable module manifest/artifact metadata |
| POST | /v1/module-submissions | Submit a module for review; never auto-publish |
| GET | /v1/catalog/plugins | Legacy v1 official plugin index during migration |
| GET | /v1/profiles/{profile_id} | Read a shared profile/layout |
| POST | /v1/profiles | Publish a user-approved declarative profile |
| POST | /v1/profiles/{profile_id}/revisions | Publish immutable profile revision |
| GET | /v1/release-flavours | Read supported Full/Essential/Slim manifests |
| POST | /v1/builds | Request a controlled build from an allowlisted manifest |
| GET | /v1/builds/{build_id} | Read build status, provenance and artifact hashes |
| GET | /v1/devices | List paired devices |
| POST | /v1/devices/pairing-sessions | Start short-lived pairing |
| POST | /v1/devices/{device_id}/sync-jobs | Queue a device-initiated sync |

Every write must be authenticated, authorized, size-limited, schema-validated, rate-limited and auditable. Use immutable revisions and content digests. Never share tokens, Wi-Fi credentials, local paths, IP addresses, device IDs, logs or personal files.

## Sharing and privacy

- Sharing is off by default and requires preview plus explicit confirmation.
- Export only an allowlist of portable fields; strip device identifiers and secrets.
- Profiles are data only. Import cannot execute commands or install modules.
- Executable module packages are distributed only through the approved module library. Profiles may declare module dependencies but cannot bundle module code.
- Show provenance, version, compatibility, permissions, digest, review state and update date for every module.

## Rollout

1. Foundation: module manifest, contribution-slot, capability/permission contracts, profile schema and sample layout.
2. Local engine: module registry, schema validator/migration, profile composer and read-only compatibility report; no cloud dependency.
3. Web workbenches: Module Forge, Layout Designer and local import/export/preview.
4. Release Composer: reproducible Full/Essential/Slim build manifests and controlled package pipeline.
5. Device bridge: explicit pairing and safe profile apply/rollback through a narrow local-service API.
6. Community Library: profile sharing first; executable module publishing only after review, signing, sandboxing, revocation and staged rollback.
7. Additional adapters/platforms after feature and hardware evidence exists.

## Foundation acceptance criteria

- Schemas reject executable payloads and unknown condition types.
- The sample profile validates against the profile schema.
- A profile contains no secrets or host-specific runtime state.
- Profile and menu item IDs are stable and independent of display labels.
- Existing Void Desk Pygame/LÖVE behaviour remains unchanged until a compatibility adapter is implemented and tested.
- Do not claim Qt 6, LVGL, cloud sync, signatures or multi-version boot support before those components exist.

## Visual customization

Profiles store `visualStyle` and `palette` independently. A visual style controls composition and rendering language (for example Megastructure, Manga Ink, Industrial, Terminal, Neon Noir or Minimal); a palette controls colours. Engines advertise which combinations they implement. The initial profile schema defines the identifiers, but cross-engine visual parity requires separate adapter implementation and screenshot evidence.
