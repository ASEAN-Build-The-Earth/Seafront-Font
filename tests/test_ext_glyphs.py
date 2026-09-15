# Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
# with Reserved Font Name "BTE Seafront".
# Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).
#
# This Font Software is licensed under the SIL Open Font License, Version 1.1.
# This license is available with a FAQ at:
# https://openfontlicense.org
"""\
Test extra glyph (ext-glyphs.yml) parsing
"""
import yaml
from seafront.model.glyphs import parse_extra_glyphs
from seafront.model.glyphs import ExtraGlyph

TEST_TEXT_1 = """\
column: 3
glyphs:
  - "uni0E0D.less"
  - "uni0E0E.short"
  - "uni0E0F.short"
"""


def test_shorthand_list():
    test_yaml = yaml.safe_load(TEST_TEXT_1)
    extra_glyphs = parse_extra_glyphs(test_yaml)
    expected = [
        ExtraGlyph(name="uni0E0D.less", cmap=None),
        ExtraGlyph(name="uni0E0E.short", cmap=None),
        ExtraGlyph(name="uni0E0F.short", cmap=None)
    ]

    assert extra_glyphs["column"] == 3
    assert len(extra_glyphs["glyphs"]) == len(expected)
    for i, glyph in enumerate(extra_glyphs["glyphs"]):
        assert glyph == expected[i]

TEST_TEXT_2 = """\
column: 6
glyphs:
  ext-00: "uni0E0D.less"
  ext-02: "uni0E0F.short"
  ext-01: "uni0E0E.short"
"""


def test_shorthand_name():
    test_yaml = yaml.safe_load(TEST_TEXT_2)
    extra_glyphs = parse_extra_glyphs(test_yaml)
    expected = [
        ExtraGlyph(name="uni0E0D.less", cmap=None),
        ExtraGlyph(name="uni0E0E.short", cmap=None),
        ExtraGlyph(name="uni0E0F.short", cmap=None)
    ]

    assert extra_glyphs["column"] == 6
    assert len(extra_glyphs["glyphs"]) == len(expected)
    for i, glyph in enumerate(extra_glyphs["glyphs"]):
        assert glyph == expected[i]

TEST_TEXT_3 = """\
glyphs:
  - name: "uni0E0D.less"
    cmap: "uni0E0D"
  - name: "uni0E0E.short"
    cmap: "U+0E0E"
  - name: "uni0E0F.short"
    cmap: 3599
"""


def test_cmap():
    test_yaml = yaml.safe_load(TEST_TEXT_3)
    extra_glyphs = parse_extra_glyphs(test_yaml)
    expected = [
        ExtraGlyph(name="uni0E0D.less", cmap=3597),
        ExtraGlyph(name="uni0E0E.short", cmap=3598),
        ExtraGlyph(name="uni0E0F.short", cmap=3599)
    ]

    assert extra_glyphs["column"] == 16
    assert len(extra_glyphs["glyphs"]) == len(expected)
    for i, glyph in enumerate(extra_glyphs["glyphs"]):
        assert glyph == expected[i]

    print(extra_glyphs)