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
from sys import stderr
from typing import TypedDict, NamedTuple, Any, Literal
from fontTools.pens.ttGlyphPen import TTGlyphPen

from seafront.generate import COLUMN_SIZE
from seafront.model.anchors import GlyphAnchors
from seafront.model.font import TypographyData, TypefaceStyles, TypefaceAccent
from seafront.unicode import parse_codepoint


class ExtraGlyph(NamedTuple):
    """
    Extra glyph definition

    :ivar name: The custom name of the glyph
    :ivar cmap: Unicode codepoint map if this glyph is a Unicode glyph
    """
    name: str | None
    cmap: int | None

    @classmethod
    def undefined(cls) -> ExtraGlyph:
        return cls(name=None, cmap=None)

    def is_undefined(self):
        return self == (None, None)

    def get_glyph_name(self) -> str | None:
        if isinstance(self.name, str):
            return self.name
        elif isinstance(self.cmap, int):
            return get_glyph_label(self.cmap)
        else:
            return None


class ExtraGlyphsList(TypedDict):
    """
    :ivar column: The display column size of this glyph list.
    :ivar glyphs: List of all extra glyphs
    """
    column: int
    glyphs: list[ExtraGlyph]


class GlyphMetric(NamedTuple):
    """
    Glyph's horizontal metric

    :ivar adv: Advance width of the glyph
    :ivar lsb: left side bearing position of the glyph
    """
    adv: int
    lsb: int

    @classmethod
    def as_marks(cls, *, adv: int, lsb: int) -> GlyphMetric:
        """
        Create the metric as Mark class.

        Mark classes will have zero advance width,
        lsb offset to the left of the metric.
        Glyph would position vertically above/below left side character.

        Equivalent to setting :code:`GlyphMetric(adv=0,lsb=lsb-adv)`
        :return: new GlyphMetric tuple
        """
        return cls(adv=0,lsb=lsb - adv)



class GlyphsTable(TypedDict):
    """
    TrueType compatible Glyphs data table.

    :ivar glyphs: glyf table, that maps glyph names to `fontTools.ttLib.tables._g_l_y_f.Glyph` objects
    :ivar glyph_order: Ordered set of all glyphs name
    :ivar metrics: Glyph's horizontal metric :class:`GlyphMetric`
    :ivar cmap: Characters/Unicode table, that maps integer codepoints to glyph name
    """
    glyphs: dict[str, Any]
    glyph_order: list[str]
    metrics: dict[str, GlyphMetric]
    cmap: dict[int, str]


class GlyphProfile(TypedDict):
    """
    Individual profile used to build each glyph.

    :ivar verbose: True for verbose printing
    :ivar pixel_size: Pixel size per upm
    :ivar anchors: Anchoring profile if exist
    :ivar typeface: The style of this glyph
    :ivar typography: Typography shared data/constants
    :ivar accent: Accent data ascender:descender size
    """
    verbose: bool
    pixel_size: int
    anchors: GlyphAnchors | None
    typeface: TypefaceStyles
    typography: TypographyData
    accent: TypefaceAccent


def prepare_glyphs(default_width: int) -> GlyphsTable:
    """
    Prepare a glyph table

    :param default_width: The default advance width set for .notdef character
    :return: a dict{glyphs,glyph_order,metrics,cmap}
    """
    glyph_order: list[str] = [".notdef"]
    glyphs: dict[str, Any] = {} # protected access `fontTools.ttLib.tables._g_l_y_f.Glyph`
    metrics: dict[str, GlyphMetric] = {}
    cmap: dict[int, str] = {}

    # mandatory .notdef
    pen = TTGlyphPen(None)
    glyphs[".notdef"] = pen.glyph()
    metrics[".notdef"] = GlyphMetric(adv=default_width, lsb=0)

    return {
        "glyphs": glyphs,
        "glyph_order": glyph_order,
        "metrics": metrics,
        "cmap": cmap
    }

UNI_PREFIX: Literal["uni"] = "uni"
"""
Prefix used in Unicode glyphs naming :code:`uni{index:04X}`.
"""


def get_glyph_label(codepoint: int) -> str:
    """
    Standard glyph uniXXXX label.

    :param codepoint: Unicode codepoint integer of this glyph
    :return: :code:`uni{index:02X}`: ext-00 to ext-FF
    """
    return f"{UNI_PREFIX}{codepoint:04X}"


EXT_PREFIX: Literal["ext-"] = "ext-"
"""
Prefix used in multiple naming for Extension/Extra glyph specifications.
For font table, this is mapped as :code:`ext-{index:02X}`.
"""


def get_extra_glyph_label(index: int) -> str:
    """
    6 Characters label to write inside font table,
    max 256 indexes (0-255/0X00-0XFF).

    :param index: Index position of this extra glyph
    :return: :code:`ext-{index:02X}`: ext-00 to ext-FF
    """
    return f"{EXT_PREFIX}{index:02X}"


def get_extra_glyph(glyph: Any) -> ExtraGlyph:
    """
    Parse a new instance of :class:`ExtraGlyph`
    """
    def accept_name(value: Any) -> str | None:
        """
        Accept user defined name for non-empty string,
        or an integer if the user prefer it for some reason.
        """
        if isinstance(value, str) and (accept := value.strip()):
            return accept
        elif isinstance(value, int):
            return str(value)
        else:
            return None

    def accept_cmap(value: Any) -> int | None:
        if value is None:
            return None
        """
        Safely parse cmap codepoint value,
        and print a warning if exception occurred.
        """
        try:
            return parse_codepoint(value)
        except ValueError as value_error:
            print(f"{'\033[93m'}Invalid unicode cmap "
                  f"for extra glyph: {value_error}{'\033[0m'}", file=stderr)
        except TypeError as type_error:
            print(f"{'\033[93m'}Invalid unicode cmap "
                  f"for extra glyph: {type_error}{'\033[0m'}", file=stderr)

    if isinstance(glyph, dict):
        cmap: Any | None = accept_cmap(glyph.get("cmap"))
        name: str | None = accept_name(glyph.get("name"))
        return ExtraGlyph(name=name, cmap=cmap)

    return ExtraGlyph(name=accept_name(glyph), cmap=None)


def parse_extra_glyphs(ext_glyphs_yml: dict) -> ExtraGlyphsList:
    column_size: int = ext_glyphs_yml.get("column", COLUMN_SIZE)
    glyphs_yaml: Any | None = ext_glyphs_yml.get("glyphs", None)

    # Could be listed glyph or list of string names

    if isinstance(glyphs_yaml, list):
        glyphs_list: list[ExtraGlyph] = []
        # Treat list as ordered indexes
        for i, value in enumerate(glyphs_yaml):
            if i > 0XFF: # Accept 0-255 indexes
                print(f"{'\033[93m'}Extra glyph '{value}' ignored, "
                      f"font table exceed max size of 256{'\033[0m'}", file=stderr)
                continue
            glyphs_list.append(get_extra_glyph(value))
        return {
            "column": column_size,
            "glyphs": glyphs_list
        }

    def parse_keyed_index(keyname: Any) -> int | None:
        if not isinstance(keyname, str):
            return None
        split = keyname.split("-")
        if len(split) <= 0:
            return None
        # get {index} from "ext-{index:02X}"
        keyed_index = int(keyname.split("-")[1], 16)
        if keyed_index > 0XFF:
            print(f"{'\033[93m'}Extra glyph '{keyname}' invalid key name, "
                  f"id exceed max size of 00 to FF{'\033[0m'}", file=stderr)
            return None
        if keyed_index < 0X00:
            print(f"{'\033[93m'}Extra glyph '{keyname}' is invalid, "
                  f"accepts prefixed name 'ext-00' to 'ext-FF'{'\033[0m'}", file=stderr)
            return None
        return  keyed_index

    # Is direct mapping of dict: glyph
    if isinstance(glyphs_yaml, dict):
        size: int = max(0, min(len(glyphs_yaml.items()), 0XFF))
        index_flag: list[int] = list(range(size))
        unknown_keys: list[tuple[Any, ExtraGlyph]] = list()
        glyphs_list: list[ExtraGlyph] = [ExtraGlyph.undefined()] * size
        for (key, value) in glyphs_yaml.items():
            if len(index_flag) <= 0:
                print(f"{'\033[93m'}Extra glyph '{key}':{value} ignored, "
                      f"font table exceed max size of 256{'\033[0m'}", file=stderr)
                continue

            glyph: ExtraGlyph = get_extra_glyph(value)
            index: int | None = parse_keyed_index(key)
            if index is not None and index in index_flag:
                index_flag.remove(index)
                glyphs_list[index] = glyph
                continue

            unknown_keys.append((key, glyph))

        for i in index_flag:
            (key, glyph) = unknown_keys.pop()
            label = get_extra_glyph_label(i)
            print(f"{'\033[93m'}Extra glyph name key name '{key}' "
                  f"labeled as '{label}'{'\033[0m'}", file=stderr)
            glyphs_list[i] = glyph

        return {
            "column": column_size,
            "glyphs": glyphs_list
        }

    return {
        "column": column_size,
        "glyphs": list()
    }