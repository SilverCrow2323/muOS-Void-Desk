# Void Desk Tool Catalog and Information Architecture

This is an inventory of tool families and entry points found in the current source tree. It is a source-grounded map, not a promise that every item is enabled on every firmware or PC. Availability depends on host packages, device capabilities, permissions, optional downloads and frontend coverage.

## Navigation model

Use three levels:

1. **Workspace** — the user's intent (Connect, Create, Maintain, Play, Media, Configure).
2. **Category** — a stable group of related tools.
3. **Tool** — one action or screen with a stable ID, capability requirements, platform support and lifecycle status.

Keep the existing NEXUS hubs as the visual top-level navigation for compatibility. The catalog can reorganize tools without renaming their internal routes. User-created profiles may reorder and relabel entries, but cannot create arbitrary executable routes.

## Current workspace/category proposal

| Workspace | Category | Existing hub / entry point | Representative tools |
|---|---|---|---|
| Connect | Network & wireless | UPLINK | Wi-Fi, hotspot, Bluetooth, network diagnostics, network probe |
| Connect | Remote access & sync | UPLINK | Rt:Tailscale-M, Syncthing, FTP, PC Uplink, BaseStation |
| Connect | Controllers & peripherals | UPLINK / MUOS APPS | Controller tools, device remapper, glyph manager |
| Create | Files & productivity | RT:TOOLBOX | File manager, editor, notes, calendar, calculator, clock |
| Create | Developer tools | DEVELOP / RT:TOOLBOX | Python REPL, shell, editor, package/build helpers |
| Maintain | System health | WORKSHOP | Device Check:Rt, diagnostics, system monitor, storage, jobs/logs |
| Maintain | Packages & environments | THE FORGE | Component installer, autostart, updates, CLI tools, APT management |
| Maintain | Performance & cleanup | WORKSHOP / THE FORGE | Boost controls, cache cleanup, CHD utilities, duplicate-file tools |
| Play | Handheld apps & games | MUOS APPS / GAMES | muOS app discovery, PortMaster hand-off, native .muxapp browser, collections |
| Media | Playback & library | MEDIA VAULT | Internet radio, media library, VoidCast IPTV, BGM normalization |
| Configure | Appearance & controls | SETTINGS | Palette/theme, font scale, language, controller bindings, status bar, VFX, boot animation |
| Configure | Sessions | START SESSION / END SESSION | XFCE, IceWM, LXDE, session hand-off, restart/exit |
| Discover | Documentation & community | INFO / COMMUNITY | Manual, diagnostics information, muOS forum/wiki, sharing entry points |
| Extend | Standalone applications | OUTERDESK / External Tools | Optional portable applications and integrations |

## Inventory by source area

### Core frontend tools

- `desk/hubs/`: Python/Pygame hub action classes for Toolbox, Workshop, Uplink, Media, Forge, Settings, Develop, Games, Community, OuterDesk and muOS Apps.
- `love/scenes/`: LÖVE scenes including Forge/APT, Calendar, Diagnostics, Display FX, External Tools, IPTV, muOS Apps, Media, Monitor, Session, Settings, Shell, Syncthing, Tailscale, Toolbox, Uplink, Workshop, Calculator, Clock and Editor.
- `love/core/`: shared scene manager, input, jobs, notifications, widgets, layout, bridge, shell client and status-facing modules.

### External application registry

`external/tools.json` is the current external tool registry (version 3). It currently declares:
- `voidcast`: standalone IPTV/media application, Python frontend, MEDIA category.
- `bgm_normalizer`: BGM normalization utility, shell launcher, MEDIA category.
- `file_gd_x`: File-GD X file manager, LÖVE launcher, TOOLBOX category.

The registry is the best starting point for a future unified catalog, but it currently describes launch metadata only. It does not yet express permissions, compatibility, dependencies, update channel, health, publisher trust or lifecycle status.

### Standalone applications under outdesk/

Source inventory includes BootAnimManager, Disc Crusher, EthoStore, ImageViewer, Little Mischief, MediaPlayer, Portable Forger and VoidCast. These should be separate catalog entries with explicit install source and compatibility metadata, not automatically treated as built-in Void Desk features.

**Security review flag:** Little Mischief contains Wi-Fi capture/scanning and attack-oriented scripts. Keep it isolated from the core catalog until its intended authorized-lab use, safeguards, permissions and packaging policy have been reviewed. Do not expose attack actions as ordinary connectivity utilities.

## Lifecycle and availability labels

Use consistent status labels in the catalog:
- `built_in`: shipped in the Void Desk package.
- `optional_dependency`: requires a host package or runtime.
- `external_app`: separately launched application.
- `experimental`: incomplete or not feature-equivalent across engines.
- `hidden`: available behind an optional navigation profile, not a security boundary.
- `unsupported_platform`: known platform mismatch.
- `deprecated`: retained for migration only.

A tool record should eventually include: stable ID, display name, short description, workspace, category, frontend route(s), launch kind, supported engines, supported platforms, required capabilities, dependencies, permissions, status, source/package, maintainer, and documentation URL.

## Consolidation rules

- One canonical tool ID regardless of engine; Pygame and LÖVE routes are adapters.
- Avoid duplicate entries for the same operation (e.g. system status exposed in both Toolbox and Workshop): one canonical tool with multiple navigation placements where useful.
- Separate read-only diagnostics from mutating maintenance actions.
- Group privileged actions (package install/remove, shell, reboot, mount, network configuration) under clear permission and confirmation boundaries.
- Keep optional desktop-image tools distinct from the handheld host environment.
- Never infer availability from a menu entry alone; use a capability/dependency probe and display an explicit unavailable reason.

## Optimization backlog

1. Preserve the existing Pygame non-blocking status poller pattern; no slow host command belongs in a render/input callback.
2. Make LÖVE configuration writes atomic and retain the previous valid file on failure.
3. Consolidate duplicate status refresh timers where the same service snapshot can be shared.
4. Make scene/tool metadata declarative so catalog, navigation and Studio can share one source.
5. Add lazy loading and cache invalidation rules for optional tool metadata/assets.
6. Add performance instrumentation for scene load, frame time, bridge queue depth and status refresh duration before speculative micro-optimizations.
