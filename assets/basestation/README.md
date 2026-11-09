# VOID BaseStation 4.0.0 — SPDW Hub PC Companion

The PC-side companion for Void Desk 10.5.4. Run it on the computer, not on
the handheld.

## Included functions

- PC Link pairing and authenticated handheld discovery.
- PC and handheld telemetry, notifications and screenshot requests.
- Authenticated file inbox for files delivered by a handheld.
- SSH terminal, remote framebuffer capture and read-only diagnostics.
- SFTP folder comparison and non-destructive save/state synchronization.
- Verified ZIP snapshots of selected remote folders, with a JSON manifest and
  per-file SHA-256 checksums.
- A service/port registry viewer for the SPDW Hub architecture.
- Sanitized support reports with live `ss -lntup` / `netstat` snapshots.

## Linux desktop installation

Install Python, Tkinter and venv support:

```bash
sudo apt install python3 python3-tk python3-venv
```

Extract the release ZIP and run:

```bash
cd VOID-BaseStation-4.0.0
sh run_basestation.sh
```

The launcher creates a local virtual environment, retains access to the system
Tkinter installation and installs the declared Python dependencies.

For a manual setup:

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python basestation.py
```

## Pair Void Desk

1. Start BaseStation.
2. Open **Tools → PC Link Pairing**.
3. Copy the PC address and private authentication token.
4. On the handheld, open **UPLINK → PC UPLINK → Add manually** and enter the
   address, port and token.
5. Open **Tools → Linked Handhelds** to view incoming telemetry.

The default PC Link port is TCP `8420`, matching the discovery client already
included in Void Desk. Legacy BaseStation profiles using the previous default
port `31337` are migrated automatically.

## Data and security

- Profiles: `~/.config/void_basestation/profiles.json`
- Private PC Link token: `~/.config/void_basestation/daemon.json`
- Received files: `~/.config/void_basestation/incoming/<device-id>/`
- Suggested backup directory: `~/Videos/VOID_Backups/`

Pairing tokens and SSH credentials are not included in diagnostic exports.
Keep the pairing token private and use the PC Link only on trusted LAN or
Tailscale networks. The management API currently uses HTTP; do not expose its
port directly to the public internet.

## Compatibility

The PC companion requires a graphical desktop with Tkinter. SSH/SFTP functions
require a reachable SSH service and working credentials on the handheld.
Pillow and psutil are optional enhancements; the app has fallback behavior
when they are unavailable.
