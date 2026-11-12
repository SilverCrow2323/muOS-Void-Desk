# Void Desk — Linux PC test bundle

The PC bundle is primarily for development, UI checks and workflow testing on a Linux computer. It is not the handheld package and is not a replacement for muOS.

## Install location

**Keep the complete extracted folder in your user's Home directory.**

1. Download the Linux PC archive from [GitHub Releases](https://github.com/SilverCrow2323/Void-Desk-Project/releases).
2. Open your Home folder.
3. Extract the archive there. It creates VoidDesk-PC/.
4. Open VoidDesk-PC/ and run launch-pc.sh.

Expected location:

~~~text
$HOME/VoidDesk-PC/
~~~

Do not scatter the bundle files across system folders. Keeping the project in one folder makes updates, logs, test assets and its virtual environment easy to manage.

## Requirements
- Linux x86_64 or aarch64
- Python 3.10+
- A graphical desktop session and SDL2 runtime libraries
- Internet access for first-run Python dependency installation

## Start
~~~bash
cd "$HOME/VoidDesk-PC"
./launch-pc.sh
~~~

The launcher invokes voiddesk.py --py. On first run, Void Desk creates .venv_desktop/ inside this folder and installs Pygame and psutil. LÖVE mode is optional and requires a system LÖVE installation.

## PC and handheld differences
| PC test build | muOS handheld |
|---|---|
| UI and navigation checks | Physical controller and device checks |
| Desktop-safe tools | Device/firmware capabilities |
| Linux desktop session | muOS application lifecycle |
| PC screenshots and logs | Handheld screenshots and logs |
| No muOS package manager | .muxapp installation |

> [!IMPORTANT]
> Passing a PC test does not certify a handheld. Test the exact device and muOS release before describing a feature as working on hardware.

## Keep data safe
Back up personal test data before replacing the folder. Do not copy .venv_desktop/ into the muOS package.
