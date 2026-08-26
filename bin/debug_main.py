#!/usr/bin/env python3
"""
Debug wrapper per main.py - cattura crash silenzioso
"""
import sys
import os
import traceback

# Get paths
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESK_DIR = os.path.join(APP_DIR, "desk")
LOG_FILE = os.path.join(APP_DIR, "data", "voiddesk_debug.log")

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

def log(msg):
    """Log to both stdout and file"""
    print(msg, flush=True)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(msg + "\n")
    except:
        pass

# Start logging
log(f"[DEBUG] === VoidDesk Debug Wrapper Start ===")
log(f"[DEBUG] APP_DIR: {APP_DIR}")
log(f"[DEBUG] DESK_DIR: {DESK_DIR}")
log(f"[DEBUG] Python: {sys.version}")
log(f"[DEBUG] sys.path: {sys.path[:3]}")

# Set up path BEFORE any imports
sys.path.insert(0, DESK_DIR)
sys.path.insert(0, APP_DIR)
log(f"[DEBUG] sys.path updated: {sys.path[:3]}")

# Try each import step by step
try:
    log("[DEBUG] Import stdlib modules...")
    import os as os_
    import json
    log("[DEBUG] ✓ stdlib OK")
    
    log("[DEBUG] Import pygame...")
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", "1")
    
    import pygame
    log(f"[DEBUG] ✓ pygame {pygame.version.ver} OK")
    
    log("[DEBUG] Import desk modules (evinput, fbdisplay, etc)...")
    import evinput
    import fbdisplay
    import icons
    log("[DEBUG] ✓ desk modules OK")
    
    log("[DEBUG] Import hubs package...")
    from desk.hubs import ForgeHub
    log("[DEBUG] ✓ hubs OK")
    
    log("[DEBUG] Import nexus...")
    from desk.nexus import NexusRenderer
    log("[DEBUG] ✓ nexus OK")
    
    log("[DEBUG] Import intro...")
    import intro
    log("[DEBUG] ✓ intro OK")
    
    log("[DEBUG] All imports successful, launching main.py...")
    log("[DEBUG] === Launching actual VoidDesk ===\n")
    
    # Now exec the actual main.py
    with open(os.path.join(DESK_DIR, "main.py")) as f:
        exec(f.read(), {"__file__": os.path.join(DESK_DIR, "main.py"), "__name__": "__main__"})
    
except Exception as e:
    log(f"\n[ERROR] {type(e).__name__}: {e}")
    log("[ERROR] Traceback:")
    log(traceback.format_exc())
    log("[ERROR] === CRASH ===\n")
    sys.exit(1)
