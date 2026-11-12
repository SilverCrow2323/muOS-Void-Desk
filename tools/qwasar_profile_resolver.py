#!/usr/bin/env python3
"""Build the read-only effective QWASAR composition for Pygame and LÖVE.

Example:
    python3 tools/qwasar_profile_resolver.py --root . \
        --output data/qwasar_effective_profile.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from desk.qwasar.profile_resolver import (  # noqa: E402
    ProfileResolutionError,
    QwasarProfileResolver,
)


def _atomic_json_write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    fd, temporary = tempfile.mkstemp(
        prefix="." + path.name + ".",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=APP_ROOT)
    parser.add_argument("--manifest", default="data/qwasar_ui_manifest.json")
    parser.add_argument("--profile", help="selected .qprofile; defaults to QWASAR_PROFILE or desk_config.json")
    parser.add_argument("--default-profile", default="data/profiles/voiddesk-handheld-default.qprofile.json",
                        help="platform-specific safe fallback profile")
    parser.add_argument("--platform", choices=("muos", "knulli", "rocknix", "desktop", "custom"),
                        help="host platform used for compatibility checks")
    parser.add_argument("--model", help="optional device model compatibility check")
    parser.add_argument("--output", type=Path, default=Path("data/qwasar_effective_profile.json"))
    parser.add_argument("--strict", action="store_true", help="reject selected-profile errors instead of falling back")
    parser.add_argument("--stdout", action="store_true", help="print the resolved JSON instead of writing the output file")
    args = parser.parse_args(argv)

    root = args.root.expanduser().resolve()
    output = args.output.expanduser()
    if not output.is_absolute():
        output = root / output
    output = output.resolve()
    if not output.is_relative_to(root):
        parser.error("--output must remain inside --root")

    try:
        selected_profile = args.profile
        if selected_profile is None and not os.environ.get("QWASAR_PROFILE"):
            config_path = root / "data" / "desk_config.json"
            try:
                config_data = json.loads(config_path.read_text(encoding="utf-8"))
                configured = config_data.get("qwasar_profile") if isinstance(config_data, dict) else None
                if isinstance(configured, str) and configured.strip():
                    selected_profile = configured
            except (OSError, UnicodeError, json.JSONDecodeError):
                pass

        default_profile = args.default_profile
        if Path(default_profile).is_absolute():
            default_profile = str(Path(default_profile).resolve())
        resolver = QwasarProfileResolver(
            root,
            manifest_path=args.manifest,
            default_profile_path=default_profile,
        )
        target_platform = args.platform or os.environ.get("VOIDDESK_PLATFORM")
        target_model = args.model or os.environ.get("VOIDDESK_MODEL")
        composition = resolver.resolve(
            selected_profile,
            fallback_to_default=not args.strict,
            target_platform=target_platform,
            target_model=target_model,
        )
        if args.stdout:
            print(json.dumps(composition, ensure_ascii=False, indent=2))
        else:
            _atomic_json_write(output, composition)
            print(
                "[QWASAR Profile Resolver] OK — "
                f"{composition['profile']['id']} → {output}"
            )
        for warning in composition.get("warnings", []):
            print("[QWASAR Profile Resolver] WARNING: " + warning, file=sys.stderr)
        return 0
    except (ProfileResolutionError, OSError, ValueError) as exc:
        print("[QWASAR Profile Resolver] ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
