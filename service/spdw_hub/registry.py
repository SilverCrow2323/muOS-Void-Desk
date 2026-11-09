# -*- coding: utf-8 -*-
"""SPDW Hub service registry validation.

This module is intentionally passive: it audits declared services and never
opens sockets, kills processes or changes firewall rules.
"""
from __future__ import print_function

import json
from pathlib import Path


REGISTRY_SCHEMA = "spdw-service-registry"
REGISTRY_VERSION = 1
VALID_HOSTS = {"pc", "handheld"}
VALID_PROTOCOLS = {"tcp", "udp"}
VALID_BINDS = {"all", "loopback", "specific", "system", "unknown"}
VALID_EXPOSURES = {"lan", "tailnet", "lan-or-tailnet", "loopback",
                   "transport", "same-as-parent", "unknown"}
VALID_AUTH = {"none", "spdw-pairing-session", "device-token",
              "rt-pin-session+csrf", "sunshine-native-auth",
              "ssh-host-auth", "managed-by-host", "unknown"}


class RegistryError(ValueError):
    """Raised when the service registry violates the Hub's port policy."""


def default_registry_path():
    return Path(__file__).resolve().with_name("services.json")


def load_registry(path=None):
    """Load and validate the service registry from JSON."""
    source = Path(path) if path is not None else default_registry_path()
    with source.open("r", encoding="utf-8") as stream:
        data = json.load(stream)
    errors = validate_registry(data)
    if errors:
        raise RegistryError("; ".join(errors))
    return data


def validate_registry(data):
    """Return every policy/schema error; return [] when the registry is valid."""
    errors = []
    if not isinstance(data, dict):
        return ["registry root must be an object"]
    if data.get("schema") != REGISTRY_SCHEMA:
        errors.append("unsupported registry schema")
    if data.get("version") != REGISTRY_VERSION:
        errors.append("unsupported registry version")

    services = data.get("services")
    if not isinstance(services, list):
        return errors + ["services must be a list"]

    ids = {}
    listener_keys = {}
    external_management = {}
    for index, item in enumerate(services):
        prefix = "services[{}]".format(index)
        if not isinstance(item, dict):
            errors.append("{} must be an object".format(prefix))
            continue
        service_id = item.get("id")
        if not isinstance(service_id, str) or not service_id.strip():
            errors.append("{} requires a non-empty id".format(prefix))
            continue
        if service_id in ids:
            errors.append("duplicate service id: {}".format(service_id))
            continue
        ids[service_id] = item

        item_type = item.get("type")
        if item_type == "protocol-family":
            base = item.get("base_port")
            if not isinstance(base, int) or not 1 <= base <= 65535:
                errors.append("{} has invalid base_port".format(service_id))
            members = item.get("members")
            if not isinstance(members, list) or not members:
                errors.append("{} must declare protocol-family members".format(service_id))
            else:
                for member in members:
                    if not isinstance(member, dict):
                        errors.append("{} contains an invalid port member".format(service_id))
                        continue
                    port = member.get("port")
                    proto = member.get("protocol")
                    if not isinstance(port, int) or not 1 <= port <= 65535:
                        errors.append("{} has an invalid member port".format(service_id))
                    if proto not in VALID_PROTOCOLS:
                        errors.append("{} has an invalid member protocol".format(service_id))
            continue

        if item_type in ("addon", "profile-default", "subsystem"):
            if item_type == "subsystem":
                parent = item.get("shares_listener_with")
                if not isinstance(parent, str) or not parent:
                    errors.append("{} must name its parent listener".format(service_id))
            continue

        if item_type != "listener":
            errors.append("{} has unsupported type {!r}".format(service_id, item_type))
            continue

        host = item.get("host")
        protocol = item.get("protocol")
        port = item.get("port")
        bind = item.get("bind")
        exposure = item.get("exposure")
        auth = item.get("auth")
        owner = item.get("owner")
        if host not in VALID_HOSTS:
            errors.append("{} has invalid host role".format(service_id))
        if protocol not in VALID_PROTOCOLS:
            errors.append("{} has invalid protocol".format(service_id))
        if not isinstance(port, int) or not 1 <= port <= 65535:
            errors.append("{} has invalid port".format(service_id))
        if bind not in VALID_BINDS:
            errors.append("{} has invalid bind policy".format(service_id))
        if exposure not in VALID_EXPOSURES:
            errors.append("{} has invalid exposure policy".format(service_id))
        if auth not in VALID_AUTH:
            errors.append("{} has invalid auth model".format(service_id))
        if not isinstance(owner, str) or not owner.strip():
            errors.append("{} requires an owning component".format(service_id))

        if (bind == "all" and exposure in ("lan", "tailnet", "lan-or-tailnet")
                and auth == "none"):
            errors.append("{} is externally exposed without authentication".format(service_id))

        if host in VALID_HOSTS and protocol in VALID_PROTOCOLS and isinstance(port, int):
            key = (host, protocol, port)
            if key in listener_keys:
                errors.append("listener collision {}: {} and {}".format(
                    key, listener_keys[key], service_id))
            else:
                listener_keys[key] = service_id

        if (item.get("management") is True
                and exposure in ("lan", "tailnet", "lan-or-tailnet")):
            external_management[host] = external_management.get(host, 0) + 1
            if external_management[host] > 1:
                errors.append("{} creates a second externally reachable management listener on {}".format(
                    service_id, host))

    for item in services:
        if not isinstance(item, dict) or item.get("type") != "subsystem":
            continue
        parent = ids.get(item.get("shares_listener_with"))
        if parent is None:
            errors.append("{} references an unknown parent listener".format(item.get("id")))
        elif parent.get("type") != "listener":
            errors.append("{} parent is not a listener".format(item.get("id")))
        elif (item.get("host") != parent.get("host")
              or item.get("port") != parent.get("port")
              or item.get("protocol") != parent.get("protocol")):
            errors.append("{} must inherit host, port and protocol from its parent".format(
                item.get("id")))

    return errors


def listeners_for_host(data, host, include_loopback=True):
    """Return declared listeners for a PC or handheld role."""
    if host not in VALID_HOSTS:
        raise ValueError("host must be 'pc' or 'handheld'")
    listeners = []
    for item in data.get("services", []):
        if not isinstance(item, dict) or item.get("type") != "listener":
            continue
        if item.get("host") != host:
            continue
        if not include_loopback and item.get("exposure") == "loopback":
            continue
        listeners.append(item)
    return sorted(listeners, key=lambda item: (item.get("port", 0), item.get("id", "")))


def port_audit(data):
    """Produce a stable, machine-readable port audit grouped by host role."""
    result = {}
    for host in sorted(VALID_HOSTS):
        result[host] = [
            {
                "id": item.get("id"),
                "port": item.get("port"),
                "protocol": item.get("protocol"),
                "bind": item.get("bind"),
                "exposure": item.get("exposure"),
                "owner": item.get("owner"),
                "auth": item.get("auth"),
                "management": bool(item.get("management")),
                "state": item.get("state", "unknown"),
            }
            for item in listeners_for_host(data, host)
        ]
    return result
