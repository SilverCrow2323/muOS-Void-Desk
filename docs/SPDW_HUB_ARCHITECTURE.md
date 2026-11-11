# SPDW Hub — Unified Connectivity Architecture

**Status:** architecture baseline for Void Desk 10.5.4  
**Role:** one operational control plane for Void Desk, muOS/Linux handhelds and the PC companion.

## 1. Product direction

SPDW Hub is not another standalone server. It is the shared connectivity and operations layer that unifies the existing tools.

- **Void Desk** remains the primary handheld application and the source of device identity, configuration and local actions.
- **SPDW Hub Device Agent** is the single management gateway on each handheld.
- **SPDW Hub PC / BaseStation** is the desktop companion and central operations dashboard.
- **Add-ons** extend the Hub through registered modules; they do not create independent user-facing portals or unmanaged listeners.

The target experience is one dashboard with device selection and tabs for Overview, Terminal, Files, Sync & Backup, Streaming, Network/Tailscale, App Catalog, Add-ons and Diagnostics.

## 2. Topology

```text
                         SPDW HUB — PC
  ┌─────────────────────────────────────────────────────────────┐
  │ Dashboard / Device inventory / Terminal / Files / Store     │
  │                                                             │
  │ Hub API + Auth + Session + Service Registry + Add-on Host   │
  │                 PC listener: 8420 (migration target)        │
  │                                                             │
  │ SSH/SFTP client ───── Tailscale client ───── Stream adapter │
  │                                  │                          │
  │                           Sunshine control UI               │
  └──────────────────────────────────┬──────────────────────────┘
                                     │ LAN or Tailscale
                                     │ authenticated pairing
                                     ▼
                     SPDW HUB — HANDHELD NODE
  ┌─────────────────────────────────────────────────────────────┐
  │ Void Desk (LÖVE / Python)                                    │
  │          │                                                  │
  │          └── Device Agent / HTTP Gateway                    │
  │              listener: 8765 (legacy-compatible target)      │
  │              ├── /api/v1/device                             │
  │              ├── /api/v1/files                               │
  │              ├── /api/v1/packages                            │
  │              ├── /api/v1/services                            │
  │              ├── /apps/tailscale                             │
  │              └── /apps/*                                     │
  │                                                             │
  │ Registered adapters: Tailscale, file operations, package    │
  │ manager, telemetry, sync and future RT Stream integration.  │
  └─────────────────────────────────────────────────────────────┘

  SSH (normally 22) remains a separate transport. SFTP should use
  the SSH subsystem where the installed muOS configuration permits.
  Sunshine media transport remains direct TCP/UDP, not HTTP-proxied.
```

The PC and handheld may use the same numeric gateway port because they are
different hosts. The aim is one management listener per host, not one global
port number for every protocol.

## 3. Ownership and responsibilities

### Void Desk

Void Desk owns the handheld experience and provides a stable local integration
surface to the Hub. LÖVE and Python frontends must call the same service
contracts. Neither frontend should launch a parallel network daemon just to
duplicate an existing function.

### Device Agent

One lifecycle-managed process owns the HTTP listener, authentication,
service discovery, status reporting and API routing. It exposes versioned
routes and dispatches work to registered adapters.

The current BaseStation web file manager is the first migration candidate:
its routes become a Files module behind the gateway's session and capability
checks. The legacy handler must not remain exposed as a second unauthenticated
server.

### PC companion

BaseStation evolves into SPDW Hub PC. Keep its useful existing foundations:
device profiles, SSH terminal, framebuffer capture, SFTP sync, backup and
diagnostics. Add a single web/API surface to the existing PC Link daemon rather
than introducing another service process or another listener.

The existing PC Link protocol is retained during migration. The browser
dashboard is served from the same BaseStation daemon on TCP `8420`, so clients
and profiles remain compatible and no additional management listener is
introduced. The native BaseStation desktop interface continues to provide
interactive SSH PTY and SFTP sync/backup functions; the first browser phase
focuses on telemetry, paired-device actions and the received-file inbox.

### Add-on host

An add-on is a module, not a new daemon by default. It declares:
- stable ID, name, version and compatibility range;
- UI entry / panel;
- API routes and actions;
- required capabilities and permissions;
- dependencies and optional external binaries;
- lifecycle hooks (probe, start, stop, health, uninstall);
- whether it requires protocol-specific listeners.

Only an add-on with a documented protocol requirement may request a listener.
The Hub validates the request against the service registry and port policy.

## 4. Unified dashboard

The PC dashboard is the operational command center:

| Section | Responsibilities |
|---|---|
| Overview | selected node, reachability, OS/build, frontend, battery, storage, services and alerts |
| Devices | discovery, pairing, profiles, multiple handhelds and reconnect |
| Terminal | SSH terminal, read-only diagnostics, controlled command palette |
| Files | browser, upload/download, text editor with safe write, permissions |
| Sync & Backup | save/state comparison, preview, verified ZIP backups, restore with confirmation |
| Streaming | RT Stream add-on, Sunshine host status, pairing, sessions, logs and stream profile |
| Network | Wi-Fi, Tailscale peers, Taildrop, DNS/routes and connection diagnostics |
| App Catalog | EthoStore / APT-backed catalogue, package metadata, install/update/remove jobs |
| Add-ons | installed modules, permissions, versions, health and lifecycle |
| Diagnostics | port ownership, service health, logs, support bundle and export |

Dangerous operations (power off, reboot, delete, restore, package removal, service
stop) require an explicit confirmation and an auditable result.

## 5. Add-on candidates

### Rt:Tailscale

Reuse the existing Rt:Tailscale-M backend and panel. First run it loopback-only
and route it through the Hub. Preserve its PIN/session/CSRF protection during
the transition; do not bypass authentication just because a reverse proxy is
present. Then migrate its UI to a Hub module without forking the CLI/service
logic.

### RT Stream / Sunshine

Integrate the existing RT Stream daemon and Sunshine controls as an add-on.
The module owns configuration, host detection, pairing, readiness checks,
session status and logs. Sunshine remains the streaming engine; the Hub owns
the operational UI and lifecycle adapter.

The public project announcement identifies the upstream source as
[SilverCrow2323/dolphin-rt-stream](https://github.com/SilverCrow2323/dolphin-rt-stream).
An announcement for version 4.2.1 dated 22 October 2026 describes a muOS
handheld frontend and a Linux PC portal built around Sunshine + Moonlight.
The announced PC-side functions include ROM-library scanning, Sunshine app
registration, cover retrieval, fullscreen Dolphin launch, 4:3 display-mode
switching and controller-profile management.

**Source audit is still blocked:** the linked GitHub connection currently
returns HTTP 404 for the repository metadata, branch listing and raw source
paths. The release announcement is useful product context, not a substitute
for code inspection. Do not infer command names, package identifiers,
configuration keys, lifecycle semantics or listener ports from the announcement.
Before implementing the adapter, obtain readable access to the repository and
record the exact commit/tag, installation contract, process ownership,
configuration files, live listener set and shutdown behavior.

### Package / App Store

Reuse EthoStore catalogue metadata and the existing muOS/APT capabilities.
The Hub provides one package job queue with progress, dependency resolution,
logs and rollback/reporting. Do not bundle a second unrelated package manager.

### SSH / SFTP

Prefer one SSH transport and the SFTP subsystem on the same SSH daemon/port.
If a given muOS image genuinely exposes SFTP on a distinct service/port,
represent that as a detected compatibility profile rather than opening a
second listener by default.

## 6. Port and listener policy

- One externally reachable management HTTP gateway per host.
- Legacy HTTP panels bind to loopback while they are being migrated.
- Do not expose web dashboards directly if they can be routed through the Hub.
- Keep required protocol transports (SSH and Sunshine streaming TCP/UDP)
  separate when the protocol requires them.
- No add-on may open a listener without a registry entry, owner, bind address,
  protocol, reason, auth model, health check and cleanup action.
- No automatic UPnP or WAN port exposure for management services.
- Tailscale is the preferred remote transport where available.

A full inventory is maintained in [SPDW_HUB_PORT_AUDIT.md](SPDW_HUB_PORT_AUDIT.md).

The first passive implementation now lives under `service/spdw_hub/`:
`services.json` declares ownership and policy, while `registry.py` validates
socket collisions across listeners and protocol-family members,
management-gateway limits and unauthenticated wildcard listeners. It
deliberately does not bind or stop anything.

The add-on contract is defined by `service/spdw_hub/manifest.schema.json`.
`addons.py` discovers manifests without importing or executing entrypoints,
checks capability grants and rejects unsafe entrypoint paths. Runtime
activation and UI mounting are still future phases; discovery is not activation.

## 7. Authentication and security

- One-time pairing code establishes a per-device credential.
- Store only hashed/rotatable credentials where possible; protect local secret
  files with owner-only permissions.
- The legacy PC Link API on TCP 8420 currently uses plain HTTP bearer-token
  authentication. Until TLS or a trusted encrypted tunnel is enforced, restrict
  it to a trusted LAN or Tailscale and never expose it through WAN port forwarding.
- Use short-lived authenticated sessions, CSRF protection and origin checks
  for browser actions.
- Apply per-route capabilities: status, files-read, files-write, terminal,
  package-install, stream-control and power-control.
- File APIs must validate canonical paths after resolving symlinks, enforce
  upload limits and write atomically.
- Never place SSH passwords, pairing tokens or private keys in exported
  diagnostics or general application logs.
- Do not proxy privileged upstream panels until their origin and session
  behavior is tested behind the Hub.

## 8. Migration sequence

### Phase A — inventory and safety

1. Record actual listeners, bind addresses, owning processes and route/auth
   contracts on both PC and handheld.
2. Add authentication to the legacy BaseStation file portal before any remote
   use; validate real paths and symlink traversal.
3. Make Rt:Tailscale's standalone panel loopback-only when managed by the Hub.
4. Define the service registry and port ownership checks.

### Phase B — shared gateway

1. Introduce the Device Agent gateway using the existing BaseStation portal
   port as the compatibility entry point.
2. Mount the authenticated file manager and health/status routes.
3. Add route adapters for Rt:Tailscale and existing PC Link capabilities.
4. Keep legacy route aliases during migration; deprecate them only after tests
   and user-facing compatibility checks.

### Phase C — PC Hub

1. Upgrade BaseStation into the single PC dashboard and management API.
2. Retain PC Link compatibility and use its existing listener as the PC gateway.
3. Consolidate SSH, SFTP, sync, backup, diagnostics and received-file inbox.
4. Add pairing, multi-device state and service inventory.

### Phase D — add-ons and catalog

1. Add the add-on manifest/loader and capability enforcement.
2. Integrate the real RT Stream/Sunshine daemon as a managed module.
3. Bring EthoStore/APT package jobs into the same dashboard.
4. Migrate Rt:Tailscale UI into the module shell.

### Phase E — release hardening

- Test both LÖVE and Python frontends.
- Test muOS Andromeda and other supported muOS branches via capability profiles.
- Validate fresh install, upgrade, uninstall, process restart and port cleanup.
- Capture screenshots and update the wiki.
- Verify the final .muxapp and PC companion artifacts.

## 9. Implemented foundations in the 10.5.4 work branch

The following pieces now have code and focused tests on the current work branch:

- The handheld Device Agent is hosted inside the existing
  `service/voiddesk_service.py` process on compatibility port `8765`.
- The old Pygame-owned HTTP server has been removed; Python and LÖVE share
  the already-running service lifecycle.
- The handheld file portal uses a generated pairing PIN, authenticated
  session cookie, CSRF checks, login throttling, body limits and canonical
  path checks. Existing file UI routes are kept for compatibility.
- The PC companion keeps the existing PC Link listener `8420`, now with
  generated bearer-token pairing, per-device message queues, handheld
  telemetry, screenshot requests, file inbox, backups and diagnostics.
- The source-level service/port registry and non-executing add-on manifest
  validator are in `service/spdw_hub/`.
- The .muxapp builder and validator now require the Device Agent package.
- A separate reproducible BaseStation 4.0 PC ZIP and release workflow are
  defined alongside the muOS .muxapp artifact.

These are implemented source changes, not claims of a completed release:
CI for the final head, a real device run and live listener ownership checks
are still required.

### Remaining integration work

- Rt:Tailscale still has its own legacy panel lifecycle; it must be routed
  through the Hub or bound to loopback with its existing PIN/session/CSRF
  protections preserved.
- The RT Stream/Sunshine daemon source has not yet been found in the
  inspected Void Desk tree. Its real repository, commands and current
  listener configuration must be imported and audited before implementing
  the add-on adapter.
- App Catalog/APT actions need to be surfaced as Hub jobs; underlying catalog
  and service capabilities must be reused instead of starting a second
  package manager.
- The full PC dashboard tab structure and add-on runtime are still being
  built on the BaseStation foundation.

## 10. Definition of done

- A single authenticated management dashboard per node.
- No unauthenticated file-management endpoint on the LAN.
- Each service has exactly one owner and an explicit lifecycle.
- A port inventory can identify every active listener and its owner.
- The same device can be managed from Void Desk and SPDW Hub without duplicate
  background daemons.
- SSH/SFTP and streaming transports work without a second management portal.
- Add-ons can be installed, disabled, health-checked and removed cleanly.
- LÖVE, Python, PC companion and the packaged release agree on the same API.
