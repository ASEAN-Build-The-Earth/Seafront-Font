# Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
# with Reserved Font Name "BTE Seafront".
# Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).
#
# This Font Software is licensed under the SIL Open Font License, Version 1.1.
# This license is available with a FAQ at:
# https://openfontlicense.org
"""\
Anchoring helpers
"""

def export_anchor_features(
    glyphs,
    *, upm: int, pixel_size: int
) -> str:
    """
    Export glyphs anchoring feature as AFDKO text

    :param glyphs: Glyphs anchoring config
    :param upm: The font's Units Per EM
    :param pixel_size: The font's pixel scale
    :return: AFDKO feature file text block
    """
    lines: list[str] = []
    units_per_pixel = upm / pixel_size
    # TODO: This would make duplicate name for more than 1 feature
    mark_classes = {
        "above": "@Anchor_AboveMarks",
        "below": "@Anchor_BelowMarks",
    }

    def pack(pixel) -> str:
        x: int = round(pixel["x"] * units_per_pixel)
        y: int = round(pixel["y"] * units_per_pixel)
        return f"{x} {y}"

    # markClass declarations
    lines.append("")
    for glyph_name, positioning in glyphs.items():
        anchor = positioning["anchor"]
        anchor_type = anchor["type"]

        if anchor_type not in ("above", "below"):
            continue

        # Anchor used when this mark attaches to a base.
        mark_class = mark_classes[anchor_type]
        mark = anchor["mark"]["base"]
        lines.append(f"markClass {glyph_name} <anchor {pack(mark)}> {mark_class};")

    # Base to mark anchoring
    lines.append("")
    lines.append("feature mark {")

    for glyph_name, positioning in glyphs.items():
        anchor = positioning["anchor"]

        if anchor["type"] != "base":
            continue

        base = anchor["base"]
        rules: list[str] = []

        for mark_type in ("above", "below"):
            if mark_type not in base:
                continue

            position = base[mark_type]
            mark_class = mark_classes[mark_type]

            rules.append(f"<anchor {pack(position)}> mark {mark_class}")

        if rules:
            lines.append(f"    pos base {glyph_name} {' '.join(rules)};")

    lines.append("} mark;")
    lines.append("")

    # Mark to mark anchoring
    lines.append("feature mkmk {")

    for glyph_name, positioning in glyphs.items():
        anchor = positioning["anchor"]
        anchor_type = anchor["type"]

        if anchor_type not in ("above", "below"):
            continue

        mkmk = anchor["mark"]["mkmk"]

        if mkmk["x"] == 0 and mkmk["y"] == 0:
            continue

        lines.append(f"    pos mark {glyph_name} <anchor {pack(mkmk)}> mark {mark_classes[anchor_type]};")

    lines.append("} mkmk;")

    return "\n".join(lines).rstrip() + "\n"