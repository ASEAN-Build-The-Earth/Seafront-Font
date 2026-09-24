# Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
# with Reserved Font Name "BTE Seafront".
# Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).
#
# This Font Software is licensed under the SIL Open Font License, Version 1.1.
# This license is available with a FAQ at:
# https://openfontlicense.org
"""\
Project file generation code
"""
from collections.abc import Callable
from importlib.resources import as_file
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import TextIO

from PIL import Image
from PIL import ImageDraw
from PIL.Image import Image as Sheet
from PIL.ImageFont import BaseImageFont
from seafront.unicode import is_non_printable
from unicodedata import category

CELL_SIZE: int = 64
"""Seafront design cell is limited to 64*64 pixel by typography design"""

COLUMN_SIZE: int = 16
"""
Seafront default column size for font design table. 
We will format all font tables by 16 columns and x rows.
"""

def generate_empty_graphics(file: Traversable,
                            parent: Path,
                            cells_count: int,
                            column_size: int=COLUMN_SIZE) -> None:
    """
    Save an empty Transparent design image and same to file.

    :param file: File location to save
    :param parent: Parent path for debugging
    :param cells_count: Cell count to determind image size
    :param column_size: Column size to determind image size
    :return: None, written to filesystem
    """
    with as_file(file) as saves:
        row_size = (cells_count + column_size - 1) // column_size
        sheet = Image.new(
            "RGBA",
            (column_size * CELL_SIZE, row_size * CELL_SIZE),
            (255, 255, 255, 0),
        )
        sheet.save(saves)
        print(f"Wrote Empty \33[33m'{saves.relative_to(parent)}'\33[0m")


def generate_font_table(fn: Callable[[int], tuple[str, Sheet, int | None]],
                        labels_font: tuple[BaseImageFont, BaseImageFont],
                        cells_count: int,
                        unifont_hex: dict[int, bytes],
                        column_size: int=COLUMN_SIZE) -> Sheet:
    """
    Generate a font table as Pillow image object

    :param fn: cell definition function by index,
        returns [1. cell name, 2. its graphic, 3. its character codepoint]
    :param cells_count: All cell counts to generate
    :param column_size: The column size to format the table
    :param labels_font: The font to use in each cell labels, as [regular, condensed]
    :param unifont_hex: Loaded Unifont table
    :return: Pillow image object
    """
    row_size = (cells_count + column_size - 1) // column_size
    sheet = Image.new(
        "RGBA",
        (column_size * CELL_SIZE, row_size * CELL_SIZE),
        (255, 255, 255, 0),
    )
    draw = ImageDraw.Draw(sheet)

    for i in range(cells_count):
        row = i // column_size
        col = i % column_size

        x = col * CELL_SIZE
        y = row * CELL_SIZE

        (label, cell, codepoint) = fn(i)
        (font16_regular, font_condensed) = labels_font
        sheet.alpha_composite(cell, (x, y))

        letter_w: int = len(label)
        letter_y: int = y - 1
        letter_x: int = x + 2
        letter_spacing: int = 1

        # Font is condensed by default for Max
        # Unicode codepoint U+10FFFF (8 characters)
        letter_font: BaseImageFont = font_condensed
        # Within 7 characters U+00FFF
        # Have more left padding
        if letter_w <= 7:
            letter_x += 2
        # Within 6 characters U+0FFF,
        # Can use regular font
        if letter_w <= 6:
            letter_spacing += 1
            letter_font = font16_regular

        for char in range(letter_w):
            draw.text((letter_x, letter_y), label[char], fill=(70, 70, 70), font=letter_font)
            w = draw.textlength(label[char], font=letter_font)
            letter_x += int(w) + letter_spacing

        # Skip drawing non-printable
        # BUT omit control/format and line/paragraph separators
        # as it has useful named graphic to display
        if (not isinstance(codepoint, int)
            or is_non_printable(category(chr(codepoint)),"Cc", "Cf", "Zl", "Zp")):
            continue

        bitmap = unifont_hex.get(codepoint)
        if bitmap is not None:
            draw_unifont_glyph(draw, bitmap, x + 3, y + 15)

    return sheet


def load_unifont_hex(io: TextIO) -> dict[int, bytes]:
    glyphs: dict[int, bytes] = {}
    for line in io:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        codepoint, bitmap = line.split(":", 1)
        glyphs[int(codepoint, 16)] = bytes.fromhex(bitmap)
    return glyphs


def draw_unifont_glyph(draw: ImageDraw.ImageDraw,
                       bitmap: bytes,
                       x: int,
                       y: int,
                       pixel_size: int = 1) -> None:
    """Draw a 16×16 Unifont bitmap directly onto an ImageDraw canvas.

    :param draw: Pillow draw class
    :param bitmap: Unifont bitmap bytes
    :param x: Draw x (top left)
    :param y: Draw y (top left)
    :param pixel_size: (Optional) Scale the draw image
    :return: None, drawn on :class:`ImageDraw.ImageDraw`
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

            draw.rectangle((
                x + col * pixel_size,
                y + row * pixel_size,
                x + (col + 1) * pixel_size - 1,
                y + (row + 1) * pixel_size - 1,
            ), fill=(0, 0, 0, 255))
