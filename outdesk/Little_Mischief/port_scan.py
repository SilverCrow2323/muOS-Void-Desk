#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple network scan (ping sweep) using nmap or fping.
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
    log_message("=== PORT SCAN START ===")
    subnet = input("Inserisci subnet (es. 192.168.1.0/24): ").strip()
    if not subnet:
        print("Subnet non valida.")
        return

    # Prova nmap, altrimenti usa ping
    if os.system("which nmap > /dev/null 2>&1") == 0:
        cmd = ["nmap", "-sn", subnet]
    elif os.system("which fping > /dev/null 2>&1") == 0:
        cmd = ["fping", "-ag", subnet]
    else:
        print("Nessuno strumento di scansione trovato (nmap o fping).")
        log_message("No scanning tool found")
        return

    log_message(f"Executing: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        log_message(f"Return code: {result.returncode}")
        log_message("Output:\n" + result.stdout)
        if result.stderr:
            log_message("Stderr:\n" + result.stderr)
        print("\nScansione completata. Vedi log.")
    except Exception as e:
        log_message(f"Exception: {e}")
        print(f"\nErrore: {e}")
    log_message("=== PORT SCAN END ===")
    print("\nPremi ENTER per tornare al menu.")
    input()

if __name__ == "__main__":
    main()