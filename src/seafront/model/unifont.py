# Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
# with Reserved Font Name "BTE Seafront".
# Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).
#
# This Font Software is licensed under the SIL Open Font License, Version 1.1.
# This license is available with a FAQ at:
# https://openfontlicense.org
"""\
unifont.hex helper
"""
from collections.abc import Callable
from typing import IO


def load_unifont_hex(io: IO[str], glyphs=None) -> dict[int, bytes]:
    """
    Load a Bitmap table from GNU Unifont .hex file

    :param io: Text IO for the unifont.hex file to load
    :param glyphs: Output dict to load data in (Optional)
    :return: Bitmap table of all Unicode codepoints in the hex file
    """
    if glyphs is None:
        glyphs = {}
    for line in io:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        codepoint, bitmap = line.split(":", 1)
        glyphs[int(codepoint, 16)] = bytes.fromhex(bitmap)
    return glyphs


def draw_unifont_glyph(bitmap: bytes,
                       draw_fn: Callable[[int, int], None]) -> None:
    """Draw a 16×16 Unifont bitmap directly onto an ImageDraw canvas.

    :param bitmap: Unifont bitmap bytes to draw
    :param draw_fn: Callable(col, row) for all pixel bits
    :return: None, drawn on draw_fn(col, row)
    """

    bytes_per_row = 2 if len(bitmap) == 32 else 1
    width = bytes_per_row * 8
    height = len(bitmap) // bytes_per_row

    for row in range(height):
        bits = int.from_bytes(
            bitmap[row * bytes_per_row:(row + 1) * bytes_per_row],
            byteorder="big",
        )

        for col in range(width):
            if not bits & (1 << (width - 1 - col)):
                continue

            draw_fn(col, row)