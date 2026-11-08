# outdesk/VoidCast/voidcast/core/player.py
# -*- coding: utf-8 -*-
# VOIDCAST // core.player — playback backend with cyberpunk HUD overlays.
#
# Exit codes (mpv → Python):
#   0/4  : normal back
#   20   : next channel
#   21   : prev channel
#   22   : toggle favorite
#   30   : request background playback
#
# In playback:
#   A  pause/play          B  exit
#   Y  toggle favorite     X  mute  (or "return to app + bg audio" in bg panel)
#   dpad up/down  next/prev          dpad left/right  seek ±30s
#   L1/R1  brightness      L2/R2  contrast
#   SELECT  details+commands overlay   M (MENU)  background manager
#   START   recording toggle

import json
import os
import shlex
import shutil
import socket
import subprocess
import time

from datetime import datetime

from . import config as C
from . import evinput
from . import i18n
from . import recorder

RESULT_BACK = "back"
RESULT_NEXT = "next"
RESULT_PREV = "prev"
RESULT_FAV = "fav"
RESULT_ERROR = "error"
RESULT_BG = "bg"

_GAMEPAD_CONF = """\
GAMEPAD_ACTION_RIGHT quit 0
GAMEPAD_ACTION_DOWN cycle pause
GAMEPAD_ACTION_LEFT quit 22
GAMEPAD_DPAD_UP quit 20
GAMEPAD_DPAD_DOWN quit 21
GAMEPAD_DPAD_LEFT seek -30
GAMEPAD_DPAD_RIGHT seek 30
GAMEPAD_LEFT_SHOULDER add volume -5
GAMEPAD_RIGHT_SHOULDER add volume 5
GAMEPAD_START show-progress
GAMEPAD_BACK show-text "${media-title}" 3000
q quit 0
n quit 20
p quit 21
"""

_C_WHITE = "&HFFFFFF&"
_C_DIM   = "&HBBBBBB&"
_C_FAINT = "&H888888&"
_C_GREEN = "&H88FF44&"
_C_YEL   = "&H44CCFF&"
_C_CRIM  = "&H4628DC&"

class Player(object):
    def __init__(self, cfg):
        self.cfg = cfg
        self.last_error = ""
        self._channel = None
        self._ctx = {}
        self._volume = 100
        self._paused = False
        self.overlay_mode = None  # None | "main" | "details" | "bg"
        self._show_until = 0
        self._toast_text = None
        self._toast_until = 0
        self._details_sel = 0
        self._last_ass = ""
        self.recording = False
        self._rec_name = ""

    def backend(self):
        pref = self.cfg.get("player_backend", "auto")
        if pref in ("mpv", "ffplay") and shutil.which(pref):
            return pref
        for cand in ("mpv", "ffplay"):
            if shutil.which(cand):
                return cand
        return None

    def play(self, channel, ctx=None):
        be = self.backend()
        if be is None:
            self.last_error = i18n.t("pl.err.no_backend")
            return RESULT_ERROR
        self._channel = channel
        self._ctx = ctx or {}
        self._volume = 100
        self._paused = False
        self.overlay_mode = None
        self._show_until = 0
        self._toast_text = None
        self._toast_until = 0
        self._details_sel = 0
        self._last_ass = ""
        self._rec_name = channel.name

        ua = self.cfg.get("user_agent", "")
        opts = getattr(channel, "opts", None) or {}
        ua = opts.get("user-agent") or ua
        referrer = opts.get("referrer", "")
        hdrs = dict(opts.get("headers", {}))
        if opts.get("origin"):
            hdrs.setdefault("Origin", opts["origin"])
        cache_s = int(self.cfg.get("player_cache_secs", 5))
        mlog_path = os.path.join(C.DATA_DIR, "mpv.log")
        if be == "mpv":
            sock_path = "/tmp/voidcast-mpv-%d.sock" % os.getpid()
            try:
                os.remove(sock_path)
            except OSError:
                pass
            cmd = ["mpv", channel.url,
                   "--no-config", "--fullscreen", "--keepaspect=yes",
                   "--video-zoom=0", "--video-align-x=0", "--video-align-y=0",
                   "--osd-level=1", "--osd-duration=2000",
                   "--user-agent=%s" % ua, "--network-timeout=12"]
            if referrer:
                cmd.append("--referrer=%s" % referrer)
            if hdrs:
                cmd.append("--http-header-fields=" + ",".join(
                    "%s: %s" % (k, v) for k, v in hdrs.items()))
            cmd += ["--cache=yes", "--cache-secs=%d" % cache_s,
                    "--input-ipc-server=%s" % sock_path]
        else:
            sock_path = None
            cmd = ["ffplay", "-fs", "-autoexit", "-loglevel", "error",
                   "-user_agent", ua]
            ff_h = dict(hdrs)
            if referrer:
                ff_h.setdefault("Referer", referrer)
            if ff_h:
                cmd += ["-headers", "".join("%s: %s\r\n" % (k, v)
                                            for k, v in ff_h.items())]
            cmd += ["-i", channel.url]
        extra = os.environ.get("VOIDCAST_MPV_EXTRA", "")
        if extra and be == "mpv":
            cmd += shlex.split(extra)
        env = dict(os.environ)
        env.pop("SDL_VIDEODRIVER", None)
        env.pop("VOIDCAST_FB", None)
        try:
            with open(mlog_path, "ab") as mlog:
                mlog.write(("\n=== %s ===\n" % channel.name)
                           .encode("utf-8", "replace"))
                proc = subprocess.Popen(cmd, stdout=mlog, stderr=mlog, env=env)
        except OSError as e:
            self.last_error = str(e)
            return RESULT_ERROR
        code = self._control_loop(proc, sock_path)
        self.overlay_mode = None
        self._toast_text = None
        if code not in (0, 4, 20, 21, 22, 30) and code >= 0:
            self.last_error = i18n.t("pl.err.exit", code,
                                     self._log_tail(mlog_path))
        if code == 20: return RESULT_NEXT
        if code == 21: return RESULT_PREV
        if code == 22: return RESULT_FAV
        if code == 30: return RESULT_BG
        if code < 0: return RESULT_BACK
        if code not in (0, 4): return RESULT_ERROR
        return RESULT_BACK

    def _log_tail(self, path, n=2):
        try:
            with open(path, "rb") as f:
                lines = f.read()[-2000:].decode("utf-8", "replace").splitlines()
            lines = [ln.strip() for ln in lines if ln.strip()]
            return " | ".join(lines[-n:])
        except OSError:
            return ""

    def _ipc(self, conn, *args):
        if conn is None:
            return False
        try:
            conn.sendall((json.dumps({"command": list(args)}) + "\n")
                         .encode("utf-8"))
            return True
        except OSError:
            return False

    # ---------- ASS helpers ----------
    def _rect(self, x, y, w, h, alpha="A0"):
        return (r"{\an7\pos(%d,%d)\p1\c&H000000&\alpha&H%s&}"
                r"m 0 0 l %d 0 l %d %d l 0 %d{\p0}"
                % (x, y, alpha, w, w, h, h))

    def _text(self, x, y, s, size=12, color=_C_WHITE, bold=False):
        s = "" if s is None else str(s)
        s = s.replace("{", "(").replace("}", ")").replace("\\", "/")
        b = r"\b1" if bold else r"\b0"
        return (r"{\an7\pos(%d,%d)\fs%d%s\c%s\3c&H000000&\bord2\shad0}%s"
                % (x, y, size, b, color, s))

    def _bar(self, x, y, w, h, pct):
        pct = max(0.0, min(1.0, pct))
        out = self._rect(x, y, w, h, alpha="40")
        fw = int(w * pct)
        if fw > 0:
            out += (r"{\an7\pos(%d,%d)\p1\c%s\alpha&H00&}"
                    r"m 0 0 l %d 0 l %d %d l 0 %d{\p0}"
                    % (x, y, _C_GREEN, fw, fw, h - 2, h - 2))
        return out

    # ---------- overlay state ----------
    def _toggle_details(self, conn):
        if self.overlay_mode == "details":
            self.overlay_mode = None
        else:
            self.overlay_mode = "details"
            self._details_sel = 0
        self._show_until = 0
        self._render(conn)

    def _toggle_bg_panel(self, conn):
        if self.overlay_mode == "bg":
            self.overlay_mode = None
        else:
            self.overlay_mode = "bg"
        self._show_until = 0
        self._render(conn)

    def _vol(self, conn, delta):
        if conn is None: return
        self._volume = max(0, min(130, self._volume + delta))
        self._ipc(conn, "set", "volume", self._volume)
        self._toast("VOL %d%%" % self._volume, 1.5)
        self._render(conn)

    def _seek(self, conn, delta):
        self._ipc(conn, "seek", delta)
        self._toast("%s %ds" % ("<<" if delta < 0 else ">>", abs(delta)), 1.2)
        self._render(conn)

    def _toast(self, text, ttl=1.5):
        self._toast_text = text
        self._toast_until = time.time() + ttl

    def _render(self, conn):
        if conn is None: return
        now = time.time()
        if self._show_until and now >= self._show_until:
            self.overlay_mode = None
            self._show_until = 0
        if self._toast_until and now >= self._toast_until:
            self._toast_text = None
            self._toast_until = 0
        if not self.overlay_mode and not self._toast_text:
            if self._last_ass:
                self._ipc(conn, "osd-overlay", 1, "none", "")
                self._last_ass = ""
            return
        ass = self._build_ass()
        if ass != self._last_ass:
            self._ipc(conn, "osd-overlay", 1, "ass-events", ass, 0, 0, 0, 0,
                      "no", "no")
            self._last_ass = ass

    def _build_ass(self):
        parts = []
        ctx = self._ctx or {}
        name = ctx.get("name", "?")
        group = ctx.get("group", "")
        idx = ctx.get("index", 0)
        total = ctx.get("total", 0)
        epg_now = ctx.get("epg_now", "")
        epg_next = ctx.get("epg_next", "")
        epg_list = ctx.get("epg_list", []) or []

        # ---- header (details + bg panels) ----
        if self.overlay_mode in ("details", "bg"):
            parts.append(self._rect(0, 0, 640, 64, alpha="A0"))
            badge = ("#%d/%d" % (idx + 1, total)) if total else ""
            if badge:
                parts.append(self._text(8, 4, badge, 10, _C_YEL))
            parts.append(self._text(8, 18, name[:34], 18, _C_WHITE, True))
            if group:
                parts.append(self._text(8, 42, group, 11, _C_DIM))
            if epg_now:
                parts.append(self._text(250, 4, "NOW", 10, _C_GREEN, True))
                parts.append(self._text(250, 18, epg_now[:34], 13, _C_WHITE))
            if epg_next:
                parts.append(self._text(250, 42, "NEXT", 10, _C_YEL, True))
                parts.append(self._text(300, 42, epg_next[:32], 11, _C_DIM))

        # ---- details panel ----
        if self.overlay_mode == "details":
            parts.append(self._rect(40, 76, 560, 336, alpha="80"))
            parts.append(self._text(56, 84, "CHANNEL DETAILS", 13, _C_CRIM, True))
            y = 108
            parts.append(self._text(56, y, "Name:", 11, _C_YEL))
            parts.append(self._text(120, y, name[:52], 11, _C_WHITE))
            y += 18
            parts.append(self._text(56, y, "Group:", 11, _C_YEL))
            parts.append(self._text(120, y, (group or "-")[:52], 11, _C_WHITE))
            y += 24
            parts.append(self._text(56, y, "PROGRAMMES", 12, _C_CRIM, True))
            y += 16
            vis = 8
            n = len(epg_list)
            if n:
                first = max(0, min(self._details_sel - vis // 2, n - vis))
                for k in range(first, min(first + vis, n)):
                    it = epg_list[k]
                    if isinstance(it, (tuple, list)):
                        p_start, p_title = it[0], it[1]
                    else:
                        p_start = getattr(it, "start", 0)
                        p_title = getattr(it, "title", "?")
                    sel = (k == self._details_sel)
                    mark = "> " if sel else "  "
                    try:
                        tm = time.strftime("%H:%M", time.localtime(p_start))
                    except Exception:
                        tm = "--:--"
                    col = _C_GREEN if sel else _C_DIM
                    parts.append(self._text(56, y,
                        "%s%s  %s" % (mark, tm, str(p_title)[:50]),
                        11, col))
                    y += 16
            else:
                parts.append(self._text(56, y, "(no EPG available)", 11, _C_FAINT))
            parts.append(self._text(56, 380,
                "dpad: navigate  ·  SELECT: close  ·  M: bg panel",
                10, _C_FAINT))

        # ---- background manager panel ----
        if self.overlay_mode == "bg":
            parts.append(self._rect(120, 100, 400, 280, alpha="40"))
            parts.append(self._text(140, 112, "BACKGROUND PLAYBACK",
                                    14, _C_CRIM, True))
            parts.append(self._text(140, 148, "▶ " + name[:40], 13, _C_WHITE))
            parts.append(self._text(140, 174,
                "Keep this stream playing as audio while you", 10, _C_DIM))
            parts.append(self._text(140, 188,
                "browse the app UI.", 10, _C_DIM))
            parts.append(self._text(140, 226,
                "[X]  Return to app  ·  background audio", 12, _C_GREEN))
            parts.append(self._text(140, 254,
                "[SELECT]  Channel details", 12, _C_YEL))
            parts.append(self._text(140, 282,
                "[B]  Stop playback and return to app", 12, _C_YEL))
            parts.append(self._text(140, 316,
                "[M]  Close this panel", 12, _C_DIM))

        # ---- toast ----
        if self._toast_text:
            parts.append(self._rect(200, 200, 240, 56, alpha="60"))
            parts.append(self._text(210, 208, self._toast_text, 16, _C_WHITE, True))
            if self._toast_text.startswith("VOL "):
                try:
                    pct = int(self._toast_text.split("%")[0].split()[-1]) / 100.0
                except Exception:
                    pct = 0
                parts.append(self._bar(210, 236, 220, 10, pct))
        return "\n".join(parts)

    # ---------- recorder ----------
    def _toggle_record(self, conn):
        if recorder.is_active():
            name = recorder.stop()
            if name:
                self._toast("REC saved", 2.5)
        else:
            name = self._rec_name or "channel"
            ok, msg = recorder.start(self._channel.url if self._channel else "",
                                      name,
                                      self.cfg.get("rec_dir",
                                                   "/mnt/mmc/MUOS/voidcast"),
                                      self.cfg.get("user_agent", ""))
            self._toast("REC" if ok else "REC FAIL", 2.5)
        self._render(conn)

    # ---------- control loop ----------
    def _control_loop(self, proc, sock_path):
        started_here = False
        if not evinput.active():
            started_here = evinput.start()
        conn = None
        last_hat = (0, 0)
        try:
            while proc.poll() is None:
                if conn is None and sock_path and os.path.exists(sock_path):
                    try:
                        c = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                        c.settimeout(0.3)
                        c.connect(sock_path)
                        conn = c
                    except OSError:
                        conn = None
                now = time.time()
                expired = False
                if self._show_until and now >= self._show_until:
                    self._show_until = 0
                    if self.overlay_mode == "main":
                        self.overlay_mode = None
                    expired = True
                if self._toast_until and now >= self._toast_until:
                    self._toast_until = 0
                    self._toast_text = None
                    expired = True
                if expired and conn is not None:
                    self._render(conn)

                if evinput.active():
                    for btn in evinput.poll():
                        if btn == "A":
                            self._ipc(conn, "cycle", "pause")
                            self._paused = not self._paused
                            self._render(conn)
                        elif btn == "B":
                            if not self._ipc(conn, "quit", 0):
                                proc.terminate()
                        elif btn == "Y":
                            self._ipc(conn, "quit", 22)
                        elif btn == "VOL-":
                            self._vol(conn, -5)
                        elif btn == "VOL+":
                            self._vol(conn, 5)
                        elif btn == "X":
                            if self.overlay_mode == "bg":
                                self._ipc(conn, "quit", 30)
                            else:
                                self._ipc(conn, "cycle", "mute")
                                self._toast("MUTE", 1.2)
                                self._render(conn)
                        elif btn == "L1":
                            self._ipc(conn, "add", "brightness", -5)
                        elif btn == "R1":
                            self._ipc(conn, "add", "brightness", 5)
                        elif btn == "L2":
                            self._ipc(conn, "add", "contrast", -5)
                        elif btn == "R2":
                            self._ipc(conn, "add", "contrast", 5)
                        elif btn == "SELECT":
                            self._toggle_details(conn)
                        elif btn == "START":
                            self._toggle_record(conn)
                        elif btn == "MENU":
                            self._toggle_bg_panel(conn)
                    hat = evinput.hat()
                    if hat != last_hat:
                        hx, hy = hat
                        if self.overlay_mode == "details":
                            n = len(self._ctx.get("epg_list", []) or [])
                            if hy > 0:
                                self._details_sel = max(0, self._details_sel - 1)
                            elif hy < 0:
                                self._details_sel = min(max(0, n - 1),
                                                        self._details_sel + 1)
                            self._render(conn)
                        else:
                            if hy > 0:
                                self._ipc(conn, "quit", 20)
                            elif hy < 0:
                                self._ipc(conn, "quit", 21)
                            elif hx < 0:
                                self._seek(conn, -30)
                            elif hx > 0:
                                self._seek(conn, 30)
                        last_hat = hat
                time.sleep(0.05)
        finally:
            if conn is not None:
                try: conn.close()
                except OSError: pass
            if started_here:
                evinput.stop()
            if sock_path:
                try: os.remove(sock_path)
                except OSError: pass
        return proc.returncode
