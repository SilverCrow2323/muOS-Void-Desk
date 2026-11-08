"""Native Rt:Tailscale-M service adapter for Void Desk.

The upstream service manager remains the single owner of tailscaled. This
module talks to its supported rt and ts entry points; it never starts
tailscaled directly and never reads or copies the node identity.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

EXIT_NODE_RE = re.compile(r"^[A-Za-z0-9_.:\-]{1,255}$")
SUMMARY_KEYS = {
    "backend", "daemon", "panel", "watchdog", "taildrop", "autostart",
    "tun", "port", "stopped", "version", "ts_version",
}


def find_install(app_dir: Path, extra_roots=()):
    """Find bundled Rt:Tailscale-M first, then known muOS app locations."""
    app_dir = Path(app_dir)
    candidates = [
        app_dir / "external" / "rt-tailscale-m" / "app" / "RtTailscale",
        app_dir / "external" / "RtTailscale",
        *[Path(p) for p in extra_roots],
        Path("/run/muos/storage/application/RtTailscale"),
        Path("/mnt/mmc/MUOS/application/RtTailscale"),
        Path("/mnt/sdcard/MUOS/application/RtTailscale"),
    ]
    seen = set()
    for candidate in candidates:
        try:
            root = candidate.resolve()
        except OSError:
            continue
        if root in seen:
            continue
        seen.add(root)
        if (root / "rt").is_file() and (root / "ts").is_file():
            return root
    return None


def _run(root: Path, executable: str, args=(), timeout=10, runner=subprocess.run):
    path = root / executable
    if not path.is_file():
        return {"ok": False, "error": f"Rt:Tailscale-M entry point missing: {executable}"}
    try:
        result = runner(
            [str(path), *[str(value) for value in args]],
            cwd=str(root), capture_output=True, text=True,
            timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"{executable} command timed out"}
    except OSError as exc:
        return {"ok": False, "error": f"cannot run {executable}: {exc}"}
    output = (result.stdout or "").strip()
    error = (result.stderr or "").strip()
    return {
        "ok": result.returncode == 0,
        "code": result.returncode,
        "output": output[-12000:],
        "error": error[-2000:],
    }


def _summary(text):
    values = {}
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if sep and key in SUMMARY_KEYS:
            values[key] = value.strip()
    return values


def _taildrop(root: Path):
    config = root / "config" / "rt.conf"
    target = ""
    try:
        for line in config.read_text(encoding="utf-8").splitlines():
            if line.startswith("TAILDROP_DIR="):
                target = line.split("=", 1)[1].strip()
    except OSError:
        pass
    folder = Path(target) if target else root / "taildrop"
    items = []
    try:
        for entry in folder.iterdir():
            if entry.is_file() and not entry.is_symlink():
                stat = entry.stat()
                items.append({
                    "name": entry.name[:200],
                    "size": stat.st_size,
                    "mtime": int(stat.st_mtime),
                })
    except OSError:
        pass
    items.sort(key=lambda item: item["mtime"], reverse=True)
    return items[:100]


def cli(app_dir: Path, *args, timeout=10):
    """Run the upstream CLI wrapper and return a CompletedProcess-like result."""
    root = find_install(app_dir)
    if root is None:
        return subprocess.CompletedProcess(
            args, 127, "", "Rt:Tailscale-M service files not found"
        )
    try:
        return subprocess.run(
            [str(root / "ts"), *[str(value) for value in args]],
            cwd=str(root), capture_output=True, text=True,
            timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(args, 124, "", "Tailscale command timed out")
    except OSError as exc:
        return subprocess.CompletedProcess(args, 127, "", str(exc))


def _setup_job_active(lock_path: Path):
    try:
        pid = int(lock_path.read_text(encoding="ascii").strip())
        if pid <= 1:
            return False
        os.kill(pid, 0)
        cmdline = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\\0", b" ")
        return b"tailscale_job.py" in cmdline
    except (OSError, ValueError):
        return False


def start_async(app_dir: Path):
    """Start the verified install/start sequence without blocking Pygame."""
    app_dir = Path(app_dir)
    data_dir = app_dir / "data"
    script = app_dir / "service" / "tailscale_job.py"
    if not script.is_file():
        return {"ok": False, "error": "Tailscale setup job is missing"}
    data_dir.mkdir(parents=True, exist_ok=True)
    lock_path = data_dir / ".tailscale_setup.pid"
    if lock_path.exists() and _setup_job_active(lock_path):
        return {"ok": True, "already_running": True}
    try:
        lock_path.unlink(missing_ok=True)
        log_file = (data_dir / "tailscale_setup.log").open("ab")
        try:
            process = subprocess.Popen(
                [sys.executable, str(script)], cwd=str(app_dir),
                stdin=subprocess.DEVNULL, stdout=log_file,
                stderr=subprocess.STDOUT, start_new_session=True,
            )
        finally:
            log_file.close()
        return {"ok": True, "pid": process.pid, "message": "Tailscale setup started"}
    except OSError as exc:
        return {"ok": False, "error": "cannot start Tailscale setup: " + str(exc)}


def status(app_dir: Path, extra_roots=(), runner=subprocess.run):
    root = find_install(app_dir, extra_roots)
    if root is None:
        return {
            "ok": True, "installed": False, "available": False,
            "message": "Rt:Tailscale-M service files not found",
            "peers": [], "taildrop": [],
        }
    summary_result = _run(root, "rt", ("summary",), timeout=5, runner=runner)
    summary = _summary(summary_result.get("output", ""))
    status_result = _run(root, "ts", ("status", "--json"), timeout=6, runner=runner)
    raw = {}
    if status_result.get("ok"):
        try:
            raw = json.loads(status_result["output"])
        except (ValueError, TypeError):
            raw = {}
    self_node = raw.get("Self") or {}
    users = raw.get("User") or {}

    def user_name(uid):
        user = users.get(str(uid)) or {}
        return user.get("LoginName") or user.get("DisplayName") or ""

    peers = []
    for peer in (raw.get("Peer") or {}).values():
        ips = peer.get("TailscaleIPs") or []
        peers.append({
            "name": peer.get("HostName") or peer.get("DNSName") or "Unknown",
            "ip": ips[0] if ips else "",
            "ips": ips,
            "online": bool(peer.get("Online")),
            "exit_node": bool(peer.get("ExitNodeOption")),
            "using": bool(peer.get("ExitNode")),
            "os": peer.get("OS") or "",
            "user": user_name(peer.get("UserID")),
        })
    peers.sort(key=lambda item: (not item["online"], item["name"].lower()))

    urls_result = _run(root, "rt", ("urls",), timeout=4, runner=runner)
    urls = [line.strip() for line in urls_result.get("output", "").splitlines()
            if line.strip().startswith(("LAN http://", "TS  http://"))]
    auth_url = str(raw.get("AuthURL") or "")
    backend = str(raw.get("BackendState") or summary.get("backend") or "Unknown")
    return {
        "ok": True,
        "installed": True,
        "available": bool(summary_result.get("ok")),
        "root": str(root),
        "backend": backend,
        "daemon": summary.get("daemon") == "1",
        "panel": summary.get("panel") == "1",
        "watchdog": summary.get("watchdog") == "1",
        "taildrop_enabled": summary.get("taildrop") == "1",
        "autostart": summary.get("autostart") == "on",
        "version": summary.get("version", ""),
        "tailscale_version": raw.get("Version", summary.get("ts_version", "")),
        "auth_url": auth_url,
        "tailnet": (raw.get("CurrentTailnet") or {}).get("Name", ""),
        "self": {
            "name": self_node.get("HostName", ""),
            "ips": self_node.get("TailscaleIPs") or [],
            "online": bool(self_node.get("Online")),
            "user": user_name(self_node.get("UserID")),
        },
        "peers": peers[:100],
        "exit_node": raw.get("ExitNodeStatus"),
        "urls": urls,
        "taildrop": _taildrop(root),
        "error": status_result.get("error", "") if not status_result.get("ok") else "",
    }


def action(app_dir: Path, name: str, value="", extra_roots=(), runner=subprocess.run):
    root = find_install(app_dir, extra_roots)
    if root is None:
        return {"ok": False, "error": "Rt:Tailscale-M service files not found"}
    if name == "install":
        return _run(root, "rt", ("install",), timeout=120, runner=runner)
    if name == "start":
        setup = _run(root, "rt", ("install",), timeout=120, runner=runner)
        if not setup.get("ok"):
            return setup
        return _run(root, "rt", ("start",), timeout=20, runner=runner)
    if name == "stop":
        return _run(root, "rt", ("stop",), timeout=20, runner=runner)
    if name == "restart":
        return _run(root, "rt", ("restart",), timeout=20, runner=runner)
    if name == "daemon_start":
        return _run(root, "rt", ("daemon", "start"), timeout=20, runner=runner)
    if name == "daemon_stop":
        return _run(root, "rt", ("daemon", "stop"), timeout=20, runner=runner)
    if name == "login":
        return _start_login(root, Path(app_dir))
    if name == "disconnect":
        return _run(root, "ts", ("down",), timeout=20, runner=runner)
    if name == "logout":
        return _run(root, "ts", ("logout",), timeout=20, runner=runner)
    if name == "autostart_on":
        return _run(root, "rt", ("autostart", "on"), timeout=12, runner=runner)
    if name == "autostart_off":
        return _run(root, "rt", ("autostart", "off"), timeout=12, runner=runner)
    if name == "panel_on":
        bind = _run(root, "rt", ("conf", "set", "PANEL_BIND", "127.0.0.1"),
                    timeout=10, runner=runner)
        if not bind.get("ok"):
            return bind
        enabled = _run(root, "rt", ("conf", "set", "PANEL", "1"),
                       timeout=10, runner=runner)
        if not enabled.get("ok"):
            return enabled
        return _run(root, "rt", ("panel", "start"), timeout=15, runner=runner)
    if name == "panel_off":
        stopped = _run(root, "rt", ("panel", "stop"), timeout=10, runner=runner)
        disabled = _run(root, "rt", ("conf", "set", "PANEL", "0"),
                        timeout=10, runner=runner)
        return disabled if disabled.get("ok") else stopped
    if name == "exit_node":
        target = str(value or "").strip()
        if target and not EXIT_NODE_RE.fullmatch(target):
            return {"ok": False, "error": "invalid exit-node address"}
        return _run(root, "ts", ("set", "--exit-node=" + target),
                    timeout=20, runner=runner)
    if name == "cancel_login":
        return _cancel_login()
    return {"ok": False, "error": "unsupported Tailscale action"}


_LOGIN_PROCESS = None


def _start_login(root: Path, app_dir: Path):
    global _LOGIN_PROCESS
    if _LOGIN_PROCESS is not None and _LOGIN_PROCESS.poll() is None:
        return {"ok": True, "already_running": True}
    cli = root / "ts"
    if not cli.is_file():
        return {"ok": False, "error": "Tailscale CLI wrapper missing"}
    try:
        log_path = Path(os.environ.get("VOIDDESK_DATA_DIR", str(app_dir / "data"))) / "tailscale_login.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_file = log_path.open("ab")
        _LOGIN_PROCESS = subprocess.Popen(
            [str(cli), "login"], cwd=str(root), stdin=subprocess.DEVNULL,
            stdout=log_file, stderr=subprocess.STDOUT, start_new_session=True,
        )
        log_file.close()
        return {"ok": True, "pid": _LOGIN_PROCESS.pid, "message": "login started; refresh status for the QR/auth URL"}
    except OSError as exc:
        return {"ok": False, "error": "cannot start Tailscale login: " + str(exc)}


def _cancel_login():
    global _LOGIN_PROCESS
    process = _LOGIN_PROCESS
    if process is None or process.poll() is not None:
        _LOGIN_PROCESS = None
        return {"ok": True, "running": False}
    try:
        process.terminate()
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)
    except OSError as exc:
        return {"ok": False, "error": str(exc)}
    _LOGIN_PROCESS = None
    return {"ok": True, "running": False}
