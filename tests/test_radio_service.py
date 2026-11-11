from __future__ import annotations

from service import voiddesk_service as service


def test_radio_catalogue_exposes_only_stable_station_ids():
    response = service.h_radio_list({})
    assert response["ok"] is True
    stations = response["stations"]
    assert len(stations) >= 5
    assert len({item["id"] for item in stations}) == len(stations)
    assert all(item["url"].startswith(("http://", "https://")) for item in stations)


def test_radio_play_rejects_unlisted_station_ids(monkeypatch):
    calls = []
    monkeypatch.setattr(
        service.iptv_module, "play_audio",
        lambda *args: calls.append(args) or (True, None),
    )
    response = service.h_radio_play({"id": "https://attacker.invalid/stream"})
    assert response["ok"] is False
    assert response["error"] == "unknown radio station"
    assert calls == []


def test_radio_play_uses_server_side_station_allowlist(monkeypatch):
    calls = []
    monkeypatch.setattr(
        service.iptv_module, "play_audio",
        lambda *args: calls.append(args) or (True, None),
    )
    station = service.RADIO_STATIONS["rai-radio-1"]
    response = service.h_radio_play({"id": "rai-radio-1"})
    assert response == {
        "ok": True, "state": "playing", "station": station["name"]
    }
    assert calls == [(station["url"], station["name"])]


def test_radio_stop_stops_only_the_audio_player(monkeypatch):
    calls = []
    monkeypatch.setattr(
        service.iptv_module, "stop_audio",
        lambda: calls.append("stop"),
    )
    response = service.h_radio_stop({})
    assert response == {"ok": True, "state": "idle"}
    assert calls == ["stop"]
