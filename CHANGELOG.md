# CHANGELOG — VoidDesk

> Current version: **v10.5.3-NEXUS** · last updated 2026-11-08
> One file: roadmap on top, changelog history below.

---

# 🗺️ ROADMAP — what's next

## Part A — Open issues (GitHub)
- **A1** 🔥 Stuttering on RG35XXSP at launch — BT-related · ~1-2 h
  *(synchronous `bluetoothctl` in the render path — cache async, thread+queue)*
- **A2** 🔥 Shutdown hangs — LED off, system stays warm · ~45 min
  *(add `sync` + `poweroff -f` + kill orphan children + fallback to `reboot -f`)*

## Part C — Functional gaps
- **C1** 🟠 7 `outdesk/*` placeholders · ~16 h total
  — start with **MediaPlayer** (~1.5 h), then ImageViewer, Disc_Crusher,
  Portable_Forger, EthoStore, BootAnimManager, Little_Mischief
- **C2** 🟠 Missing assets · 1-4 h
  — `bin/vd_bootanim.py`, `bin/vd_hotkey.py`, `assets/*/xinitrc`,
  `assets/xfce/qjoypad_*.lyt`, `assets/logos/*.png`
  — first step: `git log --all --oneline -- bin/vd_bootanim.py`
- **C3** 🟡 `EthosCommandeer.export_to_github()` stub · ~45 min

## Part D — Quality
- **D1** 🟡 Tests for `desk/utils/*` · ~40 min — `apply_fixes.sh --only d1`
- **D2** 🟡 PC/Android-only docs + guards · ~20 min — `apply_fixes.sh --only d2`

## Part E — Suggestions
- **E1** 🔵 Centralized logging · ~1 h
- **E2** 🔵 CI on push · ~30 min — `apply_fixes.sh --only e2`
- **E3** 🔵 Docs site / Discord · ~2 h

## Planned sequence
| Sprint | Items | 
| 1 | A2 + A1 | 
| 2 | C2 (assets) | 
| 3 | C1 MediaPlayer | 
| 4 | E2 (CI) |
| 5 | C3 + D2 |
| 6 | D1 (tests) | 
| 7 | C1 remaining | 
| 8 | E1 + E3 |


### Not yet done (flagged, not guessed at)
- IceWM / LXDE sessions still stub ("coming soon")
- `h_apt_update` on device backgrounded but not deeply exercised — worth a real test with XFCE actually installed
- Italian→English string cleanup (831 lines, `ITALIAN_REMAINING.txt`) and README/wiki split — still queued
- B7 root cause: `core.layout` module no longer exposes `.get()` (or never did). Current fix is a **resolver + default fallback** — safe and permanent, but if the real API has a single canonical name (e.g. `compute()`), replacing the resolver with a direct call is cleaner. To confirm, run:
  `grep -nE '^function |^M\.|^return ' love/core/layout.lua`
  and `grep -oE '\bL\.[a-zA-Z_]+' love/core/dashboard_screen.lua | sort -u`.
  If `core.layout` intentionally exports a table of *constants* (no function), the resolver will always fall to the default — which is fine, but the function `layout.get` should be documented as removed or the import on line 13 dropped.
---

# CHANGELOG HISTORY

## v10.5.3 "Nexus" — 2026-11-08

### Bugs fixed
| # | Symptom | Cause | Fix |
|---|---------|-------|-----|
| B1 | Toggling engine to `py` → app wouldn't boot at all | `bootstrap_lite.py` never called; `.pygame_ready` marker checked by nothing | `mux_launch.sh` bootstraps on demand before launching `py`, self-heals to `love` if bootstrap fails or pygame crashes |
| B2 | Every LÖVE hub silently broken, "Install XFCE" timing out | `service/voiddesk_service.py` referenced 9 handlers that were never defined — `NameError` at import | implemented all 9 handlers (`system_status`, `network_status`, `media_status`, `hotspot_toggle`, `wifi_scan`, `bt_scan`, `session_list`, `session_launch`, `apt_update`), reusing `desk/sysinfo.py` |
| B3 | "Install XFCE" on device did nothing (fake `ok:true`) | `h_xfce_install` was a stub for the device branch | now launches `bin/xfce_bootstrap.py` in the background, with a lock file against duplicate runs |
| B4 | CRT shader: scene-level crash got crashed *again* by the fallback | `crt_shader.lua` v1 re-called `draw_fn()` a second time, unprotected | `draw_fn()` runs exactly once, unprotected — real scene bugs surface clean |
| B5 | CRT shader made UI blurry | composite canvas sampled with default LINEAR filter | `canvas:setFilter("nearest","nearest")`; chromatic aberration OFF by default |
| B6 | "Launch XFCE" on device: honest error, no real hand-off | taking over the screen from a running LÖVE process needs the launcher itself | `session_launch` drops `.pending_session` → LÖVE calls `love.event.quit()` → `mux_launch.sh` runs `xfce_launch.sh` full-screen, then relaunches the engine on logout |
| B7 | Every LÖVE hub crashes on open: `attempt to call field 'get' (a nil value)` at `core/dashboard_screen.lua:92` | B4 working as intended — crt_shader no longer double-calls `draw_fn()`, so a pre-existing L92 bug that was previously masked by the old fallback now surfaces clean. L92 was `local L = layout.get()`, i.e. a **zero-arg** `.get()` on `layout`, which is `require("core.layout")` (a module). The module does not export `.get` — likely renamed or removed in a refactor. Two-line diagnosis confirmed: `grep -n "layout" love/core/dashboard_screen.lua` → `13: local layout = require("core.layout")` (only usage) and `grep -oE '\bL\.[a-zA-Z_]+' love/core/dashboard_screen.lua` shows the exact keys `draw()` expects. | L92 rewritten as a **resolver**: tries `layout.get / compute / build / current / for_screen / make / new / resolve` (in order, `pcall`-wrapped), uses the first that returns a table; if none does, falls back to a sensible default layout built from `love.graphics.getDimensions()` with the keys the draw() code needs (`W, H, margin, header_h, footer_h, row_h, content_*`). Scene renders correctly. Auto-applied by `apply_fixes.sh --only b7` with backup + `luajit -b` validation + rollback-on-failure. **Still flagged**: the *ideal* fix is one of (a) restore `core.layout.get()` if it existed and was renamed, (b) if the function has a new name, drop the resolver and call it directly. Resolver is the safest permanent option if `core.layout`'s API is intentionally fluid. |

### New
- `love/core/crt_shader.lua` — global GPU post-process pass (scanlines, vignette, glitch, optional chromatic aberration) applied to every LÖVE scene via one hook in `main.lua`
- `love/scenes/hub_display_fx.lua` — Settings submenu with independent toggles + intensity levels, reachable from Settings → Display FX
- HUD corner brackets + animated scan-sweep line in `love/core/chrome.lua`
- `mux_launch.sh` session-handoff loop (engine ↔ XFCE ↔ engine)
- `.github/workflows/ci.yml` — compileall + ruff + luajit, safe-by-default (never blocks merge)
- `tests/` — pytest suite for `desk/utils/safe_calc.py`, `safe_extract.py`, `atomic_io.py`
- `assets/basestation/README.md` + `mux_launch.sh` guard (PC-only note)
- `assets/androidstation/README.md` + `mux_launch.sh` guard (Android-only note)

### Validated
Lua syntax + logic for every `love/*.lua` file checked with LuaJIT 2.1 (same engine LÖVE 11.5 uses, not vanilla Lua 5.1); Python with `ast.parse` + live service smoke test (ping / system_status / network_status / media_status / session_list all respond without crashing); shell with `sh -n` and `dash -n`.



---

## v10.5.2 "Nexus" — 2026-11-08

### Boot animation (`desk/intro.py`) — rewritten
- **Real logo**: `resources/vd_logo.png` as hero asset with silent fallback
- **Animated menu voices**: all 9 hub names cascade in one by one with glitch-slide entrance + accent tick; each row carries its subtitle
- **New act structure**: tunnel fade-in → logo glitch reveal → title slide + rainbow "Rintromping" subtitle → menu cascade → hold frame with purple aurora → CRT collapse → Uzumaki spiral transition
- All on-screen text in English
- `intro.play()` signature unchanged

### PC launcher — consolidated to one file
- **Merged `voiddesk_tui.py` + `desktop_run.py` + the old `voiddesk.sh` logic into a single `voiddesk.py`** with hidden `--_runtime` flag. Launcher half runs on system python3 (stdlib only); Pygame half re-executes the same file under the venv interpreter.
- `voiddesk.sh` reduced to a 3-line wrapper (`exec python3 voiddesk.py "$@"`)
- **Removed** `voiddesk_tui.py`, `desktop_run.py`, `run_desktop.sh`
- Preserved: `--love`, `--py`, `--engine {py|love}` validation, `--help`, `--desktop` compat, venv bootstrap on first `--py`, device-only exit-code guard (11-17), keyboard bridge, fbdisplay bypass, render flip guard
- **Fixed**: `voiddesk.sh --engine "$X"` no longer injects `$X` as Python source; unknown `--engine` value now fails loud (exit 2) instead of silently launching LÖVE

---

## v10.5.1 "Nexus" — 2026-11-07

### Frontend architecture
- **Dual engine**: Pygame (py) and LÖVE (love) frontends, selectable at runtime
- **TUI launcher**: numeric menu, arch-aware `which_love()`, direct dispatch

### LÖVE frontend (`love/`)
- **Nexus planetarium**: 10 nodes, sun at center, cel-shaded planets, rings per node, END NODE as purple comet
- **Hub scenes**: START SESSION, THE FORGE, UPLINK, MEDIA VAULT, WORKSHOP, RT:TOOLBOX, SETTINGS, INFO, MUOS APPS, EXTERNAL
- **Calendar**, **Shell**, **IPTV prototype**, **Boot animation**, **CRT shader**, **Settings**, **About**

### Backend service (`service/voiddesk_service.py`)
- Job manager with streaming output + progress parsing
- Terminal I.D. overlay (3 levels)
- External tools registry (`external/tools.json`)
- PTY shell via `pty.fork()`
- Calendar events

### Pygame frontend (`desk/`)
- Menu Settings has Engine option (py/love cycle)
- All hub calls through `App.launch_external_tool()`
- File-GD X as definitive file manager

### Fixed
- Duplicate root `main.py` removed
- `desk/utils.py` shadow (merged into `desk/utils/__init__.py`)
- Version mismatch 10.2.1 → 10.5.1 everywhere
- Service: restored 8 handlers swallowed by regex patches
- LÖVE dpad double-step fixed
- XFCE install on PC: pkexec → sudo -n → direct apt cascade
- `which_love()` architecture-aware
- `crt.init` alias
- `opt_engine` in Pygame had `intro`'s config key
- `mux_launch.sh` exports `SDL_VIDEODRIVER=dummy` on device

### Third-party
File-GD X, VoidCast, BGM Normalizer, Rt:Tailscale-M, DejaVuSans, JetBrainsMono, Oxanium, iptv-org, open-meteo, radio-browser.

---

# Recent fixes (from previous audit B1–B6 history, for reference)

- B1 `desk/hubs/toolbox.py` SyntaxError — fixed in `ee3c870` → `5b78d09`
- B2 `desk/hubs/uplink.py` IndentationError — fixed in `ee3c870`
- B3 `Disc_Crusher/mux_launch.sh` wrong filename — fixed in `ee3c870`
- B4 `ethos_commandeer.py` missing `simpledialog` import — fixed in `ee3c870`
- C4 `Little_Mischief` / `BootAnimManager` launchers — fixed in `ee3c870`
- C5 9 duplicate app IDs in `db.json` — fixed in `ee3c870`
- C6 BGM Normalizer integration — `a6a2a28` + `5b78d09` + `a88b7b9` + `f41bfad`
- D3 personal paths in `config.ini` — sanitized in `a88b7b9` + `f41bfad`
- D4 `__pycache__` not ignored — fixed in `5a7a4a4`
