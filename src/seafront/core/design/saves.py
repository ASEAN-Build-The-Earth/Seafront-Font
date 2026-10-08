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
from typing import Literal, overload

import yaml
import seafront.font as font
from seafront.core.design.aseprite_scripts import save_graphics, export_graphics, create_project
from seafront.core.design.project import find_design_layers, save_glyphs, UnicodeProject, check_extra_glyphs

from seafront.model.font import FontYML
from seafront.unicode import UnicodeBlock

@overload
def aseprite(projects: list[UnicodeBlock], *,
             pbm: Literal[True], png: bool=False,
             verbose: bool=False) -> None: ...

@overload
def aseprite(projects: list[UnicodeBlock], *,
             png: Literal[True], pbm: bool=False,
             verbose: bool=False) -> None: ...


def aseprite(projects: list[UnicodeBlock], *,
             pbm: bool=True, png: bool=False,
             verbose: bool=False) -> None:
    """
    Save as designs using .aseprite design files in each project.

    :param projects: List of Unicode blocks to save
    :param pbm: Saves as bitmaps (:code:`.pbm` Default)
    :param png: Saves as PNG Images
    :param verbose: Verbose logging
    :return: Written to filesystem
    """
    if not (pbm or png):
        print("No saves argument (pbm/png) specified, nothing to do.")
        return

    for unicode_project in projects:
        block: str = unicode_project["name"]
        start: int = unicode_project["start"]

        project = font.project_root(block)
        with as_file(project) as project_dir:
            project_dir.mkdir(exist_ok=True)

        design_aseprite = font.project_aseprite(block)
        if design_aseprite.is_file():
            if png:
                print(f"\033[32m================= \033[1m"
                      f"(1/2) Saving '{block}' ({design_aseprite.name})\033[0m")
                save_graphics(design_aseprite, verbose)
            if pbm:
                print(f"\033[32m================= \033[1m"
                      f"(2/2) Exporting '{block}' ({design_aseprite.name})\033[0m")
                export_graphics(design_aseprite, start, verbose)

        ext_design_aseprite = font.project_ext_aseprite(block)
        if ext_design_aseprite.is_file():
            if png:
                print(f"\033[32m================= \033[1m"
                      f"(1/2) Saving '{block}' ({ext_design_aseprite.name})\033[0m")
                save_graphics(ext_design_aseprite, verbose)

            if pbm:
                print(f"\033[32m================= \033[1m"
                      f"(2/2) Exporting '{block}' ({ext_design_aseprite.name})\033[0m")
                export_graphics(ext_design_aseprite, start, verbose)


@overload
def png_image(projects: list[UnicodeBlock],
              family_name: set[str], *,
              ase: Literal[True], pbm: bool=False,
              verbose: bool=False) -> None: ...

@overload
def png_image(projects: list[UnicodeBlock],
              family_name: set[str], *,
              pbm: Literal[True], ase: bool = False,
              verbose: bool = False) -> None: ...


def png_image(projects: list[UnicodeBlock],
              family_name: set[str], *,
              pbm: bool=True, ase: bool=False,
              verbose: bool=False) -> None:
    """
    Save as designs using .png design sheets in each project.

    :param projects: List of Unicode blocks to save
    :param family_name: Set of family name selected to save
    :param pbm: Saves as bitmaps (:code:`.pbm` Default)
    :param ase: Saves as :code:`.aseprite` design (Required Aseprite app)
    :param verbose: Verbose logging
    :return: Written to filesystem
    """
    if not (pbm or ase):
        print("No saves argument (pbm/ase) specified, nothing to do.")
        return

    with font.font_yml().open(encoding="utf-8") as io:
        config: FontYML = yaml.safe_load(io)

    layers: list[UnicodeProject] = find_design_layers(projects, family_name) if pbm else []

    # For all Unicode project we want to save
    for i, design_layer in enumerate(layers):
        print(f"\033[32m================= \033[1m"
              f"({i + 1}/{len(layers)}) Saving {design_layer["family_name"]} "
              f"'{design_layer["block_name"]}'\033[0m")
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

    if not ase:
        return

    for i, unicode_project in enumerate(projects):
        block: str = unicode_project["name"]
        extra: bool = check_extra_glyphs(block) is not None

        print(f"\033[94m================= \033[1m"
              f"({i + 1}/{len(projects)}) Syncing '{block}' \033[0m")
        create_project(font.project_root(block), False, verbose)

        if extra:
            create_project(font.project_root(block), True, verbose)