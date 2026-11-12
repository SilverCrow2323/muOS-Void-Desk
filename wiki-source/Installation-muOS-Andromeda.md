# 📦 Installation — muOS 2606.0 Andromeda

## Compatibility snapshot

The current packaging target is **muOS 2606.0 Andromeda** on compatible Allwinner H700 handhelds. A successful package build is not proof that every H700 model has identical input, display, audio or power behaviour.

The official muOS site lists Jacaranda as an archived release and 2612 Supernova as in progress as of 12 November 2026. Void Desk must not label those releases certified without their own profile and hardware checks.

## Install the published package

1. Open [GitHub Releases](https://github.com/SilverCrow2323/Void-Desk-Project/releases).
2. Download the latest published `.muxapp` asset. Do **not** install the source-code ZIP.
3. Copy the package into `SD1/ARCHIVE/`.
4. On the handheld, open **Applications → Archive Manager**.
5. Select the Void Desk package and install it.
6. Launch Void Desk from the Applications menu.

The installed application directory is still named `Void-Desk/`. Do not rename or move it manually; package migration must be handled by a versioned installer.

> [!IMPORTANT]
> The latest published handheld release currently listed by GitHub is **v10.2.0**, published on 11 August 2026. v10.5.4-NEXUS is a development line, not a published stable package. See [Releases](https://github.com/SilverCrow2323/Void-Desk-Project/releases).

## First launch checklist

- Back up saves and personal configuration before testing development builds.
- Keep the device powered during package or optional desktop-image installation.
- Check free storage before installing the optional desktop environment.
- Preserve launcher and bootstrap logs if startup fails.
- Keep the native muOS frontend and recovery path available.

## Recommended frontend

Use **Pygame** for normal operation. LÖVE remains experimental and is not yet a complete feature-equivalent alternative.

<details>
<summary>🔧 Package structure notes</summary>

The `.muxapp` archive must contain one top-level `Void-Desk/` application directory. Avoid an extra nested directory or manual path renaming. For build/validation details, see [Development](Development) and the repository's [packaging documentation](https://github.com/SilverCrow2323/Void-Desk-Project/tree/main/packaging).

</details>

## Official references

- [muOS releases](https://muos.dev/release)
- [muOS release progress](https://muos.dev/release/progress)
- [Application extending guide](https://muos.dev/docs/infrastructure/extending)
- [Application launching guide](https://muos.dev/docs/infrastructure/launching)
