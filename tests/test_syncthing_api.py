from desk.syncthing_api import perform_action


def test_folder_pause_uses_granular_config_endpoint_and_preserves_other_fields():
    calls = []
    folder = {"id": "folder/one", "label": "ROMs", "paused": False,
              "path": "/mnt/mmc/ROMS", "devices": [{"deviceID": "peer"}]}

    def rest(url, key, path, method="GET", payload=None):
        calls.append((path, method, payload))
        if method == "GET":
            return dict(folder)
        return {}

    result = perform_action(rest, "http://127.0.0.1:7070", "secret",
                            "toggle_folder", folder="folder/one")
    assert result == {"ok": True, "paused": True}
    assert calls[0] == ("/rest/config/folders/folder%2Fone", "GET", None)
    assert calls[1][0] == "/rest/config/folders/folder%2Fone"
    assert calls[1][1] == "PUT"
    assert calls[1][2]["paused"] is True
    assert calls[1][2]["devices"] == folder["devices"]


def test_folder_scan_and_override_use_post_endpoints():
    calls = []

    def rest(url, key, path, method="GET", payload=None):
        calls.append((path, method))
        return {}

    assert perform_action(rest, "u", "k", "scan", folder="roms")["ok"]
    assert perform_action(rest, "u", "k", "override", folder="roms")["ok"]
    assert calls == [
        ("/rest/db/scan?folder=roms", "POST"),
        ("/rest/db/override?folder=roms", "POST"),
    ]


def test_device_pause_and_resume_use_encoded_device_id():
    calls = []

    def rest(url, key, path, method="GET", payload=None):
        calls.append((path, method))
        return {}

    perform_action(rest, "u", "k", "pause_device", device="id/with spaces")
    perform_action(rest, "u", "k", "resume_device", device="peer")
    assert calls == [
        ("/rest/system/pause?device=id%2Fwith%20spaces", "POST"),
        ("/rest/system/resume?device=peer", "POST"),
    ]


def test_invalid_syncthing_actions_are_rejected_without_requests():
    calls = []

    def rest(*args, **kwargs):
        calls.append(args)
        return {}

    result = perform_action(rest, "u", "k", "delete_everything", folder="x")
    assert result["ok"] is False
    assert calls == []
