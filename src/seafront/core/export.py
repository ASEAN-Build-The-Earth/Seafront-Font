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
from importlib.resources import as_file, files
from importlib.resources.abc import Traversable

from sys import stderr
from .glyphs import build_glyph
from ..font import FONT_DIR
from ..unicode import load_unicode_blocks
from ..model.glyphs import prepare_glyphs
from ..model.anchors import parse_glyph_anchors
from ..afdko.anchors import export_anchor_features
from ..afdko.kerning import export_kerning_feat

import seafront.__about__ as about
import seafront.font as font
import yaml

def log(verbose=False, *args):
    if verbose:
        print(*args)


def load_yaml(file: Traversable):
    with file.open(encoding="utf-8") as fp:
        return yaml.safe_load(fp)


def export(font_export, profile, export_fn):
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

    family_name = font_export["info"]["family"]
    blocks = load_unicode_blocks()
    glyph = prepare_glyphs(units_per_em // 2)  # Defaulting half an em per glyph for .notdef
    built = 0

    anchors_feature: dict = {}
    kerning_feature: dict = {}

    try:
        for block_id in font_export["unicode-blocks"]:
            face = font_export["face"]

            with as_file(font.project_glyphs(block_id, family_name, face)) as glyph_dir:
                if not glyph_dir.exists():
                    error = (
                        f"Glyphs for '{block_id}' with style '{face}' referenced in project.yml "
                        f"does not exist for exporting at: \n'{glyph_dir}'"
                    )
                    print(f"{'\033[93m'}{error}{'\033[0m'}", file=stderr)
                    continue

            anchors_yml: Traversable = font.anchors_yml(block_id)
            kerning_yml: Traversable = font.kerning_yml(block_id)

            def load_anchors():
                glyph_anchors = parse_glyph_anchors(load_yaml(anchors_yml))
                anchors_feature[block_id] = glyph_anchors
                return glyph_anchors

            # Kerning feature is processed purely under OpenType feature
            if kerning_yml.is_file():
                kerning_feature[block_id] = kerning_yml

            # Anchors positioning required to adjust each glyph if configured
            anchors = load_anchors() if anchors_yml.is_file() else None
            glyph_profile: dict = {
                "pixel_size": pixel_size,
                "anchors": anchors,
                "verbose": v,
                "typeface": face,
                "typography": profile["typography"]
            }

            for pbm in sorted(glyph_dir.glob("glyph_*.pbm")):
                index = int(pbm.stem.split("_")[1])
                codepoint: dict = { "codepoint": int(blocks[block_id]["start"]) + (index - 1) }
                log(v, f"Building Glyph index: {index} (U+{codepoint["codepoint"]:04X})")
                built += build_glyph(pbm, glyph, codepoint | glyph_profile, profile["accent"])

            # Check if extra features exist as glyphs config
            feat_glyphs = font.ext_glyphs_yml(block_id)

            if feat_glyphs.is_file():
                ext_glyph_yml = load_yaml(feat_glyphs)
                with as_file(font.project_glyphs(block_id, family_name, f"ext-{face}")) as ext_glyph_dir:
                    if not ext_glyph_dir.exists():
                        error = (
                            f"Extra glyphs for '{block_id}' required in profile/ext-glyphs.yml "
                            f"does not exist for exporting at: \n'{ext_glyph_dir.name}'"
                        )
                        print(f"{'\033[93m'}{error}{'\033[0m'}", file=stderr)
                        continue

                # Extra glyphs has user defined name
                def fn_ext_glyph_at(i) -> dict | None:
                    key = f"ext-{i:02X}"
                    if key in ext_glyph_yml["glyphs"]:
                        return ext_glyph_yml["glyphs"][key]
                    return None

                # Add all Extra glyphs
                for pbm in sorted(ext_glyph_dir.glob("glyph_*.pbm")):
                    index = int(pbm.stem.split("_")[1]) - 1
                    ext_glyph = fn_ext_glyph_at(index)
                    if not ext_glyph:
                        error = (
                            f"No definition found for Extra glyph at:\n{pbm}\n"
                            f"Expected key required in ext-glyph.yml: 'ext-{index:02X}': "
                        )
                        print(f"{'\033[93m'}{error}{'\033[0m'}", file=stderr)
                        continue

                    ext_profile: dict = {
                        "codepoint": ext_glyph["cmap"] if "cmap" in ext_glyph else None,
                        "glyph_name": ext_glyph["name"] if "name" in ext_glyph else None
                    }
                    log(v, f"Building Extra Glyph: {index} (EXT-{index:02X})")
                    built += build_glyph(pbm, glyph, glyph_profile | ext_profile, profile["accent"])
    except Exception as e:
        print(f"{'\033[93m'}Exception when collecting glyphs:\n{e}{'\033[0m'}", file=stderr)
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

    license_desc: list[str] = about.__license__.splitlines()
    license_info: str = license_desc[len(license_desc) - 1]

    info: dict[str, str] = font_export["info"]
    font_naming: list[str] = [family_name]

    # Font may have variant name as: Seafront <name>
    if isinstance(font_export["font-desc-name"], str) and font_export["font-desc-name"]:
        font_naming.append(font_export["font-desc-name"])

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
    font_naming.append(font_export["design-version"])
    unique_name: str = ' '.join(font_naming)

    name_strings: dict[str, str] = {
        # (nameID 0)
        "copyright": about.__copyright__,
        "familyName": formal_name,  # (nameID 1)
        "styleName": font_export["style"],  # (nameID 2)
        "uniqueFontIdentifier": unique_name,  # (nameID 3)
        "fullName": packed_name,  # (nameID 4)
        "version": font_export["design-version"],  # (nameID 5)
        "psName": post_script,  # (nameID 6)
        # "trademark": "", # (nameID 7)
        "manufacturer": info["manufacturer"],  # (nameID 8)
        "designer": font_export["design-credits"],  # (nameID 9)
        "description": info["description"],  # (nameID 10)
        "vendorURL": info["vendor-url"],  # (nameID 11)
        "designerURL": info["designer-url"],  # (nameID 12)
        "licenseDescription": about.__license__,  # (nameID 13)
        "licenseInfoURL": license_info,  # (nameID 14)
        # (nameID 15 reserved)
        "typographicFamily": public_name,  # (nameID 16)
        "typographicSubfamily": font_export["style"],  # (nameID 17)
        "compatibleFullName": packed_name,  # (nameID 18)
        "sampleText": font_export["sample-text"],  # (nameID 19)
    }

    # Prepare .fea feature file as raw text lines
    fea_full: list[str] = []
    afdko_parent = FONT_DIR / font_export["features-afdko"]["parent-afdko"]

    if afdko_parent.is_file():
        print(f"Exporting parent features file (AFDKO) for: {afdko_parent}")
        includes: list[str] = font_export["features-afdko"]["includes-fea"]
        features: str = afdko_parent.read_text()
        fea_full.append(features)

        # Include font specific features file
        for fea_path in includes:
            with as_file(FONT_DIR / fea_path) as fea_include_path:
                fea_full.append(f"include({fea_include_path})")
        fea_full.append("")

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
    log(v, "Result glyphs orders: ", glyph["glyph_order"])

    export_file = export_fn(post_script)
    fb.save(export_file)

    print(f"Wrote {export_file}")