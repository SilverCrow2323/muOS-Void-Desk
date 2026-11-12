# 🎨 Visual capture and assets

The visual language is **Megastructure**: industrial science fiction, monumental geometry, steel/graphite surfaces, technical labels and restrained signal colours. Documentation uses the same visual grammar, but it must remain easy to read on a phone or a narrow GitHub panel.

## 🧩 Navigation icon library

The following PNG files in `https://raw.githubusercontent.com/SilverCrow2323/Void-Desk-Project/main/resources/` are **menu and hub icons**, not screenshots of application screens. They are the visual identity assets used to represent Void Desk destinations.

| WORKSHOP | SETTINGS | THE FORGE | START SESSION | RT:TOOLBOX |
|---|---|---|---|---|
| <img src="https://raw.githubusercontent.com/SilverCrow2323/Void-Desk-Project/main/resources/workshop.png" width="76" alt="Workshop icon" /> | <img src="https://raw.githubusercontent.com/SilverCrow2323/Void-Desk-Project/main/resources/settings.png" width="76" alt="Settings icon" /> | <img src="https://raw.githubusercontent.com/SilverCrow2323/Void-Desk-Project/main/resources/the_forge.png" width="76" alt="The Forge icon" /> | <img src="https://raw.githubusercontent.com/SilverCrow2323/Void-Desk-Project/main/resources/start.png" width="76" alt="Start Session icon" /> | <img src="https://raw.githubusercontent.com/SilverCrow2323/Void-Desk-Project/main/resources/rt_toolbox.png" width="76" alt="RT Toolbox icon" /> |

| NETSPHERE / UPLINK | muOS APPS | MEDIA VAULT | INFO | END |
|---|---|---|---|---|
| <img src="https://raw.githubusercontent.com/SilverCrow2323/Void-Desk-Project/main/resources/net_sphere.png" width="76" alt="Netsphere icon" /> | <img src="https://raw.githubusercontent.com/SilverCrow2323/Void-Desk-Project/main/resources/muos.png" width="76" alt="muOS Apps icon" /> | <img src="https://raw.githubusercontent.com/SilverCrow2323/Void-Desk-Project/main/resources/media_vault.png" width="76" alt="Media Vault icon" /> | <img src="https://raw.githubusercontent.com/SilverCrow2323/Void-Desk-Project/main/resources/info.png" width="76" alt="Info icon" /> | <img src="https://raw.githubusercontent.com/SilverCrow2323/Void-Desk-Project/main/resources/end.png" width="76" alt="End icon" /> |

These are existing project assets. The NEXUS v12 diagram above is a **proposed navigation map**, not a screenshot.
## Architecture and concept diagrams

![QWASAR system map](assets/qwasar-system-map.svg)

![NEXUS v12 proposal](assets/nexus-v12-navigation.svg)

![Firmware and input resolution](assets/muos-profile-resolution.svg)

These SVG diagrams remain editable in `docs/assets/`. The same assets are copied into the GitHub Wiki by `tools/publish_wiki.sh`.

## Capture UI screens

Both frontends provide an F12 capture path when enabled. Captures and JSON metadata are written under `data/visual-captures/`.

```bash
# Pygame states and home styles
python3 tools/capture_pygame_screenshots.py --all-states

# LÖVE scene capture (requires LÖVE 11.5 on a Linux development PC)
python3 tools/capture_love_screenshots.py
```

A capture pass is renderer evidence, not proof of navigation, action behaviour or physical device support.

## Build an asset catalogue

```bash
python3 tools/visual_capture.py
python3 tools/visual_capture.py --check
```

The report indexes images and fonts, records dimensions and hashes, and checks active image references.

## Publish approved screenshots

Captures are ignored by Git by default. Inspect each image for SSIDs, IP addresses, hostnames, usernames, personal filenames and private media before exporting or committing it. Never publish real tokens or credentials.

See the repository [visual capture guide](https://github.com/SilverCrow2323/Void-Desk-Project/blob/main/docs/visual/README.md) and [documentation style guide](https://github.com/SilverCrow2323/Void-Desk-Project/blob/main/docs/DOCUMENTATION_STYLE_GUIDE.md).
