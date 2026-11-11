# QWASAR Desk — Hubs and features

QWASAR Desk uses the NEXUS home interface to route into feature hubs. Feature availability depends on engine, firmware, installed programs, hardware and permissions.

| Hub | Purpose | Notes |
|---|---|---|
| START SESSION | Start or install the optional desktop environment | XFCE is the documented baseline; setup is device- and storage-dependent |
| THE FORGE | Desktop components and packages | LÖVE package actions use the background job queue with an explicit command allowlist; cache cleaning remains incomplete |
| UPLINK | Wi-Fi, Bluetooth, hotspot and network integrations | Adapter and firmware support matter |
| MEDIA VAULT | Radio, IPTV, local media and audio tools | VoidCast is a standalone optional app; external tools are discovered from the shared registry and only installed launchers are offered |
| WORKSHOP | System status, storage and maintenance | Pygame is fuller; LÖVE diagnostics/monitor/log flows need work |
| RT:TOOLBOX | Everyday utilities | Calendar reads the shared `data/calendar.json` event store; terminal, Calculator and Clock scenes are linked; Toolbox counts are backed by the service. Notes/RSS/Weather remain incomplete |
| MUOS APPS | Discover and launch other muOS applications | Requires host application layout and permissions |
| SETTINGS | Themes, language, UI and engine settings | LÖVE settings are a smaller experimental subset |
| INFO & ABOUT | Project information and update details | Some actions display status text rather than a full manual |
| END SESSION | Close, reboot or power off | Device power-off must be tested on hardware |

For troubleshooting, use the Troubleshooting page. For engine differences, see Frontends.


## Tool taxonomy

The proposed workspace/category model is documented in [Tool Catalog](https://github.com/SilverCrow2323/Void-Desk-Project/blob/main/docs/TOOL_CATALOG.md). Tool availability is still capability- and firmware-dependent. The catalog is an inventory, not a claim that every item is enabled on every device.
