# Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
# with Reserved Font Name "BTE Seafront".
# Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).
#
# This Font Software is licensed under the SIL Open Font License, Version 1.1.
# This license is available with a FAQ at:
# https://openfontlicense.org
"""\
Glyphs helper for design projects
"""
from importlib.resources import as_file
from importlib.resources.abc import Traversable
from sys import stderr
from PIL import Image
from typing import TypedDict, Literal, ReadOnly, Any

import yaml
import seafront.font as font
import seafront.model.glyphs as glyphs

from seafront.core.design.graphics import export_graphics
from seafront.model.font import FontProfile
from seafront.model.glyphs import get_glyph_label
from seafront.unicode import UnicodeBlock


class UnicodeProject(TypedDict):
    family_name: ReadOnly[str]
    block_name: ReadOnly[str]
    start: ReadOnly[int]
    end: ReadOnly[int]
    ext: glyphs.ExtraGlyphsList | None


def find_design_layers(projects: list[UnicodeBlock],
                       families: set[str]):
    design_layers: list[UnicodeProject] = []

    for unicode_project in projects:
        block_name: str = unicode_project["name"]
        ext_glyphs: glyphs.ExtraGlyphsList | None = check_extra_glyphs(block_name)

        # Find image in each family
        for family_name in families:
            design: UnicodeProject = {
                "family_name": family_name,
                "block_name": block_name,
                "start": unicode_project["start"],
                "end": unicode_project["end"],
                "ext": ext_glyphs
            }

            design_layers.append(design)

    return design_layers


def save_unicode_glyphs(image: Traversable,
                        glyph_dir: Traversable,
                        profile: FontProfile,
                        codepoint: int) -> int:
    print(f"Saving {image.name}")

    with as_file(glyph_dir) as glyph_path, image.open("rb") as io:
        glyph_path.mkdir(exist_ok=True, parents=True)
        sheet = Image.open(io)
        return export_graphics(get_glyph_label, sheet, glyph_path, profile, codepoint)


def check_extra_glyphs(block_name: str) -> glyphs.ExtraGlyphsList | None:
    extra_dir = font.ext_glyphs_yml(block_name)
    if extra_dir.is_file():
        with extra_dir.open(encoding="utf-8") as io:
            ext_glyphs_io = yaml.safe_load(io)
            return glyphs.parse_extra_glyphs(ext_glyphs_io)
    return None


def save_extra_glyphs(image: Traversable,
                      glyph_dir: Traversable,
                      profile: FontProfile,
                      ext_glyphs: glyphs.ExtraGlyphsList) -> int:
    def name_fn(index: int) -> str:
        glyph: glyphs.ExtraGlyph =  ext_glyphs.get("glyphs")[index]

        if (ext_name := glyph.get_glyph_name()) is None:
            ext_name = glyphs.get_extra_glyph_label(index)
            print(f"{'\033[31m'}WARNING: Extra glyph '{ext_name}' "
                  f"has no configured name.{'\033[0m'}", file=stderr)

        return ext_name

    with as_file(glyph_dir) as glyph_path, image.open("rb") as io:
        glyph_path.mkdir(exist_ok=True, parents=True)
        sheet = Image.open(io)
        return export_graphics(name_fn, sheet, glyph_path, profile)


def save_glyphs(design_layer: UnicodeProject,
                styles: list[str] | dict[str, Any],
                font_profile: FontProfile) -> dict[str, dict[Literal["uni", "ext"], int]]:
    block: str = design_layer["block_name"]
    start: int = design_layer["start"]
    family: str = design_layer["family_name"]

    project = font.project_root(block)
    with as_file(project) as project_dir:
        project_dir.mkdir(exist_ok=True)

    ext_glyphs: glyphs.ExtraGlyphsList | None = design_layer["ext"]
    design = font.project_design(block, family)
    result = {}

    # For each style's image file that exist
    for style in styles:
        image = design / f"{style}.png"
        saved = {}
        if image.is_file():
            glyph_dir = font.project_glyphs(block, family, style)
            saved["uni"] = save_unicode_glyphs(image, glyph_dir, font_profile, start)

        ext_style = f"{glyphs.EXT_PREFIX}{style}"
        ext_image = design / f"{ext_style}.png"
        if (ext_glyphs is not None) and ext_image.is_file():
            glyph_dir = font.project_glyphs(block, family, ext_style)
            saved["ext"] = save_extra_glyphs(ext_image, glyph_dir, font_profile, ext_glyphs)
        result[style] = saved

    return result