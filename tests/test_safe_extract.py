import io, tarfile, pytest
from desk.utils.safe_extract import safe_tar_extractall

def _tar(name, data=b"x"):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        i = tarfile.TarInfo(name)
        i.size = len(data)
        tf.addfile(i, io.BytesIO(data))
    buf.seek(0)
    return buf

def test_ok(tmp_path):
    with tarfile.open(fileobj=_tar("ok.txt")) as tf:
        safe_tar_extractall(tf, str(tmp_path))
    assert (tmp_path / "ok.txt").is_file()

def test_traversal_blocked(tmp_path):
    with tarfile.open(fileobj=_tar("../evil.txt")) as tf:
        with pytest.raises(ValueError):
            safe_tar_extractall(tf, str(tmp_path))
