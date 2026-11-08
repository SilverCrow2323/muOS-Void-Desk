#!/usr/bin/env python3
"""Deterministic visual smoke captures for Pygame home styles and render states.

Direct state rendering checks the screen renderer, not navigation or actions.
"""
from __future__ import annotations

import argparse
import inspect
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "desk")]


class _NullPoller:
    def __init__(self, *args, **kwargs):
        self._initial = dict(kwargs.get("initial") or {})

    def snapshot(self):
        return dict(self._initial)

    def stop(self):
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--all-states", action="store_true",
        help="also smoke-render every state branch in App.render_state",
    )
    args = parser.parse_args()

    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    os.environ.setdefault("VOIDDESK_NOINTRO", "1")
    os.environ.setdefault("VOIDCAST_FB", "0")

    try:
        import pygame
        import desk.main as app_module
        from desk.utils.visual_capture import capture_surface
    except Exception as exc:
        print("[pygame-capture] import failed: %s: %s" %
              (type(exc).__name__, exc), file=sys.stderr)
        return 2

    # Keep the smoke run isolated from the developer's device config and
    # hardware services. Fonts and artwork still come from the real checkout.
    sandbox_data = Path(tempfile.mkdtemp(prefix="voiddesk-pygame-capture-"))
    config = {
        "termid_id": "VISUAL-CI",
        "intro": False,
        "sfx": False,
        "home_style": "nexus",
        "theme": "ambra",
        "pc_link_always_on": False,
        "bstation_always_on": False,
        "autostart": [],
        "autostart_exec": [],
    }
    app_module.DATA = str(sandbox_data)
    app_module.load_cfg = lambda: dict(config)
    app_module.save_cfg = lambda _cfg: True
    app_module.evinput.start = lambda: True
    app_module.evinput.stop = lambda: None
    app_module.fbdisplay.attach = lambda _surface=None: True
    app_module.fbdisplay.detach = lambda: None
    app_module.sysinfo.StatusPoller = _NullPoller

    styles = ("blame", "hud", "terminal", "orbit", "nexus")
    results = []
    errors = []
    app = None
    try:
        app = app_module.App()
        app.stack = ["home"]
        app.sel = 0
        app.trans = None
        app.prev_frame = None
        (ROOT / "data" / "visual-captures").mkdir(parents=True, exist_ok=True)

        for style in styles:
            try:
                app.cfg["home_style"] = style
                app.surface.fill((0, 0, 0))
                app.render_state()
                pygame.display.flip()
                path, error = capture_surface(
                    app.surface, ROOT, "pygame", "home-" + style)
                if not path:
                    raise RuntimeError(error or "capture returned no path")
                results.append({
                    "screen": "home-" + style,
                    "home_style": style,
                    "image": Path(path).name,
                    "width": app.surface.get_width(),
                    "height": app.surface.get_height(),
                })
                print("[pygame-capture] saved %s" % path)
            except Exception as exc:
                errors.append({
                    "screen": "home-" + style,
                    "error": "%s: %s" % (type(exc).__name__, exc),
                })
                print("[pygame-capture] failed home-%s: %s" %
                      (style, exc), file=sys.stderr)

        state_names = []
        fixture_app_dir = sandbox_data / "mapp-fixture"
        fixture_app_dir.mkdir(parents=True, exist_ok=True)
        (fixture_app_dir / "mux_launch.sh").write_text(
            "#!/bin/sh\\n# ICON: fixture\\n", encoding="utf-8"
        )

        def prepare_state(state_name):
            # These states are normally entered with data prepared by an
            # interaction. Supply inert, isolated fixtures so we can test
            # their renderer without starting a PTY, scanning devices or
            # touching real applications and files.
            if state_name == "rtshell":
                app.rtsh_buf = app_module.rtshell.TermBuffer(
                    app.rtsh_cols, app.rtsh_rows
                )
                app.rtsh_buf.feed(b"VOIDDESK VISUAL TEST\\r\\n$ ")
                app.rtsh_sess = None
                app.rtsh_welcome = False
            elif state_name == "chddetail":
                app.chd_detail_sd_idx = 0
                app.chd_detail_file = {
                    "name": "visual-fixture.cue",
                    "linked": [{
                        "name": "visual-fixture.bin",
                        "missing": False,
                        "size": 4096,
                    }],
                    "total_size": 4096,
                }
            elif state_name == "capture":
                app.map_sel = min(1, len(app.map_rows()) - 1)
                app.capture_t = time.time()
            elif state_name == "swap":
                keys = list(app_module.FUNC_BY_KEY)
                key, other = keys[0], keys[1]
                events = app.cur_map().get(key) or []
                app.pending = (key, events[0] if events else 304, other)
            elif state_name in ("mappdetail", "glyphpick"):
                app.mapp_cur = {
                    "name": "Visual Fixture",
                    "sd": "CI",
                    "dir": str(fixture_app_dir),
                    "icon": None,
                }
                app.mapp_size = 4096
                app.det_sel = 0
                app.gp_list = []
                app.gp_sel = 0
            elif state_name == "ctrlswap":
                app.ctrl_pending = (
                    "Visual fixture controller",
                    "hid:304", "hid:305", "hid:307",
                )
            elif state_name == "fmsearch":
                app.fm_search_q = "visual fixture"
                app.fm_search_results = []
                app.fm_search_sel = 0
            elif state_name == "fmbookmarks":
                app.fmbm_sel = 0
            elif state_name == "imgview":
                app.img_path = str(ROOT / "love" / "assets" / "logos"
                                   / "voiddesk.png")

        if args.all_states:
            render_source = inspect.getsource(app_module.App.render_state)
            state_names = list(dict.fromkeys(re.findall(
                r"""^\s*(?:if|elif)\s+top\s*==\s*["']([^"']+)["']""",
                render_source, re.MULTILINE,
            )))
            if not state_names:
                raise RuntimeError("could not discover App.render_state branches")
            for state_name in state_names:
                if state_name == "home":
                    continue  # covered by all five home-style variants
                screen_name = "state-" + state_name
                try:
                    app.stack = [state_name]
                    prepare_state(state_name)
                    app.surface.fill((0, 0, 0))
                    app.render_state()
                    pygame.display.flip()
                    path, error = capture_surface(
                        app.surface, ROOT, "pygame", screen_name)
                    if not path:
                        raise RuntimeError(error or "capture returned no path")
                    results.append({
                        "screen": screen_name,
                        "state": state_name,
                        "image": Path(path).name,
                        "width": app.surface.get_width(),
                        "height": app.surface.get_height(),
                    })
                    print("[pygame-capture] saved %s" % path)
                except Exception as exc:
                    errors.append({
                        "screen": screen_name,
                        "error": "%s: %s" % (type(exc).__name__, exc),
                    })
                    print("[pygame-capture] failed %s: %s" %
                          (screen_name, exc), file=sys.stderr)
    finally:
        if app is not None:
            try:
                app_module.evinput.stop()
            except Exception:
                pass
        pygame.quit()

    manifest = {
        "engine": "pygame",
        "capture_kind": "home-and-render-state-smoke" if args.all_states
                         else "home-style-smoke",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "expected_screens": ["home-" + style for style in styles] + (
            ["state-" + name for name in state_names if name != "home"]
            if args.all_states else []
        ),
        "captured": results,
        "errors": errors,
        "complete": len(results) == len(styles) + (
            len([name for name in state_names if name != "home"])
            if args.all_states else 0
        ) and not errors,
        "note": (
            "Home-style plus App.render_state branch smoke coverage; direct state "
            "rendering is not proof of navigation reachability, working actions, "
            "or handheld hardware validation."
            if args.all_states else
            "Home-style smoke coverage only; not full hub or hardware validation."
        ),
    }
    manifest_path = ROOT / "data" / "visual-captures" / "pygame-home-manifest.json"
    temporary = manifest_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(manifest, indent=2) + "\n",
                         encoding="utf-8")
    temporary.replace(manifest_path)
    print("[pygame-capture] %d/%d screens captured" %
          (len(results), len(manifest["expected_screens"])))
    return 0 if manifest["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
