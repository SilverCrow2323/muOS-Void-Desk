# 🧪 Release testing and bug reports

A package is ready only when the published description matches the actual build and the claimed device/firmware combinations have been tested on hardware.

> [!IMPORTANT]
> CI, headless rendering, QEMU and a successful archive build are useful evidence, but none of them alone proves that controller, display, audio, storage, Wi-Fi or shutdown works on a physical handheld.

## Release status snapshot

| Item | Status on 12 November 2026 |
|---|---|
| Latest published handheld package | v10.2.0, published 11 August 2026 |
| v10.5.4-NEXUS | Development / draft review; PR #66 is not merged |
| v12 | Blueprint only; not an installable release |
| Main packaging target | muOS 2606.0 Andromeda on compatible H700 hardware |
| LÖVE | Experimental; no feature-parity claim |

Always confirm the [current Releases page](https://github.com/SilverCrow2323/Void-Desk-Project/releases) before downloading a package.

## Package test checklist

- [ ] Build the `.muxapp` from the intended commit.
- [ ] Confirm one `Void-Desk/` root and required runtime files.
- [ ] Run the repository package validator.
- [ ] Install through muOS Archive Manager on the target device.
- [ ] Confirm startup, main navigation and controller mapping.
- [ ] Test media/audio, storage access and networking where in scope.
- [ ] Test service start/stop and safe error paths.
- [ ] Test return to muOS, shutdown and restart flows.
- [ ] Test update/rollback/uninstall for the release scope.
- [ ] Verify the documentation and changelog match the shipped package.

## Hardware test record

Record the exact handheld model, board identity if known, full firmware release/build, frontend, controller GUID, package version/commit, test date, scenarios and result. A broad statement such as “H700 compatible” is not enough if only one H700 model has been tested.

## Bug report contents

Include:

- version or commit;
- device and firmware;
- frontend (`py` or `love`);
- screen and selected action;
- reproduction steps;
- expected and actual behaviour;
- relevant redacted log lines or screenshot.

Open a [GitHub issue](https://github.com/SilverCrow2323/Void-Desk-Project/issues). Do not close hardware-specific issues until the affected device has been retested.

<details>
<summary>🔬 Visual test evidence — what it proves</summary>

- A PNG proves that a renderer produced a frame at a given size.
- A scene smoke test proves the scene loaded in the test environment.
- A service unit test proves the tested code path under its simulated conditions.
- A physical-device test provides evidence only for the named hardware, firmware, package and test cases.

Do not combine these into a blanket compatibility claim.

</details>
