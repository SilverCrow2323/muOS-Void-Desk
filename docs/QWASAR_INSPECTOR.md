# QWASAR Inspector

QWASAR Inspector is the first executable part of the QWASAR manifest toolchain. It is a standalone, **read-only** repository validator at `tools/qwasar_inspector.py`.

It checks:

- the default UI manifest against `schemas/qwasar-ui.schema.json`;
- component type registration, strict component property schemas, named slots and unique component-node IDs;
- menu, component and key-binding references to registered actions;
- portable profiles against `schemas/qwasar-profile.schema.json`, including workspace, section and action references;
- module manifests against `schemas/qwasar-module.schema.json`, including contribution component types, props, workspace/section references and module-local action references.

The bundled H700 profile and declarative Wi-Fi example are included in the default scan. They are examples, not proof that the profile resolver or module installer is implemented.

## Run

Requires Python 3.10+ and `jsonschema` 4.23.x:

```bash
python3 -m pip install 'jsonschema>=4.23,<5'
python3 tools/qwasar_inspector.py
```

Inspect only the UI manifest:

```bash
python3 tools/qwasar_inspector.py --manifest-only
```

Inspect custom profiles or modules (repeat either option to inspect more than one file):

```bash
python3 tools/qwasar_inspector.py \
  --profile path/to/custom.qprofile.json \
  --module path/to/custom.module.json
```

Emit machine-readable output for CI or other tooling:

```bash
python3 tools/qwasar_inspector.py --json
```

All paths are resolved relative to `--root` (the repository root by default). Exit code `0` means all selected documents passed; exit code `1` means at least one schema or cross-reference error was found.

## Safety and implementation boundary

Inspector only reads JSON and schema files. It does not install or execute modules, change profiles, enable/disable contributions, access the host package manager, or mutate repository files. It validates the structure and references of module signatures but **does not yet perform cryptographic Ed25519 verification, artifact download/hash verification, sandboxing or runtime permission enforcement**. Those belong to later trusted package/runtime components, not to this first verifier.

This CLI is not yet wired into the Pygame or LÖVE menus. The current milestone makes the verification logic executable and testable before adding a frontend entry point.
