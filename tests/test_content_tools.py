import importlib.util
import json
from pathlib import Path
import pytest


ROOT = Path(__file__).resolve().parents[1]


def load_content_tools():
    path = ROOT / "service" / "content_tools.py"
    spec = importlib.util.spec_from_file_location("voiddesk_content_tools_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_service():
    path = ROOT / "service" / "voiddesk_service.py"
    spec = importlib.util.spec_from_file_location("voiddesk_content_service_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_rss_strips_markup_and_accepts_rss_atoms():
    tools = load_content_tools()
    xml = b"""<?xml version="1.0"?>
    <rss version="2.0"><channel><item>
      <title>  A &amp; B  </title>
      <link>https://example.org/story</link>
      <description><![CDATA[<p>Useful <b>update</b> &amp; details</p>]]></description>
      <pubDate>Fri, 13 Nov 2026 12:00:00 GMT</pubDate>
    </item></channel></rss>"""
    rows = tools.parse_rss(xml, "Fixture")
    assert rows == [{
        "source": "Fixture",
        "title": "A & B",
        "summary": "Useful update & details",
        "url": "https://example.org/story",
        "published": "Fri, 13 Nov 2026 12:00:00 GMT",
    }]

    atom = b"""<feed xmlns="http://www.w3.org/2005/Atom">
      <entry><title>Atom story</title>
      <link rel="alternate" href="https://example.org/atom"/>
      <summary>Atom summary</summary><updated>2026-11-13T12:00:00Z</updated>
      </entry></feed>"""
    assert tools.parse_rss(atom, "Atom")[0]["url"] == "https://example.org/atom"


def test_parse_rss_rejects_dtd_oversized_and_unsafe_links():
    tools = load_content_tools()
    with pytest.raises(ValueError, match="forbidden"):
        tools.parse_rss(b'<!DOCTYPE feed [<!ENTITY x "boom">]><rss/>', "bad")
    with pytest.raises(ValueError, match="size"):
        tools.parse_rss(b"x" * (tools.RSS_MAX_BYTES + 1), "large")
    unsafe = b"""<rss><channel><item><title>bad</title>
      <link>javascript:alert(1)</link></item></channel></rss>"""
    assert tools.parse_rss(unsafe, "unsafe") == []


def test_refresh_rss_uses_only_selected_allowlisted_feeds(monkeypatch):
    tools = load_content_tools()
    fixture = b"""<rss><channel><item><title>One</title>
      <link>https://example.org/one</link></item></channel></rss>"""
    requested = []
    monkeypatch.setattr(
        tools, "_fetch_https",
        lambda url, host, max_bytes, timeout=6.0:
            (requested.append((url, host, max_bytes)) or fixture),
    )
    progress = []
    result = tools.refresh_rss("news", "it",
        lambda *args: progress.append(args))
    assert result["ok"] is True
    assert len(result["items"]) == 2
    assert len(requested) == 2
    assert all(row[1] in ("www.ansa.it", "www.ilpost.it") for row in requested)
    assert progress[-1][0] == 100
    with pytest.raises(ValueError, match="unsupported"):
        tools.refresh_rss("unlisted", "it")


def test_weather_geocoding_and_forecast_are_validated(monkeypatch):
    tools = load_content_tools()
    responses = [
        {"results": [{
            "name": "Milano", "country": "Italy", "admin1": "Lombardy",
            "latitude": 45.4642, "longitude": 9.19,
        }]},
        {
            "timezone": "Europe/Rome",
            "current": {
                "temperature_2m": 14.2, "relative_humidity_2m": 70,
                "apparent_temperature": 13.0, "is_day": 1,
                "precipitation": 0.0, "weather_code": 2, "wind_speed_10m": 8.0,
            },
            "daily": {
                "time": ["2026-11-13", "2026-11-14"],
                "weather_code": [2, 61],
                "temperature_2m_max": [16, 14],
                "temperature_2m_min": [10, 8],
                "precipitation_probability_max": [10, 65],
            },
        },
    ]
    requested = []
    monkeypatch.setattr(
        tools, "_json_from_host",
        lambda url, host: (requested.append((url, host)) or responses.pop(0)),
    )
    progress = []
    result = tools.refresh_weather(" Milano ",
        lambda *args: progress.append(args))
    assert result["ok"] is True
    assert result["city"] == "Milano"
    assert result["country"] == "Italy"
    assert result["current"]["temperature_2m"] == 14.2
    assert len(result["days"]) == 2
    assert requested[0][1] == tools.WEATHER_GEO_HOST
    assert requested[1][1] == tools.WEATHER_API_HOST
    assert progress[-1][0] == 100


def test_weather_rejects_empty_city_and_out_of_range_geocoding(monkeypatch):
    tools = load_content_tools()
    with pytest.raises(ValueError, match="city name"):
        tools.refresh_weather(" ")
    monkeypatch.setattr(tools, "_json_from_host", lambda *_: {
        "results": [{"name": "Invalid", "latitude": 900, "longitude": 0}]
    })
    with pytest.raises(ValueError, match="out-of-range"):
        tools.refresh_weather("Invalid")




def test_rss_job_is_supervised_and_duplicate_requests_reuse_running_job(tmp_path, monkeypatch):
    service = load_service()
    monkeypatch.setattr(service, "DATA", tmp_path)
    monkeypatch.setattr(service, "APP_DIR", ROOT)
    service._JOBS.clear()
    spawned = []

    class FakeProcess:
        pid = 98765
        def poll(self):
            return None

    def fake_popen(args, **kwargs):
        spawned.append((args, kwargs))
        return FakeProcess()

    monkeypatch.setattr(service.subprocess, "Popen", fake_popen)
    args = {
        "service_task": "rss_refresh", "category": "tech",
        "language": "en", "name": "Refresh RSS",
    }
    first = service.h_job_start(args)
    second = service.h_job_start(args)
    assert first["ok"] is True
    assert second["ok"] is True
    assert second["already"] is True
    assert first["job"]["id"] == second["job"]["id"]
    assert len(spawned) == 1
    assert spawned[0][0][-3:] == ["rss", "tech", "en"]
    assert first["job"]["progress"] == 0
    service._JOBS.clear()


def test_service_content_cache_and_job_allowlists(tmp_path, monkeypatch):
    service = load_service()
    monkeypatch.setattr(service, "DATA", tmp_path)
    assert service.h_rss_cache({}) == {"ok": True, "cached": False}
    (tmp_path / "rss_cache.json").write_text(json.dumps({
        "ok": True, "items": [{"title": "Sample"}],
    }), encoding="utf-8")
    assert service.h_rss_cache({})["items"][0]["title"] == "Sample"
    assert service.h_job_start({
        "service_task": "rss_refresh", "category": "malware",
    })["ok"] is False
    assert service.h_job_start({
        "service_task": "weather_refresh", "city": "",
    })["ok"] is False



def test_parse_rss_rejects_doctype_beyond_initial_prefix():
    tools = load_content_tools()
    xml = (
        b'<?xml version="1.0"?>'
        + (b" " * 9000)
        + b'<!DOCTYPE rss [<!ENTITY expansion "unsafe">]>'
        + b'<rss><channel><item><title>&expansion;</title>'
        + b'<link>https://example.org/story</link></item></channel></rss>'
    )
    with pytest.raises(ValueError, match="forbidden document declaration"):
        tools.parse_rss(xml, "Untrusted")
