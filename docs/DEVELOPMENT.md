# Development and verification

## Supported local environment

The automated Python checks target Python 3.11. The actual handheld Python/Pygame combination depends on the firmware image and compatible wheel availability on PyPI.

There is no root-level requirements.txt currently. The test suite uses pytest; CI linting uses Ruff. The handheld Pygame runtime is provisioned by bin/bootstrap_lite.py, while the PC launcher creates .venv_desktop and installs its own runtime dependencies.

## Set up a check environment

~~~bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install pytest ruff
~~~

## Run checks

~~~bash
python -m compileall -q BUILDCHECK.py voiddesk.py bin desk service outdesk voidcast_addons assets
python -m pytest -q
python BUILDCHECK.py
~~~

The optional smoke mode starts the Python frontend headlessly for a short interval. It needs Pygame and may not be meaningful on every CI runner:

~~~bash
python BUILDCHECK.py --smoke
~~~

## Status-poller regression tests

`tests/test_status_poller.py` exercises the asynchronous status cache without requiring Pygame or handheld hardware. It verifies that callers receive an immediate cached snapshot while a system probe is blocked, that reads do not create parallel workers, and that a failed probe does not permanently disable refresh.

The CI result is a code-level check only. Before publishing a muOS release, verify on an RG35XXSP (and preferably an RG35XX-H) that:
- the orbit animation and D-pad response remain smooth with Bluetooth enabled and disabled;
- the UPLINK Bluetooth panel can still bring the adapter up/down normally;
- END SESSION → Power off turns the device fully off and does not leave it warm with the LED off;
- normal reboot, app close and XFCE session hand-off still behave as before.

## Lua and shell checks

On Debian/Ubuntu, install LuaJIT:

~~~bash
sudo apt-get update
sudo apt-get install luajit
find love -type f -name '*.lua' -print0 | xargs -0 -r -n 1 sh -c 'luajit -b "$1" /dev/null' _
~~~

Shell entry points are POSIX-checked in CI with sh -n. For a local spot check:

~~~bash
sh -n mux_launch.sh
sh -n voiddesk.sh
~~~

## What CI does not prove

A successful GitHub Actions run proves syntax, focused unit tests, selected static diagnostics and shell/Lua parsing on Ubuntu. It does not prove:
- framebuffer behaviour or controller mapping on a physical handheld;
- compatibility with every muOS release or every H700 device;
- package install/removal flows that need real hardware and elevated privileges;
- desktop-image creation, mount, shutdown or suspend behaviour;
- every IPTV playlist, provider, network or media decoder.

Those require manual verification on the target device and should be reported as such.
