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


def zero() -> Pixel:
    """:return: :class:`Pixel` of 0, 0"""
    return { "x": 0, "y": 0 }


def parse_position(pos: Pixel | dict | list | None) -> Pixel:
    """
    Parse supported value as :class:`Pixel` of x, y.

    :param pos: Dict of x, y. Or a list of 2 member: x, y.
    :return: :class:`Pixel` of x, y.
    """
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


def _parse_anchors_setting(name: str, setting: dict) -> GlyphsPositioning | None:
    # Resolve shorthand anchor type
    # glyph_name: ABOVE
    if isinstance(setting, str):
        anchor = {"type": setting}
        metric = zero()
    elif isinstance(setting, dict):
        # Resolve shorthand
        # glyph_name.anchor: ABOVE
        # glyph_name.anchor.type: ABOVE

        anchor = setting.get("anchor", {"type": None})
        metric = setting.get("pos", zero())

        if isinstance(anchor, str):
            anchor = {"type": anchor}
        elif not isinstance(anchor, dict):
            print(f"{'\033[93m'}{name}: anchor must be a string "
                  f"or mapping{'\033[0m'}", file=stderr)
            return None
    else:
        print(f"{'\033[93m'}{name}: expected anchor definition "
              f"or shorthand{'\033[0m'}", file=stderr)
        return None

    # Parse anchor class
    anchor_type: str | None = anchor.get("type")
    group_tuple: tuple[AnchorClass, BaseLabel | MarkLabel] | None = None
    mark_class: set[MarkClass] = {"above", "below"}

    if anchor_type is not None:
        selected: str = anchor_type.lower()
        # If anchor is of base class
        if selected == "base":
            group_tuple = ("base", "base")
        else:  # If anchor is of mark class
            for classes in mark_class:
                if classes == selected:
                    group_tuple = (classes, "mark")
    if group_tuple is None:
        print(f"{'\033[93m'}{name}: anchor must specify its type{'\033[0m'}", file=stderr)
        return None

    def create[T](base: set[T], out: str):
        s = anchor.get(out)
        if isinstance(s, dict):
            mapping = {k: s.get(k) for k in base}
            return {k: parse_position(v) for k, v in mapping.items()}
        return {k: zero() for k in base}

    base_yml: set[MarkClass] = {"above", "below"}
    mark_yml: set[BaseClass] = {"base", "mkmk"}
    final_class, group = group_tuple
    base_anchor: BaseAnchor = create(base_yml, group)
    mark_anchor: MarkAnchor = create(mark_yml, group)

    result: GlyphsPositioning = {
        "anchor": {
            "type": final_class,
            "mark": mark_anchor,
            "base": base_anchor
        },
        "pos": parse_position(metric)
    }
    return result


def _add_groups(result: dict[str, GlyphsPositioning], name: str, group):
    if not isinstance(group, dict):
        print(f"\033[93mGroup [{name}]: anchor must be a mapping\033[0m", file=stderr)
        return

    if (setting := _parse_anchors_setting(name, group)) is not None:
        glyphs = group.get("glyphs", None)
        if isinstance(glyphs, str):
            result[glyphs] = setting
        elif isinstance(glyphs, list):
            for glyph in glyphs:
                result[glyph] = setting
        else:
            print(f"\033[93mGroup [{name}]: must have a key 'glyphs' "
                  f"as a list or string name\033[0m", file=stderr)


def parse_glyph_anchors(anchors_yml: dict) -> GlyphAnchors:
    """
    Parse Unicode block's profile/anchors.yml

    :param anchors_yml: anchors.yml file
    :return: Glyph positioning dictionary
    """
    result: dict[str, GlyphsPositioning] = {}
    groups = anchors_yml.get("groups", None)
    glyphs = anchors_yml.get("anchors", None)

    if glyphs is None and groups is None:
        print(f"\033[93mWARNING: No anchors config found. "
              f"One of 'anchors' or 'groups' is required.\033[0m", file=stderr)
        return result

    if isinstance(groups, dict) or isinstance(groups, list):
        for name, group in groups.items() if isinstance(groups, dict) else enumerate(groups):
            _add_groups(result, f"Group [{name}]", group)
    elif groups is not None:
        print(f"\033[93mWARNING: 'groups' config must be a mapping or a list.\033[0m", file=stderr)

    if isinstance(glyphs, dict):
        for glyph_name, setting in glyphs.items():
            if (anchor := _parse_anchors_setting(glyph_name, setting)) is not None:
                result[glyph_name] = anchor
    elif glyphs is not None:
        print(f"\033[93mWARNING: 'anchors' config must be a mapping.\033[0m", file=stderr)
        return result

    return result
