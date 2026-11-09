# SPDW Hub add-on contract

Add-ons extend the Hub UI and service layer; they do not automatically create
a background daemon or open a network listener.

Each add-on is a folder with an `addon.json` manifest and a relative entrypoint.
Discovery is non-executing: the Hub reads and validates the manifest first.
Activation will be a separate, explicit lifecycle operation.

## Manifest

See `manifest.schema.json` for the machine-readable schema and
`../addons.py` for the current validator.

Required fields identify the module, supported host, entrypoint, UI route,
capabilities, listeners and dependencies. Capabilities are allow-listed.
Destructive actions such as file writes/deletes, package changes, terminal
execution, network/stream/service management and power operations must declare
matching `confirmation_actions`.

Listeners are empty by default. A requested LAN/Tailscale listener must declare
its host, protocol, port, bind target, authentication model and reason. It
must also be reconciled against `services.json` before installation. Add-ons
cannot silently choose a free port and start their own server.

## Lifecycle

The runtime contract will expose:

- `probe(context)` — verify prerequisites and compatibility without changing state.
- `start(context)` / `stop(context)` — optional owned worker lifecycle.
- `health(context)` — structured health and version state.
- `render(context)` — optional UI integration through the Hub shell.
- `uninstall(context)` — remove only files and services owned by the add-on.

No entrypoint is imported during discovery. The runtime must check permissions,
dependency state, port ownership and user consent before activation.
