# VoidDesk 10.5.0 -> 10.5.1 (audit + fixes)

The original is untouched: every change is in `apply_patches.py` (exact matches with asserts) plus new files.

## Bugs fixed
| # | Symptom | Cause | Fix |
|---|---------|-------|-----|
| B1 | Intro never shown ("intro non riuscita" in the log) | `play_intro()` -> `render()` uses `volume_overlay`, created later | overlay and `volume_level` created before `evinput.start()` |
| B2 | Radio: on a flaky network the except block itself blows up | `self.log` does not exist in `App` | global `log(...)` |
| B3 | CURSEDEV from the Info menu -> AttributeError | `cursedev_enter` moved to `InfoHub.cursedev()` | `self.info_hub.cursedev()` |
| B4 | `render_cursedev_zenoh` blows up | `self.app.surface` inside `App` | `self.surface` |
| B5 | Context Pack writes the file, then shows an error | `it` not defined in `_vd_generate` | `it = (self.lang == "it")` |
| B6 | `DirtyRectRenderer.mark_all_dirty` NameError | `W`,`H` not defined | size taken from the display |
| B7 | `play_outerdesk_boot` defined twice | refactor leftover | dead duplicate removed |
| B8 | BGM screen: AttributeError on every frame + log flood | `App.line` / `App.rect` never defined (7 call sites) | methods added |
| W1 | First open of Workshop/Toolbox/Forge/Media/Uplink/CURSEDEV is slow, globals duplicated | wrapper used `exec` -> `from desk.main import` re-ran 34k lines | wrapper uses `import_module("desk.main")` |

## Robustness / performance
- VOL+/-: non-blocking `amixer`; `amixer sget` and dependency checks have timeouts.
- `tar.extractall` checks for path traversal (`desk/utils/safe_extract.py`, local copy in `bootstrap_lite.py`).
- Calculator: whitelisted AST with caps (`9**9**9` and `factorial(99999)` no longer freeze the device).
- `desk_config.json` and user data (VC config, custom radio list, diagnostics config): atomic writes, `.bak` fallback for the main config (`desk/utils/atomic_io.py`).
- Glyph preview cache (no load+scale per frame); NEXUS gravity Surface cache.
- Launcher: log rotation (>1MB), debug log tail only, `sgrub/` guards, portable `$?`, fixed `"D.N"` quoting.
- debug_main: log truncated per session.

## Language
The UI now defaults to English (launcher included). The Language setting still switches it/en; an existing config with `"lang": "it"` keeps Italian.

## Cleanup
Removed: root `main.py` (stale v10.2.1), `desk/utils.py` (shadowed by the `desk/utils/` package), `desk/nradar.py` (never imported), all `.pyc`. Added `.gitignore`.
If `.pyc` files are already on git: `git rm -r --cached $(git ls-files | grep -E '__pycache__|\.pyc$')`.

## Tools
- `BUILDCHECK.py` v2: all .py files, undefined names, duplicate methods, shadowed modules, scripts missing for the launcher, undefined `self.X` in `App`, unprotected tar, version consistency, `--smoke` headless run with the intro enabled. FAILS on the original (13 errors), PASSES on the patched tree.
- `desktop_run.py`: run the app in a 640x480 window with keyboard input (`python3 desktop_run.py`).

## Not touched (your call)
~130 `except: pass`; remaining non-atomic `json.dump` calls are only a disposable cache and temp files; `icons` vs `desk.icons` are loaded as two modules.
Performance was not measured on the device: validate on the RG35XX H.
