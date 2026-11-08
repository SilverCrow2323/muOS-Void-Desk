import os
from desk.utils.atomic_io import atomic_write_text, atomic_write_json, atomic_read_json

def test_text(tmp_path):
    p = str(tmp_path / "f.txt")
    atomic_write_text(p, "hi")
    assert open(p).read() == "hi"

def test_json_rt(tmp_path):
    p = str(tmp_path / "f.json")
    atomic_write_json(p, {"a": 1})
    assert atomic_read_json(p) == {"a": 1}

def test_corrupt_default(tmp_path):
    p = str(tmp_path / "f.json")
    open(p, "w").write("{bad")
    assert atomic_read_json(p, default={}) == {}
