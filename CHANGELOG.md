# CHANGELOG — VoidDesk

> **Release candidate:** `v10.5.4-NEXUS`  
> **Status:** prepared for review; not yet published as a GitHub Release  
> **Date:** 2026-11-08

This file records user-visible changes by release. The next candidate is documented separately from the previous release history. Hardware-dependent behaviour is not marked verified until it has been exercised on the target handheld.

---

## v10.5.4 "Nexus" — release candidate · 2026-11-08

### Fixed

| Reference | Reported problem | Change in this candidate | Verification status |
|---|---|---|---|
| [#2](https://github.com/SilverCrow2323/Void-Desk-Project/issues/2) | Bluetooth activity could stall the NEXUS animation and delay controller input | Host status collection now runs in a single background worker. The render path reads a cached snapshot and never waits for `hciconfig` or `bluetoothctl` to respond. | Automated regression tests added; RG35XXSP confirmation still required |
| [#2](https://github.com/SilverCrow2323/Void-Desk-Project/issues/2) | Device power-off could leave the RG35XXSP powered with its LED off | The muOS shutdown path now hands the request back to `mux_launch.sh`; the launcher stops the local service, runs `sync`, then tries forced power-off and device power-off fallbacks. | Shell and Python checks can validate the hand-off; physical RG35XXSP test still required |

### Documentation and maintenance

- Clarified that NetSurf, Falkon and Dillo are optional browsers inside the XFCE desktop image, while `qtWebBrowser` is a separate third-party muOS application.
- Added a browser error-reporting checklist and the relevant VoidDesk/XFCE log paths.
- Expanded the architecture notes for the asynchronous status cache and device power-off hand-off.
- Added regression tests for non-blocking status reads, cached snapshots and recovery after a failed probe.
- Aligned the Python application and launcher version metadata on the 10.5.4 release line and extended `BUILDCHECK.py` to inspect the PC launcher too.
- Added a repeatable LÖVE visual pass covering 20 scenes, with PNGs, JSON sidecars and a batch manifest; failed scenes are reported rather than silently omitted.
- Added F12 capture support, a 171-item visual asset inventory, and generated HTML galleries for artwork and captured screens.
- Added a GitHub Actions job that runs the real LÖVE 11.5 runtime under Xvfb and uploads the screenshot set, manifest, logs and catalog as a 30-day artifact.
- Made automated screenshots deterministic and privacy-safe by substituting synthetic system, network and media status values.
- Fixed the VOID EDIT typewriter reveal to count Unicode code points, preventing partial UTF-8 characters from crashing the renderer.
- Prepared multi-page GitHub Wiki source content and a publisher script; the one-time creation of the initial Wiki Home page remains a GitHub UI step.
- Added F12 screenshot capture in both Pygame and LÖVE, with PNG output and JSON metadata under `data/visual-captures/`.
- Added a dependency-free visual inventory tool for asset sizes, image dimensions, SHA-256 hashes, active NEXUS texture references and screenshot coverage.
- Documented the experimental/incomplete status of LÖVE; Pygame remains the recommended frontend.
- Prepared a multi-page GitHub Wiki source set for MustardOS 2606.0 Andromeda, hubs, controls, frontends, troubleshooting and development.

### Validation

The automated CI run for this candidate is the source of truth for compilation, unit tests, lint, shell parsing and LuaJIT syntax. A green CI run does **not** replace testing on the RG35XXSP or other H700 hardware.

### Open follow-ups

- **[#1 — internet browser not working](https://github.com/SilverCrow2323/Void-Desk-Project/issues/1):** not marked fixed. The report contains only “output input error”; it does not identify the browser or the screen from which it was launched. Reproduction details and the complete error/log are still needed.
- **[#2 — stutters and hangs](https://github.com/SilverCrow2323/Void-Desk-Project/issues/2):** both code paths are addressed in this candidate, but keep the issue open until the result is validated on an RG35XXSP running muOS.

### Remaining project work

- Several optional applications under `outdesk/` are still prototypes/placeholders and are not part of this release's completion claim.
- IceWM/LXDE availability depends on the optional desktop image and installed packages; XFCE remains the documented baseline.
- Device-only operations such as package installation, desktop-image repair, session hand-off and power management still require physical hardware validation.

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
