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
from sys import stderr

from PIL import Image
from PIL import ImageDraw
from PIL.Image import Image as Sheet
from PIL.ImageFile import ImageFile
from PIL.ImageFont import BaseImageFont

from seafront.font import (
    SCRIPTS_DIR,
    FONT_DIR
)
import subprocess

SCRIPT: str = "aseprite/create-project.lua"
"""aseprite project generation script"""

CELL_SIZE: int = 64
"""Seafront design cell is limited to 64*64 pixel by typography design"""

COLUMN_SIZE: int = 16
"""
Seafront default column size for font design table. 
We will format all font tables by 16 columns and x rows.
"""


def generate_font_table(fn: Callable[[int], tuple[str, ImageFile]],
                        labels_font: BaseImageFont,
                        cells_count: int,
                        column_size: int=COLUMN_SIZE) -> Sheet:
    """
    Generate a font table as Pillow image object

    :param fn: cell definition function by index, returns [1. cell name and 2. its graphic]
    :param cells_count: All cell counts to generate
    :param column_size: The column size to format the table
    :param labels_font: The font to use in each cell labels
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

        (label, cell) = fn(i)
        sheet.alpha_composite(cell, (x, y))

        draw.text(
            (x + 5, y - 1),
            label,
            font=labels_font,
            fill=(70, 70, 70),
        )

    return sheet
