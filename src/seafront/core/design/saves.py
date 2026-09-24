# Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
# with Reserved Font Name "BTE Seafront".
# Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).
#
# This Font Software is licensed under the SIL Open Font License, Version 1.1.
# This license is available with a FAQ at:
# https://openfontlicense.org
"""\
Project saving strategy for aseprite/png
"""
from importlib.resources import as_file

import yaml
import seafront.font as font
from seafront.core.design.aseprite_scripts import save_graphics, export_graphics
from seafront.core.design.project import find_design_layers, save_glyphs, UnicodeProject

from seafront.model.font import FontYML
from seafront.unicode import UnicodeBlock

def aseprite(projects: list[UnicodeBlock],
             verbose: bool) -> None:

    for unicode_project in projects:
        block: str = unicode_project["name"]
        start: int = unicode_project["start"]

        project = font.project_root(block)
        with as_file(project) as project_dir:
            project_dir.mkdir(exist_ok=True)

        design_aseprite = font.project_aseprite(block)
        if design_aseprite.is_file():
            print(f"\033[32m================= \033[1m"
                  f"(1/2) Saving '{block}' ({design_aseprite.name})\033[0m "
                  f"\033[32m=================\033[0m")
            save_graphics(design_aseprite, verbose)

            print(f"\033[32m================= \033[1m"
                  f"(2/2) Exporting '{block}' ({design_aseprite.name})\033[0m "
                  f"\033[32m=================\033[0m")
            export_graphics(design_aseprite, start, verbose)

        ext_design_aseprite = font.project_ext_aseprite(block)
        if ext_design_aseprite.is_file():
            print(f"\033[32m================= \033[1m"
                  f"(1/2) Saving '{block}' ({ext_design_aseprite.name})\033[0m "
                  f"\033[32m=================\033[0m")
            save_graphics(ext_design_aseprite, verbose)

            print(f"\033[32m================= \033[1m"
                  f"(2/2) Exporting '{block}' ({ext_design_aseprite.name})\033[0m "
                  f"\033[32m=================\033[0m")
            export_graphics(ext_design_aseprite, start, verbose)


def png_image(projects: list[UnicodeBlock],
              family_name: set[str],
              verbose: bool) -> None:
    with font.font_yml().open(encoding="utf-8") as io:
        config: FontYML = yaml.safe_load(io)

    layers: list[UnicodeProject] = find_design_layers(projects, family_name)

    # For all Unicode project we want to save
    for i, design_layer in enumerate(layers):
        print(f"\033[32m================= \033[1m"
              f"({i + 1}/{len(layers)}) Saving '{design_layer["block_name"]}'\033[0m "
              f"\033[32m=================\033[0m")
        result = save_glyphs(design_layer,
                             config["typeface"]["style"],
                             config["profile"],
                             verbose)
        for style in result.keys():
            if (uni := result[style].get("uni", 0)) > 0:
                print(f"\033[36mUnicode glyphs\033[0m: Wrote {uni} files "
                      f"for {design_layer["family_name"]} "
                      f"{config["typeface"]["style"][style]}")

            if (ext := result[style].get("ext", 0)) > 0:
                print(f"\033[36mExtra glyphs\033[0m: Wrote {ext} files "
                      f"for {design_layer["family_name"]} "
                      f"{config["typeface"]["style"][style]}")