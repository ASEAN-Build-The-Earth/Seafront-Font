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
from fontTools.fontBuilder import FontBuilder
from importlib.resources import as_file
from importlib.resources.abc import Traversable

from sys import stderr
from .glyphs import build_glyph
from seafront.unicode import load_unicode_blocks
from seafront.model.glyphs import prepare_glyphs
from seafront.model.anchors import parse_glyph_anchors
from seafront.afdko.anchors import export_anchor_features
from seafront.afdko.kerning import export_kerning_feat

import seafront.__about__ as about
import seafront.font as font
import yaml

def log(verbose=False, *args):
    if verbose:
        print(*args)


def load_yaml(file: Traversable):
    with file.open(encoding="utf-8") as fp:
        return yaml.safe_load(fp)


def export(typeface, profile, output):
    v: bool = profile["verbose"]
    pixel_size: int = profile["scale"]
    ascender: int = profile["accent"]["ascender"]  # 35 pixel
    descender: int = profile["accent"]["descender"]  # 15 pixel
    units_per_em: int = (ascender + descender) * pixel_size  # 2500

    # Guard UPM, need to fall within ± 4095 for "safety"
    if units_per_em > 4096:
        print(f"{'\033[31m'}Font unit incompatible- scale too large.\n"
              f"Please either lower your scale or step down the accent{'\033[0m'}", file=stderr)
        return

    print(f"Default width: {units_per_em // 2}")
    print(f"MAX width: {profile["typography"]["maximum-width"] * pixel_size}")

    family_name = typeface["info"]["family"]
    project = load_yaml(font.project_yml())
    blocks = load_unicode_blocks()
    glyph = prepare_glyphs(units_per_em // 2)  # Defaulting half an em per glyph for .notdef
    built = 0

    anchors_feature: dict = {}
    kerning_feature: dict = {}

    try:
        for block_id in project["blocks"]:
            face = typeface["face"]

            with as_file(font.project_glyphs(block_id, family_name, face)) as glyph_dir:
                if not glyph_dir.exists():
                    raise ValueError(
                        f"Glyphs for '{block_id}' with style '{face}' referenced in project.yml "
                        f"does not exist for exporting at: \n'{glyph_dir}'"
                    )

            anchors_yml: Traversable = font.anchors_yml(block_id)
            kerning_yml: Traversable = font.kerning_yml(block_id)

            def load_anchors():
                glyph_anchors = parse_glyph_anchors(load_yaml(anchors_yml))
                anchors_feature[block_id] = glyph_anchors
                return glyph_anchors

            # Anchors positioning required to adjust each glyph if configured
            anchors = load_anchors() if anchors_yml.is_file() else None

            for pbm in sorted(glyph_dir.glob("glyph_*.pbm")):
                index = int(pbm.stem.split("_")[1])
                codepoint = int(blocks[block_id]["start"]) + (index - 1)
                glyph_profile: dict = {
                    "codepoint": codepoint,
                    "pixel_size": pixel_size,
                    "anchors": anchors,
                    "verbose": v,
                    "typeface": face,
                    "typography": profile["typography"]
                }
                log(v, f"Building Glyph index: {index} (U+{codepoint:04X})")
                built += build_glyph(pbm, glyph, glyph_profile, profile["accent"])

            # Post build: kerning feature is processed purely under OpenType feature
            if kerning_yml.is_file():
                kerning_feature[block_id] = kerning_yml
    except Exception as e:
        print(f"{'\033[93m'}{e}{'\033[0m'}", file=stderr)
    if built == 0:
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

    info: dict[str, str] = typeface["info"]
    license_desc: list[str] = about.__license__.splitlines()
    license_info: str = license_desc[len(license_desc) - 1]
    strings_list: list[str] = [info["foundry-name"], family_name]
    family_name = ' '.join(strings_list) # BTE Seafront

    strings_list.append(typeface["style"])
    full_name: str = ' '.join(strings_list) # BTE Seafront Regular

    postscript: str = full_name.replace(' ', '-')

    strings_list.append(info["version"])
    unique_string: str = ' '.join(strings_list) # BTE Seafront Regular Version 1.000

    name_strings: dict[str, str] = {
        # (nameID 0)
        "copyright": about.__copyright__,
        "familyName": family_name, # (nameID 1)
        "styleName": typeface["style"], # (nameID 2)
        "uniqueFontIdentifier": unique_string, # (nameID 3)
        "fullName": full_name, # (nameID 4)
        "version": info["version"], # (nameID 5)
        "psName": postscript, # (nameID 6)
        # "trademark": "", # (nameID 7)
        "manufacturer": info["manufacturer"], # (nameID 8)
        "designer": info["designer"], # (nameID 9)
        "description": info["description"], # (nameID 10)
        "vendorURL": info["vendor-url"], # (nameID 11)
        "designerURL": info["designer-url"], # (nameID 12)
        "licenseDescription": about.__license__, # (nameID 13)
        "licenseInfoURL": license_info, # (nameID 14)
        # (nameID 15 reserved)
        "typographicFamily": info["family"], # (nameID 16)
        "typographicSubfamily": typeface["style"], # (nameID 17)
        "compatibleFullName": full_name, # (nameID 18)
        "sampleText": info["sample-text"], # (nameID 19)
    }

    # Prepare .fea feature file as raw text lines
    fea_full: list[str] = []

    # Collect anchoring features
    for block_id, anchors in anchors_feature.items():
        log(v, f"Exporting anchoring feature for: {block_id}")
        anchor_txt = export_anchor_features(
            anchors,
            upm=units_per_em,
            pixel_size=pixel_size,
        )
        log(v, anchor_txt)
        fea_full.append(anchor_txt)

    # Collect kerning features
    for block_id, path in kerning_feature.items():
        log(v, f"Exporting kerning feature for: {block_id}")
        kerning = load_yaml(path)
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
    filename = f"{postscript}.ttf" if output is None else \
        (output if str(output).endswith(".ttf") else f"{output}.ttf")
    fb.save(filename)
    print(f"Wrote {filename}")