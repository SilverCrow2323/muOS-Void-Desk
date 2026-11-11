# QWASAR Desk — Troubleshooting

## Black screen or immediate exit

1. Confirm the .muxapp was installed through Applications → Archive Manager from SD1 ARCHIVE/.
2. Confirm the package contains one Void-Desk/ directory at its root.
3. Check data/voiddesk.log.
4. Try the recommended Pygame frontend and inspect bootstrap logs if runtime installation fails.

## Bluetooth activity stutters the UI

The Pygame status bar reads a cached snapshot while a background poller checks Bluetooth and other host status. If the problem persists, record the device model, MustardOS build, selected engine and whether Bluetooth is enabled.

## Device does not power off

When launched by muOS, the Pygame frontend hands the shutdown request to mux_launch.sh. The launcher stops the companion service, synchronizes writes and tries forced power-off fallbacks. This path cannot be fully verified by CI.

If the device remains on, record the model, exact firmware version, screen/LED state, last lines of data/voiddesk.log, and whether the device is warm or still playing audio. Do not repeatedly force-reset during filesystem writes.

## Browser reports Input/output error

This message alone is insufficient to diagnose the problem. Report the exact browser, whether it was launched from XFCE or the muOS host, and the full error text. Useful logs include data/xfce_session.log, data/session_xfce.log and data/voiddesk.log.

NetSurf, Falkon and Dillo are optional desktop-image browsers. qtWebBrowser is a separate third-party muOS application.

## LÖVE screen has missing options

LÖVE is an experimental, incomplete prototype. If an action is labelled coming soon or does not do anything, report the scene name and selected item. Use Pygame for normal operation.
