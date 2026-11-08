# Release testing and bug reports

## Test the package

The development line is v10.5.4-NEXUS. A release must not be described as stable solely because CI is green.

Before publishing a test package:
- build the .muxapp with only one top-level Void-Desk/ folder;
- install it through Archive Manager on MustardOS 2606.0 Andromeda;
- confirm startup, controller navigation and shutdown;
- verify the Bluetooth panel and NEXUS animation together;
- test optional XFCE hand-off only if there is enough storage and network;
- test Pygame on target hardware; LÖVE remains experimental.

## Bug report template

Include VoidDesk version or commit, exact device model, MustardOS/muOS build, frontend (py or love), screen and selected action, reproduction steps, expected and actual behaviour, and relevant log lines or screenshot. Redact credentials, Wi-Fi names, private IPs, hostnames, tokens and personal filenames.

## Open issue examples

- [Browser launch error](https://github.com/SilverCrow2323/Void-Desk-Project/issues/1)
- [Bluetooth stutters / power-off](https://github.com/SilverCrow2323/Void-Desk-Project/issues/2)

Do not close hardware issues until the reporter has verified the behaviour on the affected handheld.
