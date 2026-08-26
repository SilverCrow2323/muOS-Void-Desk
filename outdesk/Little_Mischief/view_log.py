#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Viewer for the central log file (wifi_pen.log).
Uses 'less' if available, otherwise falls back to 'cat'.
"""

import os
import subprocess
import sys

LOG_FILE = "wifi_pen.log"

def main():
    if not os.path.exists(LOG_FILE):
        print(f"⚠️  File di log '{LOG_FILE}' non trovato.")
        print("Nessuna attività registrata finora.")
        input("\nPremi ENTER per tornare al menu.")
        return

    # Prova a usare less per una visualizzazione interattiva
    if os.system("which less > /dev/null 2>&1") == 0:
        subprocess.run(["less", LOG_FILE])
    else:
        # Altrimenti stampa tutto e aspetta
        with open(LOG_FILE, "r") as f:
            content = f.read()
        print(content)
        print("\n--- Fine del log ---")
        input("Premi ENTER per tornare al menu.")

if __name__ == "__main__":
    main()