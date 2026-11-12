import importlib.util
import io
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_bootstrap():
    script = ROOT / "bin" / "bootstrap_lite.py"
    spec = importlib.util.spec_from_file_location("voiddesk_bootstrap_lite_test", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_tar(path: Path, members: dict[str, bytes]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(path, "w:gz") as archive:
        for name, payload in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            info.mode = 0o644
            archive.addfile(info, io.BytesIO(payload))


def create_runtime_archives(directory: Path, *, wheel_tag="cp311-cp311-manylinux2014_aarch64"):
    write_tar(directory / "pygame.tar.gz", {
        "pygame/__init__.py": b"from . import base\\n",
        "pygame/base.cpython-311-aarch64-linux-gnu.so": b"ELF fixture",
    })
    write_tar(directory / "pygame.libs.tar.gz", {
        "pygame.libs/libSDL2-test.so.0": b"SDL fixture",
    })
    write_tar(directory / "pygame-2.6.1.data.tar.gz", {
        "pygame-2.6.1.data/headers/include/pgcompat.h": b"/* fixture */\\n",
    })
    write_tar(directory / "pygame-2.6.1.dist-info.tar.gz", {
        "pygame-2.6.1.dist-info/WHEEL": (
            ("Wheel-Version: 1.0\\nTag: " + wheel_tag + "\\n").encode()
        ),
    })


def test_bootstrap_extracts_bundled_runtime_for_muos_arm64(tmp_path):
    bootstrap = load_bootstrap()
    archives = tmp_path / "archives"
    destination = tmp_path / "runtime.candidate"
    create_runtime_archives(archives)

    ok, error = bootstrap.extract_bundled_runtime(
        archives, destination, (3, 11), "aarch64"
    )

    assert ok, error
    assert (destination / "pygame" / "__init__.py").is_file()
    assert (destination / "pygame" /
            "base.cpython-311-aarch64-linux-gnu.so").is_file()
    assert (destination / "pygame.libs" / "libSDL2-test.so.0").is_file()


def test_bootstrap_refuses_bundled_runtime_for_wrong_python_or_arch(tmp_path):
    bootstrap = load_bootstrap()
    archives = tmp_path / "archives"
    create_runtime_archives(archives)

    ok, error = bootstrap.extract_bundled_runtime(
        archives, tmp_path / "wrong-python", (3, 10), "aarch64"
    )
    assert not ok
    assert "CPython 3.11/aarch64 only" in error

    ok, error = bootstrap.extract_bundled_runtime(
        archives, tmp_path / "wrong-arch", (3, 11), "armv7l"
    )
    assert not ok
    assert "CPython 3.11/aarch64 only" in error


def test_bootstrap_rejects_tar_path_traversal(tmp_path):
    bootstrap = load_bootstrap()
    archives = tmp_path / "archives"
    create_runtime_archives(archives)
    write_tar(archives / "pygame.tar.gz", {
        "../../outside.txt": b"not allowed",
        "pygame/__init__.py": b"# fixture\\n",
    })

    ok, error = bootstrap.extract_bundled_runtime(
        archives, tmp_path / "runtime.candidate", (3, 11), "aarch64"
    )

    assert not ok
    assert "unsafe tar member" in error
    assert not (tmp_path / "outside.txt").exists()


def test_bootstrap_rejects_wrong_wheel_abi(tmp_path):
    bootstrap = load_bootstrap()
    archives = tmp_path / "archives"
    create_runtime_archives(
        archives, wheel_tag="cp310-cp310-manylinux2014_aarch64"
    )

    ok, error = bootstrap.extract_bundled_runtime(
        archives, tmp_path / "runtime.candidate", (3, 11), "aarch64"
    )

    assert not ok
    assert "ABI/platform tag mismatch" in error
