# 🧰 Troubleshooting

Start with the exact symptom and preserve logs before repeating an operation. A generic error message is rarely enough to identify a root cause.

> [!IMPORTANT]
> Include the exact handheld model, full muOS build, Void Desk version/commit and selected frontend in every report. Redact SSIDs, passwords, API keys, pairing tokens, IP addresses, hostnames and personal filenames.

## Black screen or immediate exit

1. Confirm the `.muxapp` was installed through **Applications → Archive Manager** from `SD1/ARCHIVE/`.
2. Confirm that the archive has one top-level `Void-Desk/` directory.
3. Start with the recommended Pygame frontend.
4. Preserve `data/voiddesk.log` and bootstrap/runtime logs before retrying.
5. Check free storage and permissions; do not repeatedly reinstall over an unknown partial state.

## Controller buttons behave differently

- Record the exact firmware release and device model.
- Capture SDL controller name and GUID.
- Compare the selected input profile with the actual raw button events.
- Test confirm/back/start, shoulders, triggers, stick clicks, volume and reconnect separately.
- Use the on-screen footer and calibration tool rather than assuming the same physical key across firmware releases.

See [Controls and navigation](Controls-and-navigation).

## UPLINK reports a service offline

Distinguish the local listener from the remote client and remote peer. A local file bridge being active does not prove that PC Uplink is connected. Preserve the service log and report the exact status label and timestamp.

## Tailscale or Syncthing crashes / does not connect

Record whether the daemon/service is already enabled by muOS, whether it is installed, the last status response and the relevant service logs. Avoid starting a second daemon as a workaround. Do not share API keys or authentication tokens in an issue.

## RT:Shell exits or shows a font error

A basic PTY shell does not require XFCE. Capture the complete traceback, selected shell path and font-loading error. A missing optional font should fall back to a bundled/system monospace font instead of terminating the whole panel.

## Device does not power off

The shutdown hand-off and kernel power-off fallbacks require physical-device validation. Record the device model, firmware build, whether the display/LED changed, last lines of the launcher log and whether media/audio continued. Avoid repeated hard resets while storage writes may still be active.

## Browser reports `Input/output error`

That message alone is not diagnostic. Include the exact browser, whether it was launched inside XFCE or from the muOS host, full error text and relevant session logs.

<details>
<summary>📄 Useful log and evidence checklist</summary>

- `data/voiddesk.log` — launcher and application lifecycle.
- `data/logs/` — additional service/application logs when present.
- `data/xfce_session.log` and `data/session_xfce.log` — optional desktop session.
- `data/visual-captures/` — screenshots and metadata; inspect before sharing.

Include only the relevant excerpt. Remove network identifiers, credentials, tokens, hostnames and personal paths.

</details>

## Still stuck?

Open a [GitHub issue](https://github.com/SilverCrow2323/Void-Desk-Project/issues) with reproduction steps, expected/actual result, firmware/device details and redacted logs.
