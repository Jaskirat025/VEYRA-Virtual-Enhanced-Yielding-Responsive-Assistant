#!/usr/bin/env python3
"""Generate the application and tray icons as PNG and ICO.

Run from the repository root:

    python scripts/generate_icons.py

The artwork is a simple silver core with a molten-orange ring on a gunmetal
disc, matching the design tokens. It is generated so the repository does not
depend on binary design files.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

OUTPUT = Path(__file__).resolve().parents[1] / "src-tauri" / "icons"

GUNMETAL = (22, 28, 31)
SILVER = (228, 232, 235)
STEEL = (139, 148, 155)
ACCENT = (255, 90, 31)


def _lerp(first: tuple[int, int, int], second: tuple[int, int, int], amount: float):
    amount = max(0.0, min(1.0, amount))
    return tuple(round(a + (b - a) * amount) for a, b in zip(first, second, strict=True))


def _pixel(size: int, x: int, y: int) -> tuple[int, int, int, int]:
    center = (size - 1) / 2
    dx = (x - center) / size
    dy = (y - center) / size
    distance = (dx * dx + dy * dy) ** 0.5

    alpha = max(0.0, min(1.0, (0.485 - distance) * size * 1.6))
    if alpha <= 0:
        return (0, 0, 0, 0)

    if distance < 0.30:
        colour = _lerp(SILVER, STEEL, (distance / 0.30) ** 1.4)
    elif distance < 0.345:
        colour = _lerp(STEEL, GUNMETAL, (distance - 0.30) / 0.045)
    else:
        colour = GUNMETAL

    if 0.375 <= distance <= 0.405:
        colour = ACCENT
    elif 0.405 < distance <= 0.43:
        colour = _lerp(ACCENT, GUNMETAL, (distance - 0.405) / 0.025)

    return (*colour, round(alpha * 255))


def _chunk(tag: bytes, data: bytes) -> bytes:
    body = tag + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def _png(size: int) -> bytes:
    raw = bytearray()
    for y in range(size):
        raw.append(0)
        for x in range(size):
            raw.extend(_pixel(size, x, y))

    header = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + _chunk(b"IEND", b"")
    )


def _ico(images: dict[int, bytes]) -> bytes:
    header = struct.pack("<HHH", 0, 1, len(images))
    entries = bytearray()
    offset = 6 + 16 * len(images)
    payload = bytearray()

    for size, data in sorted(images.items()):
        dimension = 0 if size >= 256 else size
        entries.extend(
            struct.pack("<BBBBHHII", dimension, dimension, 0, 0, 1, 32, len(data), offset)
        )
        offset += len(data)
        payload.extend(data)

    return header + bytes(entries) + bytes(payload)


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)

    for size, name in ((32, "32x32.png"), (128, "128x128.png"), (256, "128x128-2x.png")):
        (OUTPUT / name).write_bytes(_png(size))

    (OUTPUT / "icon.png").write_bytes(_png(512))
    (OUTPUT / "icon.ico").write_bytes(_ico({size: _png(size) for size in (16, 32, 48, 256)}))

    print(f"icons written to {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
