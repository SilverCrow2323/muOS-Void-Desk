#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# VOIDDESK // xfce_install — installa pacchetti nel chroot XFCE mostrando
# il progresso reale: apt parla via APT::Status-Fd, noi disegniamo.
# uso: xfce_install.py "<etichetta>" "<pacchetti apt>"

import os
import shutil
import subprocess
import sys
import time

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(APP, "data")
IMG = os.path.join(DATA, "xfce.img")
MNT = os.path.join(DATA, "xfce_mnt")
APPS_DB = os.path.join(DATA, ".xfce_apps")
sys.path.insert(0, os.path.join(APP, "desk"))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import imgmount  # noqa: E402

UI = True
try:
    import pygame
    import icons
    import fbdisplay
except Exception:
    UI = False
FB = None
if not UI:                       # niente pygame: uso il testo su /dev/fb0
    try:
        sys.path.insert(0, os.path.join(APP, "lib"))
        import fbtext
        FB = fbtext.Screen(title="VOIDDESK - installazione")
    except Exception:
        FB = None

W, H = 640, 480
BG = (7, 8, 11)
PANEL = (18, 20, 26)
FG = (232, 232, 232)
DIM = (150, 150, 160)
FAINT = (98, 98, 108)
OK_G = (80, 220, 110)
NO_R = (235, 70, 70)
ACC = (255, 176, 46)


def cfg_get(k, d=None):
    import json
    try:
        return json.load(open(os.path.join(DATA, "desk_config.json"))).get(
            k, d)
    except Exception:
        return d


def comp_color(c):
    """Complementare del tema (stesso algoritmo di desk/main.py): usato
    per colorare l'intera schermata di progresso quando si sta
    disinstallando, cosi' il colore racconta cosa sta succedendo anche
    da qui, non solo nel menu."""
    r, g, b = 255 - c[0], 255 - c[1], 255 - c[2]
    if r + g + b < 250:
        r, g, b = min(255, r + 90), min(255, g + 90), min(255, b + 90)
    return (r, g, b)


class Screen(object):
    """Schermata di installazione: barra per pacchetto + barra totale."""

    def __init__(self, title, pkgs, lang="it"):
        self.ok = False
        self.lang = lang
        self.title = title
        self.pkgs = list(pkgs)
        self.state = {p: "wait" for p in pkgs}
        self.cur = ""
        self.cur_pct = 0
        self.phase = "prep"
        self.tot_pct = 0
        self.msg = ""
        self.log_tail = []
        if not UI:
            return
        try:
            import json
            acc = cfg_get("theme", "ambra")
            self.acc = {"ambra": (255, 176, 46), "cremisi": (231, 54, 84),
                        "ciano": (74, 206, 224), "verde": (112, 224, 122),
                        "acciaio": (208, 214, 210)}.get(acc, ACC)
            if os.environ.get("VOIDDESK_MODE") == "remove":
                self.acc = comp_color(self.acc)
            pygame.display.init()
            pygame.font.init()
            self.surf = pygame.display.set_mode((W, H))
            fbdisplay.attach(self.surf)
            fp = os.path.join(APP, "assets", "DejaVuSans.ttf")
            self.f_big = pygame.font.Font(fp, 24)
            self.f_med = pygame.font.Font(fp, 17)
            self.f_small = pygame.font.Font(fp, 14)
            self.f_tiny = pygame.font.Font(fp, 12)
            self.ok = True
        except Exception:
            self.ok = False

    def t(self, it, en):
        return en if self.lang == "en" else it

    def text(self, s, pos, f, col, maxw=None):
        if maxw:
            while s and f.size(s)[0] > maxw:
                s = s[:-1]
        self.surf.blit(f.render(s, True, col), pos)

    def spinner(self, cx, cy, r=11):
        """Rotore di caricamento, stesso stile del menu principale: si
        vede che sta lavorando anche nei secondi vuoti prima che apt
        cominci a dare segni di vita (mount, apt update...)."""
        t = time.time() * 5.2
        for i, (rr, wd) in enumerate(((r, 3), (r - 5, 2))):
            a0 = t * (1 if i == 0 else -1.4) + i * 2.1
            pygame.draw.arc(self.surf, self.acc,
                            (cx - rr, cy - rr, rr * 2, rr * 2),
                            a0, a0 + 3.6, wd)
        pygame.draw.circle(self.surf, self.acc, (cx, cy), 2)

    def bar(self, x, y, w, h, pct, col):
        pygame.draw.rect(self.surf, (10, 10, 16), (x, y, w, h),
                         border_radius=4)
        if pct > 0:
            pygame.draw.rect(self.surf, col,
                             (x, y, max(3, int(w * pct / 100.0)), h),
                             border_radius=4)
        pygame.draw.rect(self.surf, FAINT, (x, y, w, h), 1, border_radius=4)

    def draw(self):
        if not self.ok:
            if FB is not None:      # ripiego testuale
                done = sum(1 for v in self.state.values() if v == "done")
                FB.lines = (["%s  (%d/%d)" % (self.title, done,
                                              len(self.pkgs)), ""]
                            + ["%s %s" % ("[x]" if self.state[p] == "done"
                                          else "[ ]", p)
                               for p in self.pkgs[:14]]
                            + ["", self.cur or "", "totale: %d%%" % self.tot_pct]
                            + ([self.msg] if self.msg else []))
                try:
                    FB.render()
                except Exception:
                    pass
            return
        self.surf.fill(BG)
        pygame.draw.rect(self.surf, PANEL, (0, 0, W, 44))
        pygame.draw.line(self.surf, self.acc, (0, 44), (W, 44), 2)
        self.text("Void-", (14, 9), self.f_big, FG)
        bw = self.f_big.size("Void-")[0]
        self.text("DESK", (14 + bw, 9), self.f_big, self.acc)
        lab = "INSTALLER"
        if os.environ.get("VOIDDESK_MODE") == "remove":
            lab = "UNINSTALLER"
        self.text(lab, (24 + bw + self.f_big.size("DESK")[0], 17),
                  self.f_tiny, DIM)
        self.text(self.title, (W - self.f_small.size(self.title)[0] - 14, 15),
                  self.f_small, DIM)

        # elenco pacchetti con stato
        y = 60
        done = sum(1 for v in self.state.values() if v == "done")
        self.text(self.t("PACCHETTI", "PACKAGES"), (20, y), self.f_small,
                  self.acc)
        self.text("%d / %d" % (done, len(self.pkgs)),
                  (W - 70, y), self.f_small, DIM)
        y += 22
        shown = self.pkgs
        if len(shown) > 9:
            # scorro tenendo in vista il primo pacchetto non ancora finito
            todo = [i for i, p in enumerate(shown) if self.state[p] != "done"]
            first = todo[0] if todo else 0
            first = max(0, min(first, len(shown) - 9))
            shown = shown[first:first + 9]
        for p in shown:
            st = self.state[p]
            col = OK_G if st == "done" else (FG if st == "work" else FAINT)
            cx = 24
            if st == "done":
                pygame.draw.lines(self.surf, OK_G, False,
                                  [(cx, y + 8), (cx + 4, y + 13),
                                   (cx + 12, y + 1)], 3)
            elif st == "work":
                ang = (time.time() * 5) % 6.28
                pygame.draw.arc(self.surf, self.acc,
                                (cx, y, 14, 14), ang, ang + 4.2, 3)
            else:
                pygame.draw.circle(self.surf, FAINT, (cx + 7, y + 7), 3, 1)
            self.text(p, (cx + 24, y - 1), self.f_med, col, maxw=W - 120)
            if st == "work":
                self.text(self.t("in corso", "working"), (W - 90, y + 1),
                          self.f_tiny, self.acc)
            y += 22

        # barra pacchetto corrente
        y = H - 132
        cur_lab = self.cur or self.t("preparazione...", "preparing...")
        if self.phase in ("prep", "dl") and self.cur_pct == 0:
            self.spinner(W - 34, y + 8)
            self.text(cur_lab, (20, y), self.f_med, FG, maxw=W - 130)
        else:
            self.text(cur_lab, (20, y), self.f_med, FG, maxw=W - 90)
            self.text("%d%%" % self.cur_pct, (W - 58, y), self.f_med,
                      self.acc)
        self.bar(20, y + 24, W - 40, 14, self.cur_pct, self.acc)

        # barra totale
        y += 50
        rm_mode = os.environ.get("VOIDDESK_MODE") == "remove"
        ph = {"dl": self.t("SCARICAMENTO", "DOWNLOADING"),
              "inst": self.t("RIMOZIONE" if rm_mode else "INSTALLAZIONE",
                             "REMOVING" if rm_mode else "INSTALLING"),
              "prep": self.t("PREPARAZIONE", "PREPARING"),
              "done": self.t("COMPLETATO", "DONE")}.get(self.phase, "")
        self.text(self.t("TOTALE", "OVERALL") + "  -  " + ph, (20, y),
                  self.f_small, DIM)
        self.text("%d%%" % self.tot_pct, (W - 58, y - 2), self.f_med, FG)
        self.bar(20, y + 20, W - 40, 18, self.tot_pct, OK_G)
        if self.msg:
            self.text(self.msg, (20, H - 26), self.f_tiny,
                      NO_R if "FATAL" in self.msg else FAINT, maxw=W - 40)
        pygame.display.flip()

    def close(self):
        if self.ok:
            fbdisplay.detach()
            pygame.display.quit()


mounted = imgmount.is_mounted


def umount_all():
    imgmount.umount_tree(MNT, IMG)


def apt_with_progress(pkgs, scr, log, remove=False, upgrade=False):
    """Esegue apt-get install/remove/upgrade leggendo APT::Status-Fd."""
    r, w = os.pipe()
    env = dict(os.environ)
    env["DEBIAN_FRONTEND"] = "noninteractive"
    cmd = ["chroot", MNT, "/usr/bin/env",
           "DEBIAN_FRONTEND=noninteractive",
           "PATH=/usr/sbin:/usr/bin:/sbin:/bin",
           "apt-get", "-o", "APT::Status-Fd=%d" % w,
           "-o", "Acquire::ForceIPv4=true",
           "-o", "Acquire::https::Verify-Peer=false",
           "-o", "Acquire::https::Verify-Host=false",
           "-o", "Acquire::Retries=2",
           ] + (["upgrade", "-y"] if upgrade else
                ["remove", "-y", "--purge", "--autoremove"] if remove
                else ["install", "-y", "--no-install-recommends"]) + pkgs
    proc = subprocess.Popen(cmd, stdout=log, stderr=log, pass_fds=(w,),
                            env=env)
    os.close(w)
    os.set_blocking(r, False)
    buf = b""
    last = time.time()
    while True:
        if proc.poll() is not None and not buf:
            try:
                chunk = os.read(r, 65536)
            except (BlockingIOError, OSError):
                chunk = b""
            if not chunk:
                break
        try:
            chunk = os.read(r, 65536)
        except (BlockingIOError, InterruptedError):
            chunk = b""
        except OSError:
            chunk = b""
        if chunk:
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                parse_status(line.decode("utf-8", "replace"), scr)
        if time.time() - last > 0.05:
            last = time.time()
            scr.draw()
        if proc.poll() is not None and not chunk:
            break
        time.sleep(0.02)
    os.close(r)
    return proc.wait()


def parse_status(line, scr):
    # dlstatus:<id>:<percent>:<descrizione>
    # pmstatus:<pacchetto>:<percent>:<descrizione>
    parts = line.split(":", 3)
    if len(parts) < 3:
        return
    kind, who, pct = parts[0], parts[1], parts[2]
    desc = parts[3] if len(parts) > 3 else ""
    try:
        pctf = float(pct)
    except ValueError:
        return
    if kind == "dlstatus":
        scr.phase = "dl"
        scr.cur = desc[:60]
        scr.cur_pct = int(pctf)
        scr.tot_pct = int(pctf * 0.4)
        for p in scr.pkgs:
            if p in desc and scr.state[p] == "wait":
                scr.state[p] = "work"
    elif kind == "pmstatus":
        scr.phase = "inst"
        scr.cur = "%s  -  %s" % (who, desc[:44])
        scr.cur_pct = int(pctf)
        scr.tot_pct = 40 + int(pctf * 0.6)
        if who in scr.state:
            scr.state[who] = "work"
        for p in scr.pkgs:
            if p != who and scr.state[p] == "work":
                scr.state[p] = "done"
        if "Installed" in desc or "installato" in desc:
            if who in scr.state:
                scr.state[who] = "done"
    elif kind == "pmerror":
        scr.msg = "FATAL %s: %s" % (who, desc[:60])


def run_script(cmd, scr, log):
    """Voce del catalogo che non e' apt: es. lo script ufficiale Tailscale."""
    scr.phase = "inst"
    scr.cur = cmd[:60]
    scr.cur_pct = 10
    scr.tot_pct = 20
    scr.draw()
    p = subprocess.Popen(["chroot", MNT, "/bin/bash", "-c",
                          "export DEBIAN_FRONTEND=noninteractive; "
                          "export PATH=/usr/sbin:/usr/bin:/sbin:/bin; " + cmd],
                         stdout=log, stderr=log)
    pct = 20
    while p.poll() is None:
        pct = min(92, pct + 1)
        scr.tot_pct = pct
        scr.cur_pct = min(95, scr.cur_pct + 2)
        scr.draw()
        time.sleep(0.4)
    return p.wait()


def main():
    if len(sys.argv) < 3:
        print("uso: xfce_install.py NOME PACCHETTI [remove]")
        return 2
    label, pkgs_s = sys.argv[1], sys.argv[2]
    mode = sys.argv[3] if len(sys.argv) > 3 else "install"
    script = None
    if pkgs_s.startswith("!"):
        script = pkgs_s[1:]
        pkgs = [label]
    else:
        pkgs = pkgs_s.split()
    lang = cfg_get("lang", "it")
    scr = Screen(label, pkgs, lang)
    logf = open(os.path.join(DATA, "install.log"), "ab")
    logf.write(("\n==== %s : %s ====\n" % (time.ctime(), pkgs_s)).encode())

    def note(m):
        scr.msg = m
        scr.draw()
        print(m, flush=True)
        logf.write((m + "\n").encode())

    if not os.path.exists(os.path.join(DATA, ".xfce_ready")):
        note("FATAL: desktop XFCE non installato")
        time.sleep(4)
        scr.close()
        return 1
    if subprocess.call(["curl", "-sI", "--max-time", "8",
                        "https://ports.ubuntu.com"],
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL) != 0:
        note("FATAL: rete assente (attiva il WiFi)" if lang == "it"
             else "FATAL: no network (turn on Wi-Fi)")
        time.sleep(5)
        scr.close()
        return 1

    os.makedirs(MNT, exist_ok=True)
    umount_all()                       # smonta anche i bind lasciati da XFCE
    imgmount.cleanup_stale(IMG)        # libera loop rimasti appesi
    ok, err = imgmount.mount_img(IMG, MNT)
    if not ok:
        note("FATAL: mount immagine fallito - %s" % (err or "?"))
        note("Suggerimento: chiudi il desktop XFCE e riprova, oppure usa"
             " il pannello (START+SELECT) -> Risoluzione problemi.")
        time.sleep(7)
        scr.close()
        return 1
    try:
        for typ, src, dst in (("bind", "/dev", "/dev"),
                              ("proc", "proc", "/proc"),
                              ("sysfs", "sys", "/sys")):
            os.makedirs(MNT + dst, exist_ok=True)
            if not mounted(MNT + dst):
                if typ == "bind":
                    subprocess.call(["mount", "-o", "bind", src, MNT + dst])
                else:
                    subprocess.call(["mount", "-t", typ, src, MNT + dst])
        try:
            shutil.copy("/etc/resolv.conf", MNT + "/etc/resolv.conf")
        except OSError:
            pass
        # chroot senza init: i postinst (udisks2, polkitd...) non devono
        # provare a lanciare servizi, o dpkg fallisce e resta a meta'
        try:
            prc = MNT + "/usr/sbin/policy-rc.d"
            with open(prc, "w") as f:
                f.write("#!/bin/sh\nexit 101\n")
            os.chmod(prc, 0o755)
        except OSError:
            pass
        # sblocco dpkg rimasto a meta' da un tentativo precedente:
        # e' il motivo per cui "anche se riprovo non riesce"
        scr.phase = "prep"
        scr.cur = "dpkg --configure -a"
        scr.draw()
        subprocess.call(["chroot", MNT, "/usr/bin/env",
                         "DEBIAN_FRONTEND=noninteractive",
                         "PATH=/usr/sbin:/usr/bin:/sbin:/bin",
                         "dpkg", "--configure", "-a"],
                        stdout=logf, stderr=logf)
        scr.cur = "apt-get update"
        scr.draw()
        if not script:
            subprocess.call(["chroot", MNT, "/bin/bash", "-c",
                             "DEBIAN_FRONTEND=noninteractive apt-get "
                             "-o Acquire::ForceIPv4=true "
                             "-o Acquire::https::Verify-Peer=false "
                             "-o Acquire::https::Verify-Host=false update"],
                            stdout=logf, stderr=logf)
        if script:
            rc = run_script(script, scr, logf)
        elif mode == "remove":
            rc = apt_with_progress(pkgs, scr, logf, remove=True)
        else:
            rc = apt_with_progress(pkgs, scr, logf)
        if rc != 0 and not script:
            # secondo tempo: riparo le dipendenze e riprovo una volta
            note("riparo le dipendenze e riprovo..." if lang == "it"
                 else "repairing dependencies, retrying...")
            subprocess.call(["chroot", MNT, "/usr/bin/env",
                             "DEBIAN_FRONTEND=noninteractive",
                             "PATH=/usr/sbin:/usr/bin:/sbin:/bin",
                             "apt-get", "-f", "install", "-y"],
                            stdout=logf, stderr=logf)
            subprocess.call(["chroot", MNT, "/usr/bin/env",
                             "DEBIAN_FRONTEND=noninteractive",
                             "PATH=/usr/sbin:/usr/bin:/sbin:/bin",
                             "dpkg", "--configure", "-a"],
                            stdout=logf, stderr=logf)
            rc = apt_with_progress(pkgs, scr, logf,
                                   remove=(mode == "remove"))
        if rc != 0:
            note("FATAL: installazione fallita (rc=%d)" % rc if lang == "it"
                 else "FATAL: install failed (rc=%d)" % rc)
            time.sleep(6)
            return 1
        # rc==0 non garantisce che OGNI postinst sia arrivato in fondo:
        # in un chroot senza init, un passo come "update-alternatives"
        # dentro un postinst puo' restare a meta' silenziosamente (e'
        # la stessa causa che serviva policy-rc.d per udisks2/polkitd).
        # Un secondo giro di configure -a lo completa, se serve.
        subprocess.call(["chroot", MNT, "/usr/bin/env",
                         "DEBIAN_FRONTEND=noninteractive",
                         "PATH=/usr/sbin:/usr/bin:/sbin:/bin",
                         "dpkg", "--configure", "-a"],
                        stdout=logf, stderr=logf)
        try:
            with open(os.path.join(os.path.dirname(MNT),
                                   "post_install_check.log"), "a") as vf:
                vf.write("%s pacchetti richiesti: %r\n" %
                        (time.strftime("%H:%M:%S"), pkgs))
                for probe in ("usr/bin/figlet", "usr/bin/convert"):
                    full = MNT + "/" + probe
                    isl = os.path.islink(full)
                    tgt = os.readlink(full) if isl else None
                    vf.write("  %s: esiste=%r  link=%r  punta a=%r\n" %
                            (probe, os.path.exists(full), isl, tgt))
        except OSError:
            pass
        for p in scr.pkgs:
            scr.state[p] = "done"
        scr.phase = "done"
        scr.cur = label
        scr.cur_pct = scr.tot_pct = 100
        if mode == "remove":
            scr.msg = ("Rimosso." if lang == "it" else "Removed.")
        else:
            scr.msg = ("Fatto: lo trovi nel menu Applicazioni di XFCE."
                       if lang == "it" else
                       "Done: find it in the XFCE Applications menu.")
        scr.draw()
        subprocess.call(["chroot", MNT, "/bin/bash", "-c",
                         "apt-get clean"], stdout=logf, stderr=logf)
        # aggiorno il censimento ambienti (il selettore START SESSION
        # deve vedere subito il nuovo arrivato, senza aspettare un lancio)
        try:
            envs = ["xfce"]
            if os.path.exists(MNT + "/usr/bin/icewm-session"):
                envs.append("icewm")
            if os.path.exists(MNT + "/usr/bin/startlxde"):
                envs.append("lxde")
            with open(os.path.join(DATA, ".envs"), "w") as f:
                f.write(" ".join(envs))
        except OSError:
            pass
        if mode != "remove":
            with open(APPS_DB, "a") as f:
                f.write(label + "\n")
        time.sleep(3)
        return 0
    finally:
        umount_all()
        scr.close()
        logf.close()


if __name__ == "__main__":
    sys.exit(main())
