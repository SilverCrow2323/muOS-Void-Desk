#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scan WiFi networks using iwlist.
Output saved to log.
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
    log_message("=== SCAN NETWORKS START ===")
    try:
        # Usa iwlist per scan
        result = subprocess.run(["iwlist", "wlan0", "scan"], capture_output=True, text=True, timeout=30)
        output = result.stdout
        if result.returncode != 0:
            log_message(f"iwlist error: {result.stderr}")
            print("\nErrore scansione. Verifica che wlan0 sia attivo.")
        else:
            log_message("Scan completed successfully")
            log_message("Output:\n" + output)
            print("\nScansione completata. Vedi log per i dettagli.")
    except Exception as e:
        log_message(f"Exception: {e}")
        print(f"\nErrore: {e}")
    log_message("=== SCAN NETWORKS END ===")
    print("\nPremi ENTER per tornare al menu.")
    input()

if __name__ == "__main__":
    main()