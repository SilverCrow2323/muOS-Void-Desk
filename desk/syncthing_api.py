"""Safe, small Syncthing REST actions used by Void Desk's native panel."""
from __future__ import annotations

from urllib.parse import quote


def perform_action(rest, url, key, action, *, folder=None, device=None):
    """Perform one allowlisted folder/device operation through the REST API."""
    if action in ("pause_folder", "resume_folder", "toggle_folder"):
        if not folder:
            return {"ok": False, "error": "folder ID is required"}
        encoded = quote(str(folder), safe="")
        endpoint = "/rest/config/folders/" + encoded
        config = rest(url, key, endpoint)
        if not isinstance(config, dict):
            return {"ok": False, "error": "invalid folder configuration"}
        paused = bool(config.get("paused"))
        config["paused"] = (not paused if action == "toggle_folder"
                            else action == "pause_folder")
        rest(url, key, endpoint, method="PUT", payload=config)
        return {"ok": True, "paused": config["paused"]}

    if action in ("scan", "override"):
        if not folder:
            return {"ok": False, "error": "folder ID is required"}
        encoded = quote(str(folder), safe="")
        endpoint = "/rest/db/" + action + "?folder=" + encoded
        rest(url, key, endpoint, method="POST")
        return {"ok": True, "action": action}

    if action in ("pause_device", "resume_device", "toggle_device"):
        if not device:
            return {"ok": False, "error": "device ID is required"}
        encoded = quote(str(device), safe="")
        pause = action == "pause_device"
        if action == "toggle_device":
            pause = not bool(rest(url, key, "/rest/system/connections")
                             .get("connections", {}).get(str(device), {})
                             .get("paused"))
        endpoint = "/rest/system/" + ("pause" if pause else "resume")
        rest(url, key, endpoint + "?device=" + encoded, method="POST")
        return {"ok": True, "paused": pause}

    return {"ok": False, "error": "unsupported Syncthing action"}
