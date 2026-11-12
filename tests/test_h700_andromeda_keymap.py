import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    304: "A", 305: "B", 306: "Y", 307: "X",
    310: "L1", 311: "R1", 312: "L2", 313: "R2",
    314: "SELECT", 315: "START", 316: "MENU",
}


def _assignment(path, name):
    source = (ROOT / path).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError("%s assignment not found in %s" % (name, path))


def test_andromeda_evdev_mapping_is_consistent_across_frontends():
    desk_map = _assignment("desk/evinput.py", "KEYMAP")
    cast_map = _assignment("outdesk/VoidCast/voidcast/core/evinput.py", "KEYMAP")
    known = _assignment("desk/const.py", "KNOWN_NAMES")
    qjoypad = _assignment("bin/gen_layout.py", "KNOWN")
    raw_map = _assignment("voiddesk.py", "RAW")
    expected_raw = {name: code for code, name in EXPECTED.items()}

    for current in (desk_map, cast_map, known, qjoypad):
        assert {code: current[code] for code in EXPECTED} == EXPECTED
    assert {name: raw_map[name] for name in expected_raw} == expected_raw


def test_andromeda_start_is_not_reported_as_r2():
    mapping = _assignment("desk/evinput.py", "KEYMAP")
    assert mapping[315] == "START"
    assert mapping[313] == "R2"
    assert mapping[311] == "R1"


def test_global_start_select_hotkey_uses_andromeda_codes():
    source = (ROOT / "bin/vd_hotkey.py").read_text(encoding="utf-8")
    hold = _assignment("bin/vd_hotkey.py", "_hold")
    assert set(hold) == {314, 315}
    assert "return _hold[314] and _hold[315]" in source
    assert "return [316]        # MENU" in source
    assert "if evs == [312]:" in source
