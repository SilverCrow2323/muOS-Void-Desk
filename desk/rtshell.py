# -*- coding: utf-8 -*-
# ============================================================================
#  VOIDDESK // rtshell — motore del terminale leggero Rt:Shell.
#  PTY vera sull'host (niente chroot, niente X, niente window manager:
#  e' proprio quello il motivo per cui il terminale "vero" e' lento ad
#  aprirsi) + un interprete ANSI/VT100 minimo ma robusto per i casi
#  davvero comuni: colori SGR, movimento cursore, cancellazione.
# ============================================================================
import fcntl
import os
import pty
import re
import select
import struct
import termios


ANSI_COLORS = [
    (0, 0, 0), (205, 0, 0), (0, 205, 0), (205, 205, 0),
    (0, 0, 238), (205, 0, 205), (0, 205, 205), (229, 229, 229),
]
ANSI_BRIGHT = [
    (127, 127, 127), (255, 0, 0), (0, 255, 0), (255, 255, 0),
    (92, 92, 255), (255, 0, 255), (0, 255, 255), (255, 255, 255),
]


class Cell:
    __slots__ = ("ch", "fg", "bg", "bold")

    def __init__(self, ch=" ", fg=None, bg=None, bold=False):
        self.ch = ch
        self.fg = fg
        self.bg = bg
        self.bold = bold


class TermBuffer:
    """Griglia di celle cols x rows, con un interprete ANSI/VT100 che
    capisce le sequenze davvero comuni: SGR (colori/grassetto),
    posizionamento cursore, cancellazione riga/schermo, wrap a fine
    riga. Non e' un emulatore completo -- e' quello che serve per una
    shell interattiva vera, non per un replay di terminfo esoterico."""

    ESC_CSI = re.compile(r"\x1b\[([0-9;?]*)([A-Za-z@])")

    def __init__(self, cols, rows):
        self.cols = cols
        self.rows = rows
        self.grid = [[Cell() for _ in range(cols)] for _ in range(rows)]
        self.cx = 0
        self.cy = 0
        self.fg = None
        self.bg = None
        self.bold = False
        self.dirty = True
        self._buf = b""

    def resize(self, cols, rows):
        newgrid = [[Cell() for _ in range(cols)] for _ in range(rows)]
        for y in range(min(rows, self.rows)):
            for x in range(min(cols, self.cols)):
                newgrid[y][x] = self.grid[y][x]
        self.grid = newgrid
        self.cols, self.rows = cols, rows
        self.cx = min(self.cx, cols - 1)
        self.cy = min(self.cy, rows - 1)
        self.dirty = True

    def _scroll_up(self, n=1):
        for _ in range(n):
            self.grid.pop(0)
            self.grid.append([Cell() for _ in range(self.cols)])

    def _put_char(self, ch):
        if self.cx >= self.cols:
            self.cx = 0
            self.cy += 1
            if self.cy >= self.rows:
                self._scroll_up()
                self.cy = self.rows - 1
        self.grid[self.cy][self.cx] = Cell(ch, self.fg, self.bg,
                                           self.bold)
        self.cx += 1

    def _sgr(self, params):
        if not params:
            params = [0]
        i = 0
        while i < len(params):
            p = params[i]
            if p == 0:
                self.fg = self.bg = None
                self.bold = False
            elif p == 1:
                self.bold = True
            elif p == 22:
                self.bold = False
            elif 30 <= p <= 37:
                self.fg = ANSI_COLORS[p - 30]
            elif p == 39:
                self.fg = None
            elif 40 <= p <= 47:
                self.bg = ANSI_COLORS[p - 40]
            elif p == 49:
                self.bg = None
            elif 90 <= p <= 97:
                self.fg = ANSI_BRIGHT[p - 90]
            elif 100 <= p <= 107:
                self.bg = ANSI_BRIGHT[p - 100]
            elif p == 38 and i + 1 < len(params) and \
                    params[i + 1] == 5 and i + 2 < len(params):
                self.fg = _xterm256(params[i + 2])
                i += 2
            elif p == 48 and i + 1 < len(params) and \
                    params[i + 1] == 5 and i + 2 < len(params):
                self.bg = _xterm256(params[i + 2])
                i += 2
            i += 1

    def feed(self, data):
        """Digerisce byte grezzi dal PTY, aggiornando la griglia."""
        self._buf += data
        try:
            text = self._buf.decode("utf-8")
            self._buf = b""
        except UnicodeDecodeError as e:
            text = self._buf[:e.start].decode("utf-8", errors="replace")
            self._buf = self._buf[e.start:]
            if len(self._buf) > 4:
                text += self._buf.decode("utf-8", errors="replace")
                self._buf = b""
        i = 0
        n = len(text)
        while i < n:
            ch = text[i]
            if ch == "\x1b":
                m = self.ESC_CSI.match(text, i)
                if m:
                    self._csi(m.group(1), m.group(2))
                    i = m.end()
                    continue
                else:
                    i += 1
                    continue
            elif ch == "\r":
                self.cx = 0
            elif ch == "\n":
                self.cy += 1
                if self.cy >= self.rows:
                    self._scroll_up()
                    self.cy = self.rows - 1
            elif ch == "\b":
                self.cx = max(0, self.cx - 1)
            elif ch == "\t":
                self.cx = min(self.cols - 1, (self.cx // 8 + 1) * 8)
            elif ch == "\x07":
                pass
            elif ord(ch) >= 0x20:
                self._put_char(ch)
            i += 1
        self.dirty = True

    def _csi(self, params_s, final):
        parts = params_s.split(";") if params_s else []
        params = [int(p) if p.isdigit() else 0 for p in parts]
        if final == "m":
            self._sgr(params)
        elif final == "H" or final == "f":
            row = (params[0] if params and params[0] else 1) - 1
            col = (params[1] if len(params) > 1 and params[1]
                  else 1) - 1
            self.cy = max(0, min(self.rows - 1, row))
            self.cx = max(0, min(self.cols - 1, col))
        elif final == "A":
            self.cy = max(0, self.cy - (params[0] if params else 1))
        elif final == "B":
            self.cy = min(self.rows - 1,
                          self.cy + (params[0] if params else 1))
        elif final == "C":
            self.cx = min(self.cols - 1,
                          self.cx + (params[0] if params else 1))
        elif final == "D":
            self.cx = max(0, self.cx - (params[0] if params else 1))
        elif final == "J":
            mode = params[0] if params else 0
            if mode == 2 or mode == 3:
                self.grid = [[Cell() for _ in range(self.cols)]
                            for _ in range(self.rows)]
            elif mode == 0:
                for x in range(self.cx, self.cols):
                    self.grid[self.cy][x] = Cell()
                for y in range(self.cy + 1, self.rows):
                    self.grid[y] = [Cell() for _ in range(self.cols)]
            elif mode == 1:
                for x in range(0, self.cx + 1):
                    self.grid[self.cy][x] = Cell()
                for y in range(0, self.cy):
                    self.grid[y] = [Cell() for _ in range(self.cols)]
        elif final == "K":
            mode = params[0] if params else 0
            if mode == 0:
                for x in range(self.cx, self.cols):
                    self.grid[self.cy][x] = Cell()
            elif mode == 1:
                for x in range(0, self.cx + 1):
                    self.grid[self.cy][x] = Cell()
            elif mode == 2:
                self.grid[self.cy] = [Cell() for _ in range(self.cols)]
        # le altre sequenze (save/restore cursore, modi privati '?',
        # eccetera) vengono riconosciute e scartate senza errori: non
        # servono per una shell interattiva normale


def _xterm256(n):
    if n < 8:
        return ANSI_COLORS[n]
    if n < 16:
        return ANSI_BRIGHT[n - 8]
    if n < 232:
        n -= 16
        r, g, b = n // 36, (n // 6) % 6, n % 6
        scale = lambda v: 0 if v == 0 else 55 + v * 40
        return (scale(r), scale(g), scale(b))
    v = 8 + (n - 232) * 10
    return (v, v, v)


def render_term(surface, font, buf, x0, y0, cell_w, cell_h, fg_default,
                bg_default, cursor_on=True, cursor_blink=True,
                row_start=0, row_count=None):
    """Disegna il buffer su una superficie pygame: ogni carattere in
    una cella a larghezza fissa (il font non e' monospace, quindi lo
    centro nella cella invece di fidarmi della sua avanzata naturale).
    row_start/row_count mostrano solo una porzione del buffer (le
    ultime righe, tipicamente), senza bisogno di ridimensionare la
    PTY quando cambia lo spazio disponibile a schermo."""
    import pygame
    import time as _time
    rows = buf.grid[row_start:row_start + row_count] if row_count \
        else buf.grid[row_start:]
    for y, row in enumerate(rows):
        py = y0 + y * cell_h
        for x, cell in enumerate(row):
            px = x0 + x * cell_w
            bg = cell.bg or bg_default
            if bg != bg_default:
                pygame.draw.rect(surface, bg, (px, py, cell_w, cell_h))
            if cell.ch != " ":
                fg = cell.fg or fg_default
                img = font.render(cell.ch, True, fg)
                cx = px + (cell_w - img.get_width()) // 2
                surface.blit(img, (cx, py))
    cursor_row = buf.cy - row_start
    if cursor_on and 0 <= cursor_row < len(rows) and \
            (not cursor_blink or int(_time.time() * 2) % 2):
        cx0 = x0 + buf.cx * cell_w
        cy0 = y0 + cursor_row * cell_h
        pygame.draw.rect(surface, fg_default,
                         (cx0, cy0, cell_w, cell_h), 1)


class PtySession:
    """Sessione PTY vera: bash sull'host, letture non bloccanti."""

    def __init__(self, shell="/bin/bash", cols=80, rows=30, cwd=None):
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            os.chdir(cwd or os.path.expanduser("~"))
            os.environ["TERM"] = "xterm-256color"
            os.environ["COLUMNS"] = str(cols)
            os.environ["LINES"] = str(rows)
            try:
                os.execvp(shell, [shell])
            except OSError:
                os.execvp("/bin/sh", ["/bin/sh"])
            os._exit(1)
        self.resize(cols, rows)
        self.alive = True

    def resize(self, cols, rows):
        try:
            winsz = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self.fd, termios.TIOCSWINSZ, winsz)
        except OSError:
            pass

    def read_nonblock(self, timeout=0.0):
        try:
            r, _w, _e = select.select([self.fd], [], [], timeout)
        except (OSError, ValueError):
            self.alive = False
            return b""
        if not r:
            return b""
        try:
            data = os.read(self.fd, 4096)
            if not data:
                self.alive = False
            return data
        except OSError:
            self.alive = False
            return b""

    def write(self, data):
        if not self.alive:
            return
        try:
            os.write(self.fd, data if isinstance(data, bytes) else
                     data.encode("utf-8"))
        except OSError:
            self.alive = False

    def close(self):
        try:
            os.close(self.fd)
        except OSError:
            pass
        try:
            os.kill(self.pid, 15)
        except OSError:
            pass
        self.alive = False
