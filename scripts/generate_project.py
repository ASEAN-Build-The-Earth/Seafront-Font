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
from typing import TypedDict, Any

from sys import stderr
from PIL.Image import Image as Sheet
from PIL.ImageFont import ImageFont

from seafront.core.design.project import check_extra_glyphs
from seafront.core.design.aseprite_scripts import create_project
from seafront.generate import generate_font_table, generate_empty_graphics, make_null_cell, make_font_cell
from seafront.model.font import FontYML
from seafront.model.glyphs import parse_extra_glyphs, get_extra_glyph_label, ExtraGlyphsList, EXT_PREFIX
from seafront.model.pilfont import Seafront16pxUI
from seafront.model.unifont import load_unifont_hex
from seafront.unicode import load_unicode_blocks, UnicodeBlock, is_non_printable
import seafront.font as font
import yaml
import argparse

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
             styles: list[str] | dict[str, Any],
             verbose: bool):
    font_cell: Sheet = assets["font_cell"]
    null_cell: Sheet = assets["null_cell"]
    unifont_hex: dict[int, bytes] = assets["unifont_hex"]
    seafront_ui: Seafront16pxUI[ImageFont] = assets["seafront_ui"]

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

    sheet = generate_font_table(fn, seafront_ui, count, unifont_hex)

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
        print(f"{exist} \33[33m'{image_file.relative_to(project_dir.parents[1])}'\33[0m")

    create_project(project, False, verbose)

    extension: Traversable = font.ext_glyphs_yml(block["name"])
    if extension.is_file():
        glyphs_yml = parse_extra_glyphs(load_yaml(extension))
        columns = glyphs_yml["column"]
        glyphs = glyphs_yml["glyphs"]

        def fn(i: int) -> tuple[str, Sheet, int | None]:
            cell = null_cell if glyphs[i].is_undefined() else font_cell
            return get_extra_glyph_label(i).upper(), cell, glyphs[i].cmap

        if verbose:
            print(f"{len(glyphs)} glyphs Extension feature found "
                  f"for '{block["name"]}' unicode range")

        sheet = generate_font_table(fn, seafront_ui, len(glyphs), unifont_hex, columns)
        table = font.project_ext_font_table(block["name"])
        exist = "Overwritten" if table.is_file() else "Generated"
        with as_file(table) as image_file:
            sheet.save(image_file)
            print(f"{exist} Extension \33[33m'{image_file.relative_to(project_dir.parents[1])}'\33[0m")

        create_project(project, True, verbose)


class ImageAssets(TypedDict):
    """
    Assets used in font table generation

    :ivar font_cell: Font cell image for design graphics
    :ivar null_cell: Font cell image for non-design graphics
    :ivar unifont_hex: Unifont Unicode table for character reference
    :ivar seafront_ui: Seafront labeling UI font
    """
    font_cell: Sheet
    null_cell: Sheet
    unifont_hex: dict[int, bytes]
    seafront_ui: Seafront16pxUI[ImageFont]


def main():
    unicode_blocks = load_unicode_blocks()
    project = load_yaml(font.project_yml())
    config: FontYML = load_yaml(font.font_yml())

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "block",
        nargs="*",
        help="Unicode block identifier (default: generate all configured blocks)",
    )
    parser.add_argument('-v', "--verbose",
        action="store_true",
        help="log verbose outputs"
    )

    parser.add_argument('-u', "--unifont",
        nargs="+",
        default=[UNIFONT],
        help=f"GNU Unifont .hex sample file, must be placed "
             f"under /assets directory. (Default to '{UNIFONT}')"
    )

    family_options: list[str] = config["typeface"]["family"]
    parser.add_argument(
        "-f", "--family",
        nargs="+",
        default=[family_options[0]],
        choices=family_options,
        help="Family name to generate (default: Only generate 'Seafront' Family)"
    )

    args = parser.parse_args()

    unifont: dict[int, bytes] = {}
    if isinstance(args.unifont, list) and len(args.unifont) > 0:
        for file in args.unifont:
            try: # Safely find unifont.hex file and load it
                with (font.ASSETS_DIR / file).open("r") as io:
                    load_unifont_hex(io, unifont)
                    break
            except FileNotFoundError, IsADirectoryError:
                print(f"\033[93mWARNING: '{file}' Unifont sample file not found!\n"
                      f"WARNING: Make sure the file is placed inside 'assets' directory.\033[0m", file=stderr)
    elif len(unifont) <= 0:
        print(f"\033[93mWARNING: '{UNIFONT}' Unifont sample file not found!\n"
              f"WARNING: if the file name has changed, "
              f"please provide them with --unifont argument.\033[0m", file=stderr)

    # Load all assets we will need for font table generation
    image_assets: ImageAssets = {
        "font_cell": make_font_cell(),
        "null_cell": make_null_cell(),
        "unifont_hex": unifont,
        "seafront_ui": Seafront16pxUI.load_image_font(),
    }

    if isinstance(args.block, list) and len(args.block) > 0:
        for i, block_name in enumerate(args.block):
            if block_name not in unicode_blocks:
                raise ValueError(f"Unknown Unicode block '{block_name}'")
            print(f"\033[32m================= \033[1m"
                  f"Generating {i + 1}/{len(args.block)} '{block_name}'\033[0m")
            generate(unicode_blocks[block_name],
                     image_assets,
                     families=set(args.family),
                     styles=config["typeface"]["style"],
                     verbose=args.verbose)
        return

    for i, block_name in enumerate(project["blocks"]):
        if block_name not in unicode_blocks:
            raise ValueError(
                f"'{block_name}' referenced in project.yml "
                f"but not found in unicode-blocks.json")
        print(f"\033[32m================= \033[1m"
              f"Generating {i + 1}/{len(project["blocks"])} '{block_name}'\033[0m")
        generate(unicode_blocks[block_name],
                 image_assets,
                 families=set(args.family),
                 styles=config["typeface"]["style"],
                 verbose=args.verbose)


if __name__ == "__main__":
    main()