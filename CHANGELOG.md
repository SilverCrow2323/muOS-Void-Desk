# CHANGELOG — VoidDesk

## v10.5.1 "Nexus" — 2026-11-07

### Frontend architecture
- **Dual engine**: Pygame (py) and LÖVE (love) frontends, selectable at runtime
  via `Settings → Frontend engine` (persists to desk_config.json)
- **TUI launcher** (`voiddesk_tui.py` + `voiddesk.sh`):
  - numeric menu: launch config engine / love / py, toggle, config, logs,
    dependencies, install LOVE, repair
  - `./voiddesk.sh --love | --py | --engine X | --desktop`
- **Unified launcher** honors arch (ARM device → lib/love, PC → system love)

### LÖVE frontend (`love/`)
- **Nexus planetarium**: 10 nodes, sun at center, cel-shaded planets
  (BLAME style), rings per node (asteroid_double FORGE, thin MEDIA,
  saturn_thick TOOLBOX), END NODE as purple comet with orbit-following
  tail (custom per node)
- **Hub scenes** (all with icons + inline values):
  - START SESSION, THE FORGE, UPLINK, MEDIA VAULT, WORKSHOP,
    RT:TOOLBOX, SETTINGS, INFO, MUOS APPS, EXTERNAL
- **Calendar** ("Temporal Drift"): animated monthly grid, today beam,
  selection ring rotates, event diamonds, month slide transitions,
  right detail panel
- **Shell** ("Void Terminal"): real PTY via service, quick commands bar,
  on-screen keyboard, boot sequence animation, datastream background
- **IPTV prototype**: M3U + XMLTV parsing via service, mpv player
- **Boot animation**: tunnel effect (rings + arcs + progress)
- **CRT shader**: scanlines + chromatic aberration + vignette (optional)
- **Settings**: 13 items with live values (engine, theme, lang, view,
  player, cache, EPG, UA, rec dir, logos, bootanim, preview)
- **About**: 9 items (project, manual, controls, manifesto, updates,
  platform, logs, credits)

### Backend service (`service/voiddesk_service.py`)
- **Job manager** with streaming output + progress parsing (NN% / N/M)
- **Terminal I.D.** overlay: 3 levels (item spinner / status strip /
  full-screen overlay with tabs, log, progress bar)
- **External tools** registry (`external/tools.json`): voidcast,
  bgm_normalizer, file_gd_x, rt_tailscale_m — engine-agnostic launch
- **PTY shell**: real bash via `pty.fork()`, non-blocking polling
- **Calendar events**: reads/writes `data/calendar.json`
- **Network/system/media status** for dashboard widgets

### Scenes / UX
- **Back navigation stack** (`sm.push` / `sm.back`): going back returns
  to previous scene with selection preserved
- **Scrolling dashboards**: scissor clip + arrow indicators, selected
  item kept in view
- **Fonts +25%** across the board for 640x480 readability
- **Row height** 38→54, header 56→68, footer 44→56, widget 150→180
- **Icons**: procedural icons for every menu item (no letter badges)

### Pygame frontend (`desk/`)
- Menu Settings has **Engine** option (py/love cycle)
- All hub calls go through `App.launch_external_tool()` for external tools
- File-GD X as definitive file manager (from muos-prototypes)
- BGM Normalizer, File Grid-Diver (VoidCast sibling)
- `notify()` recovered after regex damage

### Fixed
- Duplicate root `main.py` removed (was stale v10.2.1)
- `desk/utils.py` shadow (merged into `desk/utils/__init__.py`)
- Version mismatch: 10.2.1 → 10.5.1 everywhere
- Service: restored 8 handlers swallowed by regex patches
  (h_network_status, h_system_status, h_media_status, h_hotspot_toggle,
  h_list_muos_apps, h_launch_muos_app, h_toolbox_stats, h_external_status)
- LÖVE dpad double-step: hat takes priority, axis ignored, 120ms debounce
- XFCE install on PC: pkexec → sudo -n → direct apt cascade with log
- `which_love()` architecture-aware (ARM binary not used on x86_64)
- `crt.init` alias (main.lua called init, module had load)
- `opt_engine` in Pygame had `intro`'s config key and values
- `mux_launch.sh` exports SDL_VIDEODRIVER=dummy on device

### Removed
- `external/File-Grid-Diver-XX` (superseded by File-GD X)
- Old `run_desktop.sh.deprecated.*` backups

### Third-party
- File-GD X (LÖVE, from muos-prototypes) — file manager
- VoidCast (Pygame) — IPTV
- BGM Normalizer (Pygame) — audio
- Rt:Tailscale-M (LÖVE) — VPN
- DejaVuSans, JetBrainsMono, Oxanium — fonts
- iptv-org, open-meteo, radio-browser — free data APIs
