from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "service" / "iptv_module.py"
SERVICE_PATH = ROOT / "service" / "voiddesk_service.py"


def load_iptv_module():
    spec = importlib.util.spec_from_file_location("voiddesk_iptv_module_test", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_feed_urls_require_public_http_and_https_hosts():
    module = load_iptv_module()

    assert module.validate_feed_url(
        "https://example.org/guide.xml", resolve=False
    ) == "https://example.org/guide.xml"

    for url in (
        "file:///etc/passwd",
        "ftp://example.org/guide.xml",
        "http://localhost/guide.xml",
        "http://127.0.0.1/guide.xml",
        "http://10.0.0.8/guide.xml",
        "http://192.168.1.20/guide.xml",
        "https://user:password@example.org/guide.xml",
        "https://router.local/guide.xml",
    ):
        with pytest.raises(ValueError):
            module.validate_feed_url(url, resolve=False)


def test_stream_urls_allow_lan_media_but_not_local_files_or_player_options():
    module = load_iptv_module()

    assert module.validate_stream_url(
        "http://192.168.1.20:8080/live.m3u8"
    ) == "http://192.168.1.20:8080/live.m3u8"

    for url in (
        "file:///etc/passwd",
        "ftp://example.org/video",
        "--script=/tmp/evil.lua",
        "https://user:password@example.org/live.m3u8",
    ):
        with pytest.raises(ValueError):
            module.validate_stream_url(url)


def test_m3u_parser_extracts_groups_and_rejects_non_network_entries():
    module = load_iptv_module()
    playlist = """#EXTM3U url-tvg="https://guide.example.org/xmltv.xml"
#EXTINF:-1 tvg-id="news.one" tvg-name="News One" group-title="News",News One HD
https://streams.example.org/news.m3u8
#EXTINF:-1 group-title="Local",Local private stream
rtsp://192.168.1.50:8554/live
#EXTINF:-1 group-title="Bad",Local file
file:///etc/passwd
"""
    result = module.parse_m3u(playlist)

    assert len(result["channels"]) == 2
    assert [item["group"] for item in result["channels"]] == ["News", "Local"]
    assert result["channels"][0]["name"] == "News One HD"
    assert result["channels"][0]["tvg_id"] == "news.one"
    assert result["groups"] == ["News", "Local"]
    assert result["epg_urls"] == ["https://guide.example.org/xmltv.xml"]


def test_xmltv_parser_selects_current_and_next_programme():
    module = load_iptv_module()
    now = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc).timestamp()
    xmltv = b"""<?xml version="1.0" encoding="UTF-8"?>
<tv>
  <channel id="news.one">
    <display-name>News One</display-name>
  </channel>
  <programme channel="news.one" start="20261111110000 +0000" stop="20261111130000 +0000">
    <title>Current bulletin</title><desc>Live news</desc>
  </programme>
  <programme channel="news.one" start="20261111130000 +0000" stop="20261111140000 +0000">
    <title>Next programme</title>
  </programme>
</tv>
"""
    parsed = module.parse_xmltv(xmltv)
    current, following = module.epg_now_next(
        parsed, {"tvg_id": "news.one", "name": "News One"}, now=now
    )

    assert current and current["title"] == "Current bulletin"
    assert following and following["title"] == "Next programme"


def test_xmltv_parser_rejects_dtd_and_entity_declarations():
    module = load_iptv_module()
    payload = b"""<!DOCTYPE tv [<!ENTITY x SYSTEM "file:///etc/passwd">]>
<tv><channel id="x"><display-name>&x;</display-name></channel></tv>"""
    with pytest.raises(ValueError, match="DTD and entity"):
        module.parse_xmltv(payload)


def test_player_rejects_non_network_url_before_spawning_process(monkeypatch):
    module = load_iptv_module()
    spawned = []

    def fake_popen(*args, **kwargs):
        spawned.append(args)
        raise AssertionError("mpv must not be started for a local-file URL")

    monkeypatch.setattr(module.subprocess, "Popen", fake_popen)
    assert not module.play("file:///etc/passwd", "invalid")
    assert spawned == []
    assert module.status()["state"] == "error"


def test_service_registers_iptv_bridge_commands_and_visual_capture_is_offline(monkeypatch):
    spec = importlib.util.spec_from_file_location("voiddesk_service_iptv_test", SERVICE_PATH)
    assert spec and spec.loader
    service = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(service)
    monkeypatch.setattr(service, "IS_VISUAL_CAPTURE", True)

    expected = {
        "iptv_get_config",
        "iptv_load_playlist",
        "iptv_load_epg",
        "iptv_epg_for",
        "iptv_play",
        "iptv_stop",
        "iptv_status",
    }
    assert expected <= set(service.HANDLERS)

    config = service.HANDLERS["iptv_get_config"]({})
    playlist = service.HANDLERS["iptv_load_playlist"]({"url": "unused"})
    epg = service.HANDLERS["iptv_load_epg"]({"urls": []})
    playback = service.HANDLERS["iptv_play"]({"url": "unused"})

    assert config["ok"] is True
    assert playlist["ok"] is True and playlist["count"] == 2
    assert epg["ok"] is True
    assert playback["ok"] is False
