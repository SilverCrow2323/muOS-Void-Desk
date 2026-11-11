# QWASAR Store — GitHub Pages Portal Architecture

**Product:** QWASAR Studio
**Public storefront:** QWASAR Store
**Hosting proposal:** GitHub Pages for the static PWA; GitHub Releases for downloadable artifacts
**Backend:** optional QWASAR Hub for future dynamic services
**Status:** architecture specification only. No production Store, Studio repository, or Pages deployment exists yet.

## 1. Decision

Use GitHub Pages for the first public QWASAR Studio release. QWASAR Store is one workbench inside Studio, not a separate website. The same responsive PWA contains:

- Store / Community Library: browse modules, tools, themes, layouts, profiles, desktop recipes and Void Desk releases.
- Module Forge: create module manifests, add assets and adapters, validate bundles.
- Layout Designer: compose NEXUS nodes, sections, tiles and widgets like LEGO blocks.
- Release Composer: select Full, Essential, Slim or a custom permitted first-party module set.
- Device Matrix: inspect compatibility by device, firmware, frontend and capability.

Pages is appropriate for a public static frontend and catalogue. It is not an application server: it cannot safely provide accounts, private uploads, moderation queues, server-side builds or a database.

## 2. Repository boundary

When Studio implementation starts, create one dedicated repository:

**SilverCrow2323/QWASAR-Studio**

Keep Void Desk source, its local privileged service, module contract, built-in modules and local AppBuilder engine in Void-Desk-Project. Studio owns the browser application and deployment. The AppBuilder engine remains the trusted build implementation; Studio is its user-facing workbench.

Suggested repository layout:

~~~text
QWASAR-Studio/
├── app/
│   ├── store/
│   ├── module-forge/
│   ├── layout-designer/
│   ├── release-composer/
│   ├── device-matrix/
│   └── shared/
├── public/
│   ├── icons/
│   └── manifest.webmanifest
├── catalog/
│   ├── index.json
│   ├── schemas/
│   └── snapshots/
├── schemas/
├── tests/
└── .github/workflows/pages.yml
~~~

Build the PWA so it works under a GitHub Pages project path, not only at the domain root. A custom domain can be added later without making it a runtime requirement.

## 3. Store catalogue

The public catalogue is a versioned JSON index generated from reviewed metadata. Each listing should expose:

- stable ID, title, category and description;
- publisher and source repository;
- immutable version/release link and publication date;
- Void Desk API/runtime compatibility;
- frontend adapters (Pygame/LÖVE), firmware and device families;
- dependencies and optional XFCE APT package requirements;
- capabilities and permission requests;
- licence, artifact size, SHA-256 digest and signature/review state;
- screenshots, changelog and known limitations.

Initial catalogue categories:

| Category | Examples | Distribution |
|---|---|---|
| Modules | Hub panels, widgets, tools, service adapters | .qmod in GitHub Releases |
| Layouts | NEXUS/workspace compositions | .qprofile or JSON assets in Releases |
| Themes | Palettes, visual styles and assets | Declarative theme bundle |
| Tools | Standalone utilities and integrations | Source repository or Release asset |
| Desktop recipes | APT package sets and XFCE launchers | Declarative JSON recipe |
| Device packs | Tested device/firmware capability profiles | Versioned JSON metadata |
| Void Desk releases | Full, Essential, Slim .muxapp | GitHub Releases |

Catalogue metadata is not proof of device compatibility. Support claims must refer to tested model, firmware, Void Desk version and frontend combinations.

## 4. Static Store and release artifact flow

~~~text
Contributor / maintainer
        |
        v
Source repository + module manifest
        |
        v
Pull request, review and CI validation
        |
        v
Immutable GitHub Release
        |                         |
        v                         v
Artifact (.qmod/.qprofile)    Release metadata
        |                         |
        +------------+------------+
                     |
                     v
             Catalogue generator
                     |
                     v
              catalog/index.json
                     |
                     v
         QWASAR Studio on GitHub Pages
                     |
          browse / inspect / download
                     |
                     v
           Local Void Desk verifier
~~~

Do not store large .muxapp, .qmod, desktop images or other binary assets in the Pages deployment. Pages serves the frontend and public metadata; GitHub Releases (or a later artifact store) serves immutable downloads.

## 5. Pages-only v1

The first release should be useful without accounts or QWASAR Hub:

- browse categories, featured collections and item detail pages;
- search and filter by type, device, firmware, frontend, capability, licence and trust tier;
- inspect manifests, dependencies, permissions, source and changelogs;
- download immutable GitHub Release assets;
- verify SHA-256 in the browser before presenting an artifact as valid;
- import/export .qprofile locally;
- edit layouts and preview controller navigation;
- edit and validate draft module manifests locally;
- export a Release Composer selection manifest/lockfile;
- cache visited documentation, schemas and catalogue snapshots for offline reading.

The Store must not silently install modules. Download and installation are separate operations; Void Desk validates the package and requests permissions locally before activation.

## 6. What requires QWASAR Hub

Pages-only v1 does not securely provide:

- user accounts, private libraries or device identity;
- direct visitor uploads, reviews, comments or moderation queues;
- authenticated device pairing and remote sync;
- secret-bearing GitHub API calls;
- remote build execution or signing;
- server-side scanning or sandboxed module execution.

These are future QWASAR Hub responsibilities. Never place a personal access token, GitHub App private key, signing key, device credential or server secret in public JavaScript or a Pages asset.

Until Hub exists, community contributions use a pull-request flow:

1. Contributor publishes source and a proposed manifest/release in a public repository.
2. They submit catalogue metadata through a pull request.
3. CI validates schema, file inventory, digest, licence and compatibility fields.
4. Maintainers review source, permission requests and provenance.
5. The catalogue generator publishes only approved entries.
6. Users download from immutable GitHub Release assets.

Data-only profiles can have a lightweight review path. Executable modules require stronger source review, signing, explicit trust state, capability enforcement and a sandboxed runtime before installation is enabled.

## 7. Module Forge, Layout Designer and Release Composer

### Module Forge

- guided templates for widgets, tiles, hub panels, service integrations, themes, desktop launchers and APT recipes;
- strict module manifest editing and schema validation;
- Pygame/LÖVE adapter and platform compatibility declarations;
- dependency and capability/permission inspection;
- asset, localisation, documentation and bundle integrity checks;
- source and review workflow for executable community modules.

### Layout Designer

- visual composition of NEXUS nodes, workspace sections, tiles and widgets;
- reorder, hide, enable/disable, rename, regroup and replace registered contributions;
- preview for target resolution, device and frontend;
- warnings for missing modules, unavailable capabilities and incompatible routes;
- export declarative .qprofile data only. A profile never contains executable code or silently installs modules.

### Release Composer

- select Full, Essential, Slim or a custom permitted first-party module set;
- resolve dependencies and show size/compatibility estimates;
- identify optional XFCE image requirements separately from .muxapp contents;
- export a reproducible build manifest and module lockfile;
- display build provenance, SHA-256 and signing state.

Local v1 exports a manifest and guides the user to the trusted local AppBuilder. Remote builds come later through a controlled Hub request and protected build worker; never dispatch arbitrary workflow inputs from public browser code.

## 8. APT and desktop boundary

APT recipes are declarative package names and compatibility metadata, not shell scripts. Void Desk submits installation/removal through its trusted service job manager, and package operations execute only inside the optional Debian/Ubuntu XFCE image. They never run APT on the muOS Buildroot host.

An APT package shared by multiple modules must not be purged automatically when one module is removed. The user sees an orphan/dependency report and confirms any package removal. The large XFCE root filesystem remains a separate, verified optional download; even Full flavour need not embed its multi-gigabyte contents.

## 9. GitHub Actions Pages deployment

The Studio repository should use a dedicated Pages workflow:

1. Check out a pinned source revision.
2. Install locked frontend dependencies.
3. Validate catalogue entries against current schemas.
4. Reject duplicate IDs, missing digests/licences, mutable artifact URLs and unsupported trust claims.
5. Generate catalogue indexes and static item pages.
6. Run frontend tests, accessibility checks and link/asset integrity checks.
7. Upload and deploy the Pages artifact using the official Pages deployment actions.
8. Publish a deployment summary with source commit and catalogue snapshot hash.

Permission boundaries:

- PR validation gets read-only repository access.
- Only the deployment job receives Pages write and OIDC deployment permissions.
- Release signing remains in a separate maintainer-controlled workflow.
- Untrusted PR code never runs in a job with write permissions or secrets.
- Pages build jobs receive no personal token or signing key.

Do not enable the live Pages site until the dedicated Studio repository, its deployment workflow and public-content review exist.

## 10. Delivery phases

**Store v0 — public catalogue:** create QWASAR-Studio, build a static Store shell, publish a curated first-party catalogue and deploy to Pages. No accounts or uploads.

**Studio v1 — local creator workbench:** add Module Forge, Layout Designer, profile import/export, local manifest validation and Release Composer manifests.

**Store v2 — reviewed community catalogue:** add contribution templates, CI validation, publisher identities, immutable module releases, signatures and official/reviewed/unreviewed/withdrawn states.

**Hub-backed v3:** add accounts, private libraries, pairing, sync, moderation, remote build requests and build history.

## 11. Acceptance rules

- QWASAR Store is one workbench inside QWASAR Studio, not a separate web product.
- GitHub Pages hosts only the static PWA and public metadata.
- GitHub Releases hosts downloadable binary assets.
- Every installable asset has immutable provenance, digest and visible trust state.
- No secrets or device credentials are shipped to Pages.
- No profile executes code or silently installs a module.
- APT recipes target only the optional Debian/Ubuntu desktop image.
- Store browsing and local profile editing work without accounts or Hub.
- Remote publishing, uploads, moderation, pairing and build execution are not advertised until their backend is deployed.