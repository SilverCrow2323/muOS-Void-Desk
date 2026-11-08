# v10.5.4 pre-release plan

The next pre-release is gated by working user journeys, not by screenshot counts alone.

See the source-controlled [v10.5.4 completion and acceptance plan](../docs/PRE_RELEASE_10.5.4.md) for the full workstreams and release checklist.

## Main goals

- Complete the LÖVE frontend for the declared release scope.
- Evolve Pygame while keeping it the reference frontend.
- Verify every NEXUS node and selectable action end to end.
- Add a searchable APT catalogue to THE FORGE, usable from VoidDesk without launching XFCE. APT operations remain inside the existing Debian/Ubuntu chroot; muOS itself is Buildroot-based.
- Integrate Rt:Tailscale-M as a native managed service, including install, login, peers, exit nodes, Taildrop, boot lifecycle and diagnostics.
- Give Syncthing a complete native panel using the Andromeda Web Service.
- Extend PC Uplink with secure pairing, remote input and remote display.

## Validation policy

Visual capture is a smoke test. A release claim also needs action-driven tests and physical-device verification on the supported muOS firmware and hardware. Experimental features must be labelled as such until tested.

## Wiki bootstrap status

The Markdown pages in wiki-source are ready to publish, but the GitHub Wiki itself still requires the first Home page to be created in the GitHub UI. See wiki-source/README.md for the one-time bootstrap steps.
