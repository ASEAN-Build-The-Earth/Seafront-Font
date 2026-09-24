# Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
# with Reserved Font Name "BTE Seafront".
# Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).
#
# This Font Software is licensed under the SIL Open Font License, Version 1.1.
# This license is available with a FAQ at:
# https://openfontlicense.org
"""\
Anchoring data model
"""
from sys import stderr
from typing import TypedDict
from seafront.model.font import BaseLabel, MarkClass, BaseClass, MarkLabel

# Glyph classes string Literals
AnchorClass = BaseLabel | MarkClass

# Class dictionary
Pixel = TypedDict("Pixel", { "x": int, "y": int })
MarkAnchor = dict[BaseClass, Pixel]
BaseAnchor = dict[MarkClass, Pixel]


class AnchorPositioning(TypedDict):
    """
    Glyph anchoring data type

    :ivar type: The anchor class of this glyph
    :ivar mark: Anchors for glyph of mark class (above/below)
    :ivar base: Anchors for glyph of base class
    """
    type: AnchorClass
    mark: MarkAnchor
    base: BaseAnchor


class GlyphsPositioning(TypedDict):
    """
    Glyph positioning data type

    :ivar anchor: The anchors class of this glyph
    :ivar pos: The glyph position (additive) in font metrics
    """
    anchor: AnchorPositioning
    pos: Pixel


GlyphAnchors = dict[str, GlyphsPositioning]
"""
Glyphs anchoring data model, 
maps each glyph name to its positioning data.
"""


def parse_glyph_anchors(anchors_yml: dict) -> GlyphAnchors:
    """
    Parse Unicode block's profile/anchors.yml

    :param anchors_yml: anchors.yml file
    :return: Glyph positioning dictionary
    :raises TypeError: If the configuration is invalid.
    """

    mark_class: set[MarkClass] = {"above", "below"}
    result: dict[str, GlyphsPositioning] = {}

    def zero() -> Pixel:
        return { "x": 0, "y": 0 }

    def parse_position(pos: Pixel | dict | list | None) -> Pixel:
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
                print(f"{'\033[93m'}{glyph_name}: anchor must be a string "
                      f"or mapping{'\033[0m'}", file=stderr)
                continue
            if not isinstance(metric, dict):
                print(f"{'\033[93m'}{glyph_name}: metric position must be "
                      f"a mapping of x, y{'\033[0m'}", file=stderr)
                continue
        else:
            print(f"{'\033[93m'}{glyph_name}: expected anchor definition "
                  f"or shorthand{'\033[0m'}", file=stderr)
            continue

        # Parse anchor class
        anchor_type: str | None = anchor.get("type")
        group_tuple: tuple[AnchorClass, BaseLabel | MarkLabel] | None = None

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
            print(f"{'\033[93m'}{glyph_name}: anchor must specify its type{'\033[0m'}", file=stderr)
            continue

        def create[T](base: set[T], out: str):
            name = anchor.get(out)
            if isinstance(name, dict):
                mapping = { k: name.get(k) for k in base }
                return { k: parse_position(v) for k, v in mapping.items() }
            return { k: zero() for k in base }

        base_yml: set[MarkClass] = {"above", "below"}
        mark_yml: set[BaseClass] = {"base", "mkmk"}
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
