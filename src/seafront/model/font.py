# Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
# with Reserved Font Name "BTE Seafront".
# Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).
#
# This Font Software is licensed under the SIL Open Font License, Version 1.1.
# This license is available with a FAQ at:
# https://openfontlicense.org
"""\
Model view of the config file :code:`/font/font.yml`.
Changes in config file structure reflects here.
"""
from typing import TypedDict, Literal, NotRequired

BaseLabel = Literal["base"]
MarkLabel = Literal["mark"]
MkMkLabel = Literal["mkmk"]
MarkClass = Literal["above", "below"]
BaseClass = MkMkLabel | BaseLabel

RegularStyle = Literal["regular"]
MonospaceStyle = Literal["monospace"]
BoldStyle = Literal["bold"]

FontMetric = Literal["base", "half", "full"]
FontAccent = Literal["ascender", "descender"]

TypefaceStyles = RegularStyle | MonospaceStyle | BoldStyle
TypefaceAccent = dict[FontAccent, int]

TypographyConstants = TypedDict(
    "TypographyConstants", {
    "maximum-width": int,
    "origin-x": int,
    "origin-y": int,
    "x-height": int,
    "cap-height": int,
    "white-space": int,
    "right-padding": int,
    "italic-angle": int,
    "monospace-width": int
})

FontFeatures = TypedDict(
    "FontFeatures", {
    "parent-afdko": str,
    "includes-fea": list[str]
})

FontData = TypedDict(
    "FontData", {
    "design-version": str,
    "font-desc-name": NotRequired[str | None],
    "font-desc-info": str,
    "design-credits": str,
    "unicode-blocks": list[str],
    "features-afdko": FontFeatures,
    "sample-text": str
})

FontInfo = TypedDict(
    "FontInfo", {
        "foundry-name": str,
        "description": str,
        "manufacturer": str,
        "vendor-url": str,
        "designer-url": str,
        "family": NotRequired[str],
        "version": NotRequired[str]
    }
)

DefaultAnchors = dict[MkMkLabel | BaseLabel | MarkLabel, dict[MarkClass, int]]


class TypographyData(TypedDict, TypographyConstants):
    """
    Extends all typography constant variables (dict[str, int])

    :ivar anchors: Default Anchoring positions.
                   Data model is a dict of all anchor types,
                   that maps to above/below position.
    """
    anchors: DefaultAnchors


class FontProfile(TypedDict):
    """
    Font numeric profiles

    :ivar typography: Typography :class:`TypographyData`
    :ivar scale: scaling metric
    :ivar accent: accent metric ascender:descender
    """
    typography: TypographyData
    scale: dict[FontMetric, int]
    accent: dict[FontMetric, TypefaceAccent]


class TypefaceData(TypedDict):
    """
    Typeface data mappings

    :ivar family: List of all available family
    :ivar style: Name mapping for each typeface styles
    :ivar info: The font info data
    """
    family: list[str]
    style: dict[TypefaceStyles, str]
    info: FontInfo


class FontYML(TypedDict):
    """
    Full structure of /font/font.yml configuration file.

    :ivar font: All available font mapping
    :ivar typeface: Typeface data :class:`TypefaceData`
    :ivar profile: Font profile :class:`FontProfile`
    """
    font: dict[str, FontData]
    typeface: TypefaceData
    profile: FontProfile
