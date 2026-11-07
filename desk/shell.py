# -*- coding: utf-8 -*-
# VOIDDESK // shell — terminale con tastiera QWERTY a schermo, navigabile
# col dpad. I comandi girano dentro il chroot XFCE se disponibile,
# altrimenti sull'host muOS.

import os
import subprocess
import sys
import time

import pygame

W, H = 640, 480
BG = (10, 12, 16)
PANEL = (24, 26, 34)
FG = (222, 226, 232)
DIM = (140, 146, 158)
FAINT = (92, 98, 110)
OK_G = (110, 220, 130)
NO_R = (235, 90, 90)

ROWS_LOW = ["1234567890-", "qwertyuiop", "asdfghjkl;", "zxcvbnm,./"]
ROWS_UP = ["!@#$%^&*()_", "QWERTYUIOP", "ASDFGHJKL:", "ZXCVBNM<>?"]
SPECIALS_IT = ["MAIUSC", "SPAZIO", "<-", "INVIO"]
SPECIALS_EN = ["SHIFT", "SPACE", "<-", "ENTER"]


class Shell(object):
    def __init__(self, surface, font_path, accent, mnt="", lang="it",
                auto_cmd=None):
        self.s = surface
        self.accent = accent
        self.mnt = mnt if mnt and os.path.isdir(os.path.join(mnt, "usr")) \
            else ""
        self.lang = lang
        self.f_mono = self._font(font_path, 14)
        self.f_key = self._font(font_path, 15)
        self.f_small = self._font(font_path, 13)
        self.line = ""
        self.cursor = 0
        self.hist = []
        self.hist_i = 0
        self.out = [self._t("VoidDesk shell — A preme il tasto, "
                            "START esegue, SELECT esce",
                            "VoidDesk shell — A presses a key, "
                            "START runs, SELECT quits")]
        if self.mnt:
            self.out.append(self._t("comandi eseguiti nel chroot XFCE",
                                    "commands run inside the XFCE chroot"))
        else:
            self.out.append(self._t("chroot non montato: comandi su muOS",
                                    "chroot not mounted: running on muOS"))
        self.kx, self.ky = 0, 1
        self.shift = False
        self.running = True
        self.busy = False
        self.cwd = "/root" if self.mnt else "/"
        if auto_cmd:
            self.line = auto_cmd
            self.run_cmd()

    def _font(self, p, sz):
        try:
            return pygame.font.Font(p, sz)
        except Exception:
            return pygame.font.Font(None, sz)

    def _t(self, it, en):
        return en if self.lang == "en" else it

    # ------------------------------------------------------------- tastiera
    def specials(self):
        return SPECIALS_EN if self.lang == "en" else SPECIALS_IT

    def rows(self):
        base = ROWS_UP if self.shift else ROWS_LOW
        return [list(r) for r in base] + [self.specials()]

    def key_at(self, x, y):
        rs = self.rows()
        y = max(0, min(len(rs) - 1, y))
        r = rs[y]
        x = max(0, min(len(r) - 1, x))
        return r[x]

    def press(self):
        k = self.key_at(self.kx, self.ky)
        sp = self.specials()
        c = self.cursor
        if k == sp[0]:
            self.shift = not self.shift
        elif k == sp[1]:
            self.line = self.line[:c] + " " + self.line[c:]
            self.cursor += 1
        elif k == sp[2]:
            if c > 0:
                self.line = self.line[:c - 1] + self.line[c:]
                self.cursor -= 1
        elif k == sp[3]:
            self.run_cmd()
        else:
            self.line = self.line[:c] + k + self.line[c:]
            self.cursor += 1

    # --------------------------------------------------------------- comandi
    def run_cmd(self):
        cmd = self.line.strip()
        if not cmd:
            return
        self.hist.append(cmd)
        self.hist_i = len(self.hist)
        self.out.append("$ " + cmd)
        self.line = ""
        self.cursor = 0
        if cmd in ("exit", "quit"):
            self.running = False
            return
        if cmd == "clear":
            self.out = []
            return
        self.busy = True
        self.draw()
        try:
            if self.mnt:
                full = ["chroot", self.mnt, "/bin/sh", "-c",
                        "cd %s 2>/dev/null; %s" % (self.cwd, cmd)]
            else:
                full = ["/bin/sh", "-c", cmd]
            r = subprocess.run(full, capture_output=True, text=True,
                               timeout=25)
            txt = (r.stdout or "") + (r.stderr or "")
            if not txt.strip():
                txt = self._t("(nessun output)  rc=%d" % r.returncode,
                              "(no output)  rc=%d" % r.returncode)
            for ln in txt.splitlines()[-60:]:
                self.out.append(ln[:96])
        except subprocess.TimeoutExpired:
            self.out.append(self._t("[timeout dopo 25s]", "[timed out: 25s]"))
        except Exception as e:
            self.out.append("[%s]" % e)
        self.busy = False
        self.out = self.out[-400:]

    # ---------------------------------------------------------------- input
    def on_button(self, b):
        if b == "SELECT":
            self.running = False
        elif b == "A":
            self.press()
        elif b == "B":
            c = self.cursor
            if c > 0:
                self.line = self.line[:c - 1] + self.line[c:]
                self.cursor -= 1
        elif b == "START":
            self.run_cmd()
        elif b == "Y":
            self.shift = not self.shift
        elif b == "X":
            c = self.cursor
            self.line = self.line[:c] + " " + self.line[c:]
            self.cursor += 1
        elif b == "L1":                     # cronologia
            if self.hist:
                self.hist_i = max(0, self.hist_i - 1)
                self.line = self.hist[self.hist_i]
                self.cursor = len(self.line)
        elif b == "R1":
            if self.hist:
                self.hist_i = min(len(self.hist) - 1, self.hist_i + 1)
                self.line = self.hist[self.hist_i]
                self.cursor = len(self.line)
        elif b == "L2":                     # cursore carattere per carattere
            self.cursor = max(0, self.cursor - 1)
        elif b == "R2":
            self.cursor = min(len(self.line), self.cursor + 1)
        elif b == "UP":
            self.ky = (self.ky - 1) % len(self.rows())
            self.kx = min(self.kx, len(self.rows()[self.ky]) - 1)
        elif b == "DOWN":
            self.ky = (self.ky + 1) % len(self.rows())
            self.kx = min(self.kx, len(self.rows()[self.ky]) - 1)
        elif b == "LEFT":
            self.kx = (self.kx - 1) % len(self.rows()[self.ky])
        elif b == "RIGHT":
            self.kx = (self.kx + 1) % len(self.rows()[self.ky])

    # --------------------------------------------------------------- render
    def draw(self):
        self.s.fill(BG)
        pygame.draw.rect(self.s, PANEL, (0, 0, W, 26))
        self.s.blit(self.f_small.render("VOID SHELL   %s" %
                                        ("chroot XFCE" if self.mnt
                                         else "muOS host"), True,
                                        self.accent), (10, 5))
        st = self._t("occupato..." if self.busy else "pronto",
                     "busy..." if self.busy else "ready")
        self.s.blit(self.f_small.render(st, True,
                                        NO_R if self.busy else OK_G),
                    (W - 90, 5))
        # output
        y = 32
        vis = self.out[-13:]
        for ln in vis:
            col = OK_G if ln.startswith("$ ") else DIM
            self.s.blit(self.f_mono.render(ln[:88], True, col), (8, y))
            y += 16
        # riga di comando
        cy = 248
        pygame.draw.rect(self.s, (16, 20, 26), (6, cy, W - 12, 24),
                         border_radius=4)
        pygame.draw.rect(self.s, self.accent, (6, cy, W - 12, 24), 1,
                         border_radius=4)
        prompt = "$ " + self.line
        self.s.blit(self.f_mono.render(prompt[-86:], True, FG), (12, cy + 4))
        if int(time.time() * 2) % 2:
            cpos = max(0, min(len(self.line), self.cursor))
            pre = ("$ " + self.line[:cpos])[-86:]
            cw = self.f_mono.size(pre)[0]
            pygame.draw.rect(self.s, self.accent, (12 + cw, cy + 5, 7, 15))
        # tastiera
        rs = self.rows()
        ky0 = 282
        for r, row in enumerate(rs):
            n = len(row)
            kw = (W - 20) // max(1, n)
            for c, k in enumerate(row):
                x = 10 + c * kw
                y2 = ky0 + r * 44
                sel = (c == self.kx and r == self.ky)
                col_bg = self.accent if sel else (30, 34, 44)
                pygame.draw.rect(self.s, col_bg, (x + 2, y2, kw - 4, 40),
                                 border_radius=5)
                if not sel:
                    pygame.draw.rect(self.s, (52, 58, 72),
                                     (x + 2, y2, kw - 4, 40), 1,
                                     border_radius=5)
                lab = k
                if k == self.specials()[0] and self.shift:
                    lab = k.lower()
                tcol = (10, 10, 14) if sel else FG
                img = self.f_key.render(lab, True, tcol)
                self.s.blit(img, (x + (kw - img.get_width()) // 2,
                                  y2 + (40 - img.get_height()) // 2))
        pygame.display.flip()

