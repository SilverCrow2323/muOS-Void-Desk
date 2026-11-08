# Security policy

VoidDesk can invoke host utilities, install packages, manage network interfaces, mount an optional desktop image and start local services. Treat it as system-level software.

## Reporting a vulnerability

Do not publish credentials, private logs or a working exploit in a public issue.

If GitHub Security Advisories are enabled, use the **Report a vulnerability** flow. Otherwise, open a minimal issue asking the maintainer for a private reporting channel; do not attach secrets or sensitive network data.

Include the affected version, device/firmware, component, impact and a minimal reproduction. Redact usernames, IP addresses, SSIDs, tokens and personal files.

## Safe operation

- Use networking and diagnostic features only on systems and networks you own or are explicitly authorized to administer.
- Do not expose local web/file services to untrusted networks.
- Review package and shell operations before confirming them.
- Keep the device clock and CA certificates valid so HTTPS verification stays enabled.
- Treat downloaded archives, playlists, add-ons and configuration received from others as untrusted.
- Back up important data before image, package or firmware operations.
