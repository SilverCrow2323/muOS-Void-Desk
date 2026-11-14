# -*- coding: utf-8 -*-
"""Bounded, allowlisted RSS and Open-Meteo data helpers for the LÖVE frontend."""
from __future__ import annotations

import html
from html.parser import HTMLParser
import json
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone


RSS_FEEDS = (
    {"name": "ANSA", "category": "news", "language": "it",
     "url": "https://www.ansa.it/sito/ansait_rss.xml"},
    {"name": "Il Post", "category": "news", "language": "it",
     "url": "https://www.ilpost.it/feed/"},
    {"name": "BBC World", "category": "news", "language": "en",
     "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
    {"name": "HDblog", "category": "tech", "language": "it",
     "url": "https://www.hdblog.it/rss/hdblog.xml"},
    {"name": "Ars Technica", "category": "tech", "language": "en",
     "url": "https://feeds.arstechnica.com/arstechnica/index"},
    {"name": "The Verge", "category": "tech", "language": "en",
     "url": "https://www.theverge.com/rss/index.xml"},
    {"name": "Phoronix", "category": "linux", "language": "en",
     "url": "https://www.phoronix.com/rss.php"},
    {"name": "It's FOSS", "category": "linux", "language": "en",
     "url": "https://itsfoss.com/feed/"},
    {"name": "OMG Ubuntu", "category": "linux", "language": "en",
     "url": "https://www.omgubuntu.co.uk/feed"},
    {"name": "Multiplayer.it", "category": "gaming", "language": "it",
     "url": "https://www.multiplayer.it/feed/"},
    {"name": "IGN", "category": "gaming", "language": "en",
     "url": "https://feeds.ign.com/ign/games-all"},
    {"name": "PC Gamer", "category": "gaming", "language": "en",
     "url": "https://www.pcgamer.com/rss/"},
    {"name": "Time Extension", "category": "retro", "language": "en",
     "url": "https://www.timeextension.com/feed"},
    {"name": "RetroRGB", "category": "retro", "language": "en",
     "url": "https://www.retrorgb.com/feed"},
    {"name": "AnimeClick", "category": "anime", "language": "it",
     "url": "https://www.animeclick.it/rss"},
    {"name": "Anime News Network", "category": "anime", "language": "en",
     "url": "https://www.animenewsnetwork.com/all/rss.xml"},
)
RSS_CATEGORIES = ("all", "news", "tech", "linux", "gaming", "retro", "anime")
RSS_MAX_BYTES = 1_500_000
RSS_MAX_ITEMS = 8
WEATHER_GEO_HOST = "geocoding-api.open-meteo.com"
WEATHER_API_HOST = "api.open-meteo.com"
WEATHER_MAX_BYTES = 350_000


class _TextOnly(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def _plain_text(value: str, limit: int = 420) -> str:
    parser = _TextOnly()
    try:
        parser.feed(str(value or ""))
        parser.close()
        result = " ".join(" ".join(parser.parts).split())
    except Exception:
        result = re.sub(r"<[^>]{0,256}>", " ", str(value or ""))
    return html.unescape(result)[:limit]


def _tag(element, name):
    for child in list(element):
        if child.tag.rsplit("}", 1)[-1].lower() == name.lower():
            return child
    return None


def _entry_link(entry):
    links = [node for node in list(entry)
             if node.tag.rsplit("}", 1)[-1].lower() == "link"]
    if not links:
        return ""
    link = next((node for node in links
                 if node.attrib.get("rel", "alternate").lower() == "alternate"),
                links[0])
    value = link.attrib.get("href") or (link.text or "").strip()
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme not in ("https", "http") or not parsed.hostname:
        return ""
    if parsed.username or parsed.password:
        return ""
    return value[:2048]


def parse_rss(xml_bytes: bytes, source: str, limit: int = RSS_MAX_ITEMS):
    """Parse RSS 2.0, RSS 1.0 and Atom without processing DTD/entity declarations."""
    if not isinstance(xml_bytes, (bytes, bytearray)) or len(xml_bytes) > RSS_MAX_BYTES:
        raise ValueError("feed exceeds the response size limit")
    sample = bytes(xml_bytes)
    upper = sample.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise ValueError("feed contains a forbidden document declaration")
    root = ET.fromstring(sample)
    items = []
    for element in root.iter():
        local = element.tag.rsplit("}", 1)[-1].lower()
        if local not in ("item", "entry"):
            continue
        title_node = _tag(element, "title")
        summary_node = _tag(element, "description")
        if summary_node is None:
            summary_node = _tag(element, "summary")
        if summary_node is None:
            summary_node = _tag(element, "content")
        date_node = _tag(element, "pubdate")
        if date_node is None:
            date_node = _tag(element, "published")
        if date_node is None:
            date_node = _tag(element, "updated")
        title = _plain_text(title_node.text if title_node is not None else "", 220)
        link = _entry_link(element)
        if not title or not link:
            continue
        items.append({
            "source": str(source)[:80],
            "title": title,
            "summary": _plain_text(summary_node.text if summary_node is not None else "", 420),
            "url": link,
            "published": _plain_text(date_node.text if date_node is not None else "", 96),
        })
        if len(items) >= max(1, min(int(limit), 20)):
            break
    return items


class _SameHostRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, allowed_host: str):
        super().__init__()
        self.allowed_host = allowed_host.lower()

    def redirect_request(self, request, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlparse(newurl)
        if (parsed.scheme != "https" or
                (parsed.hostname or "").lower() != self.allowed_host or
                parsed.username or parsed.password):
            raise urllib.error.HTTPError(
                newurl, code, "redirect outside the allowlisted HTTPS host", headers, fp
            )
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def _fetch_https(url: str, expected_host: str, max_bytes: int, timeout: float = 6.0):
    parsed = urllib.parse.urlparse(url)
    if (parsed.scheme != "https" or parsed.hostname != expected_host or
            parsed.username or parsed.password or parsed.port not in (None, 443)):
        raise ValueError("URL is outside the allowlisted HTTPS endpoint")
    # Reject private/reserved destinations before the request; DNS is checked
    # again here rather than trusting the hostname string alone.
    try:
        addresses = socket.getaddrinfo(expected_host, 443, type=socket.SOCK_STREAM)
        for item in addresses:
            address = item[4][0]
            import ipaddress
            ip = ipaddress.ip_address(address)
            if not ip.is_global:
                raise ValueError("endpoint resolved to a non-public address")
    except OSError:
        # CI and offline handhelds must return a visible network error; the
        # actual request below will provide the definitive failure.
        pass
    opener = urllib.request.build_opener(_SameHostRedirect(expected_host))
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "VoidDesk-Love-Content/1.0",
            "Accept": "application/rss+xml, application/atom+xml, application/xml, application/json",
        },
    )
    with opener.open(request, timeout=timeout) as response:
        final = urllib.parse.urlparse(response.geturl())
        if final.scheme != "https" or final.hostname != expected_host:
            raise ValueError("response endpoint changed unexpectedly")
        declared = response.headers.get("Content-Length")
        if declared and int(declared) > max_bytes:
            raise ValueError("response is larger than the configured limit")
        body = response.read(max_bytes + 1)
    if len(body) > max_bytes:
        raise ValueError("response is larger than the configured limit")
    return body


def refresh_rss(category: str = "all", language: str = "all", progress=None):
    category = str(category or "all").lower()
    language = str(language or "all").lower()
    if category not in RSS_CATEGORIES or language not in ("all", "en", "it"):
        raise ValueError("unsupported RSS category or language")
    selected = [feed for feed in RSS_FEEDS
                if (category == "all" or feed["category"] == category)
                and (language == "all" or feed["language"] == language)]
    if category == "all":
        # Give the ALL view genuine category breadth with at most one feed
        # per category; a specific category may use up to three sources.
        chosen = set()
        selected = [
            feed for feed in selected
            if not (feed["category"] in chosen or chosen.add(feed["category"]))
        ]
    else:
        selected = selected[:3]
    results, errors = [], []
    if not selected:
        raise ValueError("no feeds match the selected category and language")
    for index, feed in enumerate(selected, 1):
        if progress:
            progress(int((index - 1) * 80 / len(selected)),
                     "FETCHING", "Fetching " + feed["name"],
                     "Reading a bounded, allowlisted public RSS/Atom feed.")
        try:
            host = urllib.parse.urlparse(feed["url"]).hostname
            body = _fetch_https(feed["url"], host, RSS_MAX_BYTES)
            results.extend(parse_rss(body, feed["name"]))
        except (OSError, ValueError, ET.ParseError, urllib.error.URLError,
                TimeoutError) as exc:
            errors.append({"source": feed["name"], "error": str(exc)[:180]})
    results.sort(key=lambda item: item["published"], reverse=True)
    if not results:
        raise RuntimeError("all selected feeds are unavailable: " +
                           "; ".join(x["source"] + ": " + x["error"] for x in errors))
    if progress:
        progress(100, "COMPLETED", "RSS feed updated",
                 "%d articles loaded; %d source errors" % (len(results), len(errors)))
    return {
        "ok": True,
        "category": category,
        "language": language,
        "updated": datetime.now(timezone.utc).isoformat(),
        "items": results[:24],
        "errors": errors,
    }


def _json_from_host(url: str, host: str):
    payload = _fetch_https(url, host, WEATHER_MAX_BYTES)
    data = json.loads(payload.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("weather service returned an invalid response")
    return data


def refresh_weather(city: str, progress=None):
    city = " ".join(str(city or "").split())
    if not city or len(city) > 80 or any(ord(ch) < 32 for ch in city):
        raise ValueError("enter a city name (maximum 80 characters)")
    if progress:
        progress(8, "GEOCODING", "Finding " + city,
                 "Resolving the city using Open-Meteo geocoding.")
    geo_url = "https://%s/v1/search?%s" % (
        WEATHER_GEO_HOST,
        urllib.parse.urlencode({"name": city, "count": 5, "language": "en", "format": "json"}),
    )
    geo = _json_from_host(geo_url, WEATHER_GEO_HOST)
    places = geo.get("results") or []
    if not places:
        raise RuntimeError("city not found: " + city)
    place = places[0]
    try:
        latitude, longitude = float(place["latitude"]), float(place["longitude"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("geocoding returned invalid coordinates")
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ValueError("geocoding returned out-of-range coordinates")
    if progress:
        progress(42, "FORECAST", "Loading forecast for " + str(place.get("name", city)),
                 "Fetching current conditions and a seven-day forecast.")
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,wind_speed_10m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "forecast_days": 7,
        "timezone": "auto",
    }
    url = "https://%s/v1/forecast?%s" % (WEATHER_API_HOST, urllib.parse.urlencode(params))
    forecast = _json_from_host(url, WEATHER_API_HOST)
    current = forecast.get("current") or {}
    daily = forecast.get("daily") or {}
    dates = daily.get("time") or []
    days = []
    for index, day in enumerate(dates[:7]):
        def value(key):
            values = daily.get(key) or []
            return values[index] if index < len(values) else None
        days.append({
            "date": day,
            "code": value("weather_code"),
            "high": value("temperature_2m_max"),
            "low": value("temperature_2m_min"),
            "rain_probability": value("precipitation_probability_max"),
        })
    if progress:
        progress(100, "COMPLETED", "Forecast ready",
                 "Current conditions and %d forecast days loaded." % len(days))
    return {
        "ok": True,
        "city": str(place.get("name") or city)[:80],
        "country": str(place.get("country") or "")[:80],
        "admin1": str(place.get("admin1") or "")[:80],
        "latitude": latitude,
        "longitude": longitude,
        "timezone": str(forecast.get("timezone") or "")[:80],
        "updated": datetime.now(timezone.utc).isoformat(),
        "current": {
            key: current.get(key) for key in (
                "temperature_2m", "relative_humidity_2m",
                "apparent_temperature", "is_day", "precipitation",
                "weather_code", "wind_speed_10m",
            )
        },
        "days": days,
    }
