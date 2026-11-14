import struct
import zlib

import pytest

from tools.capture_love_screenshots import (
    DEFAULT_SETTLE_SECONDS,
    perceptual_distance,
    perceptual_samples,
)


def _png_chunk(kind, payload):
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    )


def _write_rgb_png(path, color, width=64, height=48):
    row = bytes(color) * width
    scanlines = b"".join(b"\x00" + row for _ in range(height))
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    payload = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", header)
        + _png_chunk(b"IDAT", zlib.compress(scanlines))
        + _png_chunk(b"IEND", b"")
    )
    path.write_bytes(payload)


def test_perceptual_samples_ignore_small_animation_pulses(tmp_path):
    base = tmp_path / "base.png"
    pulse = tmp_path / "pulse.png"
    _write_rgb_png(base, (40, 70, 100))
    _write_rgb_png(pulse, (41, 71, 101))

    base_samples = perceptual_samples(base)
    pulse_samples = perceptual_samples(pulse)
    assert len(base_samples) == 32 * 24 * 3
    assert perceptual_distance(base_samples, pulse_samples) == pytest.approx(1.0)


def test_perceptual_samples_distinguish_different_scenes(tmp_path):
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    _write_rgb_png(first, (20, 30, 40))
    _write_rgb_png(second, (100, 120, 140))

    assert perceptual_distance(
        perceptual_samples(first), perceptual_samples(second)
    ) > 2.0


def test_perceptual_samples_reject_invalid_png(tmp_path):
    invalid = tmp_path / "not-a-png.png"
    invalid.write_bytes(b"not a png")
    with pytest.raises(ValueError, match="invalid PNG signature"):
        perceptual_samples(invalid)


def test_default_capture_settle_covers_pty_initialization_animation():
    assert DEFAULT_SETTLE_SECONDS == 1.6
