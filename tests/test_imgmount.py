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



def test_mount_img_refuses_loop_already_mounted_elsewhere(monkeypatch, tmp_path):
    image = tmp_path / "xfce.img"
    image.write_bytes(b"image")
    commands = []

    monkeypatch.setattr(imgmount.os, "makedirs", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(imgmount, "is_mounted", lambda _path: False)
    monkeypatch.setattr(imgmount, "loop_of", lambda _image: "/dev/loop9")
    monkeypatch.setattr(imgmount, "loop_is_mounted", lambda _device: True)
    monkeypatch.setattr(
        imgmount, "_run",
        lambda command: (commands.append(command) or None),
    )

    ok, error = imgmount.mount_img(image, tmp_path / "new-mount")

    assert not ok
    assert "/dev/loop9" in error
    assert commands == []


def test_cleanup_stale_reports_detach_failure(monkeypatch, tmp_path):
    image = tmp_path / "xfce.img"
    commands = []
    monkeypatch.setattr(imgmount, "loop_of", lambda _image: "/dev/loop3")
    monkeypatch.setattr(imgmount, "loop_is_mounted", lambda _device: False)
    monkeypatch.setattr(
        imgmount, "_call",
        lambda command: (commands.append(command) or 1),
    )

    assert not imgmount.cleanup_stale(image)
    assert commands == [["losetup", "-d", "/dev/loop3"]]


def test_umount_tree_returns_false_when_lazy_unmount_leaves_mounts(monkeypatch, tmp_path):
    root = tmp_path / "xfce_mnt"
    child = root / "proc"
    image = tmp_path / "xfce.img"
    commands = []

    monkeypatch.setattr(imgmount, "submounts", lambda _root: [str(child), str(root)])
    monkeypatch.setattr(
        imgmount, "_call",
        lambda command: (commands.append(command) or
                         (1 if command[1:2] == ["umount"] else 0)),
    )
    monkeypatch.setattr(imgmount, "is_mounted", lambda _path: False)
    monkeypatch.setattr(imgmount, "loop_of", lambda _image: "/dev/loop6")
    monkeypatch.setattr(imgmount, "loop_is_mounted", lambda _device: False)

    assert not imgmount.umount_tree(root, image)
    assert ["losetup", "-d", "/dev/loop6"] not in commands


def test_umount_tree_verifies_loop_detach_result(monkeypatch, tmp_path):
    root = tmp_path / "xfce_mnt"
    image = tmp_path / "xfce.img"
    calls = []

    monkeypatch.setattr(imgmount, "submounts", lambda _root: [])
    monkeypatch.setattr(imgmount, "is_mounted", lambda _path: False)
    monkeypatch.setattr(imgmount, "loop_of", lambda _image: "/dev/loop8")
    monkeypatch.setattr(imgmount, "loop_is_mounted", lambda _device: False)
    monkeypatch.setattr(
        imgmount, "_call",
        lambda command: (calls.append(command) or 1),
    )

    assert not imgmount.umount_tree(root, image)
    assert calls == [["losetup", "-d", "/dev/loop8"]]


def test_umount_tree_succeeds_only_after_mount_and_loop_are_gone(
        monkeypatch, tmp_path):
    root = tmp_path / "xfce_mnt"
    image = tmp_path / "xfce.img"
    calls = []
    loop_state = {"attached": True}

    monkeypatch.setattr(imgmount, "submounts", lambda _root: [])
    monkeypatch.setattr(imgmount, "is_mounted", lambda _path: False)
    monkeypatch.setattr(
        imgmount, "loop_of",
        lambda _image: "/dev/loop9" if loop_state["attached"] else None,
    )
    monkeypatch.setattr(imgmount, "loop_is_mounted", lambda _device: False)

    def detach(command):
        calls.append(command)
        loop_state["attached"] = False
        return 0

    monkeypatch.setattr(imgmount, "_call", detach)

    assert imgmount.umount_tree(root, image)
    assert calls == [["losetup", "-d", "/dev/loop9"]]


def _fake_result(returncode=0, stdout="", stderr=""):
    class Result:
        pass
    result = Result()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


def test_mount_img_does_not_fallback_when_owned_loop_cannot_detach(
        monkeypatch, tmp_path):
    image = tmp_path / "xfce.img"
    image.write_bytes(b"image")
    mountpoint = tmp_path / "xfce_mnt"
    state = {"loop": None}
    commands = []

    monkeypatch.setattr(imgmount.os, "makedirs", lambda *_a, **_k: None)
    monkeypatch.setattr(imgmount, "is_mounted", lambda _path: False)
    monkeypatch.setattr(imgmount, "loop_of", lambda _image: state["loop"])
    monkeypatch.setattr(imgmount, "loop_is_mounted", lambda _device: False)
    monkeypatch.setattr(imgmount, "free_loop", lambda: "/dev/loop4")

    def run(command):
        commands.append(command)
        if command[:2] == ["losetup", "/dev/loop4"]:
            state["loop"] = "/dev/loop4"
            return _fake_result()
        if command[0] == "mount":
            return _fake_result(1, stderr="explicit mount failed")
        raise AssertionError("unexpected command: %r" % command)

    def call(command):
        commands.append(command)
        assert command == ["losetup", "-d", "/dev/loop4"]
        return 1

    monkeypatch.setattr(imgmount, "_run", run)
    monkeypatch.setattr(imgmount, "_call", call)

    ok, error = imgmount.mount_img(image, mountpoint)

    assert not ok
    assert "impossibile sganciare il loop" in error
    assert not any(
        command[:2] == ["mount", "-o"] for command in commands
    )


def test_mount_img_falls_back_only_after_owned_loop_is_detached(
        monkeypatch, tmp_path):
    image = tmp_path / "xfce.img"
    image.write_bytes(b"image")
    mountpoint = tmp_path / "xfce_mnt"
    state = {"loop": None}
    commands = []

    monkeypatch.setattr(imgmount.os, "makedirs", lambda *_a, **_k: None)
    monkeypatch.setattr(imgmount, "is_mounted", lambda _path: False)
    monkeypatch.setattr(imgmount, "loop_of", lambda _image: state["loop"])
    monkeypatch.setattr(imgmount, "loop_is_mounted", lambda _device: False)
    monkeypatch.setattr(imgmount, "free_loop", lambda: "/dev/loop5")

    def run(command):
        commands.append(command)
        if command[:2] == ["losetup", "/dev/loop5"]:
            state["loop"] = "/dev/loop5"
            return _fake_result()
        if command[0] == "mount" and command[-2] == "/dev/loop5":
            return _fake_result(1, stderr="explicit mount failed")
        if command == ["mount", "-o", "loop", image, mountpoint]:
            assert state["loop"] is None
            return _fake_result()
        raise AssertionError("unexpected command: %r" % command)

    def call(command):
        commands.append(command)
        assert command == ["losetup", "-d", "/dev/loop5"]
        state["loop"] = None
        return 0

    monkeypatch.setattr(imgmount, "_run", run)
    monkeypatch.setattr(imgmount, "_call", call)

    ok, error = imgmount.mount_img(image, mountpoint)

    assert ok, error
    detach_index = commands.index(["losetup", "-d", "/dev/loop5"])
    fallback_index = commands.index(
        ["mount", "-o", "loop", image, mountpoint]
    )
    assert detach_index < fallback_index


def test_mount_img_does_not_duplicate_a_preexisting_unmounted_loop(
        monkeypatch, tmp_path):
    image = tmp_path / "xfce.img"
    image.write_bytes(b"image")
    mountpoint = tmp_path / "xfce_mnt"
    commands = []
    monkeypatch.setattr(imgmount.os, "makedirs", lambda *_a, **_k: None)
    monkeypatch.setattr(imgmount, "is_mounted", lambda _path: False)
    monkeypatch.setattr(imgmount, "loop_of", lambda _image: "/dev/loop7")
    monkeypatch.setattr(imgmount, "loop_is_mounted", lambda _device: False)
    monkeypatch.setattr(
        imgmount, "free_loop",
        lambda: (_ for _ in ()).throw(
            AssertionError("must reuse or refuse the existing loop")
        ),
    )
    monkeypatch.setattr(
        imgmount, "_run",
        lambda command: (
            commands.append(command) or
            _fake_result(1, stderr="existing loop mount failed")
        ),
    )
    monkeypatch.setattr(
        imgmount, "_call",
        lambda command: (_ for _ in ()).throw(
            AssertionError("must not detach a loop not owned by this call")
        ),
    )

    ok, error = imgmount.mount_img(image, mountpoint)

    assert not ok
    assert "fallback loop evitato" in error
    assert not any(command[:2] == ["mount", "-o"] for command in commands)


def test_mount_img_cleans_loop_left_by_failed_classic_fallback(
        monkeypatch, tmp_path):
    image = tmp_path / "xfce.img"
    image.write_bytes(b"image")
    mountpoint = tmp_path / "xfce_mnt"
    state = {"loop": None}
    commands = []
    monkeypatch.setattr(imgmount.os, "makedirs", lambda *_a, **_k: None)
    monkeypatch.setattr(imgmount, "is_mounted", lambda _path: False)
    monkeypatch.setattr(imgmount, "loop_of", lambda _image: state["loop"])
    monkeypatch.setattr(imgmount, "loop_is_mounted", lambda _device: False)
    monkeypatch.setattr(imgmount, "free_loop", lambda: None)

    def run(command):
        commands.append(command)
        if command == ["mount", "-o", "loop", image, mountpoint]:
            state["loop"] = "/dev/loop8"
            return _fake_result(1, stderr="classic mount failed")
        raise AssertionError("unexpected command: %r" % command)

    def call(command):
        commands.append(command)
        assert command == ["losetup", "-d", "/dev/loop8"]
        state["loop"] = None
        return 0

    monkeypatch.setattr(imgmount, "_run", run)
    monkeypatch.setattr(imgmount, "_call", call)

    ok, error = imgmount.mount_img(image, mountpoint)

    assert not ok
    assert "classic mount failed" in error
    assert commands[-1] == ["losetup", "-d", "/dev/loop8"]
    assert state["loop"] is None


def test_mount_img_keeps_loop_left_mounted_by_failed_fallback(
        monkeypatch, tmp_path):
    image = tmp_path / "xfce.img"
    image.write_bytes(b"image")
    mountpoint = tmp_path / "xfce_mnt"
    state = {"loop": None}
    commands = []
    monkeypatch.setattr(imgmount.os, "makedirs", lambda *_a, **_k: None)
    monkeypatch.setattr(imgmount, "is_mounted", lambda _path: False)
    monkeypatch.setattr(imgmount, "loop_of", lambda _image: state["loop"])
    monkeypatch.setattr(imgmount, "loop_is_mounted", lambda _device: True)
    monkeypatch.setattr(imgmount, "free_loop", lambda: None)

    def run(command):
        commands.append(command)
        state["loop"] = "/dev/loop10"
        return _fake_result(1, stderr="classic mount failed")

    def call(command):
        commands.append(command)
        raise AssertionError("must not detach a mounted loop")

    monkeypatch.setattr(imgmount, "_run", run)
    monkeypatch.setattr(imgmount, "_call", call)

    ok, error = imgmount.mount_img(image, mountpoint)

    assert not ok
    assert "/dev/loop10" in error
    assert ["losetup", "-d", "/dev/loop10"] not in commands


def test_mount_img_refuses_fallback_when_detach_reports_success_but_loop_remains(
        monkeypatch, tmp_path):
    image = tmp_path / "xfce.img"
    image.write_bytes(b"image")
    mountpoint = tmp_path / "xfce_mnt"
    state = {"loop": None}
    commands = []

    monkeypatch.setattr(imgmount.os, "makedirs", lambda *_a, **_k: None)
    monkeypatch.setattr(imgmount, "is_mounted", lambda _path: False)
    monkeypatch.setattr(imgmount, "loop_of", lambda _image: state["loop"])
    monkeypatch.setattr(imgmount, "loop_is_mounted", lambda _device: False)
    monkeypatch.setattr(imgmount, "free_loop", lambda: "/dev/loop11")

    def run(command):
        commands.append(command)
        if command[:2] == ["losetup", "/dev/loop11"]:
            state["loop"] = "/dev/loop11"
            return _fake_result()
        if command[0] == "mount":
            return _fake_result(1, stderr="explicit mount failed")
        raise AssertionError("unexpected command: %r" % command)

    def call(command):
        commands.append(command)
        assert command == ["losetup", "-d", "/dev/loop11"]
        # Simulate lazy kernel detach: command succeeds but device is still
        # listed by losetup because an open reference remains.
        return 0

    monkeypatch.setattr(imgmount, "_run", run)
    monkeypatch.setattr(imgmount, "_call", call)

    ok, error = imgmount.mount_img(image, mountpoint)

    assert not ok
    assert "loop dell'immagine risulta ancora associato" in error
    assert not any(command[:2] == ["mount", "-o"] for command in commands)


def test_mount_img_refuses_fallback_after_partial_losetup_attach_failure(
        monkeypatch, tmp_path):
    image = tmp_path / "xfce.img"
    image.write_bytes(b"image")
    mountpoint = tmp_path / "xfce_mnt"
    state = {"loop": None}
    commands = []

    monkeypatch.setattr(imgmount.os, "makedirs", lambda *_a, **_k: None)
    monkeypatch.setattr(imgmount, "is_mounted", lambda _path: False)
    monkeypatch.setattr(imgmount, "loop_of", lambda _image: state["loop"])
    monkeypatch.setattr(imgmount, "free_loop", lambda: "/dev/loop12")

    def run(command):
        commands.append(command)
        if command[:2] == ["losetup", "/dev/loop12"]:
            state["loop"] = "/dev/loop12"
            return _fake_result(1, stderr="simulated partial attach failure")
        raise AssertionError("fallback must not start: %r" % command)

    monkeypatch.setattr(imgmount, "_run", run)

    ok, error = imgmount.mount_img(image, mountpoint)

    assert not ok
    assert "/dev/loop12" in error
    assert not any(command[0] == "mount" for command in commands)


def test_mounts_propagates_unreadable_proc_mounts(monkeypatch):
    def unreadable(_path, *_args, **_kwargs):
        raise PermissionError("simulated /proc/mounts read failure")

    monkeypatch.setattr("builtins.open", unreadable)
    try:
        imgmount.mounts()
    except OSError as exc:
        assert "simulated /proc/mounts read failure" in str(exc)
    else:
        raise AssertionError("unreadable mount state must not become an empty table")


def test_mount_img_refuses_when_proc_mount_table_is_unreadable(
        monkeypatch, tmp_path):
    image = tmp_path / "xfce.img"
    image.write_bytes(b"image")
    commands = []

    monkeypatch.setattr(imgmount.os, "makedirs", lambda *_a, **_k: None)
    monkeypatch.setattr(
        imgmount, "mounts",
        lambda: (_ for _ in ()).throw(PermissionError("mount table denied")),
    )
    monkeypatch.setattr(
        imgmount, "_run",
        lambda command: (commands.append(command) or _fake_result()),
    )

    ok, error = imgmount.mount_img(image, tmp_path / "xfce_mnt")

    assert not ok
    assert "mount table denied" in error
    assert commands == []


def test_umount_tree_reports_false_when_mount_table_is_unreadable(
        monkeypatch, tmp_path):
    root = tmp_path / "xfce_mnt"
    image = tmp_path / "xfce.img"
    commands = []

    monkeypatch.setattr(
        imgmount, "mounts",
        lambda: (_ for _ in ()).throw(PermissionError("mount table denied")),
    )
    monkeypatch.setattr(
        imgmount, "_call",
        lambda command: (commands.append(command) or 0),
    )

    assert not imgmount.umount_tree(root, image)
    assert commands == []


def test_loop_of_raises_when_losetup_state_is_unavailable(monkeypatch):
    monkeypatch.setattr(
        imgmount, "_run",
        lambda _command: _fake_result(1, stderr="losetup unavailable"),
    )
    try:
        imgmount.loop_of("/tmp/xfce.img")
    except OSError as exc:
        assert "losetup unavailable" in str(exc)
    else:
        raise AssertionError("losetup failure must not mean no loop is attached")


def test_mount_img_refuses_fallback_when_losetup_state_is_unavailable(
        monkeypatch, tmp_path):
    image = tmp_path / "xfce.img"
    image.write_bytes(b"image")
    commands = []

    monkeypatch.setattr(imgmount.os, "makedirs", lambda *_a, **_k: None)
    monkeypatch.setattr(imgmount, "mounts", lambda: [])
    def run(command):
        commands.append(command)
        if command == ["losetup", "-a"]:
            return _fake_result(1, stderr="losetup unavailable")
        raise AssertionError("mount fallback must not run after losetup failure")

    monkeypatch.setattr(imgmount, "_run", run)

    ok, error = imgmount.mount_img(image, tmp_path / "xfce_mnt")

    assert not ok
    assert "losetup unavailable" in error
    assert commands == [["losetup", "-a"]]
