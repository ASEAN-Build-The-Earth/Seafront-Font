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
from typing import Literal

from PIL import Image
from fontTools.pens.ttGlyphPen import TTGlyphPen
from .extract import extract, chain, simplify, Edge

from sys import stderr

from ..model.anchors import GlyphsPositioning, AnchorPositioning
from ..model.font import TypefaceAccent, DefaultAnchors
from ..model.glyphs import GlyphsTable, GlyphMetric, GlyphProfile


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
                glyph: GlyphsTable,
                profile: GlyphProfile,
                *,
                name: str | None=None,
                cmap: int | None=None) -> Literal[0, 1]:
    """
    Read pbm bitmaps, extract it as glyphs, and compile all information in glyphs table.

    :param pbm: Path to the glyph's bitmap to build
    :param glyph: Glyphs table where result will be updated into it
    :param profile: The profile of this glyph to build
    :param cmap: Unicode codepoint integer if this glyph belongs in the Unicode table
    :param name: The name of this glyph, uses uniXXXX prefix: :code:`uni{cmap:04X}`
    :return: 1 if the glyph is successfully built in to dictionary, else 0
    """
    v: bool = profile["verbose"]
    pixel_size: int = profile["pixel_size"]
    white_space: int = profile["typography"]["white-space"]  # The white-space width
    right_padding: int = profile["typography"]["right-padding"]  # The padding between every character

    # PBM Cell: The dimension of glyph pbm file
    # TODO: currently is coded to reflect each font's designed accent,
    #       might consider making this more dynamic.
    #       For example if we want to optimize some pbm file like cropping.
    accent: TypefaceAccent = profile["accent"]
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
    if isinstance(cmap, int):
        if name is not None:
            is_extension = True
            glyph_name = name
        else:
            glyph_name = f"uni{cmap:04X}"
    else:
        # Else, glyph name must be specified
        if name is None:
            print(
                f"{'\033[93m'}Non-unicode glyph for:\n{pbm}"
                f"\n require name to be set in its profile{'\033[0m'}",
                file=stderr
            )
            return 0
        is_extension = True
        glyph_name = name

    # Special case for white-space character (U+0020)
    # TODO: Maybe a specific function for this?
    #       if we have more special characters.
    if not is_extension and cmap == 0x0020:
        log(v, f"Writing whitespace U+{cmap:04X} as {white_space}px")
        pen = TTGlyphPen(None)

        glyph["glyphs"][glyph_name] = pen.glyph()  # Empty glyph
        glyph["metrics"][glyph_name] = GlyphMetric(adv=white_space * pixel_size, lsb=0)
        glyph["glyph_order"].append(glyph_name)
        glyph["cmap"][cmap] = glyph_name
        return 1

    # Glyph's positional profile
    y_anchor: int = 0
    x_anchor: int = 0
    anchor: AnchorPositioning | None = None
    default_anchors: DefaultAnchors = profile["typography"]["anchors"]
    profile_anchors: dict[str, GlyphsPositioning] | None = profile["anchors"]
    if isinstance(profile_anchors, dict):
        # If this glyph has anchor configuration
        if glyph_name in profile_anchors:
            positioning: GlyphsPositioning = profile_anchors[glyph_name]
            anchor = positioning["anchor"]
            glyph_class = positioning["anchor"]["type"]

            if glyph_class == "above" or glyph_class == "below":
                y_anchor += default_anchors["mark"][glyph_class]

            x_anchor += int(positioning["pos"]["x"])
            y_anchor += int(positioning["pos"]["y"])

    pixels = image.load()
    fn = lambda x, y: pixels[x, y] if pixels is not None else 1
    boundary = extract(fn, w, h, origin_x, origin_y + y_anchor, pixel_size)

    if boundary is None:
        print(f"{'\033[93m'}Glyph for {glyph_name} is empty{'\033[0m'}", file=stderr)
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
                       f"for {glyph_name} is not centered: "
                       f"\nPadding is expected to span the width equally"
                       f"\n\tExpected: {start_padding} + {start_padding}"
                       f"\n\tGot: {position} + {(advance_width - position - glyph_width)}{'\033[0m'}")

    lsb: int = int(start_padding * pixel_size)
    advance: int = (advance_width + right_padding) * pixel_size
    log(v, f"{glyph_name}"
           f" bounds=({min_x},{min_y})-({max_x},{max_y}),"
           f" size={glyph_width}x{glyph_height},"
           f" lsb={lsb},"
           f" adv={advance}")

    pen = TTGlyphPen(None)
    paths = chain(edges)
    draw_glyphs(pen, paths)

    glyph["glyphs"][glyph_name] = pen.glyph()

    if anchor is not None:
        mark_class = anchor["type"]
        if mark_class == "base":
            # Default anchor will be positioned right-most of the glyph
            anchor["base"]["below"]["x"] += advance_width
            anchor["base"]["above"]["x"] += advance_width

            # With 2 anchor: below at y=0, and above at x-height
            anchor["base"]["above"]["y"] += profile["typography"]["x-height"]
        else:
            glyph["metrics"][glyph_name] = GlyphMetric.as_marks(adv=advance, lsb=lsb)

            # Above-marks need to shift the anchor up to its y position
            if mark_class == "above":
                anchor["mark"]["base"]["y"] += (max_y - 1) + default_anchors["mark"][mark_class]
                anchor["mark"]["mkmk"]["y"] += (max_y - 1) + default_anchors["mark"][mark_class]

            anchor["mark"]["mkmk"]["y"] += default_anchors["mkmk"][mark_class]

            # This one follow the metrics' x position
            # anchor["mark"]["base"]["x"] -= (origin_x + min_x - 1 - x_anchor)
            anchor["mark"]["base"]["x"] -= (origin_x + min_x - 1)
            anchor["mark"]["mkmk"]["x"] -= (origin_x + min_x - 1)

    if glyph_name not in glyph["metrics"]:
        glyph["metrics"][glyph_name] = GlyphMetric(adv=advance, lsb=lsb)

    inserted: bool = False
    if is_extension:
        unicode_name = glyph_name.split('.')[0]
        try:
            # Insert extensions to their Unicode counterpart so the order looks pretty
            # For example: uni0E4B, uni0E4B.narrow, uni0E4B.small, uni0E4C, ...
            target_index = glyph["glyph_order"].index(unicode_name)
            if target_index and (unicode_name == glyph_name):
                error: str = f"Warning: extension glyph override existing glyph for '{glyph_name}'"
                print(f"\033[93m{error}\033[0m", file=stderr)

            glyph["glyph_order"].insert(target_index + 1, glyph_name)
            inserted = True
        except ValueError:
            pass
    if not inserted:
        glyph["glyph_order"].append(glyph_name)

    if isinstance(cmap, int):
        glyph["cmap"][cmap] = glyph_name
    return 1
