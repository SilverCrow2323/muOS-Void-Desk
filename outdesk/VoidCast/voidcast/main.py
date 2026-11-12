# outdesk/VoidCast/voidcast/main.py
# -*- coding: utf-8 -*-
# ============================================================================
#  VOIDCAST v1.0 — SPDW IPTV SUITE per muOS / RG35XX H (640x480)
#  "Il segnale attraversa il VOID. Tu premi solo A." — IR Minoru⁶
# ============================================================================
#  Struttura: App = loop pygame + stack di Screen. Ogni Screen implementa
#  on_button(btn) e draw(surf). I lavori lenti (download liste/EPG) passano
#  da App.busy() che disegna un overlay di caricamento.
# ============================================================================

import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame  # noqa: E402

from core import config as C            # noqa: E402
from core import epg as epg_mod          # noqa: E402
from core import countries as countries_mod  # noqa: E402
from core import logos as logos_mod      # noqa: E402
from core import m3u                     # noqa: E402
from core import evinput                 # noqa: E402
from core.addons import AddonManager     # noqa: E402
from core import i18n                     # noqa: E402
from core.bgplay import BgPlayer          # noqa: E402
from ui.anim import Anim                  # noqa: E402
from core.config import Config           # noqa: E402
from core.player import (Player, RESULT_BACK, RESULT_ERROR, RESULT_FAV,  # noqa: E402
                         RESULT_NEXT, RESULT_PREV, RESULT_BG)
from ui import ui                        # noqa: E402
from ui.ui import (BG, BG_PANEL, FG, FG_DIM, FG_FAINT, ERR, OK, H, W,  # noqa: E402
                   ChannelGrid, GuideView, MenuList, OnScreenKeyboard,
                   Theme, Toast)

FPS = 30
_ENV_BTN = {}  # raw -> logico, derivato da SDL_GAMECONTROLLERCONFIG (muOS)


def _parse_env_gamepad():
    src = os.environ.get("SDL_GAMECONTROLLERCONFIG", "")
    names = {"a": "A", "b": "B", "x": "X", "y": "Y",
             "leftshoulder": "L1", "rightshoulder": "R1",
             "lefttrigger": "L2", "righttrigger": "R2",
             "start": "START", "back": "SELECT"}
    out = {}
    for part in src.split(","):
        if ":" not in part:
            continue
        k, v = part.split(":", 1)
        k = k.strip()
        v = v.strip()
        if k in names and v.startswith("b") and v[1:].isdigit():
            out[int(v[1:])] = names[k]
    return out


_ENV_BTN.update(_parse_env_gamepad())
KEYMAP_KB = {  # fallback tastiera per test desktop
    pygame.K_UP: "UP", pygame.K_DOWN: "DOWN",
    pygame.K_LEFT: "LEFT", pygame.K_RIGHT: "RIGHT",
    pygame.K_z: "A", pygame.K_x: "B", pygame.K_a: "X", pygame.K_s: "Y",
    pygame.K_q: "L1", pygame.K_w: "R1",
    pygame.K_RETURN: "START", pygame.K_RSHIFT: "SELECT",
    pygame.K_ESCAPE: "B",
}


def log(msg):
    try:
        with open(C.LOG_PATH, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%H:%M:%S"), msg))
    except OSError:
        pass


# ============================================================================
#  SCREENS
# ============================================================================
class Screen(object):
    title = "?"
    hints = [("A", "ok"), ("B", "indietro")]

    def __init__(self, app):
        self.app = app
        self.t = app.theme

    def on_button(self, btn):
        if btn == "B":
            self.app.pop()

    def draw(self, surf):
        pass


class HomeScreen(Screen):
    title = "VOIDCAST"

    def __init__(self, app):
        super().__init__(app)
        self.menu = MenuList(self.t, row_h=48, top=88)
        self._exit_at = 0
        self.refresh()

    def refresh(self):
        apl = self.app.cfg.active_playlist()
        nch = len(self.app.playlist.channels) if self.app.playlist else 0
        nfav = len(self.app.cfg.get("favorites", []))
        npl = len(self.app.cfg.playlists())
        try:
            nepg = len(epg_mod.collect_epg_urls(self.app.cfg,
                                                self.app.playlist))
        except Exception:
            nepg = 0
        self.menu.items = [
            (i18n.t("home.channels"),
             i18n.t("home.channels_sub",
                    apl["name"] if apl else "—", nch, nfav),
             "", "", "play"),
            (i18n.t("home.sources"),
             i18n.t("home.sources_sub", npl, nepg),
             "", "", "playlist"),
            (i18n.t("home.settings"), i18n.t("home.settings_sub"),
             "", "", "settings"),
            (i18n.t("home.exit"), i18n.t("home.exit_sub"),
             "", "", "exit"),
        ]

    def on_button(self, btn):
        if btn == "UP":
            self.menu.move(-1)
        elif btn == "DOWN":
            self.menu.move(1)
        elif btn == "A":
            i = self.menu.sel
            if i == 0:
                self.app.open_channels()
            elif i == 1:
                self.app.push(SourcesScreen(self.app))
            elif i == 2:
                self.app.push(SettingsScreen(self.app))
            elif i == 3:
                self.app.running = False
        elif btn == "B":
            now = time.time()
            if now - self._exit_at < 2.5:
                self.app.running = False
            else:
                self._exit_at = now
                self.app.toast(i18n.t("home.b_again_exit"))

    def draw(self, surf):
        self.t.header(surf, "VOIDCAST", C.APP_TAGLINE)
        self.refresh()
        self.menu.draw(surf)
        self.t.footer(surf, [("A", i18n.t("btn.open")),
                             ("B", i18n.t("home.exit"))])



class ProgrammeDetailsScreen(Screen):
    """Full details of a TV programme: times, duration, plot."""

    def __init__(self, app, ch, prog):
        super().__init__(app)
        self.ch = ch
        self.prog = prog

    def on_button(self, btn):
        if btn == "B":
            self.app.pop()
        elif btn == "A":
            self.app.pop()
            self.app.play_channel([self.ch], 0)

    def draw(self, surf):
        title = (self.prog.title or "?")
        self.t.header(surf, title[:30], self.ch.name[:30])
        y = 66
        now = time.time()
        is_live = self.prog.start <= now < self.prog.stop
        if is_live:
            pygame.draw.rect(surf, (100, 220, 120), (14, y, 100, 22),
                             border_radius=4)
            pygame.draw.circle(surf, (15, 15, 20), (24, y + 11), 4)
            self.t.text(surf, i18n.t("pl.details.live"), (34, y + 4),
                        self.t.f_small, (15, 15, 20))
            y += 32
        rows = [
            (i18n.t("pl.details.channel"), self.ch.name),
            (i18n.t("pl.details.start"),
             time.strftime("%Y-%m-%d  %H:%M",
                           time.localtime(self.prog.start))),
            (i18n.t("pl.details.stop"),
             time.strftime("%Y-%m-%d  %H:%M",
                           time.localtime(self.prog.stop))),
            (i18n.t("pl.details.duration"),
             "%d min" % max(1, int((self.prog.stop - self.prog.start) // 60))),
        ]
        for k, v in rows:
            self.t.text(surf, k.upper(), (14, y), self.t.f_small,
                        self.t.accent)
            self.t.text(surf, v, (120, y), self.t.f_small, FG,
                        maxw=W - 130)
            y += 22
        y += 8
        pygame.draw.line(surf, self.t.accent, (10, y), (W - 10, y), 1)
        y += 8
        self.t.text(surf, i18n.t("pl.details.plot").upper(), (14, y),
                    self.t.f_small, self.t.accent)
        y += 22
        plot = (self.prog.desc or "—").replace("\n", " ")
        line = ""
        for wd in plot.split():
            test = (line + " " + wd).strip()
            if self.t.f_small.size(test)[0] > W - 30:
                self.t.text(surf, line, (14, y), self.t.f_small, FG_DIM)
                y += 20
                if y > H - 50:
                    break
                line = wd
            else:
                line = test
        if line and y <= H - 50:
            self.t.text(surf, line, (14, y), self.t.f_small, FG_DIM)
        self.t.footer(surf, [("A", i18n.t("btn.play")),
                             ("B", i18n.t("btn.back"))])


class ChannelsScreen(Screen):
    """Vista canali unificata: list / grid / guide, cicla con SELECT."""

    def __init__(self, app, channels, label, mode=None):
        super().__init__(app)
        self.all_channels = channels
        self.label = label
        self.mode = mode or app.cfg.get("view_mode", "list")
        self.group_i = 0
        groups = ["*"]
        if app.cfg.get("favorites"):
            groups.append("__FAVS__")
        groups += (app.playlist.groups if app.playlist else [])
        self.groups = groups
        lg = app.cfg.get("last_group", "*")
        if lg in self.groups:
            self.group_i = self.groups.index(lg)
        self._rebuild()

    def _filtered(self):
        g = self.groups[self.group_i]
        if g == "*":
            return self.all_channels
        if g == "__FAVS__":
            favs = set(self.app.cfg.get("favorites", []))
            return [c for c in self.all_channels if c.url in favs]
        return [c for c in self.all_channels if c.group == g]

    def _rebuild(self):
        chans = self._filtered()
        self.channels = chans
        favs = set(self.app.cfg.get("favorites", []))
        use_logos = (self.app.logos
                     if self.app.cfg.get("show_logos", True) else None)
        self.menu = MenuList(self.t, row_h=40, top=64, bottom=H - 34,
                             logos=use_logos)
        self.menu.items = [(c.name, c.group,
                            "★" if c.url in favs else "", c.logo)
                           for c in chans]
        self.grid = ChannelGrid(self.t, chans, logos=use_logos)
        self.guide = GuideView(self.t, chans, logos=use_logos)

    def _sel(self):
        if self.mode == "grid":
            return self.grid.sel
        if self.mode == "guide":
            return self.guide.sel
        return self.menu.sel

    def current(self):
        if not self.channels:
            return None
        return self.channels[min(self._sel(), len(self.channels) - 1)]

    def on_button(self, btn):
        if btn == "X":
            self.app.push(SearchScreen(self.app))
            return
        if btn == "SELECT":
            order = ["list", "grid", "guide"]
            self.mode = order[(order.index(self.mode) + 1) % 3]
            self.app.cfg.set("view_mode", self.mode)
            return
        if btn in ("L1", "R1") and self.mode != "guide":
            self.group_i = (self.group_i + (1 if btn == "R1" else -1)) % len(self.groups)
            self.app.cfg.set("last_group", self.groups[self.group_i])
            self._rebuild()
            return
        if btn == "Y":
            ch = self.current()
            if ch:
                fav = self.app.cfg.toggle_favorite(ch.url)
                self.app.toast(i18n.t("ch.toast.fav_added" if fav else "ch.toast.fav_removed", ch.name))
                self._rebuild()
            return
        if btn == "START":
            ch = self.current()
            if ch:
                if self.mode == "guide":
                    prog = self.guide.current_prog(self.app.epg)
                    if prog:
                        self.app.push(ProgrammeDetailsScreen(
                            self.app, ch, prog))
                        return
                self.app.push(ChannelActionsScreen(self.app, ch))
            return
        if btn == "A":
            ch = self.current()
            if ch:
                self.app.play_channel(self.channels, self.channels.index(ch))
            return
        if btn == "B":
            self.app.pop()
            return
        # navigazione per modalità
        if self.mode == "list":
            if btn == "UP":
                self.menu.move(-1)
            elif btn == "DOWN":
                self.menu.move(1)
            elif btn == "LEFT":
                self.menu.page(-1)
            elif btn == "RIGHT":
                self.menu.page(1)
        elif self.mode == "grid":
            if btn == "UP":
                self.grid.move(0, -1)
            elif btn == "DOWN":
                self.grid.move(0, 1)
            elif btn == "LEFT":
                self.grid.move(-1, 0)
            elif btn == "RIGHT":
                self.grid.move(1, 0)
        else:  # guide
            if btn == "UP":
                self.guide.move(-1)
            elif btn == "DOWN":
                self.guide.move(1)
            elif btn == "LEFT":
                self.guide.nav_prog(-1, self.app.epg)
            elif btn == "RIGHT":
                self.guide.nav_prog(1, self.app.epg)

    def draw(self, surf):
        g = self.groups[self.group_i]
        if g == "*":
            glabel = i18n.t("ch.all")
        elif g == "__FAVS__":
            glabel = i18n.t("ch.favs_group")
        else:
            glabel = g
        sub = i18n.t("ch.sub", self.label, glabel, len(self.channels))
        self.t.header(surf, {"list": i18n.t("ch.title.list"),
                             "grid": i18n.t("ch.title.grid"),
                             "guide": i18n.t("ch.title.guide")}[self.mode], sub)
        if self.mode == "list":
            self.menu.draw(surf)
            ch = self.current()
            if ch and self.app.epg:
                cur, _ = self.app.epg.now_next(ch)
                if cur:
                    self.t.text(surf, i18n.t("ch.now_prefix") + cur.title, (12, H - 52),
                                self.t.f_small, FG_DIM, maxw=W - 24)
        elif self.mode == "grid":
            self.grid.draw(surf, self.app.epg)
        else:
            self.guide.draw(surf, self.app.epg)
        if self.mode == "guide":
            self.t.footer(surf, [("A", i18n.t("btn.play")),
                                 ("Y", i18n.t("btn.fav")),
                                 ("◄►", i18n.t("btn.epg_nav")),
                                 ("START", i18n.t("btn.details")),
                                 ("SELECT", i18n.t("btn.view")),
                                 ("L1/R1", i18n.t("btn.group"))])
        else:
            self.t.footer(surf, [("A", i18n.t("btn.play")),
                                 ("Y", i18n.t("btn.fav")),
                                 ("X", i18n.t("btn.search")),
                                 ("START", i18n.t("btn.actions")),
                                 ("SELECT", i18n.t("btn.view")),
                                 ("L1/R1", i18n.t("btn.group"))])


class ChannelActionsScreen(Screen):
    """Menu contestuale canale: play, fav, azioni addon, info."""

    def __init__(self, app, channel):
        super().__init__(app)
        self.ch = channel
        self.menu = MenuList(self.t, row_h=36, top=64)
        self.actions = []
        self._build()

    def _build(self):
        fav = self.ch.url in self.app.cfg.get("favorites", [])
        items = [(i18n.t("act.play"), "", ""),
                 (i18n.t("act.fav_remove") if fav else i18n.t("act.fav_add"),
                  "", "")]
        self.actions = ["play", "fav"]
        for addon_name, act in self.app.addons.channel_actions():
            items.append((act["label"], i18n.t("tools.addon_prefix", addon_name), "⚒"))
            self.actions.append(act)
        items.append((i18n.t("act.info"), "", ""))
        self.actions.append("info")
        self.menu.items = items

    def on_button(self, btn):
        if btn == "UP":
            self.menu.move(-1)
        elif btn == "DOWN":
            self.menu.move(1)
        elif btn == "B":
            self.app.pop()
        elif btn == "A":
            act = self.actions[self.menu.sel]
            if act == "play":
                self.app.pop()
                self.app.play_channel([self.ch], 0)
            elif act == "fav":
                self.app.cfg.toggle_favorite(self.ch.url)
                self.app.pop()
            elif act == "info":
                self.app.push(ChannelInfoScreen(self.app, self.ch))
            else:
                self.app.current_channel = self.ch
                try:
                    act["action"](self.app.addons.api)
                except Exception as e:  # noqa: BLE001
                    self.app.toast(i18n.t("tools.ko", e), ok=False)
                self._build()

    def draw(self, surf):
        self.t.header(surf, self.ch.name[:30], self.ch.group)
        self.menu.draw(surf)
        self.t.footer(surf, [("A", i18n.t("btn.execute")),
                             ("B", i18n.t("btn.back"))])


class ChannelInfoScreen(Screen):
    def __init__(self, app, ch):
        super().__init__(app)
        self.ch = ch

    def draw(self, surf):
        self.t.header(surf, i18n.t("info.title"), self.ch.name[:34])
        y = 66
        rows = [(i18n.t("info.name"), self.ch.name),
                (i18n.t("info.group"), self.ch.group),
                ("tvg-id", self.ch.tvg_id or "—"),
                ("tvg-name", self.ch.tvg_name or "—"),
                ("URL", self.ch.url)]
        if self.app.epg:
            cur, nxt = self.app.epg.now_next(self.ch)
            rows.append((i18n.t("info.now"), cur.title if cur else "—"))
            rows.append((i18n.t("info.next"), nxt.title if nxt else "—"))
            if cur and cur.desc:
                rows.append((i18n.t("info.plot"), cur.desc[:220]))
        for k, v in rows:
            self.t.text(surf, k.upper(), (14, y), self.t.f_small, self.t.accent)
            # wrap grezzo
            maxw = W - 130
            words, line, yy = str(v).split(), "", y
            for wd in words:
                test = (line + " " + wd).strip()
                if self.t.f_small.size(test)[0] > maxw:
                    self.t.text(surf, line, (120, yy), self.t.f_small, FG)
                    yy += 18
                    line = wd
                else:
                    line = test
            self.t.text(surf, line, (120, yy), self.t.f_small, FG)
            y = yy + 24
        self.t.footer(surf, [("B", i18n.t("btn.back"))])


class SourcesScreen(Screen):
    """Hub per playlist ed EPG — le due sorgenti del segnale."""
    def __init__(self, app):
        super().__init__(app)
        self.menu = MenuList(self.t, row_h=44, top=72)

    def refresh(self):
        cfg = self.app.cfg
        pls = cfg.playlists()
        apl = cfg.active_playlist()
        auto = self.app.playlist.epg_urls if self.app.playlist else []
        manual = cfg.get("epg_manual_urls", [])
        ok = len(self.app.epg.sources_ok) if self.app.epg else 0
        err = len(self.app.epg.sources_err) if self.app.epg else 0
        self.menu.items = [
            (i18n.t("src.playlists"),
             i18n.t("src.playlists_sub",
                    len(pls), apl["name"] if apl else "—"),
             "", "", "playlist"),
            (i18n.t("src.epg"),
             i18n.t("src.epg_sub",
                    len(auto), len(manual), ok, err),
             "", "", "epg"),
        ]

    def on_button(self, btn):
        if btn == "UP": self.menu.move(-1)
        elif btn == "DOWN": self.menu.move(1)
        elif btn == "B": self.app.pop()
        elif btn == "A":
            if self.menu.sel == 0:
                self.app.push(PlaylistScreen(self.app))
            elif self.menu.sel == 1:
                self.app.push(EpgScreen(self.app))

    def draw(self, surf):
        self.refresh()
        self.t.header(surf, i18n.t("src.title"), i18n.t("src.sub"))
        self.menu.draw(surf)
        self.t.footer(surf, [("A", i18n.t("btn.open")),
                             ("B", i18n.t("btn.back"))])


class PlaylistScreen(Screen):
    def __init__(self, app):
        super().__init__(app)
        self.menu = MenuList(self.t, row_h=38, top=64)
        self._rebuild()

    def _rebuild(self):
        cfg = self.app.cfg
        items = []
        active = cfg.get("active_playlist")
        for p in cfg.playlists():
            items.append((p["name"], p["source"],
                          i18n.t("pl.active") if p["id"] == active else ""))
        items.append((i18n.t("pl.add_url"), i18n.t("pl.add_url_sub"), ""))
        items.append((i18n.t("pl.add_file"), i18n.t("pl.add_file_sub"), ""))
        items.append((i18n.t("pl.preset"), i18n.t("pl.preset_sub"), ""))
        items.append((i18n.t("pl.reload"), i18n.t("pl.reload_sub"), ""))
        self.menu.items = items
        self.n_pl = len(cfg.playlists())

    def on_button(self, btn):
        if btn == "UP":
            self.menu.move(-1)
        elif btn == "DOWN":
            self.menu.move(1)
        elif btn == "B":
            self.app.pop()
        elif btn == "X":
            if self.menu.sel < self.n_pl:
                p = self.app.cfg.playlists()[self.menu.sel]
                self.app.cfg.remove_playlist(p["id"])
                self.app.toast(i18n.t("pl.deleted", p["name"]))
                self._rebuild()
        elif btn == "A":
            i = self.menu.sel
            if i < self.n_pl:
                p = self.app.cfg.playlists()[i]
                self.app.cfg.set("active_playlist", p["id"])
                self.app.reload_playlist()
                self._rebuild()
            elif i == self.n_pl:
                self.app.push(TextInputScreen(
                    self.app, i18n.t("pl.input_title"), "https://",
                    lambda url: self._add_url(url)))
            elif i == self.n_pl + 1:
                self.app.push(FileBrowserScreen(self.app, self._add_file))
            elif i == self.n_pl + 2:
                self.app.push(PresetScreen(self.app, self._rebuild))
            elif i == self.n_pl + 3:
                self.app.reload_playlist(force=True)

    def _add_url(self, url):
        name = url.rstrip("/").split("/")[-1] or "playlist"
        self.app.cfg.add_playlist(name, url, "url")
        self.app.reload_playlist()
        self._rebuild()

    def _add_file(self, path):
        self.app.cfg.add_playlist(os.path.basename(path), path, "file")
        self.app.reload_playlist()
        self._rebuild()

    def draw(self, surf):
        self.t.header(surf, i18n.t("pl.title"), i18n.t("pl.sub", self.n_pl))
        self.menu.draw(surf)
        self.t.footer(surf, [("A", i18n.t("btn.activate_open")),
                             ("X", i18n.t("btn.delete")),
                             ("B", i18n.t("btn.back"))])


class PresetScreen(Screen):
    """Preset lists: SPDW tv.m3u in testa, poi iptv-org, poi per paese."""

    def __init__(self, app, on_done):
        super().__init__(app)
        self.on_done = on_done
        self.menu = MenuList(self.t, row_h=38, top=64)
        self.entries = []
        self._rebuild()

    def _rebuild(self):
        # (kind, label, source, ptype, badge)
        self.entries = [
            ("spdw_tv", "SPDW Factory // ITALIA+",
             "presets/tv.m3u", "file", "◈"),
        ]
        for n, u in C.PRESET_PLAYLISTS:
            self.entries.append(("url", n, u, "url", ""))
        self.entries.append((
            "by_country",
            i18n.t("preset.by_country"),
            i18n.t("preset.by_country_sub", len(countries_mod.COUNTRIES)),
            None, "»",
        ))
        items = []
        for kind, name, source, ptype, badge in self.entries:
            if ptype == "file":
                sub = i18n.t("country.src_local") + source
            elif ptype == "url":
                sub = source
            else:
                sub = source  # già tradotto
            items.append((name, sub, badge))
        self.menu.items = items

    def on_button(self, btn):
        if btn == "UP":
            self.menu.move(-1)
        elif btn == "DOWN":
            self.menu.move(1)
        elif btn == "B":
            self.app.pop()
        elif btn == "A":
            kind, name, source, ptype, _ = self.entries[self.menu.sel]
            if kind == "by_country":
                self.app.push(CountryPresetScreen(self.app, self.on_done))
                return
            self.app.cfg.add_playlist(name, source, ptype)
            self.app.pop()
            self.app.reload_playlist()
            self.on_done()

    def draw(self, surf):
        self.t.header(surf, i18n.t("preset.title"), i18n.t("preset.sub"))
        self.menu.draw(surf)
        self.t.footer(surf, [("A", i18n.t("btn.add_activate")),
                             ("B", i18n.t("btn.back"))])



class CountryPresetScreen(Screen):
    """Country / category presets.
    Prefers local .m3u8 in presets/ when present, falls back to the
    iptv-org online URL for countries without a local file."""

    # COUNTRIES ISO code -> local file slug (only when they differ)
    _ALIASES = {
        "uk": "uk", "us": "usa", "kr": "korea", "tr": "turkey",
        "hk": "hong_kong", "cz": "czech_republic",
        "do": "dominican_republic", "fo": "faroe_islands",
        "tt": "trinidad", "ae": "united_arab_emirates",
        "mk": "north_macedonia", "ba": "bosnia_and_herzegovina",
        "kp": "north_korea",
    }

    def __init__(self, app, on_done):
        super().__init__(app)
        self.on_done = on_done
        self.menu = MenuList(self.t, row_h=34, top=64, bottom=H - 34)
        self.entries = []
        self._build()

    @staticmethod
    def _scan():
        presets_dir = os.path.join(C.ROOT_DIR, "presets")
        files = {}
        if os.path.isdir(presets_dir):
            for fn in os.listdir(presets_dir):
                if fn.startswith("playlist_") and fn.endswith(".m3u8"):
                    slug = fn[len("playlist_"):-len(".m3u8")]
                    files[slug] = os.path.join(presets_dir, fn)
        return files

    def _slug(self, code, name):
        if code in self._ALIASES:
            return self._ALIASES[code]
        return (name or "").lower().replace(" ", "_").replace("-", "_")

    def _build(self):
        files = self._scan()
        items, entries = [], []
        used = set()
        locals_list, online_list = [], []

        for code, name, flag in countries_mod.COUNTRIES:
            slug = self._slug(code, name)
            lp = files.get(slug)
            if lp:
                used.add(slug)
                locals_list.append((code, name, flag, slug, lp))
            else:
                online_list.append((code, name, flag))

        # 1) Countries with a local file — instant load
        for code, name, flag, slug, lp in locals_list:
            items.append((name,
                          i18n.t("country.src_local") +
                          "presets/playlist_%s.m3u8" % slug,
                          code.upper()))
            entries.append((code, name, ("file", lp)))

        # 2) Countries without a local file — online fallback
        for code, name, flag in online_list:
            items.append((name,
                          i18n.t("country.src_online") +
                          "countries/%s.m3u" % code,
                          code.upper()))
            entries.append((code, name, ("url", countries_mod.URL_TPL % code)))

        # 3) Extra local files whose slug is not in COUNTRIES
        #    (greenland, spain_vod, usa_vod, ...)
        for slug in sorted(set(files) - used):
            if slug.startswith("zz_"):
                continue
            label = slug.replace("_", " ").title()
            items.append(("▸  %s" % label,
                          i18n.t("country.src_local") +
                          "presets/playlist_%s.m3u8" % slug,
                          "EXTRA"))
            entries.append((slug, label, ("file", files[slug])))

        # 4) Category presets (zz_news_*, zz_movies, zz_music_*, zz_vod_*, ...)
        for slug in sorted(s for s in files if s.startswith("zz_")):
            label = slug[3:].replace("_", " ").title()
            items.append(("◈  %s" % label,
                          i18n.t("country.src_local") +
                          "presets/playlist_%s.m3u8" % slug,
                          i18n.t("country.category")))
            entries.append((slug, label, ("file", files[slug])))

        self.menu.items = items
        self.entries = entries

    def on_button(self, btn):
        if btn == "B":
            self.app.pop()
        elif btn == "UP":
            self.menu.move(-1)
        elif btn == "DOWN":
            self.menu.move(1)
        elif btn == "LEFT":
            self.menu.page(-1)
        elif btn == "RIGHT":
            self.menu.page(1)
        elif btn == "A" and self.entries:
            code, name, src = self.entries[self.menu.sel]
            kind, value = src
            self.app.cfg.add_playlist("preset // %s" % name.upper(),
                                      value, kind)
            self.app.pop()
            self.app.pop()
            self.app.reload_playlist()
            self.on_done()

    def draw(self, surf):
        self.t.header(surf, i18n.t("country.title"),
                      "%d/%d" % (self.menu.sel + 1, len(self.menu.items)))
        self.menu.draw(surf)
        self.t.footer(surf, [("A", i18n.t("btn.add_activate")),
                             ("L/R", i18n.t("btn.page")),
                             ("B", i18n.t("btn.back"))])



class FileBrowserScreen(Screen):
    EXTS = (".m3u", ".m3u8")
    ROOTS = ["/mnt/mmc", "/mnt/sdcard", "/mnt/usb", os.path.expanduser("~")]

    def __init__(self, app, on_pick, path=None):
        super().__init__(app)
        self.on_pick = on_pick
        self.path = path
        self.menu = MenuList(self.t, row_h=32, top=64)
        self.entries = []
        self._list()

    def _list(self):
        entries = []
        if self.path is None:
            for r in self.ROOTS:
                if os.path.isdir(r):
                    entries.append((r, True))
        else:
            entries.append(("..", True))
            try:
                for name in sorted(os.listdir(self.path)):
                    if name.startswith("."):
                        continue
                    full = os.path.join(self.path, name)
                    if os.path.isdir(full):
                        entries.append((name, True))
                    elif name.lower().endswith(self.EXTS):
                        entries.append((name, False))
            except OSError:
                pass
        self.entries = entries
        self.menu.items = [("▸ " + n if d else "· " + n, "", "") for n, d in entries]
        self.menu.sel = 0

    def on_button(self, btn):
        if btn == "UP":
            self.menu.move(-1)
        elif btn == "DOWN":
            self.menu.move(1)
        elif btn == "LEFT":
            self.menu.page(-1)
        elif btn == "RIGHT":
            self.menu.page(1)
        elif btn == "B":
            self.app.pop()
        elif btn == "A" and self.entries:
            name, is_dir = self.entries[self.menu.sel]
            if name == "..":
                parent = os.path.dirname(self.path.rstrip("/"))
                self.path = parent if parent and parent != "/" else None
                self._list()
            elif is_dir:
                self.path = name if self.path is None else os.path.join(self.path, name)
                self._list()
            else:
                full = os.path.join(self.path, name)
                self.app.pop()
                self.on_pick(full)

    def draw(self, surf):
        self.t.header(surf, i18n.t("fb.title"), self.path or i18n.t("fb.roots"))
        self.menu.draw(surf)
        self.t.footer(surf, [("A", i18n.t("btn.open")),
                             ("B", i18n.t("btn.back"))])


class EpgScreen(Screen):
    def __init__(self, app):
        super().__init__(app)
        self.menu = MenuList(self.t, row_h=36, top=64)
        self._rebuild()

    def _rebuild(self):
        app = self.app
        auto = app.playlist.epg_urls if app.playlist else []
        manual = app.cfg.get("epg_manual_urls", [])
        ok = set(u.split(" [")[0] for u in (app.epg.sources_ok if app.epg else []))
        err = dict(app.epg.sources_err) if app.epg else {}
        items = []
        self.slots = []
        for u in auto:
            state = "✓" if u in ok else ("✗" if u in err else "…")
            items.append((u[:58], i18n.t("epg.auto") + err.get(u, ""), state))
            self.slots.append(("auto", u))
        for u in manual:
            state = "✓" if u in ok else ("✗" if u in err else "…")
            items.append((u[:58], i18n.t("epg.manual") + err.get(u, ""), state))
            self.slots.append(("manual", u))
        items.append((i18n.t("epg.add"), i18n.t("epg.add_sub"), ""))
        items.append((i18n.t("epg.reload"), i18n.t("epg.reload_sub"), ""))
        items.append((i18n.t("epg.toggle",
                      i18n.t("epg.on") if app.cfg.get("epg_use_playlist_sources")
                      else i18n.t("epg.off")),
                      i18n.t("epg.toggle_sub"), ""))
        self.menu.items = items
        self.slots += [("add", None), ("reload", None), ("toggle", None)]

    def on_button(self, btn):
        if btn == "UP":
            self.menu.move(-1)
        elif btn == "DOWN":
            self.menu.move(1)
        elif btn == "B":
            self.app.pop()
        elif btn == "X":
            kind, u = self.slots[self.menu.sel]
            if kind == "manual":
                urls = self.app.cfg.get("epg_manual_urls", [])
                urls.remove(u)
                self.app.cfg.set("epg_manual_urls", urls)
                self._rebuild()
        elif btn == "A":
            kind, _ = self.slots[self.menu.sel]
            if kind == "add":
                self.app.push(TextInputScreen(
                    self.app, i18n.t("epg.input_title"), "https://", self._add_url))
            elif kind == "reload":
                self.app.reload_epg(force=True)
                self._rebuild()
            elif kind == "toggle":
                cur = self.app.cfg.get("epg_use_playlist_sources", True)
                self.app.cfg.set("epg_use_playlist_sources", not cur)
                self.app.reload_epg()
                self._rebuild()

    def _add_url(self, url):
        urls = self.app.cfg.get("epg_manual_urls", [])
        if url not in urls:
            urls.append(url)
        self.app.cfg.set("epg_manual_urls", urls)
        self.app.reload_epg(force=True)
        self._rebuild()

    def draw(self, surf):
        n = len(self.app.epg.by_key) if self.app.epg else 0
        auto_n = len(self.app.playlist.epg_urls) if self.app.playlist else 0
        manual_n = len(self.app.cfg.get("epg_manual_urls", []))
        ok_n = len(self.app.epg.sources_ok) if self.app.epg else 0
        err_n = len(self.app.epg.sources_err) if self.app.epg else 0
        self.t.header(surf, i18n.t("epg.title"),
                      i18n.t("epg.sub", n, auto_n, manual_n, ok_n, err_n))
        self.menu.draw(surf)
        self.t.footer(surf, [("A", i18n.t("btn.ok")),
                             ("X", i18n.t("btn.remove")),
                             ("B", i18n.t("btn.back"))])


class SearchScreen(Screen):
    def __init__(self, app):
        super().__init__(app)
        self.osk = OnScreenKeyboard(app.theme, i18n.t("search.title"))

    def on_button(self, btn):
        self.osk.handle(btn)
        if self.osk.done is False:
            self.app.pop()
        elif self.osk.done is True:
            q = self.osk.value.strip().lower()
            self.app.pop()
            if q and self.app.playlist:
                found = [c for c in self.app.playlist.channels
                         if q in c.name.lower() or q in c.group.lower()]
                self.app.push(ChannelsScreen(self.app, found,
                                             i18n.t("search.results", q)))

    def draw(self, surf):
        self.osk.draw(surf)


class TextInputScreen(Screen):
    def __init__(self, app, title, initial, on_ok):
        super().__init__(app)
        self.osk = OnScreenKeyboard(app.theme, title, initial)
        self.on_ok = on_ok

    def on_button(self, btn):
        self.osk.handle(btn)
        if self.osk.done is False:
            self.app.pop()
        elif self.osk.done is True:
            val = self.osk.value.strip()
            self.app.pop()
            if val:
                self.on_ok(val)

    def draw(self, surf):
        self.osk.draw(surf)


class SettingsScreen(Screen):
    """Tutto ciò che non è 'guardare' né 'sorgenti'. Lista piatta."""

    @staticmethod
    def _lang_name():
        return "English" if i18n.get_lang() == "en" else "Italiano"

    def __init__(self, app):
        super().__init__(app)
        self.menu = MenuList(self.t, row_h=36, top=64)

    def _items(self):
        cfg = self.app.cfg
        rec_sd = "SD2" if "/sdcard" in cfg.get("rec_dir", "") else "SD1"
        return [
            ("LANGUAGE",       i18n.t("set.lang_sub"), self._lang_name()),
            ("DEFAULT VIEW",   i18n.t("set.view_sub"), cfg.get("view_mode")),
            ("THEME",          i18n.t("set.theme_sub"), cfg.get("theme_accent")),
            (i18n.t("set.anim"), i18n.t("set.anim_sub"),
             i18n.t("set.anim_%d" % int(cfg.get("anim_intensity", 2)))),
            ("CHANNEL LOGOS",  i18n.t("set.logos_sub"),
             i18n.t("set.logos_yes") if cfg.get("show_logos", True)
             else i18n.t("set.logos_no")),
            ("PLAYER",         i18n.t("set.player_sub",
                                      self.app.player.backend()
                                      or i18n.t("set.player_none")),
             cfg.get("player_backend")),
            ("BUFFER",         i18n.t("set.cache_sub"),
             "%ds" % cfg.get("player_cache_secs")),
            ("EPG CACHE",      i18n.t("set.epg_age_sub"),
             "%dh" % cfg.get("epg_max_age_hours")),
            ("USER-AGENT",     cfg.get("user_agent")[:44], ""),
            ("RECORDINGS",     cfg.get("rec_dir", ""), rec_sd),
            ("QUICK GUIDE",    i18n.t("qg.sub"), ""),
            ("BUTTON MAPPING", i18n.t("set.remap_sub"), ""),
            ("ADDONS",         "%d active" % len(self.app.addons.addons), ""),
            ("LOG",            i18n.t("tools.log_sub"), ""),
            ("ABOUT",          "VOIDCAST %s" % C.APP_VERSION, "ℹ"),
            ("MUOS INPUT",     "Auto / Andromeda (=) / Non-Andromeda (!=)", (cfg.get("muos_profile", "auto").upper() + " → " + evinput.resolve_profile(cfg.get("muos_profile", "auto")).upper())),
        ]

    def on_button(self, btn):
        cfg = self.app.cfg
        if btn == "UP":
            self.menu.move(-1)
        elif btn == "DOWN":
            self.menu.move(1)
        elif btn == "B":
            self.app.pop()
        elif btn == "A" or btn in ("LEFT", "RIGHT"):
            i = self.menu.sel
            step = -1 if btn == "LEFT" else 1
            if i == 0:  # language
                new = "it" if i18n.get_lang() == "en" else "en"
                cfg.set("language", new)
                i18n.set_lang(new)
                self.app.addons.discover()
            elif i == 1:
                opts = ["list", "grid", "guide"]
                cur = opts.index(cfg.get("view_mode"))
                cfg.set("view_mode", opts[(cur + step) % 3])
            elif i == 2:
                opts = list(ui.ACCENTS.keys())
                cur = opts.index(cfg.get("theme_accent"))
                cfg.set("theme_accent", opts[(cur + step) % len(opts)])
            elif i == 3:  # animations intensity
                v = (int(cfg.get("anim_intensity", 2)) + step) % 4
                cfg.set("anim_intensity", v)
                Anim.set_intensity(v)
            elif i == 4:
                cfg.set("show_logos", not cfg.get("show_logos", True))
            elif i == 5:
                opts = ["auto", "mpv", "ffplay"]
                cur = opts.index(cfg.get("player_backend"))
                cfg.set("player_backend", opts[(cur + step) % 3])
            elif i == 6:
                cfg.set("player_cache_secs",
                        max(0, min(30, cfg.get("player_cache_secs") + step)))
            elif i == 7:
                cfg.set("epg_max_age_hours",
                        max(1, min(48, cfg.get("epg_max_age_hours") + step)))
            elif i == 8 and btn == "A":
                self.app.push(TextInputScreen(
                    self.app, "USER-AGENT", cfg.get("user_agent"),
                    lambda v: cfg.set("user_agent", v)))
            elif i == 9:
                d = cfg.get("rec_dir", "/mnt/mmc/MUOS/voidcast")
                cfg.set("rec_dir", "/mnt/sdcard/MUOS/voidcast"
                        if "/mmc" in d else "/mnt/mmc/MUOS/voidcast")
            elif i == 10 and btn == "A":
                self.app.push(QuickGuideScreen(self.app))
            elif i == 11 and btn == "A":
                self.app.push(RemapScreen(self.app))
            elif i == 12 and btn == "A":
                self.app.push(ToolsScreen(self.app))
            elif i == 13 and btn == "A":
                self.app.push(LogScreen(self.app))
            elif i == 14 and btn == "A":
                self.app.push(InfoScreen(self.app))
            elif i == 15:
                opts = ["auto", "andromeda", "not_andromeda"]
                current = cfg.get("muos_profile", "auto")
                cur = opts.index(current) if current in opts else 0
                selected = opts[(cur + step) % len(opts)]
                cfg.set("muos_profile", selected)
                evinput.set_profile(selected)
                self.app.toast("muOS input: " + evinput.resolve_profile(selected).upper())

    def draw(self, surf):
        self.t.header(surf, i18n.t("set.title"), i18n.t("set.sub"))
        self.menu.items = self._items()
        self.menu.draw(surf)
        self.t.footer(surf, [("A/◄►", i18n.t("btn.modify")),
                             ("B", i18n.t("btn.back"))])



class RemapScreen(Screen):
    ORDER = ["A", "B", "X", "Y", "L1", "R1", "SELECT", "START"]

    def __init__(self, app):
        super().__init__(app)
        self.step = 0
        self.newmap = {}

    def on_raw_button(self, raw):
        if self.step < len(self.ORDER):
            self.newmap[str(raw)] = self.ORDER[self.step]
            self.step += 1
            if self.step == len(self.ORDER):
                self.app.cfg.set("button_map", self.newmap)
                self.app.toast(i18n.t("remap.saved"))
                self.app.pop()

    def on_button(self, btn):
        pass  # gestiamo solo raw

    def draw(self, surf):
        self.t.header(surf, i18n.t("remap.title"),
                      i18n.t("remap.sub", self.step + 1, len(self.ORDER)))
        if self.step < len(self.ORDER):
            target = self.ORDER[self.step]
            self.t.text(surf, i18n.t("remap.press_for"), (40, 150),
                        self.t.f_med, FG_DIM)
            self.t.text(surf, target, (40, 200), self.t.f_big, self.t.accent)
            self.t.text(surf, i18n.t("remap.dpad_note"),
                        (40, 260), self.t.f_small, FG_FAINT)
        self.t.footer(surf, [("", i18n.t("btn.press_seq"))])


class ToolsScreen(Screen):
    def __init__(self, app):
        super().__init__(app)
        self.menu = MenuList(self.t, row_h=38, top=64)
        self._rebuild()

    def _rebuild(self):
        items = []
        self.actions = []
        for addon_name, act in self.app.addons.menu_actions():
            items.append((act["label"],
                          i18n.t("tools.addon_prefix", addon_name), "⚒"))
            self.actions.append(act)
        items.append((i18n.t("tools.reload"), i18n.t("tools.reload_sub"), ""))
        self.actions.append("rescan")
        items.append((i18n.t("tools.log"), i18n.t("tools.log_sub"), ""))
        self.actions.append("log")
        if self.app.addons.errors:
            items.append((i18n.t("tools.errors", len(self.app.addons.errors)),
                          self.app.addons.errors[0][0], ""))
            self.actions.append("errors")
        self.menu.items = items

    def on_button(self, btn):
        if btn == "UP":
            self.menu.move(-1)
        elif btn == "DOWN":
            self.menu.move(1)
        elif btn == "B":
            self.app.pop()
        elif btn == "A":
            act = self.actions[self.menu.sel]
            if act == "rescan":
                self.app.addons.discover()
                self.app.toast(i18n.t("tools.loaded", len(self.app.addons.addons)))
                self._rebuild()
            elif act == "log":
                self.app.push(LogScreen(self.app))
            elif act == "errors":
                self.app.push(LogScreen(self.app, addon_errors=True))
            else:
                try:
                    act["action"](self.app.addons.api)
                except Exception as e:  # noqa: BLE001
                    self.app.toast("Addon KO: %s" % e, ok=False)
                self._rebuild()

    def draw(self, surf):
        self.t.header(surf, i18n.t("tools.title"),
                      i18n.t("tools.sub", len(self.app.addons.addons)))
        self.menu.draw(surf)
        self.t.footer(surf, [("A", i18n.t("btn.execute")),
                             ("B", i18n.t("btn.back"))])


class LogScreen(Screen):
    def __init__(self, app, addon_errors=False):
        super().__init__(app)
        if addon_errors:
            self.lines = []
            for name, tb in app.addons.errors:
                self.lines.append("== " + name)
                self.lines += tb.splitlines()[-4:]
        else:
            try:
                with open(C.LOG_PATH, "r", encoding="utf-8") as f:
                    self.lines = f.read().splitlines()[-20:]
            except OSError:
                self.lines = [i18n.t("log.empty")]

    def draw(self, surf):
        self.t.header(surf, i18n.t("log.title"), C.LOG_PATH)
        y = 60
        for ln in self.lines[-20:]:
            self.t.text(surf, ln, (10, y), self.t.f_tiny, FG_DIM, maxw=W - 20)
            y += 18
        self.t.footer(surf, [("B", i18n.t("btn.back"))])


class QuickGuideScreen(Screen):
    TABS = ["basic", "playback", "sources", "recording", "addons", "tips"]

    def __init__(self, app):
        super().__init__(app)
        self.tab = 0
        self.scroll = 0
        self.entries = []
        self._rebuild()

    def _rebuild(self):
        self.entries = i18n.get_quick_guide(self.TABS[self.tab])
        self.scroll = 0

    def on_button(self, btn):
        if btn == "B":
            self.app.pop()
        elif btn == "L1" or btn == "LEFT":
            self.tab = (self.tab - 1) % len(self.TABS)
            self._rebuild()
        elif btn == "R1" or btn == "RIGHT":
            self.tab = (self.tab + 1) % len(self.TABS)
            self._rebuild()
        elif btn == "UP":
            self.scroll = max(0, self.scroll - 1)
        elif btn == "DOWN":
            self.scroll = min(max(0, len(self.entries) - 3), self.scroll + 1)

    def draw(self, surf):
        self.t.header(surf, i18n.t("qg.title"),
                      "TAB %d/%d" % (self.tab + 1, len(self.TABS)))
        # tab bar
        y_tab = 60
        gap = 6
        tab_w = (W - 20 - gap * (len(self.TABS) - 1)) // len(self.TABS)
        for i, tab in enumerate(self.TABS):
            x = 10 + i * (tab_w + gap)
            selected = (i == self.tab)
            if selected:
                pygame.draw.rect(surf, self.t.accent,
                                 (x, y_tab, tab_w, 26), border_radius=4)
                col = (15, 15, 20)
            else:
                pygame.draw.rect(surf, BG_PANEL,
                                 (x, y_tab, tab_w, 26), border_radius=4)
                pygame.draw.rect(surf, FG_FAINT,
                                 (x, y_tab, tab_w, 26), 1, border_radius=4)
                col = FG_DIM
            label = i18n.t("qg.tab." + tab).upper()
            f = self.t.f_tiny
            tw = f.size(label)[0]
            self.t.text(surf, label, (x + (tab_w - tw) // 2, y_tab + 7),
                        f, col)
        # entries (scrollable)
        y = 100
        visible = self.entries[self.scroll:self.scroll + 4]
        for topic, tip in visible:
            # topic with accent
            pygame.draw.rect(surf, self.t.accent, (10, y + 4, 3, 16))
            self.t.text(surf, topic, (20, y), self.t.f_med, self.t.accent)
            y += 24
            # wrap tip
            words = tip.split()
            line = ""
            for wd in words:
                test = (line + " " + wd).strip()
                if self.t.f_small.size(test)[0] > W - 44:
                    self.t.text(surf, line, (26, y), self.t.f_small, FG_DIM)
                    y += 18
                    line = wd
                else:
                    line = test
            if line:
                self.t.text(surf, line, (26, y), self.t.f_small, FG_DIM)
                y += 18
            y += 10
            if y > H - 70:
                break
        # scroll indicators
        if self.scroll > 0:
            self.t.text(surf, "▲", (W - 26, 96), self.t.f_small, self.t.accent)
        if self.scroll < len(self.entries) - 4:
            self.t.text(surf, "▼", (W - 26, H - 60),
                        self.t.f_small, self.t.accent)
        self.t.footer(surf, [("L1/R1", "tab"), ("▲▼", "scroll"),
                             ("B", i18n.t("btn.back"))])


class InfoScreen(Screen):
    """About / credits / license — scrollable, sectioned."""

    def __init__(self, app):
        super().__init__(app)
        self.scroll = 0
        self._lines = self._build()

    def _build(self):
        return [
            ("head", None),
            ("section", i18n.t("about.section.author")),
            ("kv", (i18n.t("about.section.author"), i18n.t("about.author_name"))),
            ("text", i18n.t("about.author_note")),
            ("gap", None),
            ("section", i18n.t("about.section.target")),
            ("kv", ("OS", "muOS 2601 JACARANDA")),
            ("kv", ("Device", "Anbernic RG35XX H")),
            ("kv", ("Screen", "640x480")),
            ("kv", ("Engine", "Python 3 + pygame · mpv / ffplay")),
            ("gap", None),
            ("section", i18n.t("about.section.credits")),
            ("text", i18n.t("about.cred.iptv")),
            ("text", i18n.t("about.cred.freetv")),
            ("text", i18n.t("about.cred.fonts")),
            ("text", i18n.t("about.cred.stack")),
            ("gap", None),
            ("section", i18n.t("about.section.license")),
            ("text", i18n.t("about.license_text")),
            ("text", i18n.t("about.license_warn")),
            ("gap", None),
            ("section", i18n.t("about.section.thanks")),
            ("text", i18n.t("about.thanks_text")),
        ]

    def on_button(self, btn):
        if btn == "B":
            self.app.pop()
        elif btn == "UP":
            self.scroll = max(0, self.scroll - 1)
        elif btn == "DOWN":
            self.scroll = min(max(0, len(self._lines) - 10), self.scroll + 1)

    def draw(self, surf):
        self.t.header(surf, i18n.t("about.title"),
                      i18n.t("about.app", C.APP_VERSION))
        # big title block
        y = 58
        title = i18n.t("about.app", C.APP_VERSION)
        self.t.glow_text(surf, title, (16, y), self.t.f_huge,
                         self.t.accent,
                         glow=self.t.accent,
                         radius=2)
        y += 44
        self.t.text(surf, i18n.t("about.tagline"), (18, y),
                    self.t.f_small, FG_DIM)
        y += 22
        self.t.text(surf, i18n.t("about.part_of"), (18, y),
                    self.t.f_small, FG)
        # separator
        pygame.draw.line(surf, self.t.accent, (10, y + 20),
                         (W - 10, y + 20), 1)
        y += 30
        # scrollable body
        max_y = H - 50
        for kind, val in self._lines[self.scroll:]:
            if y > max_y - 20:
                break
            if kind == "section":
                pygame.draw.rect(surf, BG_PANEL, (6, y - 2, W - 12, 20))
                pygame.draw.rect(surf, self.t.accent, (6, y - 2, 3, 20))
                self.t.text(surf, val.upper(), (16, y), self.t.f_small,
                            self.t.accent)
                y += 24
            elif kind == "kv":
                k, v = val
                self.t.text(surf, k.upper() + ":", (20, y),
                            self.t.f_tiny, self.t.accent)
                self.t.text(surf, v, (110, y), self.t.f_small, FG_DIM,
                            maxw=W - 130)
                y += 20
            elif kind == "text":
                self.t.text(surf, val, (20, y), self.t.f_small, FG,
                            maxw=W - 40)
                y += 20
            elif kind == "gap":
                y += 10
        # scroll hint
        if len(self._lines) > 10 and self.scroll < len(self._lines) - 10:
            self.t.text(surf, "▼", (W - 24, H - 60), self.t.f_small,
                        self.t.accent)
        if self.scroll > 0:
            self.t.text(surf, "▲", (W - 24, 56), self.t.f_small,
                        self.t.accent)
        self.t.footer(surf, [("▲▼", "scroll"), ("B", i18n.t("btn.back"))])



# ============================================================================
#  APP
# ============================================================================
class App(object):
    def __init__(self):
        self.cfg = Config()
        i18n.set_lang(self.cfg.get("language", "en"))
        Anim.set_intensity(self.cfg.get("anim_intensity", 2))
        self.bgplay = BgPlayer(self.cfg)
        self._bg_panel = False
        self.logos = logos_mod.Logos(self.cfg.get("user_agent", ""))
        self.theme = Theme(self.cfg.get("theme_accent", "crimson"))
        self.theme.fx_scanlines = bool(self.cfg.get("fx_scanlines", False))
        self.player = Player(self.cfg)
        self.addons = AddonManager(self)
        self._toast = Toast(self.theme)
        self.playlist = None
        self.epg = epg_mod.EPG()
        self.current_channel = None
        self.running = True
        self.stack = []
        self.screen = None
        self.joysticks = []
        self._dpad_last = (0, 0)
        self._dpad_time = 0
        self.screens = {
            "recordings": lambda: RecordingsScreen(self),
        }

    # ------------------------------------------------------------------
    def init_display(self):
        use_fb = os.environ.get("VOIDCAST_FB") == "1"
        if use_fb:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.display.init()
        pygame.font.init()
        flags = (pygame.FULLSCREEN
                 if (not use_fb and os.environ.get("VOIDCAST_WIN") != "1")
                 else 0)
        try:
            self.surface = pygame.display.set_mode((W, H), flags)
        except pygame.error:
            self.surface = pygame.display.set_mode((W, H))
        if use_fb:
            from core import fbdisplay
            if fbdisplay.attach(self.surface):
                log("display: framebuffer diretto - " + fbdisplay.info())
            else:
                log("display: fbdisplay NON disponibile, resto su SDL dummy")
        pygame.display.set_caption("VOIDCAST")
        pygame.mouse.set_visible(False)

    def init_joysticks(self):
        pygame.joystick.init()
        self.joysticks = []
        for i in range(pygame.joystick.get_count()):
            j = pygame.joystick.Joystick(i)
            j.init()
            self.joysticks.append(j)
            log("joystick %d: '%s' btn=%d hat=%d axes=%d"
                % (i, j.get_name(), j.get_numbuttons(),
                   j.get_numhats(), j.get_numaxes()))
        if not self.joysticks:
            log("input: NESSUN joystick rilevato (SDL)")
        evinput.set_profile(self.cfg.get("muos_profile", "auto"))
        if os.environ.get("VOIDCAST_FB") == "1":
            if evinput.start():
                log("input: lettore evdev attivo su %d device"
                    % len(evinput._state["fds"]))
            else:
                log("input: evdev NON disponibile")
        if _ENV_BTN:
            log("input: mappa muOS attiva: %s"
                % {k: v for k, v in sorted(_ENV_BTN.items())})

    def suspend_display(self):
        try:
            from core import fbdisplay
            fbdisplay.detach()
        except Exception:
            pass
        pygame.display.quit()

    def resume_display(self):
        self.init_display()
        self.init_joysticks()

    # ------------------------------------------------------------------
    def push(self, screen):
        self.stack.append(screen)

    def pop(self):
        if len(self.stack) > 1:
            self.stack.pop()

    def top(self):
        return self.stack[-1]

    def toast(self, msg, ok=True):
        self._toast.show(msg, ok)
        log(("[ok] " if ok else "[err] ") + msg)

    def busy(self, label, fn):
        """Esegue fn() disegnando prima un overlay di caricamento."""
        surf = self.surface
        surf.fill(BG)
        self.theme.header(surf, "VOIDCAST", i18n.t("app.busy.sub"))
        self.theme.text(surf, i18n.t("app.busy.line", label), (40, 200),
                        self.theme.f_big, self.theme.accent)
        self.theme.text(surf, i18n.t("app.busy.note"),
                        (40, 240), self.theme.f_small, FG_FAINT)
        self.theme.scanlines(surf)
        pygame.display.flip()
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            log("busy(%s) FAIL: %s" % (label, traceback.format_exc(limit=3)))
            self.toast("%s: %s" % (label, str(e)[:60]), ok=False)
            return None

    # ------------------------------------------------------------------
    def reload_playlist(self, force=False):
        entry = self.cfg.active_playlist()
        if not entry:
            self.playlist = None
            return
        ua = self.cfg.get("user_agent")

        def _do():
            return m3u.load_playlist(entry, ua)

        pl = self.busy(i18n.t("app.busy.download_list", entry["name"]), _do)
        if pl is not None:
            self.playlist = pl
            log("playlist loaded: name=%s channels=%d epg_urls=%d %s"
                % (entry["name"], len(pl.channels), len(pl.epg_urls),
                   pl.epg_urls[:5]))
            self.toast(i18n.t("app.toast.list_ok",
                       len(pl.channels), len(pl.epg_urls)))
            self.reload_epg(force=force)

    def reload_epg(self, force=False):
        urls = epg_mod.collect_epg_urls(self.cfg, self.playlist)
        log("reload_epg: %d urls %s" % (len(urls), urls[:5]))
        if not urls:
            self.epg = epg_mod.EPG()
            self.toast(i18n.t("app.toast.epg_none"), ok=False)
            return
        max_age = 0 if force else self.cfg.get("epg_max_age_hours", 12)
        ua = self.cfg.get("user_agent")

        def _do():
            e = epg_mod.EPG()
            e.load(urls, ua, max_age)
            return e

        e = self.busy(i18n.t("app.busy.load_epg", len(urls)), _do)
        if e is not None:
            self.epg = e
            msg = i18n.t("app.toast.epg_ok", len(e.sources_ok),
                                  len(e.sources_err))
            self.toast(msg, ok=not e.sources_err or bool(e.sources_ok))

    # ------------------------------------------------------------------
    def open_channels(self, mode=None, favorites=False):
        if not self.playlist or not self.playlist.channels:
            self.toast(i18n.t("app.toast.no_list"), ok=False)
            self.push(PlaylistScreen(self))
            return
        chans = self.playlist.channels
        label = "playlist"
        if favorites:
            favs = set(self.cfg.get("favorites", []))
            chans = [c for c in chans if c.url in favs]
            label = "preferiti"
        self.push(ChannelsScreen(self, chans, label, mode))

    def play_channel(self, channels, index):
        i = index
        while True:
            ch = channels[i]
            self.current_channel = ch
            ctx = self._build_play_ctx(ch, channels, i)
            log("play: %s" % ch.name)
            self.suspend_display()
            result = self.player.play(ch, ctx=ctx)
            self.resume_display()
            if result == RESULT_NEXT:
                i = (i + 1) % len(channels)
            elif result == RESULT_PREV:
                i = (i - 1) % len(channels)
            elif result == RESULT_FAV:
                fav = self.cfg.toggle_favorite(ch.url)
                self.toast(i18n.t("ch.toast.fav_added" if fav else "ch.toast.fav_removed", ch.name))
            elif result == "bg":
                if self.bgplay.start(ch):
                    self.toast(i18n.t("bg.started", ch.name))
                else:
                    self.toast("bg start failed", ok=False)
                return
            elif result == RESULT_ERROR:
                self.toast(self.player.last_error or "player error", ok=False)
                return
            else:
                return

    def _build_play_ctx(self, ch, channels, idx):
        """Contesto passato al Player per l'overlay in riproduzione."""
        ctx = {"name": ch.name, "group": ch.group,
               "index": idx, "total": len(channels),
               "epg_now": "", "epg_next": "", "epg_list": []}
        if self.epg:
            try:
                cur, nxt = self.epg.now_next(ch)
                if cur:
                    ctx["epg_now"] = cur.title
                if nxt:
                    ctx["epg_next"] = nxt.title
                win = self.epg.window(ch, time.time(), time.time() + 6 * 3600)
                ctx["epg_list"] = [(p.start, p.title) for p in win[:30]]
            except Exception:
                pass
        return ctx


    # ------------------------------------------------------------------
    def logical_button(self, raw):
        user_map = self.cfg.get("button_map", {})
        # se l'utente non ha rimappato, la mappa di muOS (dall'ambiente)
        # e' quella giusta per questo hardware
        if _ENV_BTN and user_map == C.DEFAULTS.get("button_map"):
            btn = _ENV_BTN.get(raw)
        else:
            btn = user_map.get(str(raw))
        if btn is None:
            log("input: tasto raw %d non mappato" % raw)
        return btn

    def dispatch(self, btn):
        if btn:
            self.top().on_button(btn)

    def poll_dpad(self):
        """D-pad con auto-repeat: hat 0 oppure assi 0/1 (analogico)."""
        hx, hy = 0, 0
        if evinput.active():
            hx, hy = evinput.hat()
        for j in self.joysticks:
            if j.get_numhats() > 0:
                x, y = j.get_hat(0)
                hx, hy = hx or x, hy or y
            if j.get_numaxes() >= 2:
                ax, ay = j.get_axis(0), j.get_axis(1)
                if abs(ax) > 0.6:
                    hx = hx or (1 if ax > 0 else -1)
                if abs(ay) > 0.6:
                    hy = hy or (-1 if ay > 0 else 1)
        now = time.time()
        cur = (hx, hy)
        if cur == (0, 0):
            self._dpad_last = cur
            return
        first = cur != self._dpad_last
        if first or (now - self._dpad_time) > 0.16:
            self._dpad_time = now
            self._dpad_last = cur
            if hy > 0:
                self.dispatch("UP")
            elif hy < 0:
                self.dispatch("DOWN")
            if hx < 0:
                self.dispatch("LEFT")
            elif hx > 0:
                self.dispatch("RIGHT")

    # ------------------------------------------------------------------
    def run(self):
        pygame.init()
        self.init_display()
        self.init_joysticks()
        self.addons.discover()
        self.push(HomeScreen(self))
        # bootstrap: carica lista attiva se esiste
        if self.cfg.active_playlist():
            self.reload_playlist()
        clock = pygame.time.Clock()
        while self.running:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.running = False
                elif ev.type == pygame.JOYBUTTONDOWN and not evinput.active():
                    scr = self.top()
                    if isinstance(scr, RemapScreen):
                        scr.on_raw_button(ev.button)
                    else:
                        self.dispatch(self.logical_button(ev.button))
                elif ev.type == pygame.KEYDOWN:
                    btn = KEYMAP_KB.get(ev.key)
                    self.dispatch(btn)
                elif ev.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
                    self.init_joysticks()
            if evinput.active():
                for btn in evinput.poll():
                    if btn == "MENU":
                        if self.bgplay.active:
                            self._bg_panel = not self._bg_panel
                        continue
                    if self._bg_panel:
                        # handle bg overlay controls, do not propagate
                        if btn == "A":
                            self.bgplay.toggle_pause()
                        elif btn == "B":
                            self.bgplay.stop()
                            self._bg_panel = False
                            self.toast(i18n.t("bg.stopped"))
                        elif btn == "X":
                            # resume full video
                            ch = self.bgplay.channel
                            self.bgplay.stop()
                            self._bg_panel = False
                            if ch is not None:
                                self.play_channel([ch], 0)
                        elif btn == "M":
                            self._bg_panel = False
                        continue
                    scr = self.top()
                    if isinstance(scr, RemapScreen):
                        scr.on_button(btn)
                    else:
                        self.dispatch(btn)
            self.poll_dpad()
            surf = self.surface
            if self.bgplay.active:
                self.theme.cyber_backdrop(surf)
            else:
                surf.fill(BG)
            try:
                self.top().draw(surf)
            except Exception:  # noqa: BLE001
                log("draw FAIL: %s" % traceback.format_exc(limit=3))
                self.pop()
            if self.bgplay.active:
                # small indicator top-right
                ch = self.bgplay.channel
                if ch is not None:
                    txt = i18n.t("bg.paused" if self.bgplay.paused
                                 else "bg.playing", ch.name[:24])
                    f = self.theme.f_small
                    w = f.size(txt)[0] + 20
                    s = pygame.Surface((w, 26), pygame.SRCALPHA)
                    s.fill((16, 16, 26, 200))
                    surf.blit(s, (W - w - 8, 60))
                    pygame.draw.rect(surf, self.theme.accent,
                                     (W - w - 8, 60, w, 26), 1)
                    pulse = Anim.pulse(1.2, 0.4, 1.0)
                    dot = (int(self.theme.accent[0] * pulse),
                           int(self.theme.accent[1] * pulse),
                           int(self.theme.accent[2] * pulse))
                    pygame.draw.circle(surf, dot, (W - w + 2, 73), 4)
                    self.theme.text(surf, txt, (W - w + 10, 64),
                                    self.theme.f_small, FG)
                # bg manager modal
                if self._bg_panel:
                    draw_bg_modal(self, surf)
            self._toast.draw(surf)
            self.theme.scanline_overlay(surf)
            pygame.display.flip()
            clock.tick(FPS)
        pygame.quit()



# ============================================================================
#  Background manager overlay (in-app, when bg audio is playing)
# ============================================================================
def draw_bg_modal(app, surf):
    t = app.theme
    overlay = pygame.Surface((W, H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    surf.blit(overlay, (0, 0))
    box = (90, 120, W - 180, 240)
    pygame.draw.rect(surf, BG_PANEL, box)
    pygame.draw.rect(surf, t.accent, box, 2)
    t.corner_brackets(surf, box, t.accent, size=10, thick=2)
    ch = app.bgplay.channel
    name = ch.name if ch is not None else "?"
    t.glow_text(surf, i18n.t("bg.title"), (box[0] + 20, box[1] + 16),
                t.f_big, t.accent)
    t.text(surf, "♪ " + name[:44], (box[0] + 20, box[1] + 62),
           t.f_med, FG)
    state = i18n.t("bg.pause") if not app.bgplay.paused else i18n.t("bg.pause")
    rows = [
        ("A", state),
        ("X", i18n.t("bg.resume")),
        ("B", i18n.t("bg.stop")),
        ("M", i18n.t("bg.close")),
    ]
    y = box[1] + 106
    for k, lab in rows:
        from ui import icons as icons_mod
        w = icons_mod.draw_button(surf, k, box[0] + 20, y, size=22)
        t.text(surf, lab, (box[0] + 30 + w, y + 2), t.f_small, FG_DIM)
        y += 32


# ============================================================================
#  Recordings player
# ============================================================================
class RecordingsScreen(Screen):
    def __init__(self, app):
        super().__init__(app)
        self.menu = MenuList(self.t, row_h=36, top=64)
        self.files = []
        self._rebuild()

    def _rebuild(self):
        d = self.app.cfg.get("rec_dir", "/mnt/mmc/MUOS/voidcast")
        try:
            names = [f for f in os.listdir(d) if f.endswith(".ts")]
            names.sort(reverse=True)
        except OSError:
            names = []
        self.files = [os.path.join(d, n) for n in names]
        self.menu.items = [(n, "%d KB" % (os.path.getsize(p) // 1024)
                            if os.path.exists(p) else "", "") for
                           n, p in zip(names, self.files)] or \
                          [(i18n.t("rec.empty"), "", "")]

    def on_button(self, btn):
        if btn == "UP":
            self.menu.move(-1)
        elif btn == "DOWN":
            self.menu.move(1)
        elif btn == "B":
            self.app.pop()
        elif btn == "X" and self.files:
            p = self.files[self.menu.sel]
            try:
                os.remove(p)
                self.app.toast(i18n.t("rec.deleted",
                                      os.path.basename(p)))
            except OSError:
                pass
            self._rebuild()
        elif btn == "A" and self.files:
            p = self.files[self.menu.sel]
            self._play_file(p)

    def _play_file(self, path):
        class _R:
            def __init__(self, p):
                self.url = "file://" + p
                self.name = os.path.basename(p)
                self.group = "recordings"
                self.tvg_id = self.tvg_name = self.logo = ""
                self.opts = {}
        self.app.suspend_display()
        try:
            self.app.player.play(_R(path))
        finally:
            self.app.resume_display()

    def draw(self, surf):
        self._rebuild()
        d = self.app.cfg.get("rec_dir", "")
        self.t.header(surf, i18n.t("rec.title"),
                      i18n.t("rec.sub", len(self.files), d))
        self.menu.draw(surf)
        self.t.footer(surf, [("A", i18n.t("btn.play")),
                             ("X", i18n.t("btn.delete")),
                             ("B", i18n.t("btn.back"))])



def main():
    if os.environ.get("VOIDCAST_FB") == "1":
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        # senza finestra con focus SDL scarta gli eventi joystick: forzali
        os.environ.setdefault("SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", "1")
    log("=== VOIDCAST %s boot ===" % C.APP_VERSION)
    try:
        App().run()
    except Exception:  # noqa: BLE001
        log("FATAL: %s" % traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
