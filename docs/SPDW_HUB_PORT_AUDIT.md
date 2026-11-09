# SPDW Hub — Port and Service Audit

**Scope:** code currently present in Void Desk and Rt:Tailscale-M as inspected for
the 10.5.4 work branch. This is a source-level audit, not a live `ss -lntup`
scan of a handheld or PC. Configured defaults are not proof that a service is
currently listening.

## 1. Management and companion listeners

| Host | Port | Component | Current behavior | SPDW Hub target |
|---|---:|---|---|---|
| muOS handheld | TCP 8765 | SPDW Device Agent (inside existing Void Desk service process) | Binds `0.0.0.0`; public discovery/health and PIN-paired session + CSRF-protected file APIs | **Implemented on this branch**; single service-owned gateway and legacy-compatible file routes |
| muOS handheld | TCP 8077 | Rt:Tailscale-M web panel | Config default; bind default `0.0.0.0`; PIN login, HMAC session cookie, CSRF checks and failed-login lockout | Bind to loopback and expose through the Hub module route |
| PC | TCP 8420 | BaseStation / SPDW Hub PC daemon | Discovery at `/ping`; telemetry at `/stats`; authenticated device APIs; browser dashboard at `/` | **Implemented on this branch**; the web dashboard shares the existing PC Link listener |
| PC / handheld | TCP 22 | SSH | SSH transport, commonly also provides SFTP subsystem | Retain where enabled; use the same connection for terminal and file transfer |
| Handheld profile default | TCP 2022 | SFTP | Separate SFTP profile default in BaseStation, not proof of a live independent listener | Detect whether SFTP is available over SSH first; keep 2022 only where the installed image really requires it |

### Handheld Device Agent — migration status

The former Pygame-owned `ThreadingHTTPServer` on TCP `8765` has been removed
from `desk/main.py`. The existing `service/voiddesk_service.py` process now
starts `service/spdw_hub/device_agent.py` on the same port, so this migration
does not add a second daemon or a new listener.

The gateway persists a generated pairing PIN and secret under
`data/spdw_hub/device_agent.json`, protects browser access with a session
cookie and CSRF token, rate-limits failed PIN attempts, caps request bodies,
canonicalizes paths through symlinks, and writes uploads atomically without
overwriting existing files. The existing browser routes
`/api/list`, `/api/read`, `/api/download`, `/api/upload`, `/api/mkdir`,
`/api/newfile`, `/api/write` and `/api/delete` are retained behind the
authenticated gateway for UI compatibility.

This is a source-level implementation and automated-test addition. It still
requires a real muOS hardware run and a live socket/process audit before the
port can be marked release-verified. The legacy unauthenticated handler is no
longer the intended runtime owner.

### Rt:Tailscale-M panel

The current `muOS-Rt-Tailscale` source defaults to port `8077` and bind
`0.0.0.0`. The panel has a PIN, HMAC-signed session cookie, CSRF checks and
IP-based login lockout. It still uses plain HTTP: its upstream security notes
explicitly prohibit Internet exposure and recommend loopback plus SSH tunnel
or Tailscale Serve for remote access. The Hub migration must preserve its
authentication and use an encrypted remote path; a trusted gateway is not a
reason to skip its auth migration tests.

Source checked: `SilverCrow2323/muOS-Rt-Tailscale` at
`d6aa05363cd5d56b07e63e2261c960a26d73cd9c`.

### PC Link / BaseStation daemon

The PC Link client in `desk/pcuplink.py` discovers BaseStation on port
`8420` via `/ping` and polls `/stats`, `/outbox` and per-device routes.
The BaseStation PC companion is the natural place for the PC dashboard and
existing SSH/SFTP tools. Avoid adding a separate dashboard server.

**Transport security limitation:** the current port 8420 compatibility API
uses plain HTTP with a bearer token in a request header. Authentication is
not encryption. Until HTTPS or an equivalent authenticated tunnel is enforced,
use this API only on a trusted LAN or through Tailscale; do not forward it to
the public Internet or use it on an untrusted network.

## 2. Configured optional service defaults

These are entries in BaseStation's service profile and scanner, not an assertion
that all of them run simultaneously:

| Port | Profile label | Notes |
|---:|---|---|
| TCP 8080 | Virtual Terminal (Web) | Optional external web service |
| TCP 9090 | FileBrowser (Web) | Optional external web service |
| TCP 7070 | Syncthing (Web) | Optional external web service |
| TCP 22 | SSH | Main SSH transport |
| TCP 2022 | SFTP | Separate profile default; check whether needed |

The Hub should discover and report these services, not start duplicate copies
or assume every profile is active.

The PC daemon now serves the browser-based SPDW Hub at `http://<PC-IP>:8420/`
on the same listener used by PC Link. The page authenticates using the existing
PC Link bearer token and offers host/device telemetry, notifications,
screenshot requests and downloads from the per-device received-file inbox.
It does not open an additional HTTP port.

## 3. Sunshine / Moonlight transport

Sunshine has a web UI and a GameStream transport family. Its current
configuration documentation defines a base port (default `47989`) and a
`bind_address` setting; it also permits restricting the web UI's allowed
origin to localhost, LAN or WAN. The Hub should bind the web UI to loopback
where supported and route management through its own dashboard.

The stream transport is different: Moonlight/Sunshine uses dedicated TCP and
UDP traffic. Those ports cannot be collapsed into the Hub's single HTTP
listener without breaking streaming. Manage the web UI and daemon lifecycle
through an add-on; retain only the media ports actually required by the
installed Sunshine configuration and Moonlight client.

Useful upstream references:
- https://docs.lizardbyte.dev/projects/sunshine/latest/md_docs_2configuration.html
- https://docs.lizardbyte.dev/projects/sunshine/v0.21.0/about/advanced_usage.html

## 4. Ownership target

| Service | Owner after migration | Listener policy |
|---|---|---|
| Device HTTP API + file portal | SPDW Device Agent | One LAN/Tailscale management listener |
| Rt:Tailscale UI/API | SPDW Tailscale add-on | In-process module or loopback-only legacy panel |
| PC Link API + PC dashboard | SPDW Hub PC / BaseStation | One PC management listener |
| SSH + SFTP | System SSH daemon | One SSH port where the installed subsystem supports it |
| Sunshine management UI | RT Stream add-on | Loopback-only management UI behind PC Hub |
| Sunshine streaming | Sunshine daemon | Only required TCP/UDP media ports |
| Syncthing/FileBrowser/other web apps | Respective existing services | Prefer API/SSH adapters; no duplicate Hub-managed web listeners |

## 5. Machine-readable registry

The initial source-of-truth inventory is
`service/spdw_hub/services.json`; its passive validator is
`service/spdw_hub/registry.py`. It separates listeners from protocol
subsystems, optional profile defaults and protocol families. This prevents
an SSH SFTP subsystem from being counted as a second socket and keeps the
Sunshine media transport distinct from the HTTP management gateway.

The registry validates socket collisions across both ordinary listeners and
protocol-family members. Sunshine's TCP 47990 Web UI is represented once as
the separately managed, loopback-only listener; the transport family lists
the remaining TCP/UDP GameStream sockets without duplicating that endpoint.

The registry describes target/migration policy, not live state. It must be
compared with the active socket/process scan before a listener is changed.

## 6. Live audit command set

Before changing any bind address or stopping a legacy service, collect this
from each device:

```sh
ss -lntup 2>/dev/null || netstat -lntup
ps -ef
```

Then correlate PID/program with the Hub service registry. The release audit
must report: address, port, protocol, process, owning module, auth model,
whether externally reachable, and whether the listener is required.

Do not disable a port based only on a default value in a profile. The active
process table and a real client connection test are required.
