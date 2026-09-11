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
from importlib.resources import as_file
from importlib.resources.abc import Traversable

from PIL import Image
from PIL import ImageDraw
from seafront.font import (
    SCRIPTS_DIR,
    FONT_DIR
)
import subprocess

SCRIPT: str = "aseprite/create-project.lua"
"""aseprite project generation script"""

CELL_SIZE: int = 64
"""Seafront design cell is limited to 64*64 pixel by typography design"""


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


def generate_aseprite_project(project_dir: Traversable,
                              is_extension: bool):
    try:
        # Virtual path Traversable should be convert back to
        # pathlib to be sure aseprite file won't mistake it
        with (as_file(project_dir) as project,
              as_file(SCRIPTS_DIR / SCRIPT) as scripts,
              as_file(FONT_DIR) as font):
            subprocess.run([
                "aseprite",
                "--batch",
                "--script-param", f"dir={project}",
                "--script-param", f"config={font}",
                "--script-param", f"ext={is_extension}",
                "--script", scripts,
            ], check=True)
    except subprocess.CalledProcessError:
        print(f"Internal error generating .aseprite project file.")
        pass  # handle errors in the called executable
    except OSError:
        print(f"Aseprite not found in system. Cannot generate .aseprite project file.")
        pass  # executable not found
