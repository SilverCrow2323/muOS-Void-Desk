# Void Desk — Linux PC bundle

This package is a portable source distribution for Linux desktop systems, not an AppImage or statically linked executable.

## Requirements

- Linux x86_64 or aarch64
- Python 3.10+
- A graphical desktop session and SDL2 runtime libraries
- Internet access for first-run Python dependency installation

## Start

```sh
tar -xzf Void-Desk-PC-Linux-*.tar.gz
cd VoidDesk-PC
chmod +x launch-pc.sh
./launch-pc.sh
```

The launcher invokes the existing `voiddesk.py --py` path. On first run, Void Desk creates `.venv_desktop` and installs Pygame and psutil from PyPI. LÖVE mode is optional and requires a system LÖVE installation.

muOS-specific operations (framebuffer integration, package management and the optional XFCE image lifecycle) are not available on a normal PC. Hardware-specific features remain disabled or unavailable where the host does not provide the required capabilities.

Verify the adjacent `.sha256` file before use. Keep your personal configuration and backups outside the extracted application directory when replacing builds.
