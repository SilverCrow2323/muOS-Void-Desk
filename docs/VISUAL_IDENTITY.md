# QWASAR Desk Visual Identity System

## Direction

QWASAR Desk has a recognizable industrial science-fiction identity: brutalist interfaces, immense architectural scale, dense technical typography, hard silhouettes, manga-like ink contrast, restrained grain, warning markings and vivid signal colours. The intended mood is raw, mysterious and tactile rather than glossy neon-by-default.

The visual direction may be informed by dark cyberpunk manga and architectural science fiction (including the sense of scale and materiality associated with works such as *BLAME!*), but QWASAR Desk must use its own original compositions, symbols, layouts, illustrations and typography. Do not reproduce panels, characters, logos, page layouts or signature artwork from another work.

## Separate aesthetic from palette

A **visual style** controls composition and rendering language: geometry, density, borders, texture, typography hierarchy, motion, illustration treatment and information layout.

A **palette** controls colours only: background, panel, primary accent, secondary accent, text, muted text and semantic states.

Users must be able to combine any supported visual style with any compatible palette. Do not create a separate hard-coded theme for every combination. Studio profiles should eventually store `visualStyle` and `palette` as separate identifiers with a fallback to the device default.

## Proposed visual styles

| ID | Display name | Visual language | Default use |
|---|---|---|---|
| `megastructure` | Megastructure | Monumental brutalist sci-fi, black ink, steel surfaces, sparse red/cyan signal accents, dense technical labels, architectural linework | Signature QWASAR Desk |
| `manga_ink` | Manga Ink | High-contrast monochrome, paper/ink surfaces, halftone-like texture, bold panel framing, restrained vermilion markers | Reading-heavy tools and compact displays |
| `industrial` | Industrial Console | Riveted-panel geometry, measurement marks, hazard striping, steel and amber/cyan indicators | Workshop, Forge, diagnostics |
| `terminal` | Phosphor Terminal | Monospaced hierarchy, low-colour interface, phosphor green/amber/cyan, minimal motion | Shell, logs, developer tools |
| `neon_noir` | Neon Noir | Night-city contrast, electric cyan/magenta, layered glow used sparingly | Media and entertainment |
| `minimal` | Quiet Utility | Flat surfaces, low visual noise, clear spacing, reduced animation and effects | Accessibility and low-power devices |

## Palette presets

Initial palette identifiers should include existing `crimson`, `cyberpunk`, `green`, `stealth`, plus `amber`, `ice`, `paper` and `signal_red`. Palette support must be advertised by each engine adapter; unsupported choices fall back visibly rather than silently.

## Motion and effects

- Effects are individually configurable: scanlines, grain, vignette, glitch, orbit motion, parallax and transitions.
- Provide a reduced-motion mode and a low-power preset.
- Never make text legibility depend on animation, glow or colour alone.
- Use stable frame budgets; decorative effects must be the first thing disabled under load.
- Keep controller focus indicators strong and consistent across every style.

## Engine parity

The current Pygame frontend already contains a dark megastructure-inspired visual language and configurable accent palettes. The LÖVE frontend currently has four palette definitions in `love/theme/loader.lua`. Those are palette presets, not a complete shared style system.

The first implementation adds more LÖVE palettes and documents the style taxonomy. A later shared visual-token manifest will let Pygame and LÖVE advertise the same style/palette IDs. Do not claim parity until visual-capture tests cover both engines.

## Acceptance criteria

- Style and palette are independent settings.
- Every style remains readable at 640x480 and at desktop window sizes.
- Reduced-motion and low-power options disable expensive decoration.
- Theme changes do not change tool capabilities or permissions.
- No third-party copyrighted artwork is bundled as a theme.
