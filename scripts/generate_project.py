#!/usr/bin/env python3
# Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
# with Reserved Font Name "BTE Seafront".
# Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).
#
# This Font Software is licensed under the SIL Open Font License, Version 1.1.
# This license is available with a FAQ at:
# https://openfontlicense.org
r"""generate_projects.py

Commandline script to generate Seafront fonts project files.

Usage
-----
using hatch::

    hatch run generate-project

using python::

    python generate_project.py
"""
from importlib.resources import as_file
from importlib.resources.abc import Traversable
from pathlib import Path
from unicodedata import category
from typing import cast, TypedDict, BinaryIO, TextIO, Any

from PIL import Image
from PIL import ImageFont
from PIL.Image import Image as Sheet
from PIL.ImageFont import BaseImageFont

from seafront.core.design.project import check_extra_glyphs
from seafront.generate import generate_font_table, load_unifont_hex, generate_empty_graphics
from seafront.core.design.aseprite_scripts import create_project
from seafront.model.font import FontYML
from seafront.model.glyphs import parse_extra_glyphs, get_extra_glyph_label, ExtraGlyphsList, EXT_PREFIX
from seafront.unicode import load_unicode_blocks, UnicodeBlock, is_non_printable
import seafront.font as font
import yaml
import argparse

FONT16_REGULAR: str = "BTE-Seafront-Square-Regular.ttf"
FONT_CONDENSED: str = "BTE-Seafront-Square-Condensed.ttf"
CELL_64: str = "font-cell-64px.png"
NULL_64: str = "null-cell-64px.png"
UNIFONT: str = "unifont_sample-18.0.01.hex"


def load_yaml(file: Traversable):
    with file.open(encoding="utf-8") as fp:
        return yaml.safe_load(fp)


def has_graphic(unicode: int) -> bool:
    char: str = chr(unicode)
    return not is_non_printable(category(char))


def put_empty_images(design: Traversable,
                     parent: Path,
                     style: str,
                     cell_count: int,
                     ext_glyphs: ExtraGlyphsList | None):
    image = design / f"{style}.png"
    if not image.is_file():
        generate_empty_graphics(image, parent, cell_count)

    if ext_glyphs is None:
        return

    ext_image = design / f"{EXT_PREFIX}{style}.png"
    if ext_image.is_file():
        return

    generate_empty_graphics(ext_image,
                            parent,
                            len(ext_glyphs["glyphs"]),
                            ext_glyphs["column"])

def generate(block: UnicodeBlock,
             assets: ImageAssets,
             *,
             families: set[str],
             styles: list[str] | dict[str, Any]):
    font_cell: Sheet = assets["font_cell"]
    null_cell: Sheet = assets["null_cell"]
    unifont_hex: dict[int, bytes] = assets["unifont_hex"]
    label_font: tuple[BaseImageFont, BaseImageFont] = (assets["font16_regular"],
                                                       assets["font_condensed"])

    project = font.project_root(block["name"])
    with as_file(project) as project_dir:
        project_dir.mkdir(exist_ok=True)

    start = block["start"]
    end = block["end"]
    count = end - start + 1

    def fn(i: int) -> tuple[str, Sheet, int]:
        code: int = start + i
        name: str = f"U+{code:04X}"
        cell = font_cell if has_graphic(code) else null_cell
        return name, cell, code

    sheet = generate_font_table(fn, label_font, count, unifont_hex)

    ext_glyphs: ExtraGlyphsList | None = check_extra_glyphs(block["name"])
    for family in families:
        design = font.project_design(block["name"], family)
        if not design.is_dir():
            with as_file(design) as design_dir:
                design_dir.mkdir(parents=True,exist_ok=True)
        for style in styles:
            put_empty_images(design, project_dir.parents[1], style, count, ext_glyphs)

    table = font.project_font_table(block["name"])
    exist = "Overwritten" if table.is_file() else "Generated"
    with as_file(table) as image_file:
        sheet.save(image_file)
        print(f"{exist} '{image_file.relative_to(project_dir.parents[1])}'")

    create_project(project, False)

    extension: Traversable = font.ext_glyphs_yml(block["name"])
    if extension.is_file():
        glyphs_yml = parse_extra_glyphs(load_yaml(extension))
        columns = glyphs_yml["column"]
        glyphs = glyphs_yml["glyphs"]

        def fn(i: int) -> tuple[str, Sheet, int | None]:
            cell = null_cell if glyphs[i].is_undefined() else font_cell
            return get_extra_glyph_label(i), cell, glyphs[i].cmap

        print(f"{len(glyphs)} glyphs Extension feature found for '{block["name"]}' unicode range")

        sheet = generate_font_table(fn, label_font, len(glyphs), unifont_hex, columns)
        table = font.project_ext_font_table(block["name"])
        exist = "Overwritten" if table.is_file() else "Generated"
        with as_file(table) as image_file:
            sheet.save(image_file)
            print(f"{exist} Extension '{image_file.relative_to(project_dir.parents[1])}'")

        create_project(project, True)


class ImageAssets(TypedDict):
    """
    Assets used in font table generation

    :ivar font_cell: Font cell image for design graphics
    :ivar null_cell: Font cell image for non-design graphics
    :ivar font16_regular: label font for Regular style
    :ivar font_condensed: label font for Condensed style
    :ivar unifont_hex: Unifont Unicode table for character reference
    """
    font_cell: Sheet
    null_cell: Sheet
    font16_regular: BaseImageFont
    font_condensed: BaseImageFont
    unifont_hex: dict[int, bytes]


def main():
    unicode_blocks = load_unicode_blocks()
    project = load_yaml(font.project_yml())
    config: FontYML = load_yaml(font.font_yml())

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "block",
        nargs="?",
        help="Unicode block identifier (default: generate all configured blocks)",
    )

    family_options: list[str] = config["typeface"]["family"]
    parser.add_argument(
        "-f", "--family",
        nargs="+",
        default=family_options,
        choices=family_options,
        help="Family name to generate (default: Generate all available family)",
    )

    # Load all assets we will need for font table generation
    with ((font.ASSETS_DIR / CELL_64).open("rb") as cell_64,
        (font.ASSETS_DIR / NULL_64).open("rb") as null_64,
        (font.ASSETS_DIR / FONT16_REGULAR).open("rb") as font_16px,
        (font.ASSETS_DIR / FONT_CONDENSED).open("rb") as font_16cd,
        (font.ASSETS_DIR / UNIFONT).open("r") as unifont):
        image_assets: ImageAssets = {
            "font_cell": Image.open(cell_64).convert("RGBA"),
            "null_cell": Image.open(null_64).convert("RGBA"),
            "font16_regular": ImageFont.truetype(cast(BinaryIO, font_16px), 16),
            "font_condensed": ImageFont.truetype(cast(BinaryIO, font_16cd), 16),
            "unifont_hex": load_unifont_hex(cast(TextIO, unifont))
        }

    args = parser.parse_args()
    if args.block:
        if args.block not in unicode_blocks:
            raise ValueError(f"Unknown Unicode block '{args.block}'")
        generate(unicode_blocks[args.block],
                 image_assets,
                 families=set(args.family),
                 styles=config["typeface"]["style"])
        return

    for block_id in project["blocks"]:
        if block_id not in unicode_blocks:
            raise ValueError(
                f"'{block_id}' referenced in project.yml "
                f"but not found in unicode-blocks.json")
        generate(unicode_blocks[block_id],
                 image_assets,
                 families=set(args.family),
                 styles=config["typeface"]["style"])


if __name__ == "__main__":
    main()