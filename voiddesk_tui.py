#!/usr/bin/env python3
"""VoidDesk TUI launcher — default entry point."""
import os, sys, subprocess, json
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
CFG = APP_DIR / "data" / "desk_config.json"

BANNER = r"""
╔══════════════════════════════════════════════════════════╗
║  VOIDDESK // LAUNCHER                                    ║
║  SPDW Factory · v10.5.1-NEXUS                            ║
╚══════════════════════════════════════════════════════════╝
"""

def read_cfg():
    try:
        return json.loads(CFG.read_text())
    except Exception:
        return {}

def write_cfg(cfg):
    try:
        CFG.write_text(json.dumps(cfg, indent=1))
    except Exception as e:
        print(f"  [ERR] {e}")

def which_love():
    """Prefer device love, then system."""
    local = APP_DIR / "lib" / "love"
    if local.is_file() and os.access(local, os.X_OK):
        return str(local)
    import shutil
    return shutil.which("love")

def launch_love():
    love = which_love()
    if not love:
        print("  ❌ LÖVE binary not found (lib/love or system)")
        print("     PC:     sudo apt install love")
        print("     Device: ensure lib/love is executable")
        return 1
    env = dict(os.environ)
    env["LD_LIBRARY_PATH"] = str(APP_DIR / "lib") + ":" + env.get("LD_LIBRARY_PATH", "")
    env["VOIDDESK_APP_DIR"] = str(APP_DIR)
    env.setdefault("VOIDDESK_PC", "1")
    subprocess.run([love, str(APP_DIR / "love")], env=env)
    return 0

def launch_py():
    venv_py = APP_DIR / ".venv_desktop" / "bin" / "python"
    if not venv_py.is_file():
        print("  Creating venv (first run)...")
        subprocess.run([sys.executable, "-m", "venv", str(APP_DIR / ".venv_desktop")])
        subprocess.run([str(venv_py), "-m", "pip", "install", "-q", "pygame", "psutil"])
    env = dict(os.environ)
    env["VOIDDESK_APP_DIR"] = str(APP_DIR)
    env.setdefault("VOIDDESK_PC", "1")
    subprocess.run([str(venv_py), str(APP_DIR / "desktop_run.py")], env=env)
    return 0

def start_service():
    """Start Python service in background, return Popen."""
    env = dict(os.environ)
    env["VOIDDESK_APP_DIR"] = str(APP_DIR)
    return subprocess.Popen(
        [sys.executable, str(APP_DIR / "service" / "voiddesk_service.py")],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)

def action_launch(engine):
    cfg = read_cfg()
    current_engine = cfg.get("engine", "love")
    print(f"\n  Engine: {engine}  (config has: {current_engine})")
    svc = start_service()
    print(f"  Service PID: {svc.pid}")
    try:
        import time; time.sleep(0.4)
        if engine == "love":
            launch_love()
        else:
            launch_py()
    finally:
        svc.terminate()
        try: svc.wait(timeout=2)
        except Exception: svc.kill()
    return 0

def action_toggle_engine():
    cfg = read_cfg()
    cur = cfg.get("engine", "love")
    nxt = "py" if cur == "love" else "love"
    cfg["engine"] = nxt
    write_cfg(cfg)
    print(f"\n  ✅ Engine: {cur} → {nxt}")
    return 0

def action_open_config():
    print(f"\n  Config: {CFG}")
    cfg = read_cfg()
    print(json.dumps(cfg, indent=2)[:2000])
    print("\n  Edit manually: nano " + str(CFG))
    return 0

def action_logs():
    log_dir = APP_DIR / "data" / "logs"
    if not log_dir.is_dir():
        print("\n  No logs directory")
        return 0
    logs = sorted(log_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)[:5]
    print("\n  Recent logs:")
    for i, log in enumerate(logs, 1):
        print(f"    {i}) {log.name}  ({log.stat().st_size} bytes)")
    try:
        choice = input("\n  Show which? (1-5, Enter=skip): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(logs):
            log = logs[int(choice)-1]
            print(f"\n=== {log.name} (last 40) ===")
            print("\n".join(log.read_text(errors="replace").splitlines()[-40:]))
    except (KeyboardInterrupt, EOFError):
        pass
    return 0

def action_check_deps():
    print("\n  Checking dependencies...")
    checks = [
        ("python3", sys.executable),
        ("love",    which_love() or "❌ MISSING"),
        ("Xephyr",  subprocess.run(["which", "Xephyr"], capture_output=True, text=True).stdout.strip() or "❌ (needed for XFCE on PC)"),
        ("mpv",     subprocess.run(["which", "mpv"], capture_output=True, text=True).stdout.strip() or "❌ (needed for IPTV)"),
        ("git",     subprocess.run(["which", "git"], capture_output=True, text=True).stdout.strip() or "❌"),
    ]
    for name, path in checks:
        ok = "❌" if "MISSING" in path or path == "" else "✅"
        print(f"    {ok} {name:10s} → {path}")
    return 0

def action_repair():
    print("\n  Running repair checks...")
    py_files = list(APP_DIR.glob("**/*.py"))
    errs = 0
    for f in py_files:
        if "external/" in str(f) or ".venv" in str(f):
            continue
        r = subprocess.run([sys.executable, "-m", "py_compile", str(f)],
                          capture_output=True)
        if r.returncode != 0:
            print(f"    ❌ {f}")
            errs += 1
    if errs == 0:
        print(f"    ✅ All {len(py_files)} Python files compile")
    else:
        print(f"    ❌ {errs} files with errors")
    # Lua check
    luac = subprocess.run(["which", "luac"], capture_output=True, text=True).stdout.strip()
    if luac:
        lua_errs = 0
        for f in (APP_DIR / "love").glob("**/*.lua"):
            r = subprocess.run([luac, "-p", str(f)], capture_output=True)
            if r.returncode != 0:
                print(f"    ❌ {f}")
                lua_errs += 1
        if lua_errs == 0:
            print("    ✅ All Lua files compile")
    return 0

MENU = [
    ("Launch VoidDesk (config engine)",    lambda: action_launch(read_cfg().get("engine", "love"))),
    ("Launch VoidDesk → LÖVE",             lambda: action_launch("love")),
    ("Launch VoidDesk → Pygame",           lambda: action_launch("py")),
    ("Toggle default engine",              action_toggle_engine),
    ("Open config",                        action_open_config),
    ("View logs",                          action_logs),
    ("Check dependencies",                 action_check_deps),
    ("Repair / validate",                  action_repair),
]

def main():
    os.system("clear" if os.name == "posix" else "cls")
    print(BANNER)
    cfg = read_cfg()
    print(f"  Engine (config): {cfg.get('engine', 'love').upper()}")
    print(f"  PC: {cfg.get('pc_mode', 'auto')}")
    print()
    for i, (label, _) in enumerate(MENU, 1):
        print(f"  {i}) {label}")
    print(f"  0) Exit")
    print()
    try:
        choice = input("  Choice [0-8]: ").strip()
    except (KeyboardInterrupt, EOFError):
        return 0
    if choice == "0" or not choice:
        return 0
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(MENU):
            return MENU[idx][1]()
    except (ValueError, IndexError):
        pass
    return 0

if __name__ == "__main__":
    sys.exit(main())
