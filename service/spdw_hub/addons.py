# -*- coding: utf-8 -*-
"""SPDW Hub add-on manifest validation and discovery.

Discovery is deliberately non-executing: reading a manifest never imports or
runs add-on code. A separate, permission-aware runtime will own activation.
"""
from __future__ import print_function

import json
import re
from pathlib import Path


ADDON_SCHEMA = "spdw-addon"
ADDON_VERSION = 1
ADDON_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,63}$")
CAPABILITIES = {
    "device.status.read",
    "device.screenshot",
    "files.read",
    "files.write",
    "files.delete",
    "sync.run",
    "backup.create",
    "terminal.ssh",
    "terminal.exec",
    "packages.read",
    "packages.install",
    "packages.remove",
    "network.status.read",
    "network.manage",
    "tailscale.manage",
    "stream.status.read",
    "stream.manage",
    "services.status.read",
    "services.manage",
    "device.power",
}
HOSTS = {"pc", "handheld", "both"}
LISTENER_PROTOCOLS = {"tcp", "udp"}
LISTENER_BINDS = {"loopback", "lan", "tailnet"}
DESTRUCTIVE_CAPABILITIES = {
    "files.write", "files.delete", "packages.install", "packages.remove",
    "network.manage", "tailscale.manage", "stream.manage", "services.manage",
    "device.power", "terminal.exec",
}


def _safe_relative_path(value):
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    raw_parts = value.split("/")
    if any(part in ("", ".", "..") for part in raw_parts):
        return False
    candidate = Path(value)
    return not candidate.is_absolute() and bool(candidate.parts)


def validate_addon_manifest(manifest, addon_dir=None):
    """Return validation errors for one add-on manifest."""
    errors = []
    if not isinstance(manifest, dict):
        return ["manifest must be an object"]
    if manifest.get("schema") != ADDON_SCHEMA:
        errors.append("unsupported add-on schema")
    if manifest.get("manifest_version") != ADDON_VERSION:
        errors.append("unsupported add-on manifest version")

    addon_id = manifest.get("id")
    if not isinstance(addon_id, str) or not ADDON_ID_RE.match(addon_id):
        errors.append("id must be 2-64 lowercase letters, digits, dots, underscores or hyphens")
    for field in ("name", "version", "description", "author"):
        value = manifest.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append("{} is required".format(field))

    host = manifest.get("host")
    if host not in HOSTS:
        errors.append("host must be pc, handheld or both")

    entrypoint = manifest.get("entrypoint")
    if not _safe_relative_path(entrypoint):
        errors.append("entrypoint must be a safe relative path")
    elif addon_dir is not None:
        root = Path(addon_dir).resolve()
        target = (root / entrypoint).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            errors.append("entrypoint resolves outside its add-on directory")
        else:
            if not target.is_file():
                errors.append("entrypoint file does not exist")

    ui = manifest.get("ui")
    if not isinstance(ui, dict):
        errors.append("ui must be an object")
    else:
        route = ui.get("route")
        if (not isinstance(route, str) or not route.startswith("/addons/")
                or ".." in route or "\\" in route):
            errors.append("ui.route must be a safe /addons/ route")

    capabilities = manifest.get("capabilities", [])
    if not isinstance(capabilities, list):
        errors.append("capabilities must be a list")
        capabilities = []
    unknown = sorted(set(x for x in capabilities if isinstance(x, str)) - CAPABILITIES)
    if unknown:
        errors.append("unknown capabilities: {}".format(", ".join(unknown)))
    if any(not isinstance(x, str) for x in capabilities):
        errors.append("capabilities must contain only strings")

    confirmation = manifest.get("confirmation_actions", [])
    if not isinstance(confirmation, list):
        errors.append("confirmation_actions must be a list")
        confirmation = []
    missing_confirm = sorted(
        (set(capabilities) & DESTRUCTIVE_CAPABILITIES) - set(confirmation))
    if missing_confirm:
        errors.append("destructive capabilities need confirmation_actions: {}".format(
            ", ".join(missing_confirm)))

    listeners = manifest.get("listeners", [])
    if not isinstance(listeners, list):
        errors.append("listeners must be a list")
        listeners = []
    for index, listener in enumerate(listeners):
        label = "listeners[{}]".format(index)
        if not isinstance(listener, dict):
            errors.append("{} must be an object".format(label))
            continue
        if listener.get("host") not in HOSTS:
            errors.append("{} has invalid host".format(label))
        if listener.get("protocol") not in LISTENER_PROTOCOLS:
            errors.append("{} has invalid protocol".format(label))
        port = listener.get("port")
        if not isinstance(port, int) or not 1 <= port <= 65535:
            errors.append("{} has invalid port".format(label))
        if listener.get("bind") not in LISTENER_BINDS:
            errors.append("{} bind must be loopback, lan or tailnet".format(label))
        if listener.get("bind") in ("lan", "tailnet"):
            if listener.get("auth") in (None, "", "none"):
                errors.append("{} externally reachable listener requires auth".format(label))
            if not isinstance(listener.get("reason"), str) or not listener["reason"].strip():
                errors.append("{} externally reachable listener requires a reason".format(label))

    dependencies = manifest.get("dependencies", {})
    if not isinstance(dependencies, dict):
        errors.append("dependencies must be an object")
    else:
        for key in ("binaries", "python_modules", "services", "addons"):
            value = dependencies.get(key, [])
            if not isinstance(value, list) or any(not isinstance(x, str) for x in value):
                errors.append("dependencies.{} must be a list of strings".format(key))

    return errors


def discover_addons(roots):
    """Read add-on manifests without importing their entrypoints.

    Returns records with manifest, path, enabled=False and validation errors.
    Activation is intentionally a later, explicit operation.
    """
    found = []
    seen_ids = set()
    for root in roots or []:
        base = Path(root)
        if not base.is_dir():
            continue
        for directory in sorted(base.iterdir(), key=lambda p: p.name.lower()):
            if not directory.is_dir():
                continue
            manifest_path = directory / "addon.json"
            if not manifest_path.is_file():
                continue
            try:
                with manifest_path.open("r", encoding="utf-8") as stream:
                    manifest = json.load(stream)
                errors = validate_addon_manifest(manifest, directory)
            except (OSError, ValueError) as exc:
                manifest = None
                errors = ["unable to read manifest: {}".format(exc)]
            addon_id = manifest.get("id") if isinstance(manifest, dict) else None
            if addon_id and addon_id in seen_ids:
                errors.append("duplicate add-on id: {}".format(addon_id))
            elif addon_id:
                seen_ids.add(addon_id)
            found.append({
                "id": addon_id,
                "name": manifest.get("name", directory.name) if isinstance(manifest, dict) else directory.name,
                "path": str(directory),
                "manifest": manifest,
                "errors": errors,
                "valid": not errors,
                "enabled": False,
            })
    return found
