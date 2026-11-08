#!/usr/bin/env python3
"""Deterministic smoke captures for the Pygame home-screen visual variants.

This deliberately captures the five supported home styles only. It does not
claim that every interactive hub or hardware-dependent workflow is covered.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "desk")]


class _NullPoller:
    def __init__(self, *args, **kwargs):
        pass

    def stop(self):
        pass


def main() -> int:
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
    finally:
        if app is not None:
            try:
                app_module.evinput.stop()
            except Exception:
                pass
        pygame.quit()

    manifest = {
        "engine": "pygame",
        "capture_kind": "home-style-smoke",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "expected_screens": list(styles),
        "captured": results,
        "errors": errors,
        "complete": len(results) == len(styles) and not errors,
        "note": "Home-style smoke coverage only; not full hub or hardware validation.",
    }
    manifest_path = ROOT / "data" / "visual-captures" / "pygame-home-manifest.json"
    temporary = manifest_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(manifest, indent=2) + "\n",
                         encoding="utf-8")
    temporary.replace(manifest_path)
    print("[pygame-capture] %d/%d home styles captured" %
          (len(results), len(styles)))
    return 0 if manifest["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
