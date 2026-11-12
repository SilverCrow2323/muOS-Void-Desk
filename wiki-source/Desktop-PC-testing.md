# 🖥️ Desktop version — PC testing

The Linux desktop version is primarily a **development and testing environment**. Use it to check the interface, navigation, layout and supported workflows directly on a PC before testing on a handheld.

## What works on PC
- 🧪 Run the Pygame reference frontend.
- 🧭 Inspect screens and navigation flows.
- 🧰 Test desktop-safe tools and local UI behaviour.
- 📸 Capture screenshots with the supported F12 shortcut.
- 🔍 Inspect logs and run local diagnostics.

## What is different from muOS
- No handheld framebuffer integration.
- No muOS package manager or .muxapp installation flow.
- No device-specific power-off or reboot actions.
- No guarantee that network or hardware services behave like they do on the handheld.
- XFCE image mounting and other device-only operations are unavailable unless separately implemented for the PC host.

> [!IMPORTANT]
> A successful PC test is not proof of compatibility with a physical H700 handheld. Test device input, display, audio, storage, power and muOS lifecycle on the target hardware.

## Install the PC test folder
1. Download the **Linux PC bundle** from [GitHub Releases](https://github.com/SilverCrow2323/Void-Desk-Project/releases).
2. Open your Home folder.
3. Extract the archive there.
4. Keep the resulting **VoidDesk-PC/** folder inside Home.
5. Open that folder and run **launch-pc.sh**.

Expected layout:

~~~text
/home/<your-user>/
└── VoidDesk-PC/
    ├── launch-pc.sh
    ├── voiddesk.py
    ├── desk/
    ├── love/
    ├── assets/
    ├── resources/
    └── data/
~~~

The first Pygame launch creates **.venv_desktop/** inside the PC folder and installs its Python dependencies. Internet access is required for this first setup.

## Start from a terminal
~~~bash
cd "$HOME/VoidDesk-PC"
./launch-pc.sh
~~~

For direct engine selection:

~~~bash
python3 voiddesk.py --py
python3 voiddesk.py --love
python3 voiddesk.py --help
~~~

Pygame is the reference frontend. LÖVE remains experimental and requires a system LÖVE installation on PC.

## Keep the PC copy separate
- Keep the PC test folder under $HOME/VoidDesk-PC.
- Do not copy the PC virtual environment into a muOS package.
- Back up personal test data before replacing the folder with a new build.
- Keep logs and screenshots inside the PC copy unless you deliberately export them.

See [Development](Development) for source builds and test commands.
