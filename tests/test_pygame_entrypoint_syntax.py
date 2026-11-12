from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_pygame_entrypoint_is_valid_python():
    source = (ROOT / "desk" / "main.py").read_text(encoding="utf-8")
    ast.parse(source, filename=str(ROOT / "desk" / "main.py"))
