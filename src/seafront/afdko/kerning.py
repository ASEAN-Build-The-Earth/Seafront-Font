# Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
# with Reserved Font Name "BTE Seafront".
# Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).
#
# This Font Software is licensed under the SIL Open Font License, Version 1.1.
# This license is available with a FAQ at:
# https://openfontlicense.org
"""\
Kerning helpers
"""
from ..model.positioning import KerningProfile
from io import StringIO
from sys import stderr

from fontTools.feaLib.parser import Parser as FeatureParser
from fontTools.feaLib.error import FeatureLibError
import fontTools.feaLib.ast as ast


def get_lookup_statement(lookup: str) -> ast.LookupFlagStatement:
    try:
        definition = lookup if lookup.startswith("lookupflag") else f"lookupflag {lookup}"
        lookupflag = definition if definition.endswith(";") else f"{definition};"
        ast_parser = FeatureParser(StringIO(lookupflag))
        ast_parser.advance_lexer_(comments=True)
        return ast_parser.parse_lookupflag_()
    except (FeatureLibError, AssertionError) as error:
        print(f"\033[93mWARNING: Unable to parse lookup flag: '{lookup}' ({error})\033[0m", file=stderr)
        return ast.LookupFlagStatement(0)


def export_kerning_feat(
    kerning: KerningProfile,
    *, upm: int, pixel_size: int,
) -> ast.LookupBlock | None:
    """
    Parse Unicode block's profile/kerning.yml

    :param kerning: parsed kerning feature
    :param upm: The font's Units Per EM
    :param pixel_size: The font's pixel scale
    :return: feature text in ADFKO format
    """
    # Exported features will be of one lookup block
    kern_lookup = ast.LookupBlock(kerning["lookup"]["name"])
    lookup_flag = get_lookup_statement(kerning["lookup"]["flag"])
    kern_lookup.statements.append(lookup_flag)

    groups: dict[str, list[str]] = {} # Dict of group name to glyph list
    glyphs: dict[str, tuple[str, int]] = {} # Dict of left to right kerning

    # Generate kerning rules
    units_per_pixel: float | int = upm / pixel_size
    for left_glyph, right_groups in kerning["glyphs"].items():
        for right_group, value in right_groups.items():
            units = round(value * units_per_pixel)
            glyphs[left_glyph] = right_group, units

    if len(glyphs) == 0:
        # Nothing to kern
        return None

    # Generate OpenType classes
    for group_name, group in kerning["groups"].items():
        glyph_list = group if isinstance(group, list) else [str(group)]
        groups[group_name] = glyph_list

    # Serialize rules to feature statements
    ast_glyphs: list[ast.PairPosStatement] = []
    ast_groups: dict[str, ast.GlyphClassDefinition] = {
        name: ast.GlyphClassDefinition(name, ast.GlyphClass([
            ast.GlyphName(glyph) for glyph in glyph_list
        ])) for name, glyph_list in groups.items()
    }
    for name, (kern, kern_value) in glyphs.items():
        right_kern = ast.GlyphClassName(ast_groups[kern]) if kern in groups else ast.GlyphName(kern)
        left_kern = ast.GlyphClassName(ast_groups[name]) if name in groups else ast.GlyphName(name)
        kern_ast = ast.ValueRecord(0, 0, kern_value, 0)
        ast_glyphs.append(ast.PairPosStatement(left_kern, kern_ast, right_kern, None))

    kern_lookup.statements.extend(ast_groups.values())
    kern_lookup.statements.extend(ast_glyphs)

    return kern_lookup