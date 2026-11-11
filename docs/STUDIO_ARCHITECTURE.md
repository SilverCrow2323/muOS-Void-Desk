# QWASAR Studio — Technical Architecture

**Product:** QWASAR Studio, the browser companion for QWASAR-Env  
**Status:** accepted product direction; foundation specification  
**Scope:** browser companion, portable profiles, official plugin catalog, multi-engine readiness  
**Initial runtime targets:** Pygame (py) and LÖVE (love). Qt 6 and LVGL are future adapters, not currently supported runtimes.

## Product decisions

- Studio is a responsive web app/PWA companion. The handheld remains usable without Studio or internet access.
- Users can export/import and explicitly share profiles and individual official plugins.
- Plugin publishing is restricted to official QWASAR Desk maintainers in v1. No public plugin uploads or third-party executable packages.
- Profiles are declarative data: menu ordering, labels, descriptions, icons, supported feature toggles, approved plugin settings, and visibility conditions.
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
       QWASAR Desk local service
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

- Profile editor: reorder menu entries; edit labels, descriptions and icons; enable/disable supported entries; preview changes.
- Profile library: local profiles, import/export, validation, migration and duplicate detection.
- Official plugin catalog: discover, inspect capabilities/permissions, install/update/remove supported plugins.
- Device view: display paired-device metadata and supported engines only after explicit pairing.
- Sharing: publish one profile or one official plugin reference/package after preview and confirmation.

The initial client should be a static, progressively enhanced PWA. Do not place device credentials in exported profiles or browser storage without a dedicated credential design.

### Profile format and Configuration Engine

Canonical versioned JSON Schemas live under schemas/. A profile contains stable identity and metadata, compatibility constraints, an engine preference, a declarative menu tree, typed visibility conditions, and references to official plugins with non-secret settings.

The engine validates and migrates a profile before applying it. It merges profile overrides with built-in defaults and does not rewrite the user's base configuration. Activation is transactional: validate, stage, back up the current selection, atomically activate, and retain rollback. Unknown executable/action fields are rejected.

The existing data/desk_config.json remains the legacy runtime configuration during migration. Do not replace it wholesale. A future compatibility adapter maps only supported settings into the canonical model and writes through existing safe I/O helpers.

### Version 1 compatibility identifiers

The classic handheld application is **Void Desk**, the browser companion is **QWASAR Studio**, and both are components of **QWASAR-Env**. Version 1 of the profile and plugin contracts deliberately keeps its original technical identifiers so existing drafts, tools and future importers do not need a silent breaking rename:

- Schema filenames and profile IDs such as `voiddesk-starter` remain stable.
- The profile compatibility property `minimumVoidDeskVersion` keeps its v1 spelling even though it refers to the minimum **Void Desk** runtime version.
- The official plugin publisher ID `voiddesk-official` and display name `Void Desk Official` remain reserved v1 compatibility values. Do not change them independently: a public publisher-identity migration requires a new manifest/schema version and an explicit migration path.
- These identifiers are not the displayed product brand and must not be used for new user-facing copy.

## Menu and condition model

Menu array order determines presentation order. Stable item IDs are independent of labels. Routes must resolve to entries registered by the installed QWASAR Desk build.

Visibility conditions use a closed vocabulary and are evaluated locally:
- key_sequence: bounded sequence of known controller keys.
- device_family: known platform/device family.
- feature_available: registered capability identifier.

Cheat-code sequences are easter-egg/discovery controls only. They are not authentication, authorization, encryption, or a security boundary. A hidden entry must never grant capabilities or bypass permission checks. Sequences have length/time bounds and reset on focus loss or timeout.

### Official plugin manager

Plugins are separately versioned packages with a manifest, compatibility range, declared capabilities, immutable artifact digest and detached signature. In v1:
- Only maintainer-controlled publisher IDs are accepted.
- The signed official catalog is the allowlist; unknown publishers and unsigned packages are rejected.
- Verify signature, digest, schema, compatibility and permissions before installation.
- No arbitrary shell execution. Privileged integrations require reviewed host-side capabilities with narrow typed APIs.
- Install, update, disable and remove are explicit actions. Updates are staged and rollback-capable.
- Profiles may reference official plugin IDs and configure schema-approved non-secret options. Sharing a profile never silently installs a plugin.

The manifest schema is not proof that signing/distribution already exists. Key management, rotation, revocation and publisher allowlisting must be implemented before plugin installation is enabled.

### Multi-engine and multi-version

Profiles are engine-neutral. Each frontend adapter advertises supported routes, controls and capabilities. Pygame is the primary current frontend; LÖVE exists but is not feature-equivalent. Qt 6 and LVGL remain future adapters until implemented and tested.

Runtime version management is separate from profile management. Profiles may declare a minimum QWASAR Desk version and preferred engine, but cannot install or switch binaries. Multi-version installation, boot selection, update channels and rollback belong to a separate package/boot manager.

## Planned API contract (not deployed)

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /v1/catalog/plugins | Signed official plugin catalog |
| GET | /v1/profiles/{profile_id} | Read a shared profile |
| POST | /v1/profiles | Publish a user-approved profile |
| POST | /v1/profiles/{profile_id}/revisions | Publish immutable revision |
| GET | /v1/devices | List paired devices |
| POST | /v1/devices/pairing-sessions | Start short-lived pairing |
| POST | /v1/devices/{device_id}/sync-jobs | Queue a device-initiated sync |

Every write must be authenticated, authorized, size-limited, schema-validated, rate-limited and auditable. Use immutable revisions and content digests. Never share tokens, Wi-Fi credentials, local paths, IP addresses, device IDs, logs or personal files.

## Sharing and privacy

- Sharing is off by default and requires preview plus explicit confirmation.
- Export only an allowlist of portable fields; strip device identifiers and secrets.
- Profiles are data only. Import cannot execute commands or install plugins.
- Plugin sharing is limited to official catalog entries. Profiles may declare dependencies but cannot bundle plugin code.
- Show provenance, version, compatibility, permissions, digest and update date for every plugin.

## Rollout

1. Foundation: architecture, profile schema, plugin manifest schema and sample profile.
2. Local engine: validator/migration library and read-only compatibility report; no cloud dependency.
3. Web editor: local import/export, menu editing, preview and schema validation.
4. Device bridge: explicit pairing and safe apply/rollback through a narrow local-service API.
5. Official catalog: signing, key rotation/revocation, capability enforcement and staged install/update.
6. Sharing service: opt-in profile publishing and individual official plugin sharing.
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
