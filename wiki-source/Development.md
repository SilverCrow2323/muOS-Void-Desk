# 🛠️ Development and architecture

## Runtime path

On the handheld, `mux_launch.sh` enters through the muOS application lifecycle, starts the local service and launches the configured frontend.

- `py` → `desk/main.py` using the bootstrapped Pygame runtime (reference frontend).
- `love` → `love/main.lua` using the LÖVE runtime (experimental frontend).

The service boundary is responsible for selected host capabilities and long-running jobs. Frontends should not independently spawn duplicate daemons or block their render/input loops on slow commands.

![QWASAR system overview](assets/qwasar-system-map.svg)

## Repository map

| Path | Responsibility |
|---|---|
| `desk/` | Python/Pygame frontend and hubs |
| `love/` | LÖVE frontend, scenes, widgets and theme adapters |
| `service/` | Local capability bridge and background service modules |
| `bin/` | Bootstrap, desktop hand-off and device scripts |
| `data/` | Configuration and generated runtime state |
| `schemas/` | JSON contracts and validation schemas |
| `assets/`, `resources/` | Fonts, artwork, sounds, glyphs and PNG screenshots |
| `docs/` | Architecture, product and technical documentation |
| `wiki-source/` | Source-controlled GitHub Wiki pages |
| `tests/` | Focused regression and contract tests |
| `tools/` | Build, validation and visual-capture tooling |

## Local checks

```bash
python3 -m pip install pytest ruff
python -m compileall -q BUILDCHECK.py voiddesk.py bin desk service outdesk voidcast_addons assets
python -m pytest -q
python BUILDCHECK.py
find love -type f -name '*.lua' -print0 | xargs -0 -r -n 1 sh -c 'luajit -b "$1" /dev/null' _
```

Run the checks relevant to the files you changed. A green CI job is not a physical-device certification.

## Contribution rules

- Keep pull requests focused and scoped.
- Add regression tests for behaviour changes.
- Do not hide failures with `|| true`.
- Keep optional dependencies optional.
- Avoid blocking operations in render/update/input loops.
- Give every capability one canonical service owner.
- Record exact hardware, firmware and test conditions for device claims.
- Do not claim LÖVE parity with Pygame until it is verified feature by feature.
- Mark proposals and incomplete work clearly in documentation.

## muOS host integration

Use the official application runner and documented extension points. Avoid guessed SD1/SD2 paths where a resolved path is available. Deeper integration must be namespaced, reversible and covered by backup/rollback/uninstall tests.

Official references: [Application Runner](https://community.muos.dev/t/application-runner/1282) · [Extending MustardOS](https://muos.dev/docs/infrastructure/extending) · [Frontend and Launching](https://muos.dev/docs/infrastructure/launching).

## Documentation workflow

Update the README, matching technical page and Wiki source page together when a user-facing workflow changes. Use the reusable patterns in [Documentation style guide](https://github.com/SilverCrow2323/Void-Desk-Project/blob/main/docs/DOCUMENTATION_STYLE_GUIDE.md). The diagrams in `docs/assets/` are copied into the Wiki by `tools/publish_wiki.sh`.
