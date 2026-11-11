"""Regression tests for XFCE image mount path and loop-device matching."""

from pathlib import Path

from desk import imgmount


def _mount_line(source, mountpoint, options="rw,relatime"):
    escaped = str(mountpoint).replace("\\", "\\\\").replace(" ", "\\040")
    return f"{source} {escaped} ext4 {options} 0 0"


def test_is_mounted_decodes_escaped_spaces_and_checks_exact_path(monkeypatch, tmp_path):
    mountpoint = tmp_path / "Void Desk" / "xfce_mnt"
    neighbour = tmp_path / "Void Desk" / "xfce_mnt-old"
    monkeypatch.setattr(
        imgmount, "mounts",
        lambda: [_mount_line("/dev/loop2", mountpoint)],
    )

    assert imgmount.is_mounted(mountpoint)
    assert imgmount.is_mounted_rw(mountpoint)
    assert not imgmount.is_mounted(neighbour)


def test_is_mounted_rw_reports_read_only_mount(monkeypatch, tmp_path):
    mountpoint = tmp_path / "Void Desk" / "xfce_mnt"
    monkeypatch.setattr(
        imgmount, "mounts",
        lambda: [_mount_line("/dev/loop2", mountpoint, "ro,relatime")],
    )

    assert imgmount.is_mounted(mountpoint)
    assert not imgmount.is_mounted_rw(mountpoint)


def test_submounts_decodes_paths_and_orders_deepest_first(monkeypatch, tmp_path):
    root = tmp_path / "Void Desk" / "xfce_mnt"
    child = root / "dev"
    deep = child / "pts"
    sibling = tmp_path / "Void Desk" / "xfce_mnt-old"

    monkeypatch.setattr(
        imgmount, "mounts",
        lambda: [
            _mount_line("/dev/loop2", root),
            _mount_line("devtmpfs", child),
            _mount_line("devpts", deep),
            _mount_line("/dev/loop3", sibling),
        ],
    )

    assert imgmount.submounts(root) == [
        str(deep), str(child), str(root)
    ]


def test_loop_of_matches_exact_backing_file_and_decodes_spaces(monkeypatch, tmp_path):
    image = tmp_path / "Void Desk" / "xfce.img"
    backup = Path(str(image) + ".backup")
    escaped_image = str(image).replace(" ", "\\040")
    escaped_backup = str(backup).replace(" ", "\\040")

    class Result:
        returncode = 0
        stderr = ""
        stdout = (
            f"/dev/loop4: []: ({escaped_backup})\n"
            f"/dev/loop7: []: ({escaped_image})\n"
        )

    monkeypatch.setattr(imgmount, "_run", lambda _command: Result())

    assert imgmount.loop_of(image) == "/dev/loop7"


def test_cleanup_stale_does_not_confuse_loop_device_prefixes(monkeypatch, tmp_path):
    image = tmp_path / "xfce.img"
    commands = []

    class Result:
        returncode = 0
        stderr = ""
        stdout = f"/dev/loop1: []: ({image})\n"

    monkeypatch.setattr(imgmount, "_run", lambda command: (commands.append(command) or Result()))
    monkeypatch.setattr(
        imgmount, "mounts",
        lambda: ["/dev/loop10 /mnt/other ext4 rw,relatime 0 0"],
    )

    assert imgmount.cleanup_stale(image)
    assert ["losetup", "-d", "/dev/loop1"] in commands


def test_umount_tree_keeps_loop_when_device_still_mounted(monkeypatch, tmp_path):
    root = tmp_path / "xfce_mnt"
    image = tmp_path / "xfce.img"
    commands = []

    class Result:
        returncode = 0
        stderr = ""
        stdout = f"/dev/loop5: []: ({image})\n"

    monkeypatch.setattr(imgmount, "submounts", lambda _root: [str(root)])
    monkeypatch.setattr(imgmount, "_run", lambda command: (commands.append(command) or Result()))
    monkeypatch.setattr(imgmount, "_call", lambda command: (commands.append(command) or 0))
    monkeypatch.setattr(
        imgmount, "mounts",
        lambda: [f"/dev/loop5 {root} ext4 rw,relatime 0 0"],
    )

    assert not imgmount.umount_tree(root, image)
    assert ["losetup", "-d", "/dev/loop5"] not in commands
