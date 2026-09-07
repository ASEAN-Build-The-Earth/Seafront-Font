#!/usr/bin/env python3
"""\
Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
with Reserved Font Name "BTE Seafront".
Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).

This Font Software is licensed under the SIL Open Font License, Version 1.1.
This license is available with a FAQ at:
https://openfontlicense.org
"""

from pathlib import Path
import subprocess
import argparse
import yaml

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

from scripts.blocks import load_unicode_blocks

COLUMN_SIZE: int = 16
CELL_SIZE: int = 64

ROOT = Path(__file__).resolve().parent

SCRIPT: str = "scripts/aseprite/create-project.lua"
ASSETS: Path = ROOT / "assets"
CONFIG: Path = ROOT / "config"
PROJECT: Path = CONFIG / "project.yml"
FONT_16: Path = ASSETS / "BTE-Seafront-Square-Regular.ttf"

def load_yaml(file):
    with open(file, encoding="utf-8") as fp:
        return yaml.safe_load(fp)

def generate_font_table(fn,
                        cells_count: int,
                        column_size: int,
                        cells_label):

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
            font=cells_label,
            fill=(70, 70, 70),
        )

    return sheet

def generate_aseprite_project(output: Path,
                              is_extension: bool):
    try:
        subprocess.run([
            "aseprite",
            "--batch",
            "--script-param", f"dir={output}",
            "--script-param", f"config={CONFIG}",
            "--script-param", f"ext={is_extension}",
            "--script", SCRIPT,
        ], check=True)
    except subprocess.CalledProcessError:
        print(f"Error generating Aseprite project file.")
        pass  # handle errors in the called executable
    except OSError:
        print(f"Aseprite not found in system. Cannot generate project file.")
        pass  # executable not found

def generate(block_id, block):
    font_cell = Image.open(ASSETS / "font-cell-64px.png").convert("RGBA")
    null_cell = Image.open(ASSETS / "null-cell-64px.png").convert("RGBA")
    label_font = ImageFont.truetype(FONT_16, 16)

    output: Path = ROOT / "src" / block_id
    output.mkdir(exist_ok=True)

    start = block["start"]
    end = block["end"]

    count = end - start + 1
    has_graphic = lambda char: char.isprintable() and not char.isspace()
    fn = lambda i: (
        f"U+{(start + i):04X}",
        font_cell if has_graphic(chr(start + i)) else null_cell
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

    extension: Path = output / "feature" / "glyphs.yml"
    if extension.exists():
        glyphs_yml = load_yaml(extension)
        columns = glyphs_yml["column"]
        glyphs = glyphs_yml["glyphs"]
        fn = lambda i: (
            f"ext-{i:02X}",
            font_cell if glyphs[f"ext-{i:02X}"]["name"] else null_cell
        )

        print(f"{len(glyphs)} glyphs Extension feature found for {block_id} unicode range")

        sheet = generate_font_table(fn, len(glyphs), columns, label_font)
        table = output / "ext-font-table.png"
        exist = "Overwritten" if table.exists() else "Generated"
        sheet.save(table)
        print(f"{exist} Extension {table}")

        generate_aseprite_project(output, True)

def main():
    unicode_blocks = load_unicode_blocks()
    project = load_yaml(PROJECT)

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

