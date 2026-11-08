# Development and architecture

## Runtime path

On the handheld, mux_launch.sh starts service/voiddesk_service.py and then the configured frontend:

- py: desk/main.py with the bootstrapped Pygame runtime (recommended).
- love: lib/love love/ (experimental prototype).

The local service is started by the shell launcher. LÖVE communicates with it through JSON request/response files under data/.

## Repository map

| Path | Responsibility |
|---|---|
| desk/ | Pygame frontend |
| desk/hubs/ | Pygame feature panels |
| love/ | Experimental LÖVE frontend |
| love/scenes/ | LÖVE scene modules |
| love/core/ | Scene stack, input, render, bridge, widgets and effects |
| service/ | Background service and IPTV service module |
| bin/ | Runtime bootstrap, desktop image and device scripts |
| assets/, resources/ | Artwork, fonts, sounds, images |
| tests/ | Focused regression tests |

## Local checks

~~~bash
python3 -m pip install pytest ruff
python -m compileall -q BUILDCHECK.py voiddesk.py bin desk service outdesk voidcast_addons assets
python -m pytest -q
python BUILDCHECK.py
find love -type f -name '*.lua' -print0 | xargs -0 -r -n 1 sh -c 'luajit -b "$1" /dev/null' _
~~~

CI also runs focused LÖVE core tests for lazy scene loading, scene navigation and bridge request serialization.

## Contributing

- Keep pull requests focused.
- Add regression tests when practical.
- Never hide failing checks with || true.
- Keep optional dependencies optional.
- Avoid blocking commands in render/update loops.
- Record hardware and firmware used for manual tests.
- Do not claim LÖVE parity with Pygame until verified feature by feature.
