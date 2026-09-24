# Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
# with Reserved Font Name "BTE Seafront".
# Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).
#
# This Font Software is licensed under the SIL Open Font License, Version 1.1.
# This license is available with a FAQ at:
# https://openfontlicense.org
"""\
Graphics helper for design projects
"""
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from PIL.Image import Image as Sheet
from PIL import Image

from seafront.generate import CELL_SIZE
from seafront.model.font import FontProfile, TypefaceAccent, TypographyData


def save_pbm(fn: Callable[[int, int], Literal["0", "1"]],
             w: int, h: int,
             path: str | Path) -> None:
    """
    Save a Pillow image as an ASCII PBM (P1).

    :param fn: The pixel function which asks for bitmap value 0/1 per x,y pixel
    :param w: Width of the bitmap
    :param h: Height of the bitmap
    :param path: Output path to write bitmap file
    :return: None, writted file to path
    """

    with open(path, "w", encoding="ascii") as f:
        f.write("P1\n")
        f.write(f"{w} {h}\n")

        for y in range(h):
            row: list[str] = []

            for x in range(w):
                row.append(fn(x, y))

            f.write(" ".join(row))
            f.write("\n")


def export_graphics(
    name_fn: Callable[[int], str],
    source_img: Sheet,
    glyphs_dir: Path,
    profile: FontProfile,
    verbose: bool,
    codepoint: int | None=None,
) -> int:
    """
    Mirrors aseprite script export-graphics.lua

    :param name_fn: Callback called to get the glyph name
    :param source_img: Source image to export graphics as
    :param glyphs_dir: The glyphs output directory for this image
    :param profile: Font profile for typography constants
    :param verbose: Verbose logging
    :param codepoint: The Unicode point if existed
    :return: Number of exported glyphs from source image
    """

    def to_bitmap(image: Sheet) -> Sheet:
        """
        :param image: Pillow image object
        :return: Image sheet as inverted 0/255 bitmap
        """
        if image.mode == "RGBA":
            background = Image.new("RGBA", image.size, "white")
            image = Image.alpha_composite(background, image)

        # grayscale convert "L"
        image = image.convert("L")

        def threshold_fn(p: int):
            """
            Invert of the default :code:`image.convert("1")`,
            place Black on point > 127 else White.

            This makes full black bitmap for transparent/white image sheet.
            """
            return 0 if p > 127 else 255

        return image.point(threshold_fn, mode="1")

    accent: TypefaceAccent = profile["accent"]["base"]
    typography: TypographyData = profile["typography"]

    pbm_cell: int = accent["ascender"] + accent["descender"]
    left_x: int = pbm_cell - typography["maximum-width"]
    crop_x: int = typography["origin-x"] - left_x
    crop_y: int = typography["origin-y"] + accent["descender"]

    source: Sheet = to_bitmap(source_img)
    width, height = source.size
    h = round(height / CELL_SIZE)
    w = round(width / CELL_SIZE)
    glyph_count = h * w

    saved: int = 0

    for i in range(glyph_count):
        paste_x = (i % w) * CELL_SIZE + crop_x
        paste_y = (i // w) * CELL_SIZE + crop_y

        bitmap: Sheet = Image.new("1", (pbm_cell, pbm_cell), 0)
        bitmap.paste(source, (-paste_x, -paste_y))
        pixels = bitmap.load()

        # Skip if the bitmap is empty
        # Note: that we inverted the bitmap so 0 is the background,
        #       to make Sheet.getbbox() returns None
        #       for all empty bitmap (Full white/transparent).
        if pixels is None or bitmap.getbbox() is None:
            if verbose and isinstance(codepoint, int):
                print(f"Skipped U+{codepoint + i:04X} (Empty)")
            elif verbose:
                print(f"Skipped cell [{i}] (Empty)")
            continue

        try:
            def get_pixel(x: int, y: int) -> Literal["0", "1"]:
                """
                Get bitmap pixel as 0/1 string literal.
                :class:`PixelAccess` as White (255) as foreground
                and Black (0) as background.
                """
                if (pixels is not None) and (pixels[x, y] == 255):
                    return "1"
                return "0"

            name: str = name_fn(codepoint + i) if isinstance(codepoint, int) else name_fn(i)
            save_pbm(get_pixel, pbm_cell, pbm_cell, glyphs_dir / f"{name}.pbm")
            saved = saved + 1
            if verbose:
                print(f"Wrote: {name}.pbm")
        except (FileNotFoundError, PermissionError, OSError) as error:
            print(f"Error occurred: {error}")

    return saved