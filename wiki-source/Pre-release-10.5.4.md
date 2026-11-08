# v10.5.4 pre-release plan

The next pre-release is gated by working user journeys, not by screenshot counts alone.

See the source-controlled [v10.5.4 completion and acceptance plan](../docs/PRE_RELEASE_10.5.4.md) for the full workstreams and release checklist.

## Main goals

- Complete the LÖVE frontend for the declared release scope.
- Evolve Pygame while keeping it the reference frontend.
- Verify every NEXUS node and selectable action end to end.
- Add a searchable APT catalogue to THE FORGE, usable from VoidDesk without launching XFCE. APT operations remain inside the existing Debian/Ubuntu chroot; muOS itself is Buildroot-based.
- Integrate Rt:Tailscale-M as a native managed service. LÖVE and Pygame now have in-app panels for status, QR login, peers, exit nodes, Taildrop inventory and boot startup; install/start is delegated to the upstream manager and never launches a second daemon. The upstream static/UI suite and 21 QEMU service checks passed before these UI changes; post-change CI and physical-device validation remain pending. The optional web panel is disabled by default in the package and, if enabled from Void Desk, binds to localhost only.
- Extend the native Syncthing panel using the Andromeda Web Service. Pygame now lists shared folders and devices, completion/connection state, and supports folder pause/resume, scan, override and device pause/resume. It discovers the Andromeda config on port 7070 and does not start a duplicate daemon. Add/remove flows and physical-device validation remain pending.
- Extend PC Uplink with secure pairing, remote input and remote display.
- Add `tools/build_muxapp.py`, a reproducible single-root package builder that refuses an uninitialized Tailscale submodule and vendors only its service files (not the standalone UI or identity state). Its tests and physical package install/upgrade validation are still pending.

## Validation policy

Visual capture is a smoke test. A release claim also needs action-driven tests and physical-device verification on the supported muOS firmware and hardware. Experimental features must be labelled as such until tested. File-GD X remains unavailable because its former prototype source reference had no resolvable repository URL.

## Wiki bootstrap status

The Markdown pages in wiki-source are ready to publish, but the GitHub Wiki itself still requires the first Home page to be created in the GitHub UI. See wiki-source/README.md for the one-time bootstrap steps.
