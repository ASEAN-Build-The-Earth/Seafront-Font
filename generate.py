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
FONT_32: Path = ASSETS / "BTE-Seafront-Basic-Regular.ttf"

def load_project():
    with open(PROJECT, encoding="utf-8") as fp:
        return yaml.safe_load(fp)


def generate(block_id, block):
    start = block["start"]
    end = block["end"]

    count = end - start + 1
    rows = (count + COLUMN_SIZE - 1) // COLUMN_SIZE

    font_cell = Image.open(
        ASSETS / "font-cell-64px.png"
    ).convert("RGBA")

    null_cell = Image.open(
        ASSETS / "null-cell-64px.png"
    ).convert("RGBA")

    label_font = ImageFont.truetype(FONT_32, 16)

    output: Path = ROOT / "src" / block_id
    output.mkdir(exist_ok=True)

    sheet = Image.new(
        "RGBA",
        (
            COLUMN_SIZE * CELL_SIZE,
            rows * CELL_SIZE,
        ),
        (255, 255, 255, 0),
    )

    graphics = output / "regular.png"

    if not graphics.exists():
        sheet.save(graphics)
        print(f"Written Empty {graphics}")

    draw = ImageDraw.Draw(sheet)

    for i in range(count):

        codepoint = start + i

        row = i // COLUMN_SIZE
        col = i % COLUMN_SIZE

        x = col * CELL_SIZE
        y = row * CELL_SIZE

        if codepoint < 0x20 or 0x7F <= codepoint <= 0x9F:
            cell = null_cell
        else:
            cell = font_cell

        sheet.alpha_composite(cell, (x, y))

        draw.text(
            (x + 4, y),
            f"U+{codepoint:04X}",
            font=label_font,
            fill=(70, 70, 70),
        )

    table = output / "font-table.png"
    exist = "Overwritten" if table.exists() else "Generated"
    sheet.save(table)
    print(f"{exist} {table}")

    try:
        subprocess.run([
            "aseprite",
            "--batch",
            "--script-param", f"dir={output}",
            "--script", SCRIPT,
        ], check=True)
    except subprocess.CalledProcessError:
        print(f"Error generating Aseprite project file.")
        pass  # handle errors in the called executable
    except OSError:
        print(f"Aseprite not found in system. Cannot generate project file.")
        pass  # executable not found

def main():
    unicode_blocks = load_unicode_blocks()
    project = load_project()

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

