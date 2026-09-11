# Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
# with Reserved Font Name "BTE Seafront".
# Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).
#
# This Font Software is licensed under the SIL Open Font License, Version 1.1.
# This license is available with a FAQ at:
# https://openfontlicense.org
"""\
Glyph exporting implementation
"""
from pathlib import Path
from PIL import Image
from fontTools.pens.ttGlyphPen import TTGlyphPen
from .extract import extract, chain, simplify, Edge

import sys


def log(verbose=False, *args):
    if verbose:
        print(*args)


def draw_glyphs(pen: TTGlyphPen, paths: list[list[Edge]]):
    """
    Use glyph to draw all given paths

    :param pen: Glyph pen to draw
    :param paths: Path list to render
    """

    def draw_glyph(path: list[Edge]):
        pen.moveTo(path[0][0])

        for edge in path:
            pen.lineTo(edge[1])

        pen.closePath()

    for edge_list in paths:
        simplified = simplify(edge_list)  # simplify edge list to a single path
        draw_glyph(simplified)



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
    draw_glyphs(pen, paths)

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