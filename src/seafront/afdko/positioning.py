# Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
# with Reserved Font Name "BTE Seafront".
# Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).
#
# This Font Software is licensed under the SIL Open Font License, Version 1.1.
# This license is available with a FAQ at:
# https://openfontlicense.org
"""\
Positioning feature helpers
"""
from ..model.positioning import PositioningProfile, Pixel, AnchorPositioning, AnchorClass
from ..model.font import MarkClass, MkMkLabel, MarkLabel

import fontTools.feaLib.ast as ast


def _serialize_mark_anchors(anchor: dict[MarkClass, dict[tuple[int, int], list[str]]],
                            marker: dict[MarkClass, str]):
    for above_or_below in anchor.keys():
        ast_class = ast.MarkClass(marker[above_or_below])
        for (pos, glyphs) in anchor[above_or_below].items():
            ast_glyph_list = [ast.GlyphName(glyph) for glyph in glyphs]
            ast_anchor = ast.Anchor(pos[0], pos[1])
            ast_glyph = ast.GlyphClass(ast_glyph_list)
            yield ast_class, ast_anchor, ast_glyph


def _serialize_base_anchors(anchor: dict[tuple[int | None, ...], list[str]],
                            marker: dict[MarkClass, str]):
    def anchor_ast(x: int, y: int, mark_type: MarkClass) -> tuple[ast.Anchor, ast.MarkClass]:
        return ast.Anchor(x, y), ast.MarkClass(marker[mark_type])

    for (x_above, y_above, x_below, y_below), glyph_list in anchor.items():
        ast_glyphs = ast.GlyphClass([ast.GlyphName(glyph) for glyph in glyph_list])
        ast_marks: list[tuple[ast.Anchor, ast.MarkClass]] = []

        if not (x_above is None or y_above is None):
            ast_marks.append(anchor_ast(x_above, y_above, "above"))
        if not (x_below is None or y_below is None):
            ast_marks.append(anchor_ast(x_below, y_below, "below"))

        yield ast_glyphs, ast_marks


def export_positioning_features(
    positioning: PositioningProfile,
    *, upm: int, pixel_size: int
) -> dict[MarkLabel | MkMkLabel, ast.LookupBlock | None]:
    """
    Export glyphs positioning feature as AFDKO text

    :param positioning: Parsed positioning profile
    :param upm: The font's Units Per EM
    :param pixel_size: The font's pixel scale
    :return: AFDKO feature file text block
    """
    units_per_pixel: float | int = upm / pixel_size
    def pixel(value: Pixel) -> tuple[int, int]:
        x: int = round(value["x"] * units_per_pixel)
        y: int = round(value["y"] * units_per_pixel)
        return x, y

    # markClass declarations
    # markClass {glyph_name} <anchor {pixel(mark)}> @{anchor_type};
    marks_class: dict[MarkClass, dict[tuple[int, int], list[str]]] = { "above": {}, "below": {} }

    for glyph_name, profile in positioning["positioning"].items():
        anchor: AnchorPositioning | None = profile["anchor"]
        if anchor is None:
            continue
        anchor_type: AnchorClass = anchor["type"]
        anchor_value: Pixel | None = anchor["mark"]["base"]

        if anchor_type not in ("above", "below") or anchor_value is None:
            continue

        # Anchor used when this mark attaches to a base.
        mark: tuple[int, int] = pixel(anchor_value)
        if mark in marks_class[anchor_type]:
            marks_class[anchor_type][mark].append(glyph_name)
        else:
            marks_class[anchor_type][mark] = [glyph_name]

    # Base to mark anchoring
    base_anchoring: dict[tuple[int | None, ...], list[str]] = {}

    def pack_anchor(base: dict[MarkClass, Pixel],
                    type_name: MarkClass) -> tuple[int, int] | tuple[None, None]:
        if type_name not in base or len(marks_class[type_name]) == 0:
            return None, None
        return pixel(base[type_name])

    for glyph_name, profile in positioning["positioning"].items():
        anchor: AnchorPositioning | None = profile["anchor"]
        if anchor is None or anchor["type"] != "base":
            continue

        anchor_above = pack_anchor(anchor["base"], "above")
        anchor_below = pack_anchor(anchor["base"], "below")
        anchor_key: tuple[int | None, ...] = anchor_above + anchor_below

        if anchor_key == (None, None, None, None):
            continue
        elif anchor_key in base_anchoring:
            base_anchoring[anchor_key].append(glyph_name)
        else:
            base_anchoring[anchor_key] = [glyph_name]

    # Mark to mark anchoring
    mkmk_anchoring: dict[MarkClass, dict[tuple[int, int], list[str]]] = { "above": {}, "below": {} }

    for glyph_name, profile in positioning["positioning"].items():
        anchor: AnchorPositioning | None = profile["anchor"]
        if anchor is None:
            continue
        anchor_type: AnchorClass = anchor["type"]

        if anchor_type not in ("above", "below"):
            continue

        mkmk: tuple[int, int] = pixel(anchor["mark"]["mkmk"])
        if mkmk in (mkmk_type := mkmk_anchoring[anchor_type]):
            mkmk_type[mkmk].append(glyph_name)
        else:
            mkmk_type[mkmk] = [glyph_name]

    # Serialize positioning features
    positioning_lookup: dict[
        MarkLabel | MkMkLabel,
        ast.LookupBlock | None
    ] = { "mark": None, "mkmk": None }

    # Skip if length is 0 (Nothing to lookup)
    mkmk_size = sum([ len(mkmk) for mkmk in mkmk_anchoring.values()])
    mark_size = len(base_anchoring)

    def serialize_mark_classes():
        """Serialize :class:`ast.MarkClassDefinition`"""
        for classes in _serialize_mark_anchors(marks_class, positioning["marker"]):
            mark_class, anchor_class, glyph_class = classes
            yield ast.MarkClassDefinition(mark_class, anchor_class, glyph_class)

    # Serialize base-to-mark lookup
    if mark_size > 0:
        mark_lookup = ast.LookupBlock(positioning["lookup"]["mark"])
        mark_lookup.statements.append(ast.LookupFlagStatement(0))
        mark_lookup.statements.extend(serialize_mark_classes())

        for ast_base, ast_glyph_list in _serialize_base_anchors(base_anchoring, positioning["marker"]):
            ast_base_to_mark = ast.MarkBasePosStatement(ast_base, ast_glyph_list)
            mark_lookup.statements.append(ast_base_to_mark)

        positioning_lookup["mark"] = mark_lookup

    # Serialize mark-to-mark lookup table
    if mkmk_size > 0:
        mkmk_lookup = ast.LookupBlock(positioning["lookup"]["mkmk"])
        mkmk_lookup.statements.append(ast.LookupFlagStatement(0))

        if mark_size == 0:
            # Add markClasses declaration if it hasn't been by base-to-mark lookup
            mkmk_lookup.statements.extend(serialize_mark_classes())

        for ast_classes in _serialize_mark_anchors(mkmk_anchoring, positioning["marker"]):
            ast_class, ast_anchor, ast_glyphs = ast_classes
            ast_mkmk = ast.MarkMarkPosStatement(ast_glyphs, [(ast_anchor, ast_class)])
            mkmk_lookup.statements.append(ast_mkmk)

        positioning_lookup["mkmk"] = mkmk_lookup

    return positioning_lookup
