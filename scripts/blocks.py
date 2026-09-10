#!/usr/bin/env python3
"""\
Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
with Reserved Font Name "BTE Seafront".
Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).

This Font Software is licensed under the SIL Open Font License, Version 1.1.
This license is available with a FAQ at:
https://openfontlicense.org
"""
from typing import TypedDict, Literal, Optional
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
CONFIG: Path = ROOT / "font"
BLOCKS: Path = CONFIG / "unicode-blocks.json"

UnicodeBlock = TypedDict("UnicodeBlock", { "name": str, "start": int, "end": int })


def load_unicode_blocks() -> dict[str, UnicodeBlock]:
    """
    Load embedded dict of Unicode blocks' ranges

    :return: dict{name, start, end}
    """
    with open(BLOCKS, encoding="utf-8") as fp:
        data = json.load(fp)

    blocks: dict[str, UnicodeBlock] = {}
    for key, value in data.items():
        blocks[key] = {
            "name": key,
            "start": int(value[0], 16),
            "end": int(value[1], 16),
        }
    return blocks


def export_kerning_feat(
    groups: dict, kerning: dict,
    *, upm: int, pixel_size: int,
) -> str:
    """
    Parse Unicode block's profile/kerning.yml

    :param groups: the dict 'groups' inside kerning.yml
    :param kerning: the dict 'kerning' inside kerning.yml
    :param upm: The font's Units Per EM
    :param pixel_size: The font's pixel scale
    :return: feature text in ADFKO format
    """
    units_per_pixel = upm / pixel_size
    lines = []

    # Generate OpenType classes
    for group_name, glyphs in groups.items():
        lines.append(f"    @{group_name} = [{ ' '.join(glyphs) }];")

    if groups:
        lines.append("")

    # Generate kerning rules
    for left_glyph, right_groups in kerning.items():
        for right_group, value in right_groups.items():
            units = round(value * units_per_pixel)
            lines.append(f"    pos {left_glyph} @{right_group} <0 0 {units} 0>;")

    return "\n".join(lines)

# Glyph classes string Literals
BaseValue = Literal["base"]
MarkValue = Literal["mark"]
MarkClass = Literal["above", "below"]
BaseClass = Literal["mkmk"] | BaseValue
AnchorClass = BaseValue | MarkClass

# Class dictionary
Pixel = TypedDict("Pixel", { "x": int, "y": int })
MarkAnchor = dict[BaseClass, Pixel]
BaseAnchor = dict[MarkClass, Pixel]


class AnchorPositioning(TypedDict):
    """
    Glyph anchoring data type

    :cvar type: The anchor class of this glyph
    :cvar mark: Anchors for glyph of mark class (above/below)
    :cvar base: Anchors for glyph of base class
    """
    type: AnchorClass
    mark: MarkAnchor
    base: BaseAnchor


class GlyphsPositioning(TypedDict):
    """
    Glyph positioning data type

    :cvar anchor: The anchors class of this glyph
    :cvar pos: The glyph position (additive) in font metrics
    """
    anchor: AnchorPositioning
    pos: Pixel


def parse_glyph_anchors(anchors_yml: dict) -> dict[str, GlyphsPositioning]:
    """
    Parse Unicode block's profile/anchors.yml

    :param anchors_yml: anchors.yml file
    :return: Glyph positioning dictionary
    :raises TypeError: If the configuration is invalid.
    """

    mark_class: set[MarkClass] = { "above", "below" }
    result: dict[str, GlyphsPositioning] = {}

    def zero() -> Pixel:
        return { "x": 0, "y": 0 }

    def parse_position(pos: Optional[Pixel | dict | list]) -> Pixel:
        # Parse (Optional) position
        if isinstance(pos, dict):
            x: int = int( pos.get("x", 0) )
            y: int = int( pos.get("y", 0) )
        elif isinstance(pos, list):
            x: int = int( pos[0] ) if len(pos) > 0 else 0
            y: int = int( pos[1] ) if len(pos) > 1 else 0
        else:
            return zero()

        # Pixel coordinates to font units
        return { "x": x, "y": y }

    for glyph_name, value in anchors_yml.items():
        # Resolve shorthand anchor type
        # glyph_name: ABOVE
        if isinstance(value, str):
            anchor = { "type": value }
            metric = zero()
        elif isinstance(value, dict):
            # Resolve shorthand
            # glyph_name.anchor: ABOVE
            # glyph_name.anchor.type: ABOVE

            anchor = value.get("anchor", { "type": None })
            metric = value.get("pos", zero())

            if isinstance(anchor, str):
                anchor = { "type": anchor }
            elif not isinstance(anchor, dict):
                raise TypeError(f"{glyph_name}: anchor must be a string or mapping")
            if not isinstance(metric, dict):
                raise TypeError(f"{glyph_name}: metric position must be a mapping of x, y")
        else:
            raise TypeError(f"{glyph_name}: expected anchor definition or shorthand")

        # Parse anchor class
        anchor_type: Optional[str] = anchor.get("type")
        group_tuple: Optional[tuple[AnchorClass, BaseValue | MarkValue]] = None

        if anchor_type is not None:
            selected: str = anchor_type.lower()
            # If anchor is of base class
            if selected == "base":
                group_tuple = ("base", "base")
            else: # If anchor is of mark class
                for classes in mark_class:
                    if classes == selected:
                        group_tuple = (classes, "mark")
        if group_tuple is None:
            raise TypeError(f"{glyph_name}: anchor must specify its type")

        def create[T](base: set[T], out: str) -> dict[T, Pixel]:
            name = anchor.get(out)
            if isinstance(name, dict):
                mapping = { k: name.get(k) for k in base }
                return { k: parse_position(v) for k, v in mapping.items() }
            return { k: zero() for k in base }

        base_yml: set[MarkClass] = { "above", "below" }
        mark_yml: set[BaseClass] = { "base", "mkmk"}
        final_class, group = group_tuple
        base_anchor: BaseAnchor = create(base_yml, group)
        mark_anchor: MarkAnchor = create(mark_yml, group)

        result[glyph_name] = {
            "anchor": {
                "type": final_class,
                "mark": mark_anchor,
                "base": base_anchor
            },
            "pos": parse_position(metric)
        }

    return result

def export_anchor_features(
    glyphs: dict[str, GlyphsPositioning],
    *, upm: int, pixel_size: int
) -> str:
    lines: list[str] = []
    units_per_pixel = upm / pixel_size

    mark_classes: dict[MarkClass, str] = {
        "above": "@Anchor_AboveMarks",
        "below": "@Anchor_BelowMarks",
    }

    def pack(pixel: Pixel) -> str:
        x: int = round(pixel["x"] * units_per_pixel)
        y: int = round(pixel["y"] * units_per_pixel)
        return f"{x} {y}"

    # ==================================================
    # markClass declarations
    # ==================================================
    lines.append("")
    for glyph_name, positioning in glyphs.items():
        anchor = positioning["anchor"]
        anchor_type = anchor["type"]

        if anchor_type not in ("above", "below"):
            continue

        mark_class = mark_classes[anchor_type]

        # Anchor used when this mark attaches to a base.
        mark = anchor["mark"]["base"]
        lines.append(f"markClass {glyph_name} <anchor {pack(mark)}> {mark_class};")

    # --------------------------------------------------
    # Base -> mark positioning
    # --------------------------------------------------
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

    # --------------------------------------------------
    # Mark -> mark positioning
    # --------------------------------------------------
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