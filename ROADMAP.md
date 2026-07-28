# VoidDesk — Roadmap

What's shipped, what's in progress, roughly in the order it'll land. This tracks active development and gets updated as things move.

---

## ✅ Shipped

### Real terminal & CLI Arsenal
- Real `xterm` session on a minimal X setup (fullscreen via `matchbox-window-manager`, not a fake in-app shell)
- Gamepad-native input mapping: D-pad/left stick → arrows (keyboard navigation), A/START → Enter, X → Backspace, Y → space, right stick → scrollback
- On-screen keyboard, always visible from session start, adjustable size
- CLI tool catalogue with install status, green-phosphor themed UI, selectable accent colour
- Dedicated Live Panel for the terminal context: resume, launch another tool, core process health check, troubleshooting (Ctrl+C included), keyboard settings
- True in-place restart of the current tool, not just a full session bounce

### Void Installer
- MX-style expandable/collapsible categories
- Renamed from "Software Installer" for consistency with the rest of the native tool suite

### Log Registry
- Every log the app writes, catalogued in one place, organised by subsystem
- One-tap archive-to-SD (zip), with a dedicated diagnostic log for the archiver itself

### Visual identity
- Seamless animated background (grid, gears, fan, status LEDs, occasional glitches) — no more tiling seams
- Real "mechanical" window transitions with a slight overshoot, not a flat fade
- Custom boot animation: animated multicolour title treatment, ending in a rotating light-wipe that reveals the menu
- Five distinct home menu styles, cycled with **Y**
- *Nexus* home style: large single-node view, cable-connected info panels, dedicated travel sound
- Six analog/digital clock faces, three of them new (enriched analog with a seconds sub-dial, skeleton, pilot)
- Real calendar grid (not floating numbers) with full weekday names in week view
- A metallic "content panel" backing applied across most text-heavy screens for readability against the animated background
- Adjustable text size (4 levels) and three independent VFX detail sliders (0–5): background animation, transitions, screen effects

### Fixes worth mentioning
- Package install status detection, PATH configuration for the terminal session, and a handful of D-pad/navigation regressions — all diagnosed from real device logs, not guessed at

---

## 🚧 In progress / next up

### FORGE
- **Update Environments**: now opens a tabbed window (L1/R1 between XFCE/IceWM/LXDE) instead of firing an update blind — richer per-environment detail (source, install date, version comparison against the latest available) still to come
- A CLI environment/shell tab in the same window
- **Mustard Store**: feasibility still being scoped — a listing of community-made muOS.dev apps, or a submission-form approach

### CLI Arsenal → CLI Script Runner
- Full rename and a dedicated boot animation
- Merging Arsenal + Installer into one categorised view
- Richer per-tool detail cards: dependencies, version, install date, author, a command reference
- A proper mini installer window for individual tool installs, separate from the main Void Installer
- Official icons per tool

### Elsewhere
- **START SESSION**: per-environment detail window reachable directly from the picker
- **MuOS Apps**: a more modern, rounder visual pass
- **Wi-Fi / Bluetooth / Hotspot**: deeper per-connection detail views, paired-device management, connected-device lists
- **Syncthing**: a proper themed panel instead of a generic wrapper
- **File Manager**: dark theme pass, storage tiles with free-space bars, bookmarks

---

## Notes

This list is intentionally blunt about what's not done yet — VoidDesk moves fast and in public, and a roadmap that only shows finished work isn't a very useful one. Check the commit history for the most current state of any item above.
