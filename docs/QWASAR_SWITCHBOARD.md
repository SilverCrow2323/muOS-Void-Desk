# QWASAR Switchboard

QWASAR Switchboard's first executable core is a **profile-only editor** in `tools/qwasar_switchboard.py`. It updates declarative `.qprofile` state; it is not an installer or service manager.

## Supported operations

- Enable, disable or hide a workspace or section.
- Enable/disable a module in the profile (without uninstalling it).
- Enable, disable or hide an installed contribution by stable ID.
- Enable/disable a registered global panel.
- Reorder workspaces and sections.
- Preview the effective state after applying profile overrides.
- Restore the bundled H700 default profile.

"Disabled" and "hidden" are different: disabled removes the contribution from the active profile; hidden preserves its enabled state but suppresses its presentation. Neither state removes package files.

## Safety and persistence

The Switchboard core reads and validates the UI manifest and profile schemas before accepting changes. It checks workspace, section and action references, and rejects imported profiles that disable the central shell or the protected END NODE/recovery surfaces.

Mutations are prepared in memory first. Persistence is explicit and uses the existing atomic-write helper with a `.bak` backup. A stable sibling lock serializes writers, and a SHA-256 snapshot rejects stale edits instead of silently overwriting changes made by another process.

Module enable/disable here is only a profile state change. It does **not** install/uninstall a package, stop a provider/job, grant permissions, or execute module code. The future runtime coordinator must consume the updated profile and perform any provider lifecycle changes through the existing service/job boundary.

Executable modules remain subject to the separate QWASAR module trust model. Switchboard does not verify Ed25519 signatures, download artifacts, create sandboxes or grant capabilities.

## Run

Requires Python 3.10+ and `jsonschema` 4.23.x:

```bash
python3 -m pip install 'jsonschema>=4.23,<5'
python3 tools/qwasar_switchboard.py preview
```

Mutations require both an explicit destination profile and `--save`. This avoids accidentally editing the repository's bundled sample profile:

```bash
cp data/profiles/voiddesk-handheld-default.qprofile.json /tmp/my-voiddesk.qprofile.json

python3 tools/qwasar_switchboard.py \
  --profile /tmp/my-voiddesk.qprofile.json --save \
  workspace-state rt-toolbox disabled

python3 tools/qwasar_switchboard.py \
  --profile /tmp/my-voiddesk.qprofile.json \
  preview
```

Other commands:

```bash
python3 tools/qwasar_switchboard.py --profile /tmp/my-voiddesk.qprofile.json --save section-state rt-toolbox toolbox.files-storage hidden
python3 tools/qwasar_switchboard.py --profile /tmp/my-voiddesk.qprofile.json --save module-state community.network.example disabled
python3 tools/qwasar_switchboard.py --profile /tmp/my-voiddesk.qprofile.json --save move-workspace rt-toolbox 0
python3 tools/qwasar_switchboard.py --profile /tmp/my-voiddesk.qprofile.json --save reset-profile
```

The Python API is also available:

```python
from pathlib import Path
from tools.qwasar_switchboard import QwasarSwitchboard

switchboard = QwasarSwitchboard(
    Path.cwd(),
    Path("/tmp/my-voiddesk.qprofile.json"),
)
switchboard.set_workspace_state("rt-toolbox", "hidden")
print(switchboard.preview())
switchboard.save()
```

## Implementation boundary

This is the transactional profile-editing core and its CLI. It is not yet connected to the Pygame or LÖVE SETTINGS screens, and no active frontend menu is changed by editing a profile until the runtime profile resolver is implemented.
