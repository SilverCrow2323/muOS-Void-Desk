# QWASAR Profile Resolver

**Status:** implemented as a shared resolver and launcher preflight; frontend adoption is in progress. The LÖVE NEXUS adapter applies top-level workspace order, visibility and enabled state. Pygame exposes profile selection and loads the generated snapshot, but its legacy NEXUS arrangement and RT:TOOLBOX section migration are not yet profile-driven.

## 1. Purpose and boundaries

A QWASAR profile is portable, declarative data. It describes workspace order, visibility/enabled state, menu order/visibility, shell regions, global panels, theme tokens, input bindings and safe user settings.

A profile does **not** define a route implementation, execute Lua/Python, install or uninstall modules, grant permissions, choose package paths, or change the trusted capability broker. Installation remains a THE FORGE responsibility. QWASAR Switchboard edits a profile; it does not alter files installed by THE FORGE.

The Resolver reads three classes of input:

| Input | Source of truth |
|---|---|
| UI/workspace/action definitions | `data/qwasar_ui_manifest.json` |
| Profile structure and safe portable settings | `schemas/qwasar-profile.schema.json` |
| Selected user arrangement | `data/profiles/*.qprofile.json` or `qwasar_profile` in `data/desk_config.json` |

It produces one generated snapshot at `data/qwasar_effective_profile.json`. That file is ignored by Git and is regenerated before the selected frontend starts.

## 2. Startup pipeline

1. The normal platform launcher identifies the platform and selects a platform-specific safe default.
2. `tools/qwasar_profile_resolver.py` reads the manifest and selected profile.
3. The resolver checks the UI schema and profile schema when `jsonschema` is installed, then performs structural, cross-reference, compatibility and protected-area checks.
4. Valid overrides are merged into a deterministic engine-neutral composition.
5. The CLI writes the composition atomically to the generated snapshot.
6. The frontend reads that same snapshot. If it is missing or invalid, the frontend keeps its built-in legacy defaults rather than executing untrusted profile content.

### Platform defaults

| Host | Platform ID | Safe default |
|---|---|---|
| H700 / muOS | `muos` | `data/profiles/voiddesk-handheld-default.qprofile.json` |
| Linux PC | `desktop` | `data/profiles/voiddesk-desktop-default.qprofile.json` |

The device launcher passes `--platform muos --model H700`. The PC launcher passes `--platform desktop`. A profile is rejected when its `compatibility.platforms` does not include the target platform or `any`, when its optional model allowlist does not contain the target model, or when its `minimumUiApi` exceeds the manifest API version.

A custom profile can be selected by setting `qwasar_profile` in `data/desk_config.json` to a path relative to the application root, for example:

~~~json
{
  "engine": "love",
  "qwasar_profile": "data/profiles/my-handheld.qprofile.json"
}
~~~

The `QWASAR_PROFILE` environment variable takes precedence over that config value. The selected profile remains data-only.

## 3. CLI usage

Run from the repository root:

~~~bash
# Validate and write the H700 composition
python3 tools/qwasar_profile_resolver.py \
  --root . \
  --platform muos --model H700 \
  --default-profile data/profiles/voiddesk-handheld-default.qprofile.json \
  --output data/qwasar_effective_profile.json

# Resolve the PC composition
python3 tools/qwasar_profile_resolver.py \
  --root . \
  --platform desktop \
  --default-profile data/profiles/voiddesk-desktop-default.qprofile.json

# Inspect the result without writing a file
python3 tools/qwasar_profile_resolver.py --root . --stdout

# Reject an invalid selected profile instead of falling back
python3 tools/qwasar_profile_resolver.py \
  --root . --profile data/profiles/custom.qprofile.json --strict --stdout
~~~

Useful options:

| Option | Purpose |
|---|---|
| `--root` | Application root containing the manifest, schemas and profile files |
| `--manifest` | Alternate manifest path, relative to `--root` unless absolute |
| `--profile` | Explicit selected profile; otherwise `QWASAR_PROFILE` or `desk_config.json` is used |
| `--default-profile` | Platform-specific fallback profile |
| `--platform` | Compatibility target: `muos`, `knulli`, `rocknix`, `desktop` or `custom` |
| `--model` | Optional device-model compatibility check |
| `--strict` | Return an error instead of falling back from an invalid selected profile |
| `--stdout` | Print the resolved JSON instead of writing the output snapshot |
| `--output` | Output path; must remain inside `--root` |

The output is written through a same-directory temporary file followed by an atomic replacement. The manifest and source profile are never rewritten.

## 4. Validation, fallback and trust

The Resolver checks:

- unique workspace, section override and menu references;
- workspace and section membership before applying order or visibility overrides;
- registered action IDs for profile key bindings;
- declared global-panel IDs;
- protected workspaces, shell regions, recovery paths and protected module/contribution states;
- separate `enabled` and `visible` flags;
- safe user-setting keys, including case-insensitive rejection of password, secret, token, credential, private-key, API-key, install-path and filesystem-path names.

If a selected profile is missing, malformed or incompatible, the Resolver attempts the platform-specific bundled default and records a warning in the snapshot. If that fallback is also unusable, the CLI returns a non-zero status; both launchers log the failure and continue with the frontend's legacy built-in composition. They do not block the device from returning to muOS or the PC desktop.

When the Python `jsonschema` package is available, full Draft 2020-12 validation is applied to the canonical UI and profile schemas. On a lean runtime without `jsonschema`, the Resolver records a warning and still performs its built-in structural, compatibility, protected-area and cross-reference checks. Release/CI validation must install `jsonschema` so complete schema validation remains mandatory in the build pipeline.

Profiles and the generated snapshot are never executed as code. Signature verification, module artifact verification, code sandboxing and runtime capability enforcement are separate trust requirements and are not claimed by this Resolver.

## 5. Frontend adapter status

### LÖVE

- `love/main.lua` loads the generated snapshot at startup.
- `love/core/nodes.lua` maps stable QWASAR workspace IDs to existing NEXUS node IDs.
- Profile order changes within-orbit navigation order without changing legacy node indices, scene IDs or orbit identity.
- A hidden workspace is removed from visible NEXUS nodes.
- A disabled-but-visible workspace remains visible, is marked disabled and cannot be opened.
- END NODE remains protected by Resolver validation.
- Legacy MUOS APPS and WORKSHOP nodes remain as compatibility extras; they are not silently reinterpreted as QWASAR workspaces.
- LÖVE Settings shows the active profile name.

### Pygame

- The Pygame Settings screen lists compatible `.qprofile.json` files.
- Saving a selection stores `qwasar_profile` in `data/desk_config.json`; a restart is required for the launcher to regenerate the snapshot.
- Pygame reads and caches the generated profile summary at startup.
- Pygame's legacy NEXUS node arrangement and the migration of its separate TOOLBOX/WORKSHOP menus into the four QWASAR RT:TOOLBOX sections are not yet driven by the composition. Stable legacy indices are deliberately preserved until that adapter migration is implemented and tested.

### Shared pending work

- Consume shell region, home-panel and global-panel overrides in both frontends.
- Apply profile-driven RT:TOOLBOX section/menu order and contributions.
- Map every old Pygame destination and action to stable manifest IDs, including explicit aliases and unsupported-route states.
- Add profile import/export UX and profile migration from the previous configuration format.
- Verify the full flow on a physical H700 device and a Linux PC.

## 6. Tests and release checks

The Python tests cover default H700 resolution, desktop compatibility, workspace/section/menu ordering, visibility versus enabled state, safe settings, module/contribution state data, registered action references, protected END NODE/shell behaviour, invalid-profile fallback, atomic output and output-path containment.

The LÖVE core tests cover stable node IDs, profile order, hidden workspaces and disabled workspaces. These tests are part of CI; a green workflow is still required before merging the feature branch.

Before a device release:

1. run the Inspector against the manifest, schemas and profile files;
2. run the Resolver on the target platform and inspect the generated snapshot;
3. test both default and custom profile selection;
4. test fallback with a malformed/incompatible selected profile;
5. confirm END NODE, return-to-firmware and recovery remain reachable;
6. confirm that uninstalling Void Desk leaves the normal muOS startup path intact.

