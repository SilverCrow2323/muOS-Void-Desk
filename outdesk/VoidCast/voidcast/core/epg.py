# outdesk/VoidCast/voidcast/core/epg.py
# -*- coding: utf-8 -*-
# VOIDCAST // core.epg — motore EPG XMLTV multi-sorgente
#
# - Scarica N sorgenti XMLTV (anche .gz), con cache su disco
# - Indicizza programmi per channel-id e per display-name (lowercase)
# - Match canale: tvg-id > tvg-name > nome canale

import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

from . import config as C
from . import net


def _parse_xmltv_time(s):
    """'20260714203000 +0200' -> epoch UTC (float). Tollerante."""
    if not s:
        return None
    s = s.strip()
    base, tz = (s.split(" ", 1) + [""])[:2] if " " in s else (s, "")
    base = base[:14].ljust(14, "0")
    try:
        dt = datetime.strptime(base, "%Y%m%d%H%M%S")
    except ValueError:
        return None
    offset = timedelta(0)
    tz = tz.strip()
    if len(tz) == 5 and tz[0] in "+-":
        try:
            offset = timedelta(hours=int(tz[1:3]), minutes=int(tz[3:5]))
            if tz[0] == "-":
                offset = -offset
        except ValueError:
            offset = timedelta(0)
    return (dt - offset).replace(tzinfo=timezone.utc).timestamp()


class Programme(object):
    __slots__ = ("start", "stop", "title", "desc")

    def __init__(self, start, stop, title, desc=""):
        self.start = start
        self.stop = stop
        self.title = title
        self.desc = desc


class EPG(object):
    def __init__(self):
        self.by_key = {}      # chiave lowercase -> [Programme]
        self.sources_ok = []  # url caricate con successo
        self.sources_err = []  # (url, errore)
        self.loaded_at = 0

    # ------------------------------------------------------------------
    def load(self, urls, user_agent=None, max_age_hours=12):
        self.by_key.clear()
        self.sources_ok, self.sources_err = [], []
        for url in urls:
            try:
                data, cached = net.cached_fetch(url, C.EPG_CACHE_DIR,
                                                max_age_hours, user_agent)
                self._parse(data)
                self.sources_ok.append(url + (" [cache]" if cached else ""))
            except Exception as e:  # noqa: BLE001 — su handheld si sopravvive
                self.sources_err.append((url, str(e)[:80]))
        for progs in self.by_key.values():
            progs.sort(key=lambda p: p.start)
        self.loaded_at = time.time()

    def _parse(self, data):
        # id -> [display names]; poi mappiamo i programmi su tutte le chiavi
        chan_names = {}
        # iterparse per non mangiare RAM su XMLTV enormi
        import io
        for event, el in ET.iterparse(io.BytesIO(data), events=("end",)):
            tag = el.tag.split("}")[-1]
            if tag == "channel":
                cid = (el.get("id") or "").strip().lower()
                names = [(dn.text or "").strip().lower()
                         for dn in el.findall("display-name") if dn.text]
                if cid:
                    chan_names[cid] = names
                el.clear()
            elif tag == "programme":
                cid = (el.get("channel") or "").strip().lower()
                start = _parse_xmltv_time(el.get("start"))
                stop = _parse_xmltv_time(el.get("stop"))
                t_el = el.find("title")
                d_el = el.find("desc")
                title = (t_el.text or "").strip() if t_el is not None and t_el.text else "?"
                desc = (d_el.text or "").strip() if d_el is not None and d_el.text else ""
                if cid and start:
                    prog = Programme(start, stop or start + 1800, title, desc)
                    keys = [cid] + chan_names.get(cid, [])
                    for k in set(keys):
                        self.by_key.setdefault(k, []).append(prog)
                el.clear()

    # ------------------------------------------------------------------
    def programmes_for(self, channel):
        for key in channel.epg_keys():
            progs = self.by_key.get(key)
            if progs:
                return progs
        return []

    def now_next(self, channel, now=None):
        now = now or time.time()
        progs = self.programmes_for(channel)
        cur, nxt = None, None
        for p in progs:
            if p.start <= now < p.stop:
                cur = p
            elif p.start > now:
                nxt = p
                break
        return cur, nxt

    def window(self, channel, start, stop):
        return [p for p in self.programmes_for(channel)
                if p.stop > start and p.start < stop]


def collect_epg_urls(cfg, playlist):
    """Fonti EPG effettive: quelle dichiarate nella lista + manuali. Dedup."""
    urls = []
    if cfg.get("epg_use_playlist_sources", True) and playlist is not None:
        urls.extend(playlist.epg_urls)
    urls.extend(cfg.get("epg_manual_urls", []))
    out, seen = [], set()
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out
