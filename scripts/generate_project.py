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
from seafront.generate import generate_font_table, generate_aseprite_project
from seafront.unicode import load_unicode_blocks
from seafront.font import (
    project_yml,
    project_root,
    ext_glyphs_yml,
    ASSETS_DIR
)
import yaml
import argparse

COLUMN_SIZE: int = 16
"""We will format all font tables by 16 columns and x rows"""

FONT_16: str = "BTE-Seafront-Square-Regular.ttf"
CELL_64: str = "font-cell-64px.png"
NULL_64: str = "null-cell-64px.png"


def load_yaml(file: Traversable):
    with file.open(encoding="utf-8") as fp:
        return yaml.safe_load(fp)


def generate(block_name, block):
    with as_file(ASSETS_DIR) as assets:
        font_cell = Image.open(assets / CELL_64).convert("RGBA")
        null_cell = Image.open(assets / NULL_64).convert("RGBA")
        label_font = ImageFont.truetype(assets / FONT_16, 16)

    with as_file(project_root(block_name)) as output:
        output.mkdir(exist_ok=True)

    start = block["start"]
    end = block["end"]
    count = end - start + 1
    fn = lambda i: (
        f"U+{(start + i):04X}",
        null_cell if ((start + i) < 0x20 or 0x7F <= (start + i) <= 0x9F) else font_cell
    )
    sheet = generate_font_table(fn, count, COLUMN_SIZE, label_font)

    # TODO: Adapt to new graphics directory
    # graphics = output / "regular.png"
    #
    # if not graphics.exists():
    #     sheet.save(graphics)
    #     print(f"Written Empty {graphics}")

    table = output / "font-table.png"
    exist = "Overwritten" if table.exists() else "Generated"
    sheet.save(table)
    print(f"{exist} {table}")

    generate_aseprite_project(output, False)

    extension: Traversable = ext_glyphs_yml(block_name)
    if extension.is_file():
        glyphs_yml = load_yaml(extension)
        columns = glyphs_yml["column"]
        glyphs = glyphs_yml["glyphs"]
        fn = lambda i: (
            f"ext-{i:02X}",
            font_cell if glyphs[f"ext-{i:02X}"]["name"] else null_cell
        )
        print(f"{len(glyphs)} glyphs Extension feature found for '{block_name}' unicode range")

        sheet = generate_font_table(fn, len(glyphs), columns, label_font)
        table = output / "ext-font-table.png"
        exist = "Overwritten" if table.exists() else "Generated"
        sheet.save(table)
        print(f"{exist} Extension {table}")

        generate_aseprite_project(output, True)


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