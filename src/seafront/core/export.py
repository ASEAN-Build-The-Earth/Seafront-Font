# Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
# with Reserved Font Name "BTE Seafront".
# Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).
#
# This Font Software is licensed under the SIL Open Font License, Version 1.1.
# This license is available with a FAQ at:
# https://openfontlicense.org
"""\
Font exporting implementations
"""
from pathlib import Path
from typing import TypedDict, Callable

from fontTools.fontBuilder import FontBuilder
from importlib.resources import as_file
from importlib.resources.abc import Traversable

from sys import stderr
from .glyphs import build_glyph
from ..font import FONT_DIR
from ..unicode import load_unicode_blocks, UnicodeBlock
from ..afdko.anchors import export_anchor_features
from ..afdko.kerning import export_kerning_feat
from ..model.anchors import parse_glyph_anchors, GlyphAnchors
from ..model.font import TypefaceStyles, FontInfo, FontData, TypographyData, TypefaceAccent

import seafront.model.glyphs as glyphs
import seafront.__about__ as about
import seafront.font as font
import yaml


def log(verbose=False, *args):
    if verbose:
        print(*args)


def load_yaml(file: Traversable):
    with file.open(encoding="utf-8") as fp:
        return yaml.safe_load(fp)


class FontExport(TypedDict):
    """
    Information of the font to export.

    :ivar style: The style name of this Font
    :ivar name: The name of this Font
    :ivar info: Metadata infos
    :ivar face: The style name identifier
    """
    style: str
    name: str
    info: FontInfo
    face: TypefaceStyles


class FontProfile(TypedDict):
    """
    :ivar verbose: True to verbose printing
    :ivar scale: Pixel size scaling
    :ivar accent: Accent size ascender:descender
    :ivar typography: Typography shared data :class:`TypographyData`
    """
    verbose: bool
    scale: int
    accent: TypefaceAccent
    typography: TypographyData


def export(export_fn: Callable[[str], Path],
           font_export: FontExport,
           font_data: FontData,
           profile: FontProfile):
    """
    Export font as TrueType .ttf file

    :param export_fn: Function to translate (str) generated name into export file Path
    :param font_export: Font's exporting information
    :param font_data: Font metadata information
    :param profile: Typeface profile
    :return:
    """
    v: bool = profile["verbose"]
    pixel_size: int = profile["scale"]
    ascender: int = profile["accent"]["ascender"]
    descender: int = profile["accent"]["descender"]
    units_per_em: int = (ascender + descender) * pixel_size

    # Guard UPM, need to fall within ± 4095 for "safety"
    if units_per_em > 4096:
        print(f"{'\033[31m'}Font unit incompatible- scale too large.\n"
              f"Please either lower your scale or step down the accent{'\033[0m'}", file=stderr)
        return

    family_name: str = font_export["info"]["family"]
    blocks: dict[str, UnicodeBlock] = load_unicode_blocks()
    glyph: glyphs.GlyphsTable = glyphs.prepare_glyphs(units_per_em // 2)  # Defaulting half an em per glyph for .notdef
    built: int = 0

    anchors_feature: dict[str, GlyphAnchors] = {}
    kerning_feature: dict[str, Traversable]  = {}
    unicode_missing: tuple[str, str] | None  = None

    try:
        for block_name in font_data["unicode-blocks"]:
            face = font_export["face"]

            glyph_dir = font.project_glyphs(block_name, family_name, face)
            if not glyph_dir.is_dir():
                with as_file(glyph_dir) as missing_path:
                    unicode_missing = (block_name, rf"{missing_path}")
                continue

            anchors_yml: Traversable = font.anchors_yml(block_name)
            kerning_yml: Traversable = font.kerning_yml(block_name)

            def load_anchors() -> GlyphAnchors:
                glyph_anchors = parse_glyph_anchors(load_yaml(anchors_yml))
                anchors_feature[block_name] = glyph_anchors
                return glyph_anchors

            # Kerning feature is processed purely under OpenType feature
            if kerning_yml.is_file():
                kerning_feature[block_name] = kerning_yml

            # Anchors positioning required to adjust each glyph if configured
            anchors: GlyphAnchors | None = load_anchors() if anchors_yml.is_file() else None
            glyph_profile: glyphs.GlyphProfile = {
                "pixel_size": pixel_size,
                "anchors": anchors,
                "verbose": v,
                "typeface": face,
                "typography": profile["typography"],
                "accent": profile["accent"]
            }

            start: int = blocks[block_name]["start"]
            for index in range(blocks[block_name]["end"] - start + 1):
                codepoint: int = start + index
                pbm = glyph_dir / f"{glyphs.get_glyph_label(codepoint)}.pbm"
                if not pbm.is_file():
                    log(v, f"Skipping Glyph: U+{codepoint:04X} (No PBM file)")
                    continue
                log(v, f"Building Glyph: U+{codepoint:04X}")
                built += build_glyph(pbm, glyph, glyph_profile, cmap=codepoint)

            # Check if extra features exist as glyphs config
            ext_glyphs_yml = font.ext_glyphs_yml(block_name)

            if not ext_glyphs_yml.is_file():
                continue

            ext_glyph_dir = font.project_glyphs(block_name, family_name, f"{glyphs.EXT_PREFIX}{face}")
            if not ext_glyph_dir.is_dir():
                glyph_error = (
                    f"Extra glyphs for '{block_name}' required in profile/{glyphs.EXT_PREFIX}glyphs.yml "
                    f"does not exist for exporting at: \n'{ext_glyph_dir.name}'"
                )
                print(f"{'\033[93m'}{glyph_error}{'\033[0m'}", file=stderr)
                continue

            # Add all Extra glyphs
            ext_glyph_list = glyphs.parse_extra_glyphs(load_yaml(ext_glyphs_yml))
            for index, ext_glyph in enumerate(ext_glyph_list["glyphs"]):
                if (filename := ext_glyph.get_glyph_name()) is None:
                    filename = glyphs.get_extra_glyph_label(index)

                pbm = ext_glyph_dir / f"{filename}.pbm"
                if not pbm.is_file():
                    glyph_error = (
                        f"Extra glyph {glyphs.get_extra_glyph_label(index)} "
                        f"PBM file '{pbm.name}' not found!")
                    log(v, f"\033[93m{glyph_error}\033[0m")
                    continue

                log(v, f"Building Extra Glyph: {index} (EXT-{index:02X})")
                built += build_glyph(pbm, glyph, glyph_profile, name=filename, cmap=ext_glyph.cmap)
    except Exception as e:
        print(f"{'\033[93m'}Exception when collecting glyphs:\n{e}{'\033[0m'}", file=stderr)
    if unicode_missing is not None:
        (missing_name, missing_dir) = unicode_missing
        error_details = (f"\n  required for '{family_name}' with '{font_export["face"]}' typeface at: "
                         f"\n  {missing_dir}"
                         f"\n  (font/font.yml font.{font_export["name"]}.unicode-blocks)")
        raise ValueError(f"{font_export["name"]} Missing required Unicode block"
                         f" '{missing_name}'" + error_details)
    elif built == 0:
        raise ValueError("No available glyphs found for this typeface.")

    # ------------------------------
    # Font metadata
    # ------------------------------

    ascent: int = ascender * pixel_size
    descend: int = descender * pixel_size
    x_height: int = profile["typography"]["x-height"] * pixel_size
    cap_height: int = profile["typography"]["cap-height"] * pixel_size
    italic_angle: int = profile["typography"]["italic-angle"]
    underline_position: int = -pixel_size * 2 # Place 2 pixel below
    underline_thickness: int = pixel_size * 2 # With size of 2 pixel

    log(v, f"Typography"
       f" ascent={ascent},"
       f" descent={descend},"
       f" unitsPerEm={units_per_em}")
    fb = FontBuilder(unitsPerEm=units_per_em, isTTF=True)

    fb.setupGlyphOrder(glyph["glyph_order"])
    fb.setupCharacterMap(glyph["cmap"])
    fb.setupGlyf(glyph["glyphs"])
    fb.setupHorizontalMetrics(glyph["metrics"]) # The default advancing width
    fb.setupHorizontalHeader(ascent=ascent, descent=-descend)

    fb.setupOS2(
        sTypoAscender=ascent,
        sTypoDescender=-descend,
        usWinAscent=ascent,
        usWinDescent=descend,
        sxHeight=x_height,
        sCapHeight=cap_height,
        fsType=0, # 0: Installable embedding, 2: Restricted License embedding, 4: Preview & Print embedding, 8: Editable embedding
        fsSelection=0x40, # "bold italic": 0x21, "bold": 0x20, "italic": 0x01, "regular": 0x40
        usWeightClass=500, # Medium weight, as our font is kind of thick by design
        usWidthClass=5 # Normal width, we won't have condensed or expanded width
    )

    license_desc: list[str] = about.__license__.splitlines()
    license_info: str = license_desc[len(license_desc) - 1]

    info: FontInfo = font_export["info"]
    font_naming: list[str] = [family_name]

    # Font may have variant name as: Seafront <name>
    descriptor: str | None = font_data.get("font-desc-name")
    if descriptor is not None and isinstance(descriptor, str):
        font_naming.append(descriptor)

    # The full name without foundry prefix, read as the display name often
    public_name: str = ' '.join(font_naming)

    # BTE Seafront <name>
    font_naming.insert(0, info["foundry-name"])
    formal_name: str = ' '.join(font_naming)

    # BTE Seafront <name> Regular
    font_naming.append(font_export["style"])
    packed_name: str = ' '.join(font_naming)

    # BTE-Seafront-<name>-Regular
    post_script: str = packed_name.replace(' ', '-')

    # BTE Seafront <name> Regular Version 1.000
    identifier: str | None = font_export["info"].get("version")
    if identifier is not None and isinstance(identifier, str):
        font_version = identifier
    else:
        font_version = font_data["design-version"]
    font_naming.append(font_version)
    unique_name: str = ' '.join(font_naming)

    name_strings: dict[str, str] = {
        # (nameID 0)
        "copyright": about.__copyright__,
        "familyName": formal_name,  # (nameID 1)
        "styleName": font_export["style"],  # (nameID 2)
        "uniqueFontIdentifier": unique_name,  # (nameID 3)
        "fullName": packed_name,  # (nameID 4)
        "version": font_version,  # (nameID 5)
        "psName": post_script,  # (nameID 6)
        # "trademark": "", # (nameID 7)
        "manufacturer": info["manufacturer"],  # (nameID 8)
        "designer": font_data["design-credits"],  # (nameID 9)
        "description": info["description"],  # (nameID 10)
        "vendorURL": info["vendor-url"],  # (nameID 11)
        "designerURL": info["designer-url"],  # (nameID 12)
        "licenseDescription": about.__license__,  # (nameID 13)
        "licenseInfoURL": license_info,  # (nameID 14)
        # (nameID 15 reserved)
        "typographicFamily": public_name,  # (nameID 16)
        "typographicSubfamily": font_export["style"],  # (nameID 17)
        "compatibleFullName": packed_name,  # (nameID 18)
        "sampleText": font_data["sample-text"],  # (nameID 19)
    }

    # Prepare .fea feature file as raw text lines
    fea_full: list[str] = []
    afdko_parent = FONT_DIR / font_data["features-afdko"]["parent-afdko"]

    if afdko_parent.is_file():
        log(v, f"Exporting parent features file (AFDKO) for: {afdko_parent.name}")
        includes: list[str] = font_data["features-afdko"]["includes-fea"]
        features: str = afdko_parent.read_text()
        fea_full.append(features)

        # Include font specific features file
        for fea_path in includes:
            with as_file(FONT_DIR / fea_path) as fea_include_path:
                fea_full.append(f"include({fea_include_path})")
        fea_full.append("")

    # Collect anchoring features
    for block_name, feature in anchors_feature.items():
        log(v, f"Exporting anchoring feature for: {block_name}")
        anchor_txt = export_anchor_features(
            feature,
            upm=units_per_em,
            pixel_size=pixel_size,
        )
        log(v, anchor_txt)
        fea_full.append(anchor_txt)

    # Collect kerning features
    for block_name, kerning_path in kerning_feature.items():
        log(v, f"Exporting kerning feature for: {block_name}")
        kerning = load_yaml(kerning_path)
        fea_txt = export_kerning_feat(
            kerning["groups"],
            kerning["kerning"],
            upm=units_per_em,
            pixel_size=pixel_size,
        )
        log(v, fea_txt)
        fea_full.append("feature kern {")
        fea_full.append(fea_txt)
        fea_full.append("} kern;")

    final_features_string = '\n'.join(fea_full)

    fb.addOpenTypeFeatures(final_features_string)

    fb.setupNameTable(name_strings)

    fb.setupPost(
        formatType=3.0,
        italicAngle=italic_angle,
        underlinePosition=underline_position,
        underlineThickness=underline_thickness,
        isFixedPitch=0,
        minMemType42=0,
        maxMemType42=0,
        minMemType1=0,
        maxMemType1=0,
    )
    log(v, "Written Metadata: ", name_strings)
    log(v, "Result glyphs orders: ", glyph["glyph_order"])

    export_file = export_fn(post_script)
    fb.save(export_file)

    print(f"\033[32mWrote: {export_file}")