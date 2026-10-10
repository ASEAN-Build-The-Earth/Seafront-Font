# Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
# with Reserved Font Name "BTE Seafront".
# Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).
#
# This Font Software is licensed under the SIL Open Font License, Version 1.1.
# This license is available with a FAQ at:
# https://openfontlicense.org
"""\
Positioning data model
"""
from sys import stderr
from typing import TypedDict, Literal, Any
from .font import BaseLabel, MarkClass, BaseClass, MarkLabel, MkMkLabel

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
    anchor: AnchorPositioning | None
    pos: Pixel


GlyphsPosTable = dict[str, GlyphsPositioning]
"""
Glyphs anchoring data model, 
maps each glyph name to its positioning data.
"""


class PositioningProfile(TypedDict):
    lookup: dict[MkMkLabel | MarkLabel, str]
    marker: dict[MarkClass, str]
    positioning: dict[str, GlyphsPositioning]


class KerningProfile(TypedDict):
    lookup: dict[Literal["name"], str]
    groups: dict[str, list[str]]
    glyphs: dict[str, dict[str, int]]


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


def _parse_glyph_positioning(groups, glyphs) -> GlyphsPosTable:
    """
    Parse Unicode block's profile/anchors.yml

    :param groups: Glyph groupings
    :param glyphs: Glyph table
    :return: Glyph positioning table
    """
    result: dict[str, GlyphsPositioning] = {}

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


def parse_horizontal_kerning(feature_index: int,
                             kerning_yml: dict) -> KerningProfile:
    """
    :param feature_index: Index identifier of this feature
    :param kerning_yml: :code:`kerning.yml` profile file
    :return: Horizontal kerning profile
    """
    def name(fallback: str) -> dict[Literal["name"], str]:
        if (isinstance(lookup := kerning_yml.get("lookup", {}), dict)
        and isinstance(lookup_name := lookup.get("name", fallback), str)):
            return { "name": lookup_name }
        elif isinstance(lookup, str):
            return { "name": lookup }
        else:
            return { "name": fallback }

    return {
        "lookup": name(f"kernHorizontalKerninglookup{feature_index}"),
        "groups": kerning_yml.get("groups", {}),
        "glyphs": kerning_yml.get("glyphs", {})
    }


def parse_glyph_positioning(feature_index: int,
                            positioning_yml: dict) -> PositioningProfile:
    """
    :param feature_index: Index identifier of this feature
    :param positioning_yml: :code:`positioning.yml` profile file
    :return: Glyphs positioning profile
    """

    def name(yml: Any, key: str, fallback: str):
        return yml.get(key, fallback) if isinstance(yml, dict) else fallback

    marker = positioning_yml.get("marker", {})
    lookup = positioning_yml.get("lookup", {})
    positioning_table: GlyphsPosTable = _parse_glyph_positioning(
        positioning_yml.get("groups", None),
        positioning_yml.get("glyphs", None)
    )

    return {
        "positioning": positioning_table,
        "lookup": {
            "mark": name(lookup, "mark", f"markMarkPositioninglookup{feature_index}"),
            "mkmk": name(lookup, "mkmk", f"mkmkMarktoMarklookup{feature_index}")
        },
        "marker": {
            "above": name(marker, "above", f"Anchor{feature_index}_AboveMarks"),
            "below": name(marker, "below", f"Anchor{feature_index}_BelowMarks")
        }
    }
