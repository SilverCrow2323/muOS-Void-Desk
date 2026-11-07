# 📦 RUNTIME ARCHIVES
**Precompiled dependencies for VoidDesk — zero internet, zero hassle.**

---

## 📌 Overview
This folder contains precompiled runtime archives for VoidDesk. 
On first boot, the bootstrap extracts them automatically into `runtime/`, ensuring all dependencies are ready without any network connection. 

If these archives are missing or corrupted, the bootstrap falls back to downloading dependencies via `pip`/`apt` or from GitHub releases.

---

## 📂 Archive Contents

| Archive File | Description |
| :--- | :--- |
| `pygame-2.6.1.data.tar.gz` | Pygame data files & resources |
| `pygame-2.6.1.dist-info.tar.gz` | Pygame distribution metadata |
| `pygame.libs.tar.gz` | Pygame compiled libraries (`.so`) |
| `pygame.tar.gz` | Pygame Python source modules |

> ✅ **Note:** These four archives provide a complete, self-contained Pygame runtime — no external dependencies required.

---

## 📁 Expected Structure
Each archive may contain either:
* Direct Python packages (e.g., `pygame/`, `evinput/`, `fbdisplay/`)
* A root `runtime/` folder containing all packages

The bootstrap merges all archives into the `runtime/` directory, preserving the final structure:

```text
voiddesk/
├── runtime/
│   ├── pygame/
│   ├── pygame.libs/
│   ├── pygame-2.6.1.data/
│   ├── pygame-2.6.1.dist-info/
│   └── ... (other dependencies)
├── assets/
│   └── runtime_archives/
│       ├── pygame-2.6.1.data.tar.gz
│       ├── pygame-2.6.1.dist-info.tar.gz
│       ├── pygame.libs.tar.gz
│       └── pygame.tar.gz
└── ...

```

---

## 🔄 Bootstrap Priority

The bootstrap follows this ordered fallback chain:

1. **`runtime/` already exists and is complete?**
* → ✅ SKIP — use existing runtime


2. **Archives present in `assets/runtime_archives/`?**
* → ✅ EXTRACT — offline, zero network


3. **Internet available?**
* → ✅ DOWNLOAD — via `pip`/`apt` (system packages)


4. **GitHub releases available?**
* → ✅ DOWNLOAD — prebuilt runtime from GitHub


5. **Nothing works?**
* → ❌ FAIL — show error and exit



---

## 🛠️ How to Use

### 🔹 For End Users

Nothing to do. The bootstrap handles everything automatically.

### 🔹 For Developers (Creating Archives)

If you have a working `runtime/` directory and want to package it:

**ZIP format**

```bash
cd /path/to/voiddesk
zip -r assets/runtime_archives/mycustom_runtime.zip runtime/

```

**TAR.GZ format**

```bash
cd /path/to/voiddesk
tar -czf assets/runtime_archives/mycustom_runtime.tar.gz runtime/

```

> ⚠️ **Note:** Archives are extracted in alphabetical order by filename. Name them carefully if dependency order matters (e.g., `00_pygame.tar.gz`).

---

## 🧪 Verification

After extraction, you can verify the runtime:

```bash
ls -la runtime/
python3 -c "import pygame; print(pygame.version.ver)"

```

**Expected output:** `2.6.1` (or your installed version).

---

## 🐛 Troubleshooting

| Symptom | Possible Cause | Solution |
| --- | --- | --- |
| **ModuleNotFoundError: No module named 'pygame'** | Runtime not extracted | Check `assets/runtime_archives/` exists and contains archives |
| **`runtime/` exists but import fails** | Corrupted extraction | Delete `runtime/` and restart VoidDesk |
| **Archives present but not extracted** | Permission issues | Check write permissions on `runtime/` directory |
| **Network fallback fails** | No internet or pip missing | Manually install dependencies via `pip install pygame` |

---

## 📊 Archive Size Comparison

| Format | Size (approx) | Speed |
| --- | --- | --- |
| **.zip** | 15–20 MB | Fast extraction |
| **.tar.gz** | 12–18 MB | Slower extraction, smaller size |
| **.tgz** | 12–18 MB | Same as `.tar.gz` |

> 💡 **Recommendation:** Use `.tar.gz` for smaller package size, `.zip` for faster extraction on low-power devices.

---

## 🔗 Related Resources

* [VoidDesk GitHub Repository](https://www.google.com/search?q=%23)
* [Pygame Documentation](https://www.google.com/search?q=https://www.pygame.org/docs/)
* [muOS Firmware](https://www.google.com/search?q=%23)

---

## 📝 License

This runtime packaging is part of the VoidDesk project.
All third-party libraries (Pygame, etc.) retain their original licenses.

*Last updated: 2026-08-26 — SPDW Factory 🚀*
