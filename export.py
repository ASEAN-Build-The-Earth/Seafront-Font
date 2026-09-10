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
from scripts.blocks import (load_unicode_blocks,
                            export_kerning_feat,
                            parse_glyph_anchors,
                            export_anchor_features, AnchorPositioning, GlyphsPositioning)

import argparse
import yaml
import sys

VERBOSE = False
CELL_SIZE: int = 64

ROOT = Path(__file__).resolve().parent
CONFIG: Path = ROOT / "font"
PROJECT: Path = CONFIG / "project.yml"
FONT: Path = CONFIG / "font.yml"

def to_glyphs_dir(block: str, family: str, style: str) -> Path:
    return ROOT / "src" / block / "glyphs" / family / style

def to_profile_yml(block: str, file: str) -> Path:
    return ROOT / "src" / block / "profile" / file

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
        # log(verbose, f"Starting {path[0][0]}")
        pen.moveTo(path[0][0])

        for edge in path:
            # log(verbose, f"Drawing {edge[1]}")
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
    codepoint: int | None = profile["codepoint"]
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
    glyph_name: str
    is_extension: bool = False

    # Check for codepoint identity
    if isinstance(codepoint, int):
        if "glyph_name" in profile:
            is_extension = True
            glyph_name = profile["glyph_name"]
        else:
            glyph_name = f"uni{codepoint:04X}"
    else:
        if "glyph_name" not in profile:
            print(
                f"{'\033[93m'}Non-unicode glyph for:\n{pbm}"
                f"\n require name to be set in its profile{'\033[0m'}",
                file=sys.stderr
            )
            return 0
        is_extension = True
        glyph_name = profile["glyph_name"]


    # Special case for space character (U+0020)
    if codepoint == 0x0020:
        log(v, f"Writing whitespace U+{codepoint:04X} as {white_space}px")
        pen = TTGlyphPen(None)

        glyph["glyphs"][glyph_name] = pen.glyph()  # Empty glyph
        glyph["metrics"][glyph_name] = (white_space  * pixel_size, 0)
        glyph["glyph_order"].append(glyph_name)
        glyph["cmap"][codepoint] = glyph_name
        return 1

    # Glyph's positional profile
    y_anchor = 0
    x_anchor = 0
    anchor: AnchorPositioning | None = None
    anchor_type: str | None = None
    options = dict(base="base", above="mark", below="mark")

    if isinstance(profile["anchors"], dict):
        anchors = profile["anchors"]

        # If this glyph has anchor configuration
        if glyph_name in anchors:
            positioning: GlyphsPositioning = anchors[glyph_name]
            anchor = positioning["anchor"]
            glyph_class = positioning["anchor"]["type"]
            anchor_type = options[glyph_class]

            if anchor_type == "mark":
                y_anchor += profile["typography"]["anchors"]["mark"][glyph_class]

            x_anchor += int( positioning["pos"]["x"] )
            y_anchor += int( positioning["pos"]["y"] )

    pixels = image.load()
    fn = lambda x, y: pixels[x, y] if pixels is not None else 1
    boundary = extract(fn, w, h, origin_x , origin_y + y_anchor, pixel_size)

    if boundary is None:
        print(f"{'\033[93m'}Glyph for '{glyph_name}' is empty{'\033[0m'}", file=sys.stderr)
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

        if v: # Verbose logging in case a glyph is not centered by default
            position = (origin_x + advance_width) - (max_x + 1)
            if position != start_padding:
                log(v, f"{'\033[93m'}Monospace glyph "
                      f"for '{glyph_name}' is not centered: "
                      f"\nPadding is expected to span the width equally"
                      f"\n\tExpected: {start_padding} + {start_padding}"
                      f"\n\tGot: {position} + {(advance_width - position - glyph_width)}{'\033[0m'}")

    lsb: int = int( start_padding * pixel_size )
    advance: int = (advance_width + right_padding) * pixel_size
    log(v, f"{glyph_name}"
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

    if is_extension:
        unicode_name = glyph_name.split('.')[0]
        try:
            # Insert extensions to their Unicode counterpart so the order looks pretty
            # For example: uni0E4B, uni0E4B.narrow, uni0E4B.small, uni0E4C, ...
            target_index = glyph["glyph_order"].index(unicode_name)
            if target_index and (unicode_name == glyph_name):
                error: str = f"Warning: extension glyph override existing glyph for '{glyph_name}'"
                print(f"\033[93m{error}\033[0m", file=sys.stderr)

            glyph["glyph_order"].insert(target_index + 1, glyph_name)
        except ValueError:
            glyph["glyph_order"].append(glyph_name)
    else:
        glyph["glyph_order"].append(glyph_name)

    if isinstance(codepoint, int):
        glyph["cmap"][codepoint] = glyph_name

    return 1

def export(font, profile, output):
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

    family_name: str = font["info"]["family"]
    blocks = load_unicode_blocks()
    glyph = prepare_glyphs(units_per_em // 2) # Defaulting half an em per glyph for .notdef
    built = 0

    anchors_feature: dict = {}
    kerning_feature: dict = {}

    try:
        for block_id in font["unicode-blocks"]:
            face = font["face"]
            glyph_dir: Path = to_glyphs_dir(block_id, family_name, face)
            anchors_yml: Path = to_profile_yml(block_id, "anchors.yml")
            kerning_yml: Path = to_profile_yml(block_id, "kerning.yml")

            if not glyph_dir.exists():
                error = (
                    f"Glyphs for '{block_id}' required for '{font["name"]}' "
                    f"does not exist for exporting at: \n'{glyph_dir}'"
                )
                print(f"{'\033[93m'}{error}{'\033[0m'}", file=sys.stderr)
                continue

            anchors = None
            if anchors_yml.exists():
                anchors = parse_glyph_anchors( load_yaml(anchors_yml) )
                anchors_feature[block_id] = anchors

            # Add all Unicode Glyphs
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
                log(v, f"Building Glyph index: {index} ({codepoint}: U+{codepoint:04X})")
                built += build_glyph(pbm, glyph, glyph_profile, profile["accent"])

            # Check if extra features exist as glyphs config
            feat_glyphs: Path = to_profile_yml(block_id, "ext-glyphs.yml")

            if feat_glyphs.exists():
                ext_glyph_yml = load_yaml(feat_glyphs)
                ext_glyph_dir = to_glyphs_dir(block_id, family_name, f"ext-{face}")
                if not ext_glyph_dir.exists():
                    error = (
                        f"Extra glyphs for '{block_id}' required in profile/ext-glyphs.yml "
                        f"does not exist for exporting at: \n'{ext_glyph_dir}'"
                    )
                    print(f"{'\033[93m'}{error}{'\033[0m'}", file=sys.stderr)
                    continue

                # Extra glyphs has user defined name
                def fn_ext_glyph_at(i) -> dict | None:
                    key = f"ext-{i:02X}"
                    if key in ext_glyph_yml["glyphs"]:
                        return ext_glyph_yml["glyphs"][key]
                    return None

                # Add all Extra glyphs
                for pbm in sorted(ext_glyph_dir.glob("glyph_*.pbm")):
                    index = int(pbm.stem.split("_")[1]) - 1
                    ext_glyph = fn_ext_glyph_at(index)
                    if not ext_glyph:
                        error = (
                            f"No definition found for Extra glyph at:\n{pbm}\n"
                            f"Expected key required in ext-glyph.yml: 'ext-{index:02X}': "
                        )
                        print(f"{'\033[93m'}{error}{'\033[0m'}", file=sys.stderr)
                        continue

                    cmap_codepoint = ext_glyph["cmap"] if "cmap" in ext_glyph else None
                    ext_glyph_name = ext_glyph["name"] if "name" in ext_glyph else None
                    glyph_profile: dict = {
                        "codepoint": cmap_codepoint,
                        "glyph_name": ext_glyph_name,
                        "anchors": anchors,
                        "pixel_size": pixel_size,
                        "verbose": v,
                        "typeface": face,
                        "typography": profile["typography"]
                    }

                    log(v, f"Building Extra Glyph: {index} (EXT-{index:02X})")
                    built += build_glyph(pbm, glyph, glyph_profile, profile["accent"])

            # Post build: kerning feature is processed purely under OpenType feature
            if kerning_yml.exists():
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

    license_desc: list[str] = LICENSE.splitlines()
    license_info: str = license_desc[len(license_desc) - 1]

    info: dict[str, str] = font["info"]
    font_naming: list[str] = [ family_name ]

    # Font may have variant name as: Seafront <name>
    if isinstance(font["font-desc-name"], str) and font["font-desc-name"]:
        font_naming.append(font["font-desc-name"])

    # The full name without foundry prefix, read as the display name often
    public_name: str = ' '.join(font_naming)

    # BTE Seafront <name>
    font_naming.insert(0, info["foundry-name"])
    formal_name: str = ' '.join(font_naming)

    # BTE Seafront <name> Regular
    font_naming.append(font["style"])
    packed_name: str = ' '.join(font_naming)

    # BTE-Seafront-<name>-Regular
    post_script: str = packed_name.replace(' ', '-')

    # BTE Seafront <name> Regular Version 1.000
    font_naming.append(info["version"])
    unique_name: str = ' '.join(font_naming)

    name_strings: dict[str, str] = {
        # (nameID 0)
        "copyright": COPYRIGHT,
        "familyName": formal_name, # (nameID 1)
        "styleName": font["style"], # (nameID 2)
        "uniqueFontIdentifier": unique_name, # (nameID 3)
        "fullName": packed_name, # (nameID 4)
        "version": info["version"], # (nameID 5)
        "psName": post_script, # (nameID 6)
        # "trademark": "", # (nameID 7)
        "manufacturer": info["manufacturer"], # (nameID 8)
        "designer": info["designer"], # (nameID 9)
        "description": info["description"], # (nameID 10)
        "vendorURL": info["vendor-url"], # (nameID 11)
        "designerURL": info["designer-url"], # (nameID 12)
        "licenseDescription": LICENSE, # (nameID 13)
        "licenseInfoURL": license_info, # (nameID 14)
        # (nameID 15 reserved)
        "typographicFamily": public_name, # (nameID 16)
        "typographicSubfamily": font["style"], # (nameID 17)
        "compatibleFullName": packed_name, # (nameID 18)
        "sampleText": info["sample-text"], # (nameID 19)
    }

    # 2. Include initial .fea as parent features
    fea_full: list[str] = []
    afdko_parent: Path = CONFIG / font["features-afdko"]["parent-afdko"]

    if afdko_parent.exists():
        print(f"Exporting features file (AFDKO) for:\nFile \"{afdko_parent}\", line 1")
        includes: list[Path] = font["features-afdko"]["includes-fea"]
        features: str = Path(afdko_parent).read_text()
        fea_full.append(features)

        # Include font specific features file
        for fea_path in includes:
            fea_full.append(f"include({CONFIG / fea_path})")
        fea_full.append("")


    # 3. Compile and embed the features into the font object
    # This modifies the font object in-place

    for block_id, anchors in anchors_feature.items():
        print(f"Exporting anchors for: {block_id}")
        anchor_txt = export_anchor_features(
            anchors,
            upm=units_per_em,
            pixel_size=pixel_size,
        )
        print(anchor_txt)
        fea_full.append(anchor_txt)

    for block_id, path in kerning_feature.items():
        print(f"Exporting kernings for: {block_id}")
        kerning = load_yaml(path)
        fea_txt = export_kerning_feat(
            kerning["groups"],
            kerning["kerning"],
            upm=units_per_em,
            pixel_size=pixel_size,
        )
        print(fea_txt)
        fea_full.append("feature kern {")
        fea_full.append(fea_txt)
        fea_full.append("} kern;")

    final_features_string = '\n'.join(fea_full)
    print(final_features_string)

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
    log(v, "Glyphs Metadata: ", glyph["glyph_order"])
    filename = f"{post_script}.ttf" if output is None else \
        (output if str(output).endswith(".ttf") else f"{output}.ttf")
    fb.save(filename)
    print(f"Wrote {filename}")

def main():
    config = load_yaml(FONT)

    parser = argparse.ArgumentParser(
        description="Export a TrueType font from this project",
        formatter_class=argparse.RawTextHelpFormatter
    )

    typeface_options = [*config["typeface"]["style"]]
    accent_options = [*config["profile"]["accent"]]
    family_options = config["typeface"]["family"]

    parser.add_argument('-v', "--verbose",
        default=False, const=True,
        type=bool, nargs="?",
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

    # Positional Arguments
    #  export.py {font_options} {output_filename)

    available_font = { k: v["font-desc-info"] for k, v in config["font"].items() }
    font_desc_text = "\n".join(f"- \033[1m\033[32m{key:<8}\033[0m : {val}" for key, val in available_font.items())
    font_hint_text = "\33[90mThe export profile can be configured under \033[4m/font/font.yml\033[0m"
    font_help_text = "\n".join([ "Which font to export? (Required):", font_desc_text, font_hint_text ])
    file_help_text = "Output file name *.ttf, default to the psName of exporting font."

    parser.add_argument("font", choices=available_font, help=font_help_text)

    parser.add_argument("output", nargs="?",  help=file_help_text)

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

    font_export: dict = {
        "style": config["typeface"]["style"][face],
        "info": config["typeface"]["info"],
        "name": args.font,
        "face": face
    }
    font_export |= config["font"][args.font]
    font_profile: dict = {
        "typography": config["profile"]["typography"],
        "scale": config["profile"]["scale"][scale],
        "accent": config["profile"]["accent"][accent],
        "verbose": args.verbose
    }

    log(args.verbose, "Export Profile: ", font_export, font_profile)
    export(font_export, font_profile, args.output)

if __name__ == "__main__":
    main()