#!/usr/bin/env python3
r""" export_seafront.py

Commandline script to export Seafront fonts.

Usage
-----
using hatch::

    hatch run export-seafront

using python::

    python export_seafront.py
"""
COPYRIGHT = """\
Copyright (c) 2026, BuildTheEarth (buildtheearth.net), \
Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).\
"""
LICENSE = """\
Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
with Reserved Font Name "BTE Seafront".
Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).

This Font Software is licensed under the SIL Open Font License, Version 1.1.
This license is available with a FAQ at:
https://openfontlicense.org
"""

from pathlib import Path
from PIL import Image
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from importlib.resources import as_file
from importlib.resources.abc import Traversable
from seafront.core.extract import extract, chain, simplify, Edge
from seafront.unicode import load_unicode_blocks
from seafront.model.anchors import parse_glyph_anchors
from seafront.afdko.anchors import export_anchor_features
from seafront.afdko.kerning import export_kerning_feat

import seafront.font as font
import argparse
import yaml
import sys

VERBOSE = False
CELL_SIZE: int = 64


def load_yaml(file: Traversable):
    with file.open(encoding="utf-8") as fp:
        return yaml.safe_load(fp)


def log(verbose=False, *args):
    if verbose:
        print(*args)


def draw_glyphs(verbose: bool, pen: TTGlyphPen, paths: list[list[Edge]]):
    """
    Use glyph to draw all given paths

    :param verbose: Whether to log the path drawing or not
    :param pen: Glyph pen to draw
    :param paths: Path list to render
    """

    def draw_glyph(path: list[Edge]):
        log(verbose, f"Starting {path[0][0]}")
        pen.moveTo(path[0][0])

        for edge in path:
            log(verbose, f"Drawing {edge[1]}")
            pen.lineTo(edge[1])

        pen.closePath()

    for edge_list in paths:
        simplified = simplify(edge_list)  # simplify edge list to a single path
        draw_glyph(simplified)


# ------------------------------
# Build glyphs
# ------------------------------

def prepare_glyphs(default_width: int) -> dict:
    """
    Prepare a glyph table

    :param default_width: The default advance width set for .notdef character
    :return: a dict{glyphs,glyph_order,metrics,cmap}
    """
    glyph_order = [".notdef"]
    glyphs = {}
    metrics = {}
    cmap = {}

    # mandatory .notdef
    pen = TTGlyphPen(None)
    glyphs[".notdef"] = pen.glyph()
    metrics[".notdef"] = (default_width, 0)

    return {
        "glyphs": glyphs,
        "glyph_order": glyph_order,
        "metrics": metrics,
        "cmap": cmap
    }


def build_glyph(pbm: Path,
                glyph: dict,
                profile,
                accent) -> int:
    """

    :param pbm: Path to the glyph's bitmap to build
    :param glyph:
    :param profile:
    :param accent:
    :return: 1 if the glyph is successfully built in to dictionary, else 0
    """
    v: bool = profile["verbose"]
    codepoint: int = profile["codepoint"]
    pixel_size: int = profile["pixel_size"]
    white_space: int = profile["typography"]["white-space"]  # The white-space width
    right_padding: int = profile["typography"]["right-padding"]  # The padding between every character

    # PBM Cell: The dimension of glyph pbm file
    # TODO: currently is coded to reflect each font's designed accent
    # TODO: might consider making this more dynamic
    pbm_cell: int = accent["ascender"] + accent["descender"]

    origin_x: int = pbm_cell - profile["typography"]["maximum-width"]
    origin_y: int = accent["ascender"]

    image = Image.open(pbm)
    w, h = image.size

    if w != pbm_cell or h != pbm_cell:
        raise ValueError(
            f"Glyphs .pbm has mismatch accent dimension. "
            f"Expected {pbm_cell}*{pbm_cell}, Got {w}*{h} at:\n'{pbm}'"
        )

    # Glyph's identity
    # Standard uni0000 (:04X) Unicode glyph naming
    glyph_name: str = f"uni{codepoint:04X}"

    # Special case for space character (U+0020)
    if codepoint == 32:
        glyph_name = f"uni{codepoint:04X}"

        log(v, f"Writing whitespace U+{codepoint:04X} as {white_space}px")
        pen = TTGlyphPen(None)

        glyph["glyphs"][glyph_name] = pen.glyph()  # Empty glyph
        glyph["metrics"][glyph_name] = (white_space * pixel_size, 0)
        glyph["glyph_order"].append(glyph_name)
        glyph["cmap"][codepoint] = glyph_name
        return 1

        # Glyph's positional profile
    y_anchor: int = 0
    x_anchor: int = 0
    anchor: dict | None = None
    anchor_type: str | None = None
    options = dict(base="base", above="mark", below="mark")

    if isinstance(profile["anchors"], dict):
        anchors = profile["anchors"]

        # If this glyph has anchor configuration
        if glyph_name in anchors:
            positioning = anchors[glyph_name]
            anchor = positioning["anchor"]
            glyph_class = positioning["anchor"]["type"]
            anchor_type = options[glyph_class]

            if anchor_type == "mark":
                y_anchor += profile["typography"]["anchors"]["mark"][glyph_class]

            x_anchor += int(positioning["pos"]["x"])
            y_anchor += int(positioning["pos"]["y"])

    pixels = image.load()
    fn = lambda x, y: pixels[x, y] if pixels is not None else 1
    boundary = extract(fn, w, h, origin_x, origin_y + y_anchor, pixel_size)

    if boundary is None:
        print(f"{'\033[93m'}Glyph for U+{codepoint:04X} is empty{'\033[0m'}", file=sys.stderr)
        return 0

    edges, bounds = boundary
    min_x, min_y, max_x, max_y = bounds
    glyph_width = max_x - min_x + 1
    glyph_height = max_y - min_y + 1

    # lsb & advance
    # This 2 metrics determined how glyph is displayed relative to its "advance" width
    # The "lsb" is the starting point of the glyph's minimum point

    start_padding = origin_x - min_x + x_anchor
    advance_width = max_x - origin_x + 1

    # Only monospace will need special care to ensure every glyph has same width
    if profile["typeface"] == "monospace":
        # The left-over space if some character is smaller than monospace width
        # We assume the padding is equal left and right for it to be place on the center
        advance_width = profile["typography"]["monospace-width"]
        start_padding = (advance_width - glyph_width) / 2

        if v:  # Verbose logging in case a glyph is not centered by default
            position = (origin_x + advance_width) - (max_x + 1)
            if position != start_padding:
                log(v, f"{'\033[93m'}Monospace glyph "
                       f"for U+{codepoint:04X} is not centered: "
                       f"\nPadding is expected to span the width equally"
                       f"\n\tExpected: {start_padding} + {start_padding}"
                       f"\n\tGot: {position} + {(advance_width - position - glyph_width)}{'\033[0m'}")

    lsb: int = int(start_padding * pixel_size)
    advance: int = (advance_width + right_padding) * pixel_size
    log(v, f"U+{codepoint:04X}"
           f" bounds=({min_x},{min_y})-({max_x},{max_y}),"
           f" size={glyph_width}x{glyph_height},"
           f" lsb={lsb},"
           f" adv={advance}")

    pen = TTGlyphPen(None)
    paths = chain(edges)
    draw_glyphs(v, pen, paths)

    glyph["glyphs"][glyph_name] = pen.glyph()

    if not anchor_type == "mark":
        glyph["metrics"][glyph_name] = (advance, lsb)
    else:
        # Mark classes required to be zero width as
        # it would position vertically from left side character
        glyph["metrics"][glyph_name] = (0, lsb - advance)

    if anchor is not None:
        if not anchor_type == "mark":
            # Default anchor will be positioned right-most of the glyph
            anchor["base"]["below"]["x"] += advance_width
            anchor["base"]["above"]["x"] += advance_width

            # With 2 anchor: below at y=0, and above at x-height
            anchor["base"]["above"]["y"] += profile["typography"]["x-height"]
        else:
            # Above-marks need to shift the anchor up to its y position
            if anchor["type"] == "above":
                anchor["mark"]["base"]["y"] += (max_y - 1) + profile["typography"]["anchors"]["mark"][anchor["type"]]
                anchor["mark"]["mkmk"]["y"] += (max_y - 1) + profile["typography"]["anchors"]["mark"][anchor["type"]]

            anchor["mark"]["mkmk"]["y"] += profile["typography"]["anchors"]["mkmk"][anchor["type"]]

            # This one follow the metrics' x position
            # anchor["mark"]["base"]["x"] -= (origin_x + min_x - 1 - x_anchor)
            anchor["mark"]["base"]["x"] -= (origin_x + min_x - 1)
            anchor["mark"]["mkmk"]["x"] -= (origin_x + min_x - 1)

    glyph["glyph_order"].append(glyph_name)
    glyph["cmap"][codepoint] = glyph_name
    return 1


def export(typeface, profile, output):
    v: bool = profile["verbose"]
    pixel_size: int = profile["scale"]
    ascender: int = profile["accent"]["ascender"]  # 35 pixel
    descender: int = profile["accent"]["descender"]  # 15 pixel
    units_per_em: int = (ascender + descender) * pixel_size  # 2500

    # Guard UPM, need to fall within ± 4095 for "safety"
    if units_per_em > 4096:
        print(f"{'\033[31m'}Font unit incompatible- scale too large.\n"
              f"Please either lower your scale or step down the accent{'\033[0m'}", file=sys.stderr)
        return

    print(f"Default width: {units_per_em // 2}")
    print(f"MAX width: {profile["typography"]["maximum-width"] * pixel_size}")

    family_name = typeface["info"]["family"]
    project = load_yaml(font.project_yml())
    blocks = load_unicode_blocks()
    glyph = prepare_glyphs(units_per_em // 2)  # Defaulting half an em per glyph for .notdef
    built = 0

    anchors_feature: dict = {}
    kerning_feature: dict = {}

    try:
        for block_id in project["blocks"]:
            face = typeface["face"]

            with as_file(font.project_glyphs(block_id, family_name, face)) as glyph_dir:
                if not glyph_dir.exists():
                    raise ValueError(
                        f"Glyphs for '{block_id}' with style '{face}' referenced in project.yml "
                        f"does not exist for exporting at: \n'{glyph_dir}'"
                    )

            anchors_yml: Traversable = font.anchors_yml(block_id)
            kerning_yml: Traversable = font.kerning_yml(block_id)

            def load_anchors():
                glyph_anchors = parse_glyph_anchors(load_yaml(anchors_yml))
                anchors_feature[block_id] = glyph_anchors
                return glyph_anchors

            # Anchors positioning required to adjust each glyph if configured
            anchors = load_anchors() if anchors_yml.is_file() else None

            for pbm in sorted(glyph_dir.glob("glyph_*.pbm")):
                index = int(pbm.stem.split("_")[1])
                codepoint = int(blocks[block_id]["start"]) + (index - 1)
                glyph_profile: dict = {
                    "codepoint": codepoint,
                    "pixel_size": pixel_size,
                    "anchors": anchors,
                    "verbose": v,
                    "typeface": face,
                    "typography": profile["typography"]
                }
                log(v, f"Building Glyph index: {index} (U+{codepoint:04X})")
                built += build_glyph(pbm, glyph, glyph_profile, profile["accent"])

            # Post build: kerning feature is processed purely under OpenType feature
            if kerning_yml.is_file():
                kerning_feature[block_id] = kerning_yml
    except Exception as e:
        print(f"{'\033[93m'}{e}{'\033[0m'}", file=sys.stderr)
    if built == 0:
        raise ValueError("No available glyphs found for this typeface.")

    # ------------------------------
    # Font metadata
    # ------------------------------

    ascent: int = ascender * pixel_size
    descend: int = descender * pixel_size
    x_height: int = profile["typography"]["x-height"] * pixel_size
    cap_height: int = profile["typography"]["cap-height"] * pixel_size
    italic_angle: int = profile["typography"]["italic-angle"]
    underline_position: int = -pixel_size * 2 # Place 2 pixel below
    underline_thickness: int = pixel_size * 2 # With size of 2 pixel

    log(v, f"Typography"
       f" ascent={ascent},"
       f" descent={descend},"
       f" unitsPerEm={units_per_em}")
    fb = FontBuilder(unitsPerEm=units_per_em, isTTF=True)

    fb.setupGlyphOrder(glyph["glyph_order"])
    fb.setupCharacterMap(glyph["cmap"])
    fb.setupGlyf(glyph["glyphs"])
    fb.setupHorizontalMetrics(glyph["metrics"]) # The default advancing width
    fb.setupHorizontalHeader(ascent=ascent, descent=-descend)

    fb.setupOS2(
        sTypoAscender=ascent,
        sTypoDescender=-descend,
        usWinAscent=ascent,
        usWinDescent=descend,
        sxHeight=x_height,
        sCapHeight=cap_height,
        fsType=0, # 0: Installable embedding, 2: Restricted License embedding, 4: Preview & Print embedding, 8: Editable embedding
        fsSelection=0x40, # "bold italic": 0x21, "bold": 0x20, "italic": 0x01, "regular": 0x40
        usWeightClass=500, # Medium weight, as our font is kind of thick by design
        usWidthClass=5 # Normal width, we won't have condensed or expanded width
    )

    info: dict[str, str] = typeface["info"]
    license_desc: list[str] = LICENSE.splitlines()
    license_info: str = license_desc[len(license_desc) - 1]
    strings_list: list[str] = [info["foundry-name"], family_name]
    family_name = ' '.join(strings_list) # BTE Seafront

    strings_list.append(typeface["style"])
    full_name: str = ' '.join(strings_list) # BTE Seafront Regular

    postscript: str = full_name.replace(' ', '-')

    strings_list.append(info["version"])
    unique_string: str = ' '.join(strings_list) # BTE Seafront Regular Version 1.000

    name_strings: dict[str, str] = {
        # (nameID 0)
        "copyright": COPYRIGHT,
        "familyName": family_name, # (nameID 1)
        "styleName": typeface["style"], # (nameID 2)
        "uniqueFontIdentifier": unique_string, # (nameID 3)
        "fullName": full_name, # (nameID 4)
        "version": info["version"], # (nameID 5)
        "psName": postscript, # (nameID 6)
        # "trademark": "", # (nameID 7)
        "manufacturer": info["manufacturer"], # (nameID 8)
        "designer": info["designer"], # (nameID 9)
        "description": info["description"], # (nameID 10)
        "vendorURL": info["vendor-url"], # (nameID 11)
        "designerURL": info["designer-url"], # (nameID 12)
        "licenseDescription": LICENSE, # (nameID 13)
        "licenseInfoURL": license_info, # (nameID 14)
        # (nameID 15 reserved)
        "typographicFamily": info["family"], # (nameID 16)
        "typographicSubfamily": typeface["style"], # (nameID 17)
        "compatibleFullName": full_name, # (nameID 18)
        "sampleText": info["sample-text"], # (nameID 19)
    }

    # Prepare .fea feature file as raw text lines
    fea_full: list[str] = []

    # Collect anchoring features
    for block_id, anchors in anchors_feature.items():
        log(v, f"Exporting anchoring feature for: {block_id}")
        anchor_txt = export_anchor_features(
            anchors,
            upm=units_per_em,
            pixel_size=pixel_size,
        )
        log(v, anchor_txt)
        fea_full.append(anchor_txt)

    # Collect kerning features
    for block_id, path in kerning_feature.items():
        log(v, f"Exporting kerning feature for: {block_id}")
        kerning = load_yaml(path)
        fea_txt = export_kerning_feat(
            kerning["groups"],
            kerning["kerning"],
            upm=units_per_em,
            pixel_size=pixel_size,
        )
        log(v, fea_txt)
        fea_full.append("feature kern {")
        fea_full.append(fea_txt)
        fea_full.append("} kern;")

    final_features_string = '\n'.join(fea_full)

    fb.addOpenTypeFeatures(final_features_string)

    fb.setupNameTable(name_strings)

    fb.setupPost(
        formatType=3.0,
        italicAngle=italic_angle,
        underlinePosition=underline_position,
        underlineThickness=underline_thickness,
        isFixedPitch=0,
        minMemType42=0,
        maxMemType42=0,
        minMemType1=0,
        maxMemType1=0,
    )
    log(v, "Written Metadata: ", name_strings)
    filename = f"{postscript}.ttf" if output is None else \
        (output if str(output).endswith(".ttf") else f"{output}.ttf")
    fb.save(filename)
    print(f"Wrote {filename}")


def main():
    config = load_yaml(font.font_yml())

    parser = argparse.ArgumentParser(description='Export a TrueType font from this project')

    accent_options = [*config["profile"]["accent"]]
    typeface_options = [*config["typeface"]["style"]]
    family_options = config["typeface"]["family"]

    parser.add_argument('-v', "--verbose",
        default=False,
        type=bool,
        help="log verbose outputs",
    )
    parser.add_argument('-i', "--identifier",
        nargs="?",
        type=str,
        help="The font's version number to export ex. 1.000",
    )

    parser.add_argument('-s', "--scale",
        default=accent_options[0],
        choices=accent_options,
        help="The scale preset that affect the font's internal positioning.\n"
             f"Default to '{accent_options[0]}'",
    )

    parser.add_argument('-a', "--accent",
        default=accent_options[0],
        choices=accent_options,
        help="The accent preset of this font which define the ascent\n"
             f"and descend line of this font, Default to '{accent_options[0]}'",
    )

    parser.add_argument(
        "-t", "--typeface",
        default=typeface_options[0],
        choices=typeface_options,
        help="Typeface to export configured in config/font.yml.\n"
             f"Default to '{typeface_options[0]}'",
    )

    parser.add_argument(
        "-c", "--family",
        default=family_options[0],
        choices=family_options,
        help="The family name to export",
    )

    parser.add_argument(
        "output",
        nargs="?",
        help="Output file name *.ttf, default to the psName of exporting typeface.",
    )

    args = parser.parse_args()

    def get_argument(argument, key, profile=config["profile"]):
        if argument not in profile[key]:
            raise ValueError(f"Expected key for '{argument}' in '{key}' not found in config/font.yml")
        return argument

    def assert_profile(key, profile=config["profile"]):
        if key not in profile:
            raise ValueError(f"'{key}' export profile not found in config/font.yml")

    face = get_argument(args.typeface, "style", config["typeface"])
    scale = get_argument(args.scale, "scale")
    accent = get_argument(args.accent, "accent")

    assert_profile("info", config["typeface"])
    assert_profile("style", config["typeface"])
    assert_profile("regular", config["typeface"]["style"])
    assert_profile("typography")
    assert_profile("scale")
    assert_profile("accent")

    if args.family:
        config["typeface"]["info"]["family"] = args.family

    if args.identifier:
        config["typeface"]["info"]["version"] = f"Version {args.identifier}"

    typeface: dict = {
        "face": face,
        "style": config["typeface"]["style"][face],
        "info": config["typeface"]["info"]
    }
    profiles: dict = {
        "typography": config["profile"]["typography"],
        "scale": config["profile"]["scale"][scale],
        "accent": config["profile"]["accent"][accent],
        "verbose": args.verbose
    }

    log(args.verbose, "Export Profile: ", typeface, profiles)
    export(typeface, profiles, args.output)


if __name__ == "__main__":
    main()