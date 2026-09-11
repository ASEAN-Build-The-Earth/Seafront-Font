# Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
# with Reserved Font Name "BTE Seafront".
# Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).
#
# This Font Software is licensed under the SIL Open Font License, Version 1.1.
# This license is available with a FAQ at:
# https://openfontlicense.org
"""\
Glyph data model
"""
from fontTools.pens.ttGlyphPen import TTGlyphPen


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