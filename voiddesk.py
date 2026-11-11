#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Legacy version marker for BUILDCHECK.py and older package tooling: VOIDDESK NEXUS v10.5.4
r"""
QWASAR DESK / NEXUS v10.5.4 — PC Runtime & Launcher (legacy file: voiddesk.py)
SPDW Factory · Single-File Hybrid Launcher & Diagnostics Suite

Modes (dispatched by cli()):
  * (no args) / --desktop   → Interactive Rich Terminal TUI Menu
  * --love                  → Launch LÖVE engine with local/system fallback
  * --py                    → Launch Pygame engine (re-execs --_runtime in venv)
  * --engine {py|love}      → Exec specified validated engine backend
  * --repair                → Run automated code compilation & environment checks
  * --help / -h             → Display usage manual
  * --_runtime              → HIDDEN: Pygame desktop runtime (invoked in venv)
"""

import os
import sys
import time
import json
import shutil
import platform
import subprocess
from pathlib import Path

# Paths Setup
APP_DIR = Path(__file__).resolve().parent
SELF    = Path(__file__).resolve()
CFG     = APP_DIR / "data" / "desk_config.json"
VENV_PY = APP_DIR / ".venv_desktop" / "bin" / "python"
LOG_DIR = APP_DIR / "data" / "logs"

# Terminal Color Codes (ANSI)
class Color:
    CYAN    = "\033[96m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    RED     = "\033[91m"
    PURPLE  = "\033[95m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RESET   = "\033[0m"

BANNER = rf"""{Color.CYAN}{Color.BOLD}
 ╔══════════════════════════════════════════════════════════════════╗
 ║                                                                  ║
 ║   ██████╗ ██╗    ██╗ █████╗ ███████╗ █████╗ ██████╗              ║
 ║  ██╔═══██╗██║    ██║██╔══██╗██╔════╝██╔══██╗██╔══██╗             ║
 ║  ██║   ██║██║ █╗ ██║███████║███████╗███████║██████╔╝             ║
 ║  ██║▄▄ ██║██║███╗██║██╔══██║╚════██║██╔══██║██╔══██╗             ║
 ║  ╚██████╔╝╚███╔███╔╝██║  ██║███████║██║  ██║██║  ██║             ║
 ║   ╚══▀▀═╝  ╚══╝╚══╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝             ║
 ║                                                                  ║
 ║   {Color.GREEN}QWASAR // NEXUS CONTROL INTERFACE · SPDW FACTORY · v10.5.4{Color.CYAN}   ║
 ╚══════════════════════════════════════════════════════════════════╝{Color.RESET}"""

DEFAULT_CONFIG = {
    "engine": "love",
    "pc_mode": "auto",
    "debug": False,
    "video_driver": "x11"
}

# Device restrictions mapping (RG35XX-H vs PC)
DEVICE_ONLY = {
    11: "XFCE desktop launch requires the RG35XX-H handheld (arm64 + /dev/fb0).",
    12: "XFCE installation requires the RG35XX-H handheld (arm64 Ubuntu chroot).",
    13: "Package install requires the RG35XX-H handheld.",
    14: "Package removal requires the RG35XX-H handheld.",
    15: "System update requires the RG35XX-H handheld.",
    16: "muOS app launch requires the RG35XX-H handheld.",
    17: "Real terminal requires the RG35XX-H handheld.",
}

# ================================================================== CONFIG ==
def read_cfg():
    if not CFG.exists():
        write_cfg(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        data = json.loads(CFG.read_text(encoding="utf-8"))
        # Merge with defaults
        merged = DEFAULT_CONFIG.copy()
        merged.update(data)
        return merged
    except Exception as e:
        print(f"  {Color.RED}[ERR] Config parse failed: {e}{Color.RESET}")
        return DEFAULT_CONFIG.copy()

def write_cfg(cfg):
    try:
        CFG.parent.mkdir(parents=True, exist_ok=True)
        CFG.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        return True
    except Exception as e:
        print(f"  {Color.RED}[ERR] Cannot write config: {e}{Color.RESET}")
        return False

# ==================================================================== LOVE ==
def which_love():
    """Detect LÖVE binary depending on platform (ARM vs x86_64)."""
    arch = platform.machine().lower()
    is_arm = arch in ("aarch64", "armv7l", "arm64")
    local = APP_DIR / "lib" / "love"
    local_ok = local.is_file() and os.access(local, os.X_OK)
    system_love = shutil.which("love")

    if is_arm:
        return str(local) if local_ok else system_love
    if system_love:
        return system_love
    if local_ok:
        print(f"  {Color.YELLOW}⚠️  lib/love is ARM binary; cannot run natively on {arch}{Color.RESET}")
        print("     Please install PC version: sudo apt install love")
    return None

def prepare_qwasar_profile():
    """Generate the read-only shared composition snapshot before either engine starts."""
    resolver = APP_DIR / "tools" / "qwasar_profile_resolver.py"
    if not resolver.is_file():
        return False
    output = APP_DIR / "data" / "qwasar_effective_profile.json"
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(resolver),
                "--root", str(APP_DIR),
                "--output", str(output),
            ],
            cwd=str(APP_DIR),
            env=dict(os.environ, VOIDDESK_APP_DIR=str(APP_DIR)),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if result.stdout:
            print(result.stdout.rstrip())
        if result.returncode != 0:
            print(
                f"{Color.YELLOW}[QWASAR] Profile preflight failed "
                f"(rc={result.returncode}); the frontend will use its safe legacy defaults."
                f"{Color.RESET}"
            )
            return False
        return output.is_file()
    except OSError as exc:
        print(f"{Color.YELLOW}[QWASAR] Profile preflight unavailable: {exc}{Color.RESET}")
        return False


def launch_love():
    prepare_qwasar_profile()
    love = which_love()
    if not love:
        print(f"  {Color.RED}❌ LÖVE binary not found!{Color.RESET}")
        print("     PC:     sudo apt install love")
        print("     Device: Ensure lib/love has executable (+x) permissions")
        return 1
    
    print(f"  {Color.GREEN}🚀 Spawning LÖVE engine via: {love}{Color.RESET}")
    env = dict(os.environ)
    env["LD_LIBRARY_PATH"] = str(APP_DIR / "lib") + ":" + env.get("LD_LIBRARY_PATH", "")
    env["VOIDDESK_APP_DIR"] = str(APP_DIR)
    env.setdefault("VOIDDESK_PC", "1")
    
    love_dir = APP_DIR / "love"
    if not love_dir.is_dir():
        print(f"  {Color.YELLOW}⚠️  LÖVE source directory not found at: {love_dir}{Color.RESET}")
    
    try:
        subprocess.run([love, str(love_dir)], env=env)
        return 0
    except Exception as e:
        print(f"  {Color.RED}❌ Failed to launch LÖVE process: {e}{Color.RESET}")
        return 1

# ================================================================= SERVICE ==
def start_service():
    """Start the QWASAR background daemon service."""
    py = str(VENV_PY) if VENV_PY.is_file() else sys.executable
    svc_script = APP_DIR / "service" / "voiddesk_service.py"
    
    if not svc_script.is_file():
        # Fallback dummy handle if service script doesn't exist yet
        print(f"  {Color.DIM}[SERVICE] No background service found at {svc_script.name}, skipping.{Color.RESET}")
        return None

    env = dict(os.environ)
    env["VOIDDESK_APP_DIR"] = str(APP_DIR)
    try:
        proc = subprocess.Popen(
            [py, str(svc_script)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env,
        )
        print(f"  {Color.GREEN}✔ Background Service Started (PID: {proc.pid}){Color.RESET}")
        return proc
    except Exception as e:
        print(f"  {Color.RED}[ERR] Failed starting service: {e}{Color.RESET}")
        return None

# ======================================================= PYGAME RUNTIME ====
def run_pygame_runtime():
    """VENV runtime executor for Pygame desktop mode."""
    APP = str(APP_DIR)
    os.environ["SDL_VIDEODRIVER"] = os.environ.get("VD_VIDEO") or {
        "win32": "windows", "darwin": "cocoa"}.get(sys.platform, "x11")
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    sys.path[:0] = [os.path.join(APP, "desk"), APP]

    try:
        import pygame
    except ImportError:
        print(f"{Color.RED}[RUNTIME ERR] Pygame is not installed in the virtual environment.{Color.RESET}")
        return 1

    K = pygame
    KEYS = {
        K.K_z: "A", K.K_RETURN: "A",
        K.K_x: "B", K.K_BACKSPACE: "B",
        K.K_a: "Y", K.K_s: "X",
        K.K_q: "L1", K.K_w: "R1",
        K.K_e: "L2", K.K_r: "R2",
        K.K_TAB: "SELECT", K.K_SPACE: "START",
        K.K_ESCAPE: "MENU", K.K_m: "MENU",
        K.K_MINUS: "VOL-", K.K_EQUALS: "VOL+",
    }
    RAW = {"A": 304, "B": 305, "Y": 306, "X": 307, "L1": 308, "R1": 309,
           "L2": 314, "R2": 315, "SELECT": 310, "START": 311, "MENU": 312,
           "VOL-": 114, "VOL+": 115}

    _q, _held = [], set()

    def install_keyboard_bridge():
        try:
            import evinput
        except ImportError:
            return
        real_get = pygame.event.get

        def get(*a, **k):
            evs = real_get(*a, **k)
            for e in evs:
                if e.type == pygame.KEYDOWN:
                    _held.add(e.key)
                    if e.key in KEYS:
                        _q.append(KEYS[e.key])
                elif e.type == pygame.KEYUP:
                    _held.discard(e.key)
            return evs

        pygame.event.get = get
        state = {"active": False, "raw": []}

        evinput.start = lambda: state.update({"active": True}) or True
        evinput.stop = lambda: state.update({"active": False})
        evinput.active = lambda: state["active"]
        evinput.poll = lambda: _q.copy() and _q.clear()
        evinput.poll_raw = lambda: [RAW[n] for n in evinput.poll() if n in RAW]
        evinput.hat = lambda: ((pygame.K_RIGHT in _held) - (pygame.K_LEFT in _held),
                               (pygame.K_UP in _held) - (pygame.K_DOWN in _held))

    def install_fbdisplay_bypass():
        try:
            import fbdisplay as _fb
            _fb.attach = lambda surface=None: True
            _fb.detach = lambda: None
        except ImportError:
            pass

    capture_screen = {"name": "home"}

    def install_guards():
        try:
            import desk.main as m
            _orig_render = m.App.render
            def render_with_flip(self, *a, **k):
                res = _orig_render(self, *a, **k)
                try:
                    stack = getattr(self, "stack", None)
                    if stack:
                        capture_screen["name"] = str(stack[-1])
                except Exception:
                    pass
                try: pygame.display.flip()
                except Exception: pass
                return res
            m.App.render = render_with_flip

            _orig_run = m.App.run
            def _guarded_run(self):
                while True:
                    result = _orig_run(self)
                    if result in DEVICE_ONLY:
                        msg = DEVICE_ONLY[result]
                        print(f"[desktop] Blocked device action ({result}): {msg}")
                        self.running, self.exit_code = True, 0
                        continue
                    return result
            m.App.run = _guarded_run
        except Exception as e:
            print(f"[desktop] Main import notice: {e}")

    def install_visual_capture():
        """Bind the documented F12 shortcut to the Pygame screenshot writer."""
        real_get = pygame.event.get

        def get_with_capture(*a, **k):
            events = real_get(*a, **k)
            for event in events:
                if (event.type == pygame.KEYDOWN
                        and event.key == pygame.K_F12):
                    try:
                        from utils.visual_capture import capture_surface
                        surface = pygame.display.get_surface()
                        if surface is None:
                            print("[visual-capture] no active display surface")
                            continue
                        path, error = capture_surface(
                            surface, APP, "pygame", capture_screen["name"])
                        if path:
                            print("[visual-capture] saved " + path)
                        else:
                            print("[visual-capture] failed: " + str(error))
                    except Exception as exc:
                        print("[visual-capture] failed: %s: %s" %
                              (type(exc).__name__, exc))
            return events

        pygame.event.get = get_with_capture

    install_keyboard_bridge()
    install_fbdisplay_bypass()
    install_guards()
    install_visual_capture()

    try:
        import importlib
        main = importlib.import_module("desk.main")
        return main.App().run()
    except Exception as e:
        print(f"{Color.RED}[RUNTIME EXCEPTION] Failed to execute desk.main: {e}{Color.RESET}")
        return 1

# ================================================================ LAUNCHER ==
def launch_py():
    """Ensure VENV and run pygame runtime inside it."""
    prepare_qwasar_profile()
    if not VENV_PY.is_file():
        print(f"  {Color.YELLOW}⚙️ Setting up Python Virtual Environment (.venv_desktop)...{Color.RESET}")
        subprocess.run([sys.executable, "-m", "venv", str(APP_DIR / ".venv_desktop")])
        print(f"  {Color.YELLOW}📦 Installing dependencies (pygame, psutil)...{Color.RESET}")
        subprocess.run([str(VENV_PY), "-m", "pip", "install", "-q", "pygame", "psutil"])
        print(f"  {Color.GREEN}✔ Venv created successfully!{Color.RESET}")

    print(f"  {Color.GREEN}🚀 Re-executing QWASAR Desk inside Pygame VENV...{Color.RESET}")
    env = dict(os.environ)
    env["VOIDDESK_APP_DIR"] = str(APP_DIR)
    env.setdefault("VOIDDESK_PC", "1")
    subprocess.run([str(VENV_PY), str(SELF), "--_runtime"], env=env)
    return 0

def action_launch(engine):
    cfg = read_cfg()
    print(f"\n  {Color.BOLD}Starting Engine:{Color.RESET} {Color.CYAN}{engine.upper()}{Color.RESET}")
    svc = start_service()
    try:
        time.sleep(0.3)
        if engine == "love":
            launch_love()
        else:
            launch_py()
    finally:
        if svc:
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
    print(f"\n  {Color.GREEN}✔ Engine Switched:{Color.RESET} {cur.upper()} ➔ {Color.BOLD}{nxt.upper()}{Color.RESET}")
    time.sleep(1)
    return 0

def action_edit_config_tui():
    cfg = read_cfg()
    while True:
        os.system("clear" if os.name == "posix" else "cls")
        print(f"{Color.CYAN}═══ QWASAR CONFIG EDITOR ═══{Color.RESET}\n")
        print(f"  1) Default Engine : {Color.GREEN}{cfg.get('engine', 'love').upper()}{Color.RESET}")
        print(f"  2) PC Mode        : {Color.YELLOW}{cfg.get('pc_mode', 'auto')}{Color.RESET}")
        print(f"  3) Debug Mode     : {'ON' if cfg.get('debug') else 'OFF'}")
        print(f"  4) Video Driver   : {cfg.get('video_driver', 'x11')}")
        print(f"  0) Save & Return\n")
        
        c = input(f"  {Color.BOLD}Select item to toggle [0-4]: {Color.RESET}").strip()
        if c == "1":
            cfg["engine"] = "py" if cfg.get("engine") == "love" else "love"
        elif c == "2":
            cfg["pc_mode"] = "force_device" if cfg.get("pc_mode") == "auto" else "auto"
        elif c == "3":
            cfg["debug"] = not cfg.get("debug", False)
        elif c == "4":
            drivers = ["x11", "windows", "cocoa", "dummy"]
            cur_idx = drivers.index(cfg.get("video_driver", "x11")) if cfg.get("video_driver") in drivers else 0
            cfg["video_driver"] = drivers[(cur_idx + 1) % len(drivers)]
        elif c == "0" or not c:
            write_cfg(cfg)
            print(f"  {Color.GREEN}✔ Configuration saved to desk_config.json{Color.RESET}")
            time.sleep(0.8)
            break
    return 0

def action_logs():
    if not LOG_DIR.is_dir():
        print(f"\n  {Color.YELLOW}No logs directory found.{Color.RESET}")
        input("\n Press ENTER to continue...")
        return 0
    logs = sorted(LOG_DIR.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)[:5]
    if not logs:
        print(f"\n  {Color.YELLOW}No log files present.{Color.RESET}")
        input("\n Press ENTER to continue...")
        return 0

    print(f"\n  {Color.CYAN}=== RECENT LOG FILES ==={Color.RESET}")
    for i, log in enumerate(logs, 1):
        print(f"    {i}) {log.name} ({log.stat().st_size} bytes)")
    
    try:
        choice = input(f"\n  Show log file [1-{len(logs)}, Enter=skip]: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(logs):
            log = logs[int(choice) - 1]
            print(f"\n{Color.GREEN}=== {log.name} (Last 30 lines) ==={Color.RESET}")
            lines = log.read_text(errors="replace").splitlines()[-30:]
            for line in lines:
                print(f"  {Color.DIM}{line}{Color.RESET}")
            input("\n Press ENTER to return...")
    except (KeyboardInterrupt, EOFError):
        pass
    return 0

def action_check_deps():
    print(f"\n  {Color.CYAN}=== DIAGNOSTICS & SYSTEM DEPENDENCIES ==={Color.RESET}")
    checks = [
        ("Python 3",   sys.executable, True),
        ("LÖVE 2D",    which_love() or "MISSING", False),
        ("Xephyr",     shutil.which("Xephyr") or "NOT FOUND (XFCE PC runner)", False),
        ("mpv",        shutil.which("mpv")    or "NOT FOUND (IPTV Player)", False),
        ("git",        shutil.which("git")    or "NOT FOUND", False),
        ("luac",       shutil.which("luac")   or "NOT FOUND (Lua Syntax)", False),
    ]
    for name, path, mandatory in checks:
        if "NOT FOUND" in path or "MISSING" in path:
            status = f"{Color.RED}❌ MISSING{Color.RESET}" if mandatory else f"{Color.YELLOW}⚠️ OPTIONAL{Color.RESET}"
        else:
            status = f"{Color.GREEN}✅ OK{Color.RESET}"
        print(f"    {status} {Color.BOLD}{name:12s}{Color.RESET} ➔ {path}")
    
    input(f"\n {Color.DIM}Press ENTER to return...{Color.RESET}")
    return 0

def action_repair():
    print(f"\n  {Color.CYAN}=== RUNNING AUTOMATED CODE COMPILATION REPAIR ==={Color.RESET}")
    py_files = [f for f in APP_DIR.glob("**/*.py") if "external/" not in str(f) and ".venv" not in str(f)]
    errs = 0
    for f in py_files:
        r = subprocess.run([sys.executable, "-m", "py_compile", str(f)], capture_output=True)
        if r.returncode != 0:
            print(f"    {Color.RED}❌ Syntax Error:{Color.RESET} {f.relative_to(APP_DIR)}")
            errs += 1
    
    if errs == 0:
        print(f"    {Color.GREEN}✅ All {len(py_files)} Python files compiled cleanly.{Color.RESET}")
    else:
        print(f"    {Color.RED}❌ Found syntax errors in {errs} files.{Color.RESET}")

    luac = shutil.which("luac")
    if luac and (APP_DIR / "love").is_dir():
        lua_files = list((APP_DIR / "love").glob("**/*.lua"))
        lua_errs = 0
        for f in lua_files:
            r = subprocess.run([luac, "-p", str(f)], capture_output=True)
            if r.returncode != 0:
                print(f"    {Color.RED}❌ Lua Error:{Color.RESET} {f.relative_to(APP_DIR)}")
                lua_errs += 1
        if lua_errs == 0:
            print(f"    {Color.GREEN}✅ All {len(lua_files)} Lua scripts validated successfully.{Color.RESET}")
            
    input(f"\n {Color.DIM}Press ENTER to return...{Color.RESET}")
    return 0

# ==================================================================== MENU ==
MENU = [
    ("Launch QWASAR Desk (Default Config)", lambda: action_launch(read_cfg().get("engine", "love"))),
    ("Launch QWASAR Desk → LÖVE Engine",    lambda: action_launch("love")),
    ("Launch QWASAR Desk → Pygame Engine",  lambda: action_launch("py")),
    ("Quick Switch Default Engine",       action_toggle_engine),
    ("Interactive Config Editor",         action_edit_config_tui),
    ("Log Matrix Inspector",              action_logs),
    ("Run System Dependency Check",       action_check_deps),
    ("Auto-Repair & Code Compiler",       action_repair),
]

def tui_main():
    while True:
        os.system("clear" if os.name == "posix" else "cls")
        print(BANNER)
        cfg = read_cfg()
        eng_color = Color.GREEN if cfg.get("engine") == "love" else Color.CYAN
        
        print(f"  {Color.BOLD}CURRENT ENGINE:{Color.RESET} {eng_color}{cfg.get('engine', 'love').upper()}{Color.RESET}"
              f"  │  {Color.BOLD}PC MODE:{Color.RESET} {cfg.get('pc_mode', 'auto')}"
              f"  │  {Color.BOLD}ARCH:{Color.RESET} {platform.machine()}\n")

        for i, (label, _) in enumerate(MENU, 1):
            print(f"  {Color.CYAN}{i:2d}){Color.RESET} {label}")
        print(f"  {Color.RED} 0){Color.RESET} Exit Launcher\n")
        
        try:
            choice = input(f"  {Color.BOLD}Select Option [0-{len(MENU)}]: {Color.RESET}").strip()
            if choice == "0" or not choice:
                print(f"\n  {Color.DIM}Exiting QWASAR Desk launcher.{Color.RESET}\n")
                return 0
            idx = int(choice) - 1
            if 0 <= idx < len(MENU):
                MENU[idx][1]()
        except (ValueError, IndexError):
            pass
        except (KeyboardInterrupt, EOFError):
            print("\n")
            return 0

def print_help():
    print(f"""{Color.BOLD}QWASAR Desk Launcher CLI Usage:{Color.RESET}
  ./voiddesk.py              Interactive Terminal TUI Dashboard
  ./voiddesk.py --love       Direct Launch LÖVE 2D Engine
  ./voiddesk.py --py         Direct Launch Pygame Venv Engine
  ./voiddesk.py --engine X   Launch engine X (py | love)
  ./voiddesk.py --repair     Run automated code validation tests
  ./voiddesk.py --help       Show this usage manual
""")

def cli(argv):
    if not argv or argv[0] in ("--desktop",):
        return tui_main()
    cmd = argv[0]
    if cmd == "--love":
        return action_launch("love")
    if cmd == "--py":
        return action_launch("py")
    if cmd == "--engine":
        eng = argv[1] if len(argv) > 1 else "love"
        if eng not in ("py", "love"):
            print(f"  {Color.RED}[ERR] Unknown engine: {eng} (expected: py | love){Color.RESET}")
            return 2
        return action_launch(eng)
    if cmd == "--repair":
        return action_repair()
    if cmd in ("--help", "-h"):
        print_help()
        return 0
    if cmd == "--_runtime":
        return run_pygame_runtime()
        
    print(f"  {Color.RED}[ERR] Unknown option: {cmd}{Color.RESET}\n")
    print_help()
    return 2

if __name__ == "__main__":
    sys.exit(cli(sys.argv[1:]))