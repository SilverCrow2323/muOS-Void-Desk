from __future__ import annotations

import gzip
import importlib.util
import ssl
import urllib.request
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "service" / "iptv_module.py"


def load_iptv():
    spec = importlib.util.spec_from_file_location("iptv_module_test", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_url_validation_separates_fetch_and_stream_schemes():
    module = load_iptv()
    assert module.validate_url("https://example.test/list.m3u") == "https://example.test/list.m3u"
    assert module.validate_url("rtsp://stream.example.test/live", stream=True).startswith("rtsp://")
    for url in ("file:///etc/passwd", "ftp://example.test/list", "https://user:pass@example.test/list"):
        with pytest.raises(ValueError):
            module.validate_url(url)
    with pytest.raises(ValueError):
        module.validate_url("rtmp://stream.example.test/live")


def test_default_tls_context_keeps_hostname_and_certificate_checks(monkeypatch):
    module = load_iptv()
    real_create = ssl.create_default_context
    captured = {}

    def recording_context(*args, **kwargs):
        context = real_create(*args, **kwargs)
        captured["context"] = context
        return context

    monkeypatch.setattr(module.ssl, "create_default_context", recording_context)
    module._opener()
    assert captured["context"].check_hostname is True
    assert captured["context"].verify_mode == ssl.CERT_REQUIRED


def test_https_redirect_cannot_downgrade_to_plain_http():
    module = load_iptv()
    redirect = module._SafeRedirectHandler()
    request = urllib.request.Request("https://example.test/list.m3u")
    with pytest.raises(ValueError, match="insecure redirect"):
        redirect.redirect_request(
            request, None, 302, "Found", {}, "http://example.test/list.m3u"
        )


def test_fetch_bytes_enforces_content_and_decompressed_size_limits(monkeypatch):
    module = load_iptv()

    class Headers(dict):
        pass

    class Response:
        def __init__(self, body, length):
            self.body = body
            self.headers = Headers({"Content-Length": str(length)})

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def geturl(self):
            return "https://example.test/list.m3u"

        def read(self, size):
            return self.body[:size]

    class Opener:
        def __init__(self, response):
            self.response = response

        def open(self, _request, timeout):
            assert timeout == 3
            return self.response

    monkeypatch.setattr(module, "_opener", lambda _ua=None: Opener(
        Response(b"12345", 5)
    ))
    with pytest.raises(ValueError, match="size limit"):
        module.fetch_bytes("https://example.test/list.m3u", timeout=3, max_bytes=4)

    expanded = b"A" * 100
    compressed = gzip.compress(expanded)
    monkeypatch.setattr(module, "_opener", lambda _ua=None: Opener(
        Response(compressed, len(compressed))
    ))
    with pytest.raises(ValueError, match="decompressed"):
        module.fetch_bytes(
            "https://example.test/list.m3u", timeout=3, max_bytes=32
        )


def test_m3u_parser_filters_unsafe_stream_and_epg_urls():
    module = load_iptv()
    playlist = """#EXTM3U url-tvg="https://epg.example.test/guide.xml,file:///etc/passwd"
#EXTINF:-1 tvg-id="news.1" group-title="News",Example News
https://stream.example.test/live.m3u8
#EXTINF:-1 group-title="Unsafe",Local file
file:///etc/passwd
#EXTINF:-1 group-title="Radio",Example Radio
rtsp://radio.example.test/live
"""
    parsed = module.parse_m3u(playlist)
    assert [item["name"] for item in parsed["channels"]] == [
        "Example News", "Example Radio"
    ]
    assert parsed["groups"] == ["News", "Radio"]
    assert parsed["epg_urls"] == ["https://epg.example.test/guide.xml"]
    assert len(parsed["channels"]) == 2


def test_xmltv_parser_rejects_dtd_and_entities():
    module = load_iptv()
    unsafe = b'<!DOCTYPE tv [<!ENTITY x "boom">]><tv><channel id="x"/></tv>'
    with pytest.raises(ValueError, match="declarations"):
        module.parse_xmltv(unsafe)


def test_mpv_receives_stream_url_after_option_terminator(tmp_path, monkeypatch):
    module = load_iptv()
    (tmp_path / "data").mkdir()
    module.APP_DIR = tmp_path

    class FakeProcess:
        pid = 321

        def poll(self):
            return None

        def terminate(self):
            return None

        def wait(self, timeout=None):
            return 0

        def kill(self):
            return None

    captured = {}

    def fake_popen(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return FakeProcess()

    monkeypatch.setattr(module.shutil, "which", lambda name: "/usr/bin/mpv" if name == "mpv" else None)
    monkeypatch.setattr(module.subprocess, "Popen", fake_popen)
    url = "https://stream.example.test/live.m3u8?token=a-b"
    assert module.play(url, "Example News") is True
    assert captured["args"][-2:] == ["--", url]
    assert captured["kwargs"]["start_new_session"] is True
    module.stop()


def test_mpv_rejects_non_stream_urls_before_spawning(monkeypatch):
    module = load_iptv()
    called = {"value": False}
    monkeypatch.setattr(module.shutil, "which", lambda _name: "/usr/bin/mpv")
    monkeypatch.setattr(
        module.subprocess, "Popen",
        lambda *_args, **_kwargs: called.update(value=True),
    )
    assert module.play("file:///etc/passwd", "Unsafe") is False
    assert called["value"] is False
