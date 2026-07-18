#!/usr/bin/env python3
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
from scripts.extract import extract, chain, simplify, Edge
from scripts.blocks import load_unicode_blocks

import argparse
import yaml
import sys

VERBOSE = False
CELL_SIZE: int = 64

ROOT = Path(__file__).resolve().parent
CONFIG: Path = ROOT / "config"
PROJECT: Path = CONFIG / "project.yml"
FONT: Path = CONFIG / "font.yml"

def to_glyphs_dir(block: str, style: str) -> Path:
    return ROOT / "src" / block / "glyphs" / style

def load_yaml(file: Path):
    with open(file, encoding="utf-8") as fp:
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
        simplified = simplify(edge_list) # simplify edge list to a single path
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
                profile) -> int:
    """

    :param pbm: Path to the glyph's bitmap to build
    :param glyph:
    :param profile:
    :return: 1 if the glyph is successfully built in to dictionary, else 0
    """
    v: bool = profile["verbose"]
    codepoint: int = profile["codepoint"]
    pixel_size: int = profile["pixel_size"]
    white_space: int = profile["typography"]["white-space"]  # The white-space width
    origin_x: int = profile["typography"]["origin-x"]
    origin_y: int = CELL_SIZE - profile["typography"]["origin-y"]  # 42: image coordinates
    right_padding: int = profile["typography"]["right-padding"]  # The padding between every character

    # Special case for space character (U+0020)
    if codepoint == 32:
        glyph_name = f"uni{codepoint:04X}"

        log(v, f"Writing whitespace U+{codepoint:04X} as {white_space}px")
        pen = TTGlyphPen(None)

        glyph["glyphs"][glyph_name] = pen.glyph()  # Empty glyph
        glyph["metrics"][glyph_name] = (white_space  * pixel_size, 0)
        glyph["glyph_order"].append(glyph_name)
        glyph["cmap"][codepoint] = glyph_name
        return 1

    image = Image.open(pbm)
    w, h = image.size
    pixels = image.load()
    fn = lambda x, y: pixels[x, y] if pixels is not None else 1
    boundary = extract(fn, w, h, origin_x, origin_y, pixel_size)

    if boundary is None:
        print(f"{'\033[93m'}Glyph for U+{codepoint:04X} is empty{'\033[0m'}", file=sys.stderr)
        return 0

    edges, bounds = boundary
    min_x, min_y, max_x, max_y = bounds
    glyph_width = max_x - min_x + 1
    glyph_height = max_y - min_y + 1

    # The starting points
    lsb = (origin_x - min_x) * pixel_size
    advance = (max_x - origin_x + 1 + right_padding) * pixel_size
    log(v, f"U+{codepoint:04X}"
        f" bounds=({min_x},{min_y})-({max_x},{max_y}),"
        f" size={glyph_width}x{glyph_height},"
        f" lsb={lsb},"
        f" adv={advance}")

    pen = TTGlyphPen(None)
    paths = chain(edges)
    draw_glyphs(v, pen, paths)

    glyph_name = f"uni{codepoint:04X}"

    glyph["glyph_order"].append(glyph_name)
    glyph["glyphs"][glyph_name] = pen.glyph()
    glyph["metrics"][glyph_name] = (advance, lsb)
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

    project = load_yaml(PROJECT)
    blocks = load_unicode_blocks()
    glyph = prepare_glyphs(units_per_em // 2) # Defaulting half an em per glyph for .notdef
    built = 0

    try:
        for block_id in project["blocks"]:
            style = str(typeface["style"]).lower()
            glyph_dir: Path = to_glyphs_dir(block_id, style)

            if not glyph_dir.exists():
                raise ValueError(
                    f"Glyphs for '{block_id}' with style '{style}' referenced in project.yml "
                    f"does not exist for exporting at: \n'{glyph_dir}'"
                )

            for pbm in sorted(glyph_dir.glob("glyph_*.pbm")):
                index = int(pbm.stem.split("_")[1])
                codepoint = int(blocks[block_id]["start"]) + (index - 1)
                glyph_profile: dict = {
                    "codepoint": codepoint,
                    "pixel_size": pixel_size,
                    "verbose": v,
                    "typography": profile["typography"]
                }
                log(v, f"Building Glyph index: {index} (U+{codepoint:04X})")
                built += build_glyph(pbm, glyph, glyph_profile)
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
    strings_list: list[str] = [info["family-name"]]

    if info["custom-name"]:
        strings_list.append(info["custom-name"])

    strings_list.append(typeface["style"])

    full_name: str = ' '.join(strings_list)
    postscript: str = full_name.replace(' ', '-')
    strings_list.append(info["version"])
    unique_string: str = ' '.join(strings_list)

    name_strings: dict[str, str] = {
        # (nameID 0)
        "copyright": COPYRIGHT,
        "familyName": info["family-name"], # (nameID 1)
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
        "typographicFamily": info["family-name"], # (nameID 16)
        "typographicSubfamily": typeface["style"], # (nameID 17)
        "compatibleFullName": full_name, # (nameID 18)
        "sampleText": info["sample-text"], # (nameID 19)
    }

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
    config = load_yaml(FONT)

    parser = argparse.ArgumentParser(description='Export a TrueType font from this project')

    profile_options = ["base", "half", "full"]
    typeface_options = ["regular", "bold", "monospace"] # italic can be font attribute

    parser.add_argument('-v', "--verbose",
        default=False,
        type=bool,
        help="log verbose outputs",
    )

    parser.add_argument('-s', "--scale",
        default=profile_options[0],
        choices=profile_options,
        help="The scale preset that affect the font's internal positioning.\n"
             f"Default to '{profile_options[0]}'",
    )

    parser.add_argument('-a', "--accent",
        default=profile_options[0],
        choices=profile_options,
        help="The accent preset of this font which define the ascent\n"
             f"and descend line of this font, Default to '{profile_options[0]}'",
    )

    parser.add_argument(
        "-t", "--typeface",
        default=typeface_options[0],
        choices=typeface_options,
        help="Typeface to export configured in config/font.yml.\n"
             f"Default to '{typeface_options[0]}'",
    )

    parser.add_argument(
        "-c", "--custom-name",
        type=str,
        help="Optional, custom name appended on family name, ex. \"Basic\": BTE Seafront Basic",
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

    if args.custom_name:
        config["typeface"]["info"]["custom-name"] = args.custom_name

    typeface: dict = {
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