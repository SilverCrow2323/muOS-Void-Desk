import io
import stat
import tarfile
import zipfile

import pytest

from desk.utils.safe_extract import safe_tar_extractall, safe_zip_extractall


def _tar(name, data=b"x"):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as archive:
        item = tarfile.TarInfo(name)
        item.size = len(data)
        archive.addfile(item, io.BytesIO(data))
    buf.seek(0)
    return buf


def _zip(name, data=b"x", mode=None):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w") as archive:
        info = zipfile.ZipInfo(name)
        if mode is not None:
            info.external_attr = mode << 16
        archive.writestr(info, data)
    buf.seek(0)
    return buf


def test_tar_safe_file_extracts(tmp_path):
    with tarfile.open(fileobj=_tar("safe.txt")) as archive:
        safe_tar_extractall(archive, str(tmp_path))
    assert (tmp_path / "safe.txt").read_bytes() == b"x"


def test_tar_path_traversal_is_rejected(tmp_path):
    with tarfile.open(fileobj=_tar("../outside.txt")) as archive:
        with pytest.raises(ValueError, match="path traversal"):
            safe_tar_extractall(archive, str(tmp_path))


def test_zip_safe_nested_file_extracts(tmp_path):
    with zipfile.ZipFile(_zip("package/module.py", b"print('ok')")) as archive:
        safe_zip_extractall(archive, str(tmp_path))
    assert (tmp_path / "package" / "module.py").read_text() == "print('ok')"


@pytest.mark.parametrize(
    "name",
    ["../outside.txt", "/absolute.txt", r"..\\outside.txt", "C:/outside.txt"],
)
def test_zip_traversal_and_absolute_paths_are_rejected(tmp_path, name):
    with zipfile.ZipFile(_zip(name)) as archive:
        with pytest.raises(ValueError):
            safe_zip_extractall(archive, str(tmp_path))
    assert not (tmp_path.parent / "outside.txt").exists()


def test_zip_symbolic_link_is_rejected(tmp_path):
    symlink_mode = stat.S_IFLNK | 0o777
    with zipfile.ZipFile(_zip("link", b"target", symlink_mode)) as archive:
        with pytest.raises(ValueError, match="special file"):
            safe_zip_extractall(archive, str(tmp_path))


def test_zip_expanded_size_limit_is_enforced(tmp_path):
    with zipfile.ZipFile(_zip("large.bin", b"0123456789")) as archive:
        with pytest.raises(ValueError, match="size limit"):
            safe_zip_extractall(archive, str(tmp_path), max_total_size=5)


def test_zip_duplicate_normalized_paths_are_rejected(tmp_path):
    data = io.BytesIO()
    with zipfile.ZipFile(data, mode="w") as archive:
        archive.writestr("pkg/./module.py", b"a")
        archive.writestr("pkg/module.py", b"b")
    data.seek(0)
    with zipfile.ZipFile(data) as archive:
        with pytest.raises(ValueError, match="duplicate"):
            safe_zip_extractall(archive, str(tmp_path))
