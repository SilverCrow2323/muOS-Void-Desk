#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clear the central log file (wifi_pen.log).
"""

import os

LOG_FILE = "wifi_pen.log"

def main():
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
        print("✅ Log cancellato.")
    else:
        print("ℹ️  Nessun log da cancellare.")
    input("\nPremi ENTER per tornare al menu.")

if __name__ == "__main__":
    main()