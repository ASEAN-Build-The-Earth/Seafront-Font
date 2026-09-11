# Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
# with Reserved Font Name "BTE Seafront".
# Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).
#
# This Font Software is licensed under the SIL Open Font License, Version 1.1.
# This license is available with a FAQ at:
# https://openfontlicense.org
"""\
Paths constants for Seafront project
"""
from importlib.resources import files
from importlib.resources.abc import Traversable

ASSETS_DIR: Traversable = files("assets")
"""assets traversable root"""

SCRIPTS_DIR: Traversable = files("scripts")
"""scripts traversable root"""

FONT_DIR: Traversable = files("font")
"""font traversable root"""

PROJECT_DIR: Traversable = files("projects")
"""seafront projects root"""

SEAFRONT_DIR: Traversable = files("seafront")
"""seafront src root"""


def font_yml() -> Traversable:
    return FONT_DIR / "font.yml"


def project_yml() -> Traversable:
    return FONT_DIR / "project.yml"


def unicode_blocks_json() -> Traversable:
    return FONT_DIR / "unicode-blocks.json"


def project_root(block_name: str) -> Traversable:
    return PROJECT_DIR / block_name


def project_glyphs(block_name: str, family: str, style: str) -> Traversable:
    return PROJECT_DIR / block_name / "glyphs" / family / style


def project_export(block_name: str, family: str) -> Traversable:
    return PROJECT_DIR / block_name / "export" / family


def project_design(block_name: str, family: str) -> Traversable:
    return PROJECT_DIR / block_name / "design" / family


def anchors_yml(block_name: str) -> Traversable:
    return PROJECT_DIR / block_name / "profile" / "anchors.yml"


def kerning_yml(block_name: str) -> Traversable:
    return PROJECT_DIR / block_name / "profile" / "kerning.yml"


def ext_glyphs_yml(block_name: str) -> Traversable:
    return PROJECT_DIR / block_name / "profile" / "ext-glyphs.yml"