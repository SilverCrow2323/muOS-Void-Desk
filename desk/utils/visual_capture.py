"""Dependency-light screenshot writer for the Pygame frontend."""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any


def _safe_token(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9_-]+", "-", str(value or "screen"))
    return token.strip("-_")[:48] or "screen"


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def capture_surface(surface: Any, app_dir: str | os.PathLike[str],
                    engine: str, screen: str) -> tuple[str | None, str | None]:
    """Write the current Pygame Surface plus a machine-readable JSON sidecar."""
    try:
        import pygame
    except Exception as exc:  # pragma: no cover - optional runtime dependency
        return None, "Pygame is unavailable: %s" % exc

    try:
        root = Path(app_dir).resolve()
        output = root / "data" / "visual-captures"
        output.mkdir(parents=True, exist_ok=True)

        stamp = time.strftime("%Y%m%dT%H%M%S", time.gmtime())
        millis = int(time.time() * 1000) % 1000
        eng = _safe_token(engine.lower())
        screen_name = _safe_token(screen.lower())
        stem = "%s__%s__%s_%03d" % (eng, screen_name, stamp, millis)
        image_path = output / (stem + ".png")
        pygame.image.save(surface, str(image_path))
        width, height = surface.get_size()

        _write_json_atomic(image_path.with_suffix(".json"), {
            "engine": eng,
            "screen": screen_name,
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "width": int(width),
            "height": int(height),
            "image": image_path.name,
            "version": "10.5.4",
        })
        return str(image_path), None
    except Exception as exc:
        return None, "%s: %s" % (type(exc).__name__, exc)
