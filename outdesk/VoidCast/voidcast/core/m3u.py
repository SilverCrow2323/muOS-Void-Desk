# outdesk/VoidCast/voidcast/core/m3u.py
# -*- coding: utf-8 -*-
# VOIDCAST // core.m3u — parser M3U/M3U8 con estrazione attributi e fonti EPG
#
# Supporta:
#   #EXTM3U url-tvg="http://a.xml,http://b.xml.gz" x-tvg-url="..."
#   #EXTINF:-1 tvg-id="Rai1.it" tvg-name="Rai 1" tvg-logo="..." group-title="Generalisti",Rai 1
#   #EXTVLCOPT:http-user-agent=...  (ignorato ma non fatale)

import re

from . import i18n

ATTR_RE = re.compile(r'([A-Za-z0-9_-]+)="(.*?)"')


class Channel(object):
    __slots__ = ("name", "url", "tvg_id", "tvg_name", "logo", "group",
                 "index", "opts")

    def __init__(self, name, url, tvg_id="", tvg_name="", logo="", group="",
                 index=0, opts=None):
        self.name = name or tvg_name or "???"
        self.url = url
        self.tvg_id = tvg_id
        self.tvg_name = tvg_name
        self.logo = logo
        self.group = group or i18n.t("m3u.no_group")
        self.index = index
        # opzioni per-canale da #EXTVLCOPT / #EXTHTTP:
        #   user-agent, referrer, origin, headers{dict}
        self.opts = opts or {}

    def epg_keys(self):
        keys = []
        if self.tvg_id:
            keys.append(self.tvg_id.strip().lower())
        if self.tvg_name:
            keys.append(self.tvg_name.strip().lower())
        keys.append(self.name.strip().lower())
        return keys


class Playlist(object):
    def __init__(self):
        self.channels = []
        self.epg_urls = []   # fonti EPG dichiarate nella lista (possono essere N)
        self.groups = []

    def build_groups(self):
        seen, groups = set(), []
        for ch in self.channels:
            if ch.group not in seen:
                seen.add(ch.group)
                groups.append(ch.group)
        self.groups = groups


def parse_m3u(text):
    """Parsa testo M3U -> Playlist. Robusto contro liste sporche."""
    pl = Playlist()
    pending = None  # dict attributi in attesa dell'URL
    idx = 0
    if text.startswith("\ufeff"):  # BOM UTF-8: romperebbe il match di #EXTM3U
        text = text.lstrip("\ufeff")
    for raw in text.splitlines():
        line = raw.strip().lstrip("\ufeff")
        if not line:
            continue
        if line.upper().startswith("#EXTM3U"):
            # attributi case-insensitive
            attrs_ci = {}
            for k, v in ATTR_RE.findall(line):
                attrs_ci[k.lower()] = v
            # varianti accettate (tutte in minuscolo)
            for key in ("url-tvg", "x-tvg-url", "tvg-url",
                        "epg-url", "xmltv-url",
                        "url_tvg", "x_tvg_url", "tvg_url",
                        "epg_url", "xmltv_url"):
                val = attrs_ci.get(key, "")
                if not val:
                    continue
                for u in val.split(","):
                    u = u.strip().strip("\"'")
                    if u and u not in pl.epg_urls:
                        pl.epg_urls.append(u)
            continue
        if line.startswith("#EXTINF"):
            attrs = dict(ATTR_RE.findall(line))
            name = line.rsplit(",", 1)[1].strip() if "," in line else ""
            pending = {
                "name": name,
                "tvg_id": attrs.get("tvg-id", ""),
                "tvg_name": attrs.get("tvg-name", ""),
                "logo": attrs.get("tvg-logo", ""),
                "group": attrs.get("group-title", ""),
            }
            continue
        if line.startswith("#EXTVLCOPT:") and pending is not None:
            body = line.split(":", 1)[1]
            if "=" in body:
                k, v = body.split("=", 1)
                k = k.strip().lower()
                v = v.strip()
                o = pending.setdefault("opts", {})
                if k == "http-user-agent":
                    o["user-agent"] = v
                elif k in ("http-referrer", "http-referer"):
                    o["referrer"] = v
                elif k == "http-origin":
                    o["origin"] = v
            continue
        if line.startswith("#EXTHTTP:") and pending is not None:
            try:
                import json as _json
                hdrs = _json.loads(line.split(":", 1)[1])
                if isinstance(hdrs, dict):
                    o = pending.setdefault("opts", {})
                    o.setdefault("headers", {}).update(
                        {str(k): str(v) for k, v in hdrs.items()})
            except ValueError:
                pass
            continue
        if line.startswith("#"):
            continue  # KODIPROP, EXTGRP, commenti vari
        # riga URL
        if pending is not None:
            pl.channels.append(Channel(
                pending["name"], line, pending["tvg_id"], pending["tvg_name"],
                pending["logo"], pending["group"], idx,
                pending.get("opts")))
            idx += 1
            pending = None
        elif line.startswith(("http://", "https://", "rtmp://", "rtsp://", "udp://")):
            pl.channels.append(Channel(line.split("/")[-1][:40], line, index=idx))
            idx += 1
    pl.build_groups()
    return pl


def load_playlist(entry, user_agent=None):
    """Carica una entry playlist di config ({source, type}) -> Playlist."""
    from . import net
    if entry["type"] == "url":
        text = net.fetch_text(entry["source"], user_agent)
    else:
        with open(entry["source"], "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    return parse_m3u(text)
