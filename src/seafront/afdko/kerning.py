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

def export_kerning_feat(
    kerning: KerningProfile,
    *, upm: int, pixel_size: int,
) -> str:
    """
    Parse Unicode block's profile/kerning.yml

    :param kerning: parsed kerning feature
    :param upm: The font's Units Per EM
    :param pixel_size: The font's pixel scale
    :return: feature text in ADFKO format
    """
    units_per_pixel = upm / pixel_size
    lines = []

    # Generate OpenType classes
    for group_name, glyphs in kerning["groups"].items():
        lines.append(f"    @{group_name} = [{ ' '.join(glyphs) }];")

    if kerning["groups"]:
        lines.append("")

    # Generate kerning rules
    for left_glyph, right_groups in kerning["glyphs"].items():
        for right_group, value in right_groups.items():
            units = round(value * units_per_pixel)
            lines.append(f"    pos {left_glyph} @{right_group} <0 0 {units} 0>;")

    return "\n".join(lines)