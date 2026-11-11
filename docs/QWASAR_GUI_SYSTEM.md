# QWASAR GUI System — Engine-Neutral Interface Contract

**Product family:** QWASAR-Env  
**First host application:** Void Desk  
**Contract:** QWASAR UI Composition API 1.0 (design baseline)  
**Status:** architecture contract and reference manifest; runtime-generated layouts are not yet implemented.

## 1. Purpose

QWASAR must describe an interface once and let each rendering engine present it using native primitives. Pygame and LÖVE are the first adapters. Qt 6, LVGL and Web are future adapters. A future engine must not require a second copy of every menu, widget, profile or module definition.

This contract covers:

- global application chrome: header, footer, status areas and navigation hints;
- home composition: NEXUS and its left/right side panels;
- global overlays: media player, jobs, notifications, quick settings and confirmations;
- workspaces such as START SESSION, THE FORGE, MEDIA VAULT and RT:TOOLBOX;
- menus, menu entries, widgets, layout containers and interaction states;
- the boundary between declarative UI, registered actions and privileged host capabilities.

The reference manifest lives in `data/qwasar_ui_manifest.json`; its JSON Schema is `schemas/qwasar-ui.schema.json`.

## 2. Architecture: one definition, multiple renderers

~~~text
               QWASAR UI MANIFEST + USER PROFILE
                            |
                   schema + ID validation
                            |
                  UI composition resolver
                 /          |           \
            shell          workspaces    overlays
              |                |             |
         component tree   component tree  component tree
              \                |             /
                   semantic event model
                            |
                    ENGINE ADAPTER API
          /          /        |        \          \
      Pygame       LÖVE      Qt 6      LVGL       Web
      current     current    future    future     future
                            |
                   HOST CAPABILITY BROKER
                            |
               typed Void Desk / platform service
~~~

### Engine adapters

Each adapter implements the same logical responsibilities:

1. discover the engine's screen size, density and input capabilities;
2. measure and arrange logical component trees;
3. render registered component types using native primitives;
4. translate keyboard, controller, touch, mouse and accessibility input into semantic QWASAR intents;
5. maintain focus order, selected/disabled/loading states and modal focus;
6. dispatch component events to registered action IDs;
7. expose text-entry, clipboard and media-control support when the engine/platform provides them;
8. report unsupported component features so the resolver can choose a safe fallback.

An adapter must not own business logic or privileged host operations. The service/capability layer remains responsible for system actions. It is valid for an adapter to advertise only a subset of capabilities.

### Compatibility rule

A UI manifest can target multiple engines. Each component declares a minimum UI API and optional engine capabilities. If an adapter cannot render a component, the resolver must use its declared fallback or show an explicit unavailable state. It must never silently omit a destructive action or claim feature parity.

## 3. Interface tree and LEGO model

The canonical hierarchy is:

~~~text
Application
└── Shell
    ├── Header
    ├── Main viewport
    │   └── Home / Workspace
    │       ├── Region
    │       ├── Section
    │       ├── Container
    │       ├── Widget / Menu
    │       └── Menu entry
    ├── Footer
    ├── Side panels
    ├── Global overlays
    └── Notifications / Job dock
~~~

Definitions:

- **Shell** is the stable frame and owns global input, focus, navigation, overlays and safe recovery.
- **Workspace** is a destination with a purpose-specific layout template.
- **Region** is a named placement slot such as header.leading, home.left, home.main, home.right or overlay.media.
- **Section** is a named group inside a workspace, for example "Network", "Storage" or "Developer tools".
- **Container** controls layout and composition: stack, row, column, grid, scroll, split or tabs.
- **Widget** displays information or offers a bounded interaction, such as a status card, meter, graph, media control or quick tile.
- **Menu** is a navigable collection of entries.
- **Menu entry** is a declarative item with a stable ID and a registered route/action reference.
- **Action** is a host-registered operation, not code embedded in a profile or layout.

A profile may reorder, hide, group, relabel and restyle compatible contributions. It cannot create a new executable route, arbitrary shell command, raw Lua/Python/JavaScript callback or privileged capability.

## 4. Global shell is buildable too

The header and footer are component trees, not fixed artwork. Each has required system-owned slots and optional user/module slots.

### Header slots

- `header.leading`: QWASAR/Void Desk mark, home or back affordance;
- `header.context`: current workspace title, breadcrumb and optional subtitle;
- `header.status`: battery, storage, network, Bluetooth, time and service-state widgets;
- `header.trailing`: user-selected shortcuts or profile indicator.

A user can change ordering, visibility, density and supported widgets. The host retains a minimum recovery/navigation affordance and must not allow a profile to hide a critical error or permission prompt.

### Footer slots

- `footer.navigation`: current controller/keyboard hints;
- `footer.context`: contextual action hints for the selected row;
- `footer.status`: connection, job or media state when useful;
- `footer.shortcuts`: optional user-defined shortcuts.

On a small handheld, hints collapse to the most relevant actions. On desktop/web, the same slots can become a status bar, toolbar or keyboard shortcut strip.

### NEXUS side panels

NEXUS has a main orbital navigation area and two configurable side regions:

- `home.left`: favourites, pinned tools, profiles, quick launch or a user-created launcher;
- `home.right`: system telemetry, network, storage, jobs, media state or contextual widgets.

Each side region may be hidden, collapsed, swapped or populated with compatible widget contributions. On 640×480, panels should open as drawers/overlays instead of permanently stealing the central viewport. On wide screens, they can remain docked. Focus must move into an opened drawer and return to the invoking node when it closes.

## 5. Global media panel and the M shortcut

The media player is a shell-level panel, not a duplicate media screen. It can be opened over any workspace and displays the active backend's state.

The default keyboard shortcut is `M` → `panel.media.toggle`. Escape closes the overlay or returns to the previous navigation level. The physical handheld mapping is device-profile controlled; it must not be hardcoded to a controller button until the target device's chord and muOS hotkeys are validated.

The panel may contain:

- current source and now-playing metadata;
- play/pause, stop and seek where the backend supports them;
- volume and mute controls where the platform exposes them;
- previous/next only when the active source provides a queue;
- a route to MEDIA VAULT for full library, IPTV and radio browsing;
- explicit states: idle, loading, playing, paused, buffering, unavailable and error.

The panel is capability-driven. If there is no media backend, the shortcut can open a clear unavailable message or be disabled in the profile. It must never start a second player when one is already owned by the service.

## 6. Component catalogue

The initial component registry is engine-neutral. Each component defines a stable type ID, property contract, child slots, supported states, events and fallback.

### Layout and surfaces

| Type | Purpose |
|---|---|
| `layout.stack` | Vertical or horizontal composition |
| `layout.row` / `layout.column` | Aligned linear layout |
| `layout.grid` | Responsive tile/card grid |
| `layout.scroll` | Bounded scroll viewport |
| `layout.split` | Primary/secondary pane |
| `surface.panel` | Framed panel, card or drawer surface |
| `surface.overlay` | Layered floating surface |

### Display and status

| Type | Purpose |
|---|---|
| `display.text`, `display.icon`, `display.badge` | Basic content primitives |
| `widget.status-card` | Label, value, detail and health state |
| `widget.stat`, `widget.gauge`, `widget.progress` | Numeric status |
| `widget.sparkline`, `widget.chart` | Trend and history |
| `widget.quick-tile` | Compact shortcut/status tile |
| `widget.media-player` | Shared media state and transport controls |
| `widget.item-list` | Data-backed list with empty/loading/error states |

### Navigation and interaction

| Type | Purpose |
|---|---|
| `menu.list`, `menu.entry` | Controller/keyboard navigable menus |
| `navigation.breadcrumb` | Current path and back context |
| `navigation.drawer` | Side navigation / workspace switcher |
| `input.toggle`, `input.slider`, `input.select` | Schema-backed settings inputs |
| `overlay.drawer`, `overlay.dialog` | Modal and non-modal surfaces |
| `feedback.toast`, `feedback.progress` | Temporary messages and job progress |

Widgets expose typed properties and events. They do not execute arbitrary code. State is supplied by the relevant registered provider or action.

## 7. Menu model: how entries are added

Every menu entry requires:

- stable `id` independent of its displayed label;
- `kind`: `route`, `command`, `submenu`, `toggle`, `value`, `dynamic`, `external` or `separator`;
- localisable `label`, optional description and icon;
- optional `actionId` referring to a registered host action;
- optional child entries or a trusted data provider;
- capability/availability requirements;
- enabled, loading, busy, unavailable and error presentation;
- confirmation and danger metadata for privileged/destructive operations.

Adding a menu voice therefore means:

1. add or reference a stable contribution ID;
2. declare its label, icon, description and placement;
3. select an existing registered route or action ID;
4. declare required capabilities and permission/confirmation level;
5. define loading, empty, unavailable and error states;
6. add an automated contract test and visual-capture case.

A module can contribute a menu entry only to a slot supported by the installed UI API. A profile can move or hide that entry, but cannot change its action target or privilege.

### Entry kinds

- `route`: opens a registered workspace, scene or panel;
- `command`: requests one typed service action;
- `submenu`: opens declared child entries;
- `toggle`: changes a setting through a typed setter;
- `value`: opens a bounded picker/selector;
- `dynamic`: populates entries through an allowlisted provider (for example discovered muOS applications);
- `external`: launches a registered external application after dependency and trust checks;
- `separator`: visual grouping only; never executable.

## 8. Workspaces have different visual grammars

A generic list dashboard is a fallback, not the design target. The workspace declares a template, and each template composes the same components differently.

| Workspace | Template | Layout grammar |
|---|---|---|
| START SESSION | `session-selector` | Three compact environment cards, install/launch actions, disk/RAM summary and hand-off state |
| THE FORGE | `package-workbench` | Package/environment tabs, search/filter, package list, details/confirmation pane and persistent job dock |
| UPLINK | `network-console` | Connection overview, service cards, peer/device lists and grouped connect/manage actions |
| MEDIA VAULT | `media-library` | Source tabs, library/list pane, now-playing panel, IPTV/radio entry points and playback hand-off |
| RT:TOOLBOX | `tool-workbench` | Quick tools grid, category navigation, diagnostics/monitor widgets and contextual tool area |
| SETTINGS | `settings-workbench` | Grouped schema-backed forms, current values, reset/preview and save state |
| INFO / COMMUNITY | `reference-library` | Documentation/release cards, changelog, credits and community resources |
| END NODE | `system-exit` | Focused confirmation surface for exit, reboot or power-off; no unrelated widgets |

### RT:TOOLBOX consolidation

Merge the current TOOLBOX destination with the current WORKSHOP/diagnostics destination into one top-level **RT:TOOLBOX** node.

Proposed internal sections:

1. **Quick Access** — calculator, clock, calendar, editor and pinned tools.
2. **Files** — file manager, media/file helpers and user-selected storage tools.
3. **Diagnostics** — Void Diag, system information, service health and logs.
4. **Monitor** — CPU, RAM, temperature, storage and live history.
5. **Maintenance** — safe cleanup, backup/restore, cache and repair helpers.
6. **Developer** — shell, Python tools and build utilities, gated by capability/permissions.

Move APT package operations and desktop-image installation to **THE FORGE**, so package management remains in one place. RT:TOOLBOX can link to the package workbench but should not own a second APT menu.

Keep legacy route IDs such as `hub_toolbox` and `hub_workshop` as aliases during migration. Old profiles should resolve to RT:TOOLBOX with the appropriate section selected rather than breaking.

## 9. Layout and responsive rules

- Use logical units, spacing tokens and constraints; do not store engine-specific pixel coordinates in profiles.
- Layout primitives include stack, row, column, grid, scroll and split.
- Each region declares min/max size, preferred size, gap, padding, alignment and overflow behaviour.
- The adapter maps logical density to physical pixels and device scale.
- The same manifest should adapt between 640×480 handheld, desktop window and browser viewport.
- Prioritise focus/selection visibility and text truncation/wrapping over decorative effects.
- Reduced motion and low-power profiles are first-class.
- Every scrollable region exposes focus, current selection and visible-range state.
- Unsupported component features render a documented fallback.

## 10. Theme and visual design

Style, palette and density are separate.

- **Style** changes composition language: Megastructure, Manga Ink, Industrial, Terminal, Neon Noir or Minimal.
- **Palette** changes colours only: Crimson, Cyberpunk, Green, Stealth, Amber, Ice, Paper or Signal Red.
- **Density** changes spacing, row height, information volume and panel sizing: compact, comfortable or spacious.
- **Motion** controls transitions/effects: full, reduced or off.
- **Input scheme** controls focus order and hints: handheld, keyboard/mouse, touch or accessible.

A theme may skin a component but cannot change its action, permission or capability.

## 11. Action, permission and trust boundary

The UI tree is declarative. A component can reference an action ID but cannot define the implementation of that action.

Registered actions resolve through the host capability broker:

- route actions resolve only to installed/registered routes;
- command actions resolve only to typed service handlers;
- toggles and value inputs call schema-validated setters;
- external launches resolve only through the trusted external-tool registry;
- destructive actions use host-owned confirmation surfaces;
- permission denial and missing capabilities are visible, not disguised as success.

No UI manifest, profile or community module may inject shell strings, executable paths, scripts, raw socket access, credentials or unrestricted filesystem paths.

## 12. Repository and source-of-truth boundaries

| Concern | Canonical source |
|---|---|
| UI component types/slots and API version | `schemas/qwasar-ui.schema.json` |
| Default Void Desk composition | `data/qwasar_ui_manifest.json` |
| User arrangement/preferences | portable profile schema and profile data |
| Tool inventory | `data/tool_catalog.json` |
| Module identity/capability declarations | `schemas/voiddesk-plugin.schema.json` (legacy name retained until a compatible migration) |
| Runtime route/service implementations | registered frontend scenes and service handler catalogue |
| Native rendering | Pygame/LÖVE/other engine adapter |

Studio's future Layout Designer consumes the same manifest and schemas. It edits layout composition and profile overrides; it does not emit arbitrary engine code.

## 13. Implementation phases

1. **Contract baseline:** land schema, default manifest, docs and structural tests. No runtime replacement yet.
2. **Component registry:** register existing LÖVE/Pygame components against stable IDs and add compatibility fallbacks.
3. **Shell composition:** migrate header, footer, NEXUS side panels and media overlay to named slots.
4. **Workspace templates:** migrate one workspace at a time, beginning with RT:TOOLBOX and THE FORGE after MEDIA VAULT is stable.
5. **Profile resolver:** apply profile overrides transactionally and preserve v1 profile migration.
6. **Module contributions:** allow signed/official modules to register declared slots; community executable modules remain disabled until signing/review/capability enforcement exist.
7. **Studio editor:** use the same component registry and UI schema to build visual LEGO-style editing and preview.
8. **Additional engines:** implement Qt 6, LVGL or Web adapters only after the adapter contract is exercised by both existing frontends.

## 14. Completion criteria

- The same UI manifest is readable by Pygame and LÖVE adapters.
- Header/footer and NEXUS side panels are assembled from registered components.
- The M shortcut toggles the shared media overlay without changing the active workspace.
- Every visible menu entry resolves to a registered route/action and has honest state handling.
- Workspace templates differ by declared content grammar, not duplicated ad-hoc code.
- RT:TOOLBOX replaces separate Toolbox/Workshop NEXUS destinations without breaking legacy route/profile references.
- A sample custom profile can reorder/hide components without embedding code or changing permissions.
- Schema, manifest, route/action tests and device interaction tests pass.

---

This document defines the intended QWASAR GUI architecture. It does not claim that profile-driven runtime composition, dynamic component installation, the global M media overlay or the consolidated RT:TOOLBOX navigation is already implemented.
