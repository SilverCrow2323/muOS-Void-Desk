# QWASAR Field Portal — Publishing and maintenance

This guide is the operational source of truth for building, publishing and maintaining the static documentation portal.

## Product surfaces

| Surface | Purpose | Source |
|---|---|---|
| Field Portal | Designed project overview and guide navigation | `site/index.html` |
| Architecture dossier | Host/application/service boundaries and frontends | `site/architecture.html` |
| Field Manual | muOS installation, firmware matrix and visual references | `site/field-manual.html` |
| Asset Atlas | Ten NEXUS navigation icons and the distinct THE FORGE screen capture | `site/asset-atlas.html` |
| QWASAR Studio concept | Local prototype of four browser workbenches and theme previews | `site/studio.html` |
| v12 Blueprint | Proposed NEXUS destinations, satellites and delivery gates | `site/blueprint.html` |
| 404 | Recovery route for unknown paths | `site/404.html` |

The portal is static HTML, CSS and vanilla JavaScript. The build uses Python's standard library. It has no Node build dependency; Node is used in CI only to parse-check the shared JavaScript file.

## Build locally

From the repository root:

```bash
python3 tools/build_site.py --output _site
```

The builder:
1. requires all seven HTML pages;
2. copies the original SVG diagrams and brand symbol;
3. copies the ten navigation icon PNGs into `assets/icons/`;
4. copies `resources/forge-menu.png` separately into `assets/screens/`;
5. validates local links and in-page fragments;
6. verifies the Asset Atlas contains exactly ten icon entries and keeps the THE FORGE icon separate from its actual screen;
7. checks that Studio contains four workbenches, the manifest-backed sample action IDs and both data-only export paths;
8. verifies the global command palette is present on each main page.

The generated `_site/` folder is an output artifact. Edit the files under `site/`, not the generated copy.

Optional JavaScript syntax check (Node.js):

```bash
node --check site/assets/site.js
```

## Pull request validation

The CI workflow runs the site builder, JavaScript syntax check, Python unit tests, repository integrity audit, visual asset validation, utility lint, shell syntax checks, supported Pygame captures, package builds and the LÖVE/Rt:Tailscale-M integration suite.

A successful desktop CI run is not physical H700 certification. Record actual device model, muOS release, controller GUID, tested frontend and test outcome separately.

## Publish with GitHub Pages

The repository workflow is `.github/workflows/deploy-site.yml`.

One-time repository setup:
1. Merge the reviewed site/documentation PR into `main`.
2. Open **Settings → Pages**.
3. Under **Build and deployment**, choose **GitHub Actions** as the source.
4. Open **Actions → Publish QWASAR Field Portal** and confirm the deployment job succeeds.
5. Open the deployment URL reported by GitHub Pages. The expected project URL is `https://silvercrow2323.github.io/Void-Desk-Project/`.

The workflow builds `_site/`, uploads it as the Pages artifact and deploys it. It runs on changes to the portal, its builder, source diagrams, brand assets, resource PNGs and the deployment workflow, or through manual dispatch.

Do not publish by uploading the generated `_site/` folder into the repository root. GitHub Actions owns the deployment artifact.

## Content and asset rules

- Keep source Markdown in `docs/` and `wiki-source/`; the portal is the visual reading experience, not the only copy of technical knowledge.
- Keep diagrams as editable SVG in `docs/assets/`.
- Keep menu/hub icons in `resources/`. The ten recognised icons are `workshop.png`, `settings.png`, `the_forge.png`, `start.png`, `rt_toolbox.png`, `net_sphere.png`, `muos.png`, `media_vault.png`, `info.png` and `end.png`.
- Keep the actual THE FORGE screen capture as `resources/forge-menu.png`. Never label it as an icon or substitute `the_forge.png` for it.
- Use text alternatives for meaningful images; decorative diagrams may use empty alternatives only when the surrounding caption supplies their meaning.
- Any new page must be added to `REQUIRED_SITE_PAGES` in `tools/build_site.py` when it is part of the core portal, and its links must pass the builder.
- Keep navigation and the Ctrl/⌘+K command palette in sync across all main pages.

## Status and trust language

- The published handheld baseline remains separate from development branches and the v12 blueprint.
- Pygame is the reference handheld frontend; LÖVE remains experimental and not feature-equivalent.
- The Studio page is a local interactive concept. It does not claim a deployed cloud API, device pairing, community publishing, executable module installation, package building or release signing.
- Profile exports are declarative data. They must not contain shell commands, scripts, executable paths, credentials or privileged operations.
- Executable community modules remain disabled until source review, signing, capability enforcement, sandboxing, revocation and rollback are operational.
- Do not infer physical device/controller compatibility from CI, a screenshot or a successful desktop build.

## Rollback and recovery

If the deployment is broken:
1. Inspect the failed **Publish QWASAR Field Portal** run and its build/deploy step.
2. Revert the offending source commit or create a corrective PR; do not edit the Pages artifact manually.
3. Confirm `python3 tools/build_site.py --output _site` succeeds locally.
4. Confirm the PR CI and deployment workflow both succeed.
5. Re-open the Pages deployment URL and inspect the overview, field manual, Asset Atlas and Studio on desktop and mobile.

The source of truth is the latest reviewed `main` commit. Old deployment artifacts are not a substitute for a source rollback.
