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
from io import BytesIO
from base64 import b64decode

from PIL import Image
from PIL import ImageDraw
from PIL.Image import Image as Sheet
from PIL.ImageDraw import ImageDraw as Draw
from PIL.ImageFont import ImageFont

from seafront.model.pilfont import Seafront16pxUI
from seafront.model.unifont import draw_unifont_glyph
from seafront.unicode import is_non_printable
from unicodedata import category

CELL_SIZE: int = 64
"""Seafront design cell is limited to 64*64 pixel by typography design"""

COLUMN_SIZE: int = 16
"""
Seafront default column size for font design table. 
We will format all font tables by 16 columns and x rows.
"""

FONT_CELL_32PX = (
    b"iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAMAAABEpIrGAAAATlBMVEUAAAAAAAD4+P"
    b"j////G4Lap8NPR8OPf8OnL2/y52fin1vS3v/a2w+Tu9vvm8vm0x9HAzdT79YH/+pH1"
    b"3O3tzOf64fLyydH1wcH89fr88PjzX8d/AAAAGnRSTlMA//////////////////////"
    b"///////////wdS/SAAAADTSURBVDiNvZOLDoMgDEWJKzo1iryc/v+PrsUCgy0xy8x6"
    b"k0OAcm0JCpAp1jUiBwg5zVHbjty3eXqRFDLPwl7IypJ/cXisSRlJmNDcorxFBmRhQp"
    b"5YjwzIutZhUWUstYNiB22OBVU7KK7BaD7ADl3LQgccyOFYUERMiPstOuBADnyAKMV4"
    b"j6GcQzo39DwnjB8S+qFIAG1Y+Akk1XBIEUGASQvWI6kGPkCEtzbJoWyzuihyKC7qgi"
    b"7SRUEXxnSzEBbPa/i9iy8eTMMOJ4/W+urRnv3+T2qwJYya7JL/AAAAAElFTkSuQmCC"
)
"""
Seafront design font cell encoded as 32px image bytes for optimized generation,
synced with :code:`assets/font-cell-64px.png`.
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


def make_font_cell() -> Sheet:
    """
    Create font table's font cell by embedded image data.

    :return: The image cell 64x64
    """
    cell_32px = Image.open(BytesIO(b64decode(FONT_CELL_32PX))).convert("RGBA")
    return cell_32px.resize((CELL_SIZE, CELL_SIZE), Image.Resampling.NEAREST)


def make_null_cell(*,
                   border_color: str = "#fbf581",
                   grid_x_color: str = "#f8f8f8",
                   grid_y_color: str = "#ffffff") -> Sheet:
    """
    Create font table's null cells,
    as checker board-like filled image::

        B B B B B
        B X Y X B
        B Y X Y B
        B X Y X B
        B B B B B

    :param border_color: 2px border color B of the cell, default to light yellow
    :param grid_x_color: 4px Grid filling color X
    :param grid_y_color: 4px Grid filling color Y
    :return: The image cell 64x64
    """
    size: int = CELL_SIZE // 2
    border: int = 1
    grid_size: int = 2
    image = Image.new("RGBA", (size, size), border_color)
    draw = ImageDraw.Draw(image)

    # Draw checker board-like pattern to fill null cell
    for y in range(border, size - border):
        for x in range(border, size - border):
            x_grid: int = (x - border) // grid_size
            y_grid: int = (y - border) // grid_size

            if (x_grid + y_grid) % 2 == 0:
                draw.point((x, y), fill=grid_x_color)
            else:
                draw.point((x, y), fill=grid_y_color)

    return image.resize((CELL_SIZE, CELL_SIZE), Image.Resampling.NEAREST)


def generate_font_table(fn: Callable[[int], tuple[str, Sheet, int | None]],
                        seafront_ui: Seafront16pxUI[ImageFont],
                        cells_count: int,
                        unifont_hex: dict[int, bytes],
                        column_size: int=COLUMN_SIZE) -> Sheet:
    """
    Generate a font table as Pillow image object

    :param fn: cell definition function by index,
        returns [1. cell name, 2. its graphic, 3. its character codepoint]
    :param cells_count: All cell counts to generate
    :param column_size: The column size to format the table
    :param seafront_ui: Seafront UI font for font-table's labeling
    :param unifont_hex: Loaded Unifont table
    :return: Pillow image object
    """
    row_size: int = (cells_count + column_size - 1) // column_size
    sheet: Sheet = Image.new(
        "RGBA",
        (column_size * CELL_SIZE, row_size * CELL_SIZE),
        (255, 255, 255, 0),
    )
    draw: Draw = ImageDraw.Draw(sheet)

    for i in range(cells_count):
        x: int = (i % column_size) * CELL_SIZE
        y: int = (i // column_size) * CELL_SIZE

        (label, cell, codepoint) = fn(i)
        sheet.alpha_composite(cell, (x, y))

        letter_w: int = len(label)
        letter_y: int = y - 1
        letter_x: int = x + 2
        letter_spacing: int = 0

        # Font is compact by default for narrower characters
        # Unicode codepoint U+10FFFF (8 characters)
        letter_font = seafront_ui.compact
        # Within 7 characters U+00FFF
        # Have more left padding
        if letter_w <= 7:
            letter_x += 2
        # Within 6 characters U+0FFF,
        # Can use squared style font
        if letter_w <= 6:
            letter_spacing += 1
            letter_font = seafront_ui.squared

        for char in range(letter_w):
            draw.text((letter_x, letter_y), label[char], fill=(70, 70, 70), font=letter_font)
            w: float | int = draw.textlength(label[char], font=letter_font)
            letter_x += int(w) + letter_spacing

        # Skip drawing non-printable
        # BUT omit control/format and line/paragraph separators
        # as it has useful named graphic to display
        if (not isinstance(codepoint, int)
            or is_non_printable(category(chr(codepoint)),"Cc", "Cf", "Zl", "Zp")):
            continue

        bitmap = unifont_hex.get(codepoint)
        if bitmap is not None:
            x += 3
            y += 15
            def draw_fn(col: int, row: int):
                draw.rectangle((
                    x + col, y + row,
                    x + (col + 1) - 1,
                    y + (row + 1) - 1,
                ), fill=(0, 0, 0, 255))
            draw_unifont_glyph(bitmap, draw_fn)

    return sheet
