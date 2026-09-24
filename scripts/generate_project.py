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
from PIL import Image
from PIL import ImageFont
from PIL.ImageFile import ImageFile

from seafront.generate import generate_font_table
from seafront.core.design.aseprite_scripts import create_project
from seafront.model.glyphs import parse_extra_glyphs, get_extra_glyph_label
from seafront.unicode import load_unicode_blocks
from seafront.font import (
    project_yml,
    project_root,
    project_font_table,
    project_ext_font_table,
    ext_glyphs_yml,
    ASSETS_DIR
)
import yaml
import argparse

FONT_16: str = "BTE-Seafront-Square-Regular.ttf"
CELL_64: str = "font-cell-64px.png"
NULL_64: str = "null-cell-64px.png"


def load_yaml(file: Traversable):
    with file.open(encoding="utf-8") as fp:
        return yaml.safe_load(fp)


def has_graphic(unicode: int) -> bool:
    char: str = chr(unicode)
    return char.isprintable() and not char.isspace()


def generate(block_name, block):
    with as_file(ASSETS_DIR) as assets:
        font_cell = Image.open(assets / CELL_64).convert("RGBA")
        null_cell = Image.open(assets / NULL_64).convert("RGBA")
        label_font = ImageFont.truetype(assets / FONT_16, 16)

    project = project_root(block_name)
    with as_file(project) as project_dir:
        project_dir.mkdir(exist_ok=True)

    start = block["start"]
    end = block["end"]
    count = end - start + 1

    def fn(i: int) -> tuple[str, ImageFile]:
        code: int = start + i
        name: str = f"U+{code:04X}"
        cell = font_cell if has_graphic(code) else null_cell
        return name, cell

    sheet = generate_font_table(fn, label_font, count)

    # TODO: Adapt to new graphics directory
    # graphics = output / "regular.png"
    #
    # if not graphics.exists():
    #     sheet.save(graphics)
    #     print(f"Written Empty {graphics}")

    table = project_font_table(block_name)
    exist = "Overwritten" if table.is_file() else "Generated"
    with as_file(table) as image_file:
        sheet.save(image_file)
        print(f"{exist} '{image_file.relative_to(project_dir.parents[1])}'")

    create_project(project, False)

    extension: Traversable = ext_glyphs_yml(block_name)
    if extension.is_file():
        glyphs_yml = parse_extra_glyphs(load_yaml(extension))
        columns = glyphs_yml["column"]
        glyphs = glyphs_yml["glyphs"]

        def fn(i: int) -> tuple[str, ImageFile]:
            cell = null_cell if glyphs[i].is_undefined() else font_cell
            return get_extra_glyph_label(i), cell

        print(f"{len(glyphs)} glyphs Extension feature found for '{block_name}' unicode range")

        sheet = generate_font_table(fn, label_font, len(glyphs), columns)
        table = project_ext_font_table(block_name)
        exist = "Overwritten" if table.is_file() else "Generated"
        with as_file(table) as image_file:
            sheet.save(image_file)
            print(f"{exist} Extension '{image_file.relative_to(project_dir.parents[1])}'")

        create_project(project, True)


def main():
    unicode_blocks = load_unicode_blocks()
    project = load_yaml(project_yml())

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "block",
        nargs="?",
        help="Unicode block identifier (default: generate all configured blocks)",
    )

    args = parser.parse_args()
    if args.block:
        if args.block not in unicode_blocks:
            raise ValueError(f"Unknown Unicode block '{args.block}'")
        generate(args.block, unicode_blocks[args.block])
        return

    for block_id in project["blocks"]:
        if block_id not in unicode_blocks:
            raise ValueError(
                f"'{block_id}' referenced in project.yml but not found in unicode-blocks.json"
            )
        generate(block_id, unicode_blocks[block_id])


if __name__ == "__main__":
    main()