# Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
# with Reserved Font Name "BTE Seafront".
# Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).
#
# This Font Software is licensed under the SIL Open Font License, Version 1.1.
# This license is available with a FAQ at:
# https://openfontlicense.org
"""\
Serialized features helper
"""
from importlib.resources import as_file
from importlib.resources.abc import Traversable

from .kerning import export_kerning_feat
from .positioning import export_positioning_features
from ..model.positioning import parse_horizontal_kerning, PositioningProfile

import seafront.font as font
import fontTools.feaLib.ast as ast
import yaml


def dump_features(parent: str,
                  includes: str | list,
                  positioning_fea: dict[str, PositioningProfile],
                  kerning_feature: dict[str, Traversable],
                  *,
                  upm: int,
                  pixel_size: int,
                  debug: bool=False,
                  verbose: bool=False) -> str:
    """
    Generate positioning & kerning features as raw text string.

    :param parent: Parent feature file (path relative to /font) to begin the file.
    :param includes: Feature files to include post generation. (as :class:`ast.IncludeStatement`)
    :param positioning_fea: ALL parsed positioning features as :class:`PositioningProfile`
    :param kerning_feature: All :code:`kerning.yml` resource files as :class:`Traversable`
    :param upm: units-per-em
    :param pixel_size: Font pixel scaling size
    :param debug: Print debugging comment in the generated text
    :param verbose: Verbose logging
    :return: string
    """
    # Prepare .fea feature file as raw text lines
    fea_full: list[str] = []
    afdko_parent = font.FONT_DIR / parent
    fea_includes = []

    if afdko_parent.is_file():
        # log(v, f"Exporting parent features file (AFDKO) for: {afdko_parent.name}")
        features: str = afdko_parent.read_text()
        fea_full.append(features)

    if isinstance(includes, list):
        fea_includes.extend(includes)
    elif isinstance(includes, str):
        fea_includes.append(includes)

    # Collect anchoring features
    if debug and len(positioning_fea) > 0:
        fea_full.append(f"""\
# ============================================================
# START GENERATED POSITIONING FEATURES
# ============================================================
        """)

    for block_name, feature in positioning_fea.items():
        if verbose:
            print(f"Exporting anchoring feature for: {block_name}")

        for lookup in export_positioning_features(feature, upm=upm, pixel_size=pixel_size).values():
            if lookup is None:
                continue
            fea_full.append(lookup.asFea())

    if debug and len(positioning_fea) > 0:
        fea_full.append(f"""\
# ============================================================
# END GENERATED POSITIONING FEATURES
# ============================================================
        """)

    # Collect kerning features
    if debug and len(kerning_feature) > 0:
        fea_full.append(f"""\
# ============================================================
# START GENERATED KERNING FEATURES
# ============================================================
        """)
    for i, (block_name, kerning_path) in enumerate(kerning_feature.items()):
        if verbose:
            print(f"Exporting kerning feature for: {block_name}")
        with kerning_path.open(encoding="utf-8") as io:
            kerning_yml = yaml.safe_load(io)
            kerning = parse_horizontal_kerning(i, kerning_yml)
            fea_txt = export_kerning_feat(
                kerning,
                upm=upm,
                pixel_size=pixel_size,
            )
            if fea_txt is not None:
                fea_full.append(fea_txt.asFea())
    if debug and len(kerning_feature) > 0:
        fea_full.append(f"""\
# ============================================================
# END GENERATED KERNING FEATURES
# ============================================================
        """)

    # Include font specific features file
    for fea_path in fea_includes:
        with as_file(font.FONT_DIR / fea_path) as fea_include_path:
            ast_include = ast.IncludeStatement(fea_include_path)
            fea_full.append(ast_include.asFea())

    return '\n'.join(fea_full)