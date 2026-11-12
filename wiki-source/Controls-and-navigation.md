# 🎮 Controls and navigation

Void Desk is designed for controller-first navigation. The exact physical button assigned to an action can vary by device, firmware release and controller identity.

> [!IMPORTANT]
> Treat the active screen footer and the detected input profile as the source of truth. Do not assume that an SDL button number or physical label is identical across every muOS release.

## Semantic controls

| Logical action | Purpose |
|---|---|
| `CONFIRM` | Activate the selected item |
| `BACK` | Close the current panel or return |
| `START` | Screen-specific primary action |
| `QUICK_PANEL` | Open quick controls where available |
| `MEDIA_PANEL` | Open playback controls where available |
| `VOLUME_UP` / `VOLUME_DOWN` | Adjust volume where supported |
| `PAGE_PREV` / `PAGE_NEXT` | Change tab, category or page |
| `SYSTEM_MENU` | Open the system/context menu |

The physical-to-semantic mapping belongs in a versioned controller profile. A screen should consume logical actions, not raw device-specific button indices.

## Default navigation model

| Input family | Typical behaviour |
|---|---|
| D-pad / left stick | Navigate focused items |
| Confirm action | Open / select |
| Back action | Return / cancel |
| Shoulder buttons | Switch tabs/categories where shown |
| Start / Select | Contextual actions shown in the footer |
| Volume controls | Route to the active audio path where supported |

These are logical expectations, not a promise that a specific physical button has the same mapping on every firmware.

## PC keyboard testing

The LÖVE PC test layer supports keyboard navigation for development. Exact keys can change with the selected input adapter. F12 is the screenshot shortcut when enabled by the active frontend.

## Firmware-aware mapping

The target resolver uses firmware release + device/board identity + SDL GUID. Andromeda, Jacaranda and future Supernova profiles must remain independently versioned until tests prove that they are equivalent.

See the [muOS compatibility design](https://github.com/SilverCrow2323/Void-Desk-Project/blob/main/docs/MUOS_FIRMWARE_COMPATIBILITY.md).

<details>
<summary>🧪 Manual input capture checklist</summary>

- Record the exact firmware build and handheld model.
- Capture controller name and SDL GUID.
- Test every button, d-pad direction, analog axis, trigger and stick click.
- Test combinations, held input, repeat and reconnection.
- Confirm volume/media shortcuts separately from navigation.
- Save the raw event log and the final semantic map with a date and device ID.

</details>

## Screenshot shortcut

When supported, press **F12** while the frontend is visible. The capture and JSON sidecar are written under `data/visual-captures/`. Review images for private information before sharing them.
