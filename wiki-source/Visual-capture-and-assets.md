# 🎨 Visual capture and assets

The visual language is **Megastructure**: industrial science fiction, monumental geometry, steel/graphite surfaces, technical labels and restrained signal colours. Documentation uses the same visual grammar, but it must remain easy to read on a phone or a narrow GitHub panel.

## 📷 Existing interface PNGs

These repository PNGs are earlier interface references. They are not v12 mock-ups and do not certify that every linked action works.

<p align="center">
  <img src="https://raw.githubusercontent.com/SilverCrow2323/Void-Desk-Project/main/resources/nexus-menu.png" alt="Earlier NEXUS screen" width="48%" />
  <img src="https://raw.githubusercontent.com/SilverCrow2323/Void-Desk-Project/main/resources/uplink-hub.png" alt="Earlier Uplink screen" width="48%" />
  <img src="https://raw.githubusercontent.com/SilverCrow2323/Void-Desk-Project/main/resources/media_vault.png" alt="Earlier Media Vault screen" width="48%" />
  <img src="https://raw.githubusercontent.com/SilverCrow2323/Void-Desk-Project/main/resources/workshop.png" alt="Earlier Workshop screen" width="48%" />
</p>

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
