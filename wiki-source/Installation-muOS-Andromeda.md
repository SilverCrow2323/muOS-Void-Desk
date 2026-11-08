# Installation — MustardOS / muOS 2606.0 Andromeda

## Compatibility

The current packaging target is MustardOS (muOS) **2606.0 Andromeda** on compatible H700 handhelds. Hardware-specific behaviour still needs testing on each model. Do not assume older muOS releases or other distributions are compatible.

## Install a .muxapp

1. Download the .muxapp asset from the relevant GitHub Release. Do not install the source-code ZIP.
2. Copy the .muxapp file to the **ARCHIVE/** folder on SD1.
3. On the handheld, open **Applications → Archive Manager**.
4. Select the VoidDesk package and install it.
5. Launch VoidDesk from the Applications menu.

The .muxapp archive has one top-level application directory: **Void-Desk/**. It contains the launcher and app files. There must not be an extra application/ directory nested inside the package.

## First launch

- Keep the device connected to reliable Wi-Fi during optional desktop-image setup.
- Back up important saves and configuration before installing test builds or changing firmware.
- Keep the device powered while the desktop image or packages are being installed.
- Check that sufficient free storage is available before starting optional XFCE setup.

## Recommended engine

Use the **Pygame** frontend. The LÖVE frontend is an experimental prototype and is not yet a complete alternative.
