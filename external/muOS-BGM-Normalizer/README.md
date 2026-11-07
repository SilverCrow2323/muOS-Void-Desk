<p align="center">
  <img src="https://i.ibb.co/dw5vs93C/muos-20260721-014801.png" width="640" alt="SPDW BGM Normalizer Banner">
</p>

<h1 align="center">🎵 SPDW BGM Normalizer</h1>
<p align="center">
  <b>Professional-grade audio normalization for muOS & PC.</b><br>
  <i>Convert, normalize, and optimize your music for the ultimate handheld BGM experience.</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/muOS-Compatible-7B68EE?style=flat-square&logo=linux">
  <img src="https://img.shields.io/badge/PC-Windows%20%7C%20Linux%20%7C%20macOS-3776AB?style=flat-square&logo=python">
  <img src="https://img.shields.io/badge/Python-3.11+-Python?style=flat-square&logo=python&color=3776AB">
  <img src="https://img.shields.io/badge/SDL2-ctypes-FF6F00?style=flat-square">
  <img src="https://img.shields.io/badge/FFmpeg-Required-green?style=flat-square&logo=ffmpeg">
  <img src="https://img.shields.io/badge/SPDW-Factory_Lab-00FFCC?style=flat-square">
</p>

---

## 📖 Overview

**SPDW BGM Normalizer** is a powerful, zero-dependency GUI application designed to convert, normalize, and optimize your music collection for use as **background music (BGM)** on **Anbernic handhelds running muOS** — or directly on your **PC**.

Whether you have a messy library of MP3s, FLACs, and WAVs in varying volumes, this tool unifies everything into perfectly normalized **OGG Vorbis** files at your target LUFS level. No more jarring volume spikes between tracks. No more incompatible formats. Just clean, consistent BGM for your gaming sessions.

Built with pure Python and SDL2 via ctypes — no pip, no bloat, no nonsense.

<p align="center">
  <img src="https://i.ibb.co/WpWXv28t/muos-20260721-014739.png" width="640" alt="BGM Normalizer Main Menu">
</p>

<p align="center">
  <img src="https://i.ibb.co/dsq703Q2/muos-20260721-014721.png" width="640" alt="BGM Normalizer Menu">
</p>
---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🎮 **Native muOS Integration** | Seamless launcher via `mux_launch.sh` with full controller support |
| 💻 **Full PC Support** | Runs on Windows, Linux, and macOS with keyboard + mouse or gamepad |
| 🔊 **LUFS Loudness Normalization** | Professional EBU R128 / ITU-R BS.1770 loudness targeting (-14 to -23 LUFS) |
| 🔄 **Smart Format Conversion** | Converts MP3, FLAC, WAV, M4A, AAC, WMA, OPUS, MP4, WebM → OGG Vorbis |
| ✂️ **Silence Trimming** | Auto-removes leading and trailing silence for gapless playback |
| 🗑️ **Optional Source Deletion** | Delete original files after successful conversion to save SD space |
| 🎨 **3 Visual Themes** | SPDW Megastructure, Tailscale Classic, SPDW Hybrid |
| 🌐 **Multilingual UI** | English & Italian with external `lang.json` support |
| 🎵 **Built-in Audio Preview** | Preview any track before converting (15-second clips) |
| 📊 **Real-time Progress** | Live conversion progress with per-track and overall percentage |
| 📝 **Persistent Logging** | Full operation log saved to `spdw_bgm_normalizer.log` |
| ⚡ **Zero Dependencies** | Pure Python + SDL2 ctypes — no pip packages required |

---

## 🚀 Supported Formats

### Input Formats
`.mp3` `.flac` `.wav` `.ogg` `.m4a` `.aac` `.wma` `.opus` `.mp4` `.webm`

### Output Format
`.ogg` (OGG Vorbis, 44.1kHz, quality 6)

### LUFS Presets
| Preset | Target | Use Case |
|--------|--------|----------|
| **-14.0 LUFS** | muOS / BGM Standard | Balanced, modern streaming loudness |
| **-12.0 LUFS** | Retro Handheld / Loud | Punchy, audible on handheld speakers |
| **-10.0 LUFS** | Punchy High-Volume | Maximum impact, minimal dynamics |
| **-23.0 LUFS** | EBU R128 Broadcast | Film/TV standard, wide dynamic range |

---

## 📥 Installation

### muOS (Handheld)

1. **Download** `SPDW-BGM-Normalizer.muxapp`
2. **Copy** to your SD card:
   ```
   /mnt/mmc/MUOS/ARCHIVE/
   ```
3. **Boot** muOS → **Applications → Archive Manager**
4. **Select** `SPDW-BGM-Normalizer.muxapp` → press **A** to install
5. **Restart** your handheld
6. Find **BGM Normalizer** under **Applications**

### PC (Windows / Linux / macOS)

1. **Clone** or download the repository
2. **Install FFmpeg** (required):
   - **Windows**: `choco install ffmpeg` or download from [ffmpeg.org](https://ffmpeg.org)
   - **Linux**: `sudo apt install ffmpeg`
   - **macOS**: `brew install ffmpeg`
3. **Place fonts** in the app folder:
   - `font.ttf` — UI font (required)
   - `fontbgm.ttf` — Large title font (optional, fallback to font.ttf)
   - `fontnorm.ttf` — Badge font (optional, fallback to font.ttf)
4. **Run**:
   ```bash
   python3 bgm_normalizer.py
   ```

---

## 🎮 Controls

### muOS (Controller)

| Button | Action |
|--------|--------|
| **D-Pad ↑↓** | Navigate menus / file list |
| **A** | Confirm / Select / Toggle checkbox |
| **B** | Back / Cancel |
| **X** | Toggle file selection (mark/unmark) |
| **Y** | Toggle file info panel |
| **L1** | Filter: select all non-OGG files |
| **R1** | Page Down (file list) |
| **START** | Preview selected track |

### PC (Keyboard)

| Key | Action |
|-----|--------|
| **↑ ↓** | Navigate |
| **Enter / Space / A** | Confirm |
| **Esc / B** | Back |
| **X** | Toggle selection |
| **Y** | Toggle info |
| **P** | Preview |
| **F** | Filter non-OGG |
| **R** | Rescan folder |
| **PgUp / PgDn** | Scroll file list |

---

## 📂 Project Structure

```
SPDW-BGM-Normalizer/
├── bgm_normalizer.py           # Main application (Python 3 / SDL2)
├── mux_launch.sh               # muOS entry-point wrapper
├── config.ini                  # User settings (presets, paths, theme)
├── lang.json                   # Translation strings (EN / IT)
├── font.ttf                    # UI font (REQUIRED)
├── fontbgm.ttf                 # Title font (optional)
├── fontnorm.ttf                # Badge font (optional)
├── spdw_bgm_normalizer.log     # Operation log (auto-generated)
├── README.md                   # This file
└── glyph/
    └── icon.png                # muOS menu icon
```

---

## ⚙️ Configuration

Settings are persisted in `config.ini`:

```ini
lang = en
scan_source = both
theme = spdw
target_lufs = -14.0
sample_rate = 44100
ogg_quality = 6
delete_originals = false
normalize_volume = true
trim_silence = false
convert_to_ogg = true
glitch_fx = true
out_mode = default
pc_input_dir = ~/Music/BGM
pc_output_dir = ~/Music/BGM_Normalized
```

---

## 💡 Troubleshooting

| Issue | Solution |
|-------|----------|
| **App won't start** | Ensure `font.ttf` is in the app folder. Check `spdw_bgm_normalizer.log` for errors |
| **"ffmpeg not found"** | Install FFmpeg and ensure it's in your system PATH |
| **Conversion is very slow** | Normalization is CPU-intensive. Large files (5min+) can take 2-5 minutes on handheld |
| **LUFS analysis times out** | The app falls back to 1-pass direct normalization automatically |
| **Files not appearing** | Check `scan_source` (SD1/SD2/both on muOS) or `pc_input_dir` on PC |
| **Output files not found** | On muOS, check `/mnt/mmc/MUOS/music/`. On PC, check `~/Music/BGM_Normalized/` |
| **OGG files not playing in muOS** | Ensure muOS BGM settings are configured to scan the correct folder |

---

## 🎨 Themes

| Theme | Preview | Style |
|-------|---------|-------|
| **SPDW Megastructure** | Neon cyan borders, HUD corners, subtle analog glitch FX | Cyberpunk industrial |
| **Tailscale Classic** | Clean corporate dark, minimal, professional | Modern enterprise |
| **SPDW Hybrid** | Balanced fusion: cyan accents + clean layout | Best of both worlds |

Switch themes in **Options → Theme Selection**.

---

## 📜 About

<p align="center">
  <b>SPDW BGM Normalizer v8.6 — Definitive Edition</b>
</p>

> Engineered for muOS & PC.  
> Normalize your world. One track at a time.

**Part of the Chou Henka Project ecosystem.**

Architected and maintained by **Kentani Kenji** *(Sir Pips du Wilson)* — SPDW Factory Lab.

This tool was born from the need to unify scattered music libraries into a consistent, handheld-optimized BGM collection. No more volume roulette. No more format headaches. Just press Start and let the Normalizer handle the rest.

> *"The waveform is the message. The Rintrompo guides the amplitude. Sbrobs."*

<p align="center">
  <img src="https://img.shields.io/badge/SPDW-Factory_Lab-00FFCC?style=for-the-badge">
  <img src="https://img.shields.io/badge/Chou_Henka-Project-FF00FF?style=for-the-badge">
  <img src="https://img.shields.io/badge/muOS-Powered-7B68EE?style=for-the-badge">
</p>

---

## ⚖️ License

Released as part of the Chou Henka Project. Free for personal use. Modify, share, and normalize responsibly.

**Credits:**
- **SPDW Factory Lab** — Design, code, and relentless optimization
- **muOS (MustardOS)** — The firmware that makes handhelds sing
- **FFmpeg** — The engine under the hood
- **SDL2** — The graphics backbone
