# Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
# with Reserved Font Name "BTE Seafront".
# Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).
#
# This Font Software is licensed under the SIL Open Font License, Version 1.1.
# This license is available with a FAQ at:
# https://openfontlicense.org
"""\
Test AFDKO features we used inside :code:`seafront.afdko`
"""
from typing import NamedTuple, TypedDict, LiteralString

from fontTools.feaLib.ast import *
from io import StringIO

import seafront.afdko.kerning as test_kerning
import pytest


def _clean_text(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


@pytest.mark.parametrize("statement", [
    pytest.param("lookupflag 0;"),
    pytest.param("lookupflag RightToLeft;"),
    pytest.param("lookupflag IgnoreBaseGlyphs;"),
    pytest.param("lookupflag IgnoreLigatures;"),
    pytest.param("lookupflag IgnoreMarks;"),
    pytest.param("lookupflag RightToLeft MarkAttachmentType @MarkSet1;"),
    pytest.param("lookupflag UseMarkFilteringSet [uni0001 uni0002 uni0003];")])
def test_lookupflag(statement):
    ast_parser = test_kerning._create_statement_parser(StringIO(statement))
    ast_parsed = ast_parser.parse_lookupflag_()
    assert isinstance(ast_parsed, LookupFlagStatement)
    assert ast_parsed.asFea().strip() == statement.strip()


@pytest.mark.parametrize("expected, name, glyphs, anchor", [
    pytest.param("markClass [uni0E31 uni0E34 uni0E35] <anchor -96 512> @MarkClass1;",
                 "MarkClass1", ["uni0E31", "uni0E34", "uni0E35"], (-96, 512), id="Definition 1")])
def test_mark_class(expected, name, glyphs, anchor):
    x, y = anchor
    glyph_names = [GlyphName(glyph) for glyph in glyphs]
    mark_class = MarkClass(name)
    definition = MarkClassDefinition(mark_class, Anchor(x, y), GlyphClass(glyph_names))
    mark_class.addDefinition(definition)

    assert mark_class.asFea().strip() == expected.strip()


@pytest.mark.parametrize("expected, base, marks", [
    pytest.param("pos base [uni0E34 uni0E35] <anchor 320 512> mark @MarkClass1;",
                 ["uni0E34", "uni0E35"], [((320, 512), "MarkClass1")], id="1 Anchor"),
    pytest.param("pos base [uni0E31] <anchor 512 320> mark @MarkClass1 <anchor 512 0> mark @MarkClass2;",
                 ["uni0E31"], [((512, 320), "MarkClass1"), ((512, 0), "MarkClass2")], id="2 Anchors")])
def test_pos_mark(expected, base, marks):
    glyphs = [ GlyphName(glyph) for glyph in base ]
    anchors = [ (Anchor(x, y), MarkClass(name)) for (x, y), name in marks ]
    definition = MarkBasePosStatement(GlyphClass(glyphs), anchors)
    compiled_text = _clean_text(definition.asFea())

    assert " ".join(compiled_text) == expected.strip()


@pytest.mark.parametrize("expected, mark, marks", [
    pytest.param("pos mark [uni0E34 uni0E35] <anchor 320 512> mark @MarkClass1;",
                 ["uni0E34", "uni0E35"], [((320, 512), "MarkClass1")], id="1 Anchor"),
    pytest.param("pos mark [uni0E31] <anchor 512 320> mark @MarkClass1 <anchor 512 0> mark @MarkClass2;",
                 ["uni0E31"], [((512, 320), "MarkClass1"), ((512, 0), "MarkClass2")], id="2 Anchors")])
def test_mark_mark(expected, mark, marks):
    glyphs = [ GlyphName(glyph) for glyph in mark ]
    anchors = [ (Anchor(x, y), MarkClass(name)) for (x, y), name in marks ]
    definition = MarkMarkPosStatement(GlyphClass(glyphs), anchors)
    compiled_text = _clean_text(definition.asFea())

    assert " ".join(compiled_text) == expected.strip()


class _Group(NamedTuple):
    name: str
    glyphs: list[str]


class _Pos[T: int | None](NamedTuple):
    cls: str | list[str]
    pos: T


class _Pair[L, R](NamedTuple):
    l: _Pos[L]
    r: _Pos[R]


class LookupTest(TypedDict):
    name: LiteralString
    expected: LiteralString
    classes: list[_Group]
    statements: list[_Pair[int | None, int]]


TEST_LOOKUPS: list[LookupTest] = [{
    "name": "TestKernLookup1",
    "expected": """\
lookup TestKernLookup1 {
    lookupflag 0;
    @group.1 = [uni0E50 uni0E51];
    @group.2 = [uni0E54 uni0E55];
    pos [uni0E40] @group.1 <0 0 -64 0>;
    pos [uni0E50] @group.2 <0 0 -32 0>;
} TestKernLookup1;
    """,
    "classes": [
        _Group(name="group.1", glyphs=["uni0E50", "uni0E51"]),
        _Group(name="group.2", glyphs=["uni0E54", "uni0E55"])],
    "statements": [
        _Pair(l=_Pos(cls=["uni0E40"], pos=None), r=_Pos(cls="group.1", pos=-64)),
        _Pair(l=_Pos(cls=["uni0E50"], pos=None), r=_Pos(cls="group.2", pos=-32))]
}, {
    "name": "TestKernLookup2",
    "expected": """\
lookup TestKernLookup2 {
    lookupflag 0;
    @group.1 = [uni0E34 uni0E35];
    @group.2 = [uni0E54 uni0E55];
    pos [uni0E40] <0 0 -128 0> @group.1 <0 0 -64 0>;
    pos @group.2 <0 0 -64 0> [uni0E50 uni0E56] <0 0 -32 0>;
} TestKernLookup2;
    """,
    "classes": [
        _Group(name="group.1", glyphs=["uni0E34", "uni0E35"]),
        _Group(name="group.2", glyphs=["uni0E54", "uni0E55"])],
    "statements": [
        _Pair(l=_Pos(cls=["uni0E40"], pos=-128), r=_Pos(cls="group.1", pos=-64)),
        _Pair(l=_Pos(cls="group.2", pos=-64), r=_Pos(cls=["uni0E50", "uni0E56"], pos=-32))]
}]


@pytest.mark.parametrize("name, expected, classes, statements", [
    pytest.param(*lookups.values(), id=lookups["name"]) for lookups in TEST_LOOKUPS])
def test_pos_lookup(name: LiteralString,
                    expected: LiteralString,
                    classes: list[_Group],
                    statements: list[_Pair[int | None, int]]):

    features = LookupBlock(name) # lookup TestKernLookup {
    features.statements.append(LookupFlagStatement(0)) # lookupflag 0;

    groups = {
        group.name: GlyphClassDefinition(group.name, GlyphClass([
            GlyphName(glyph) for glyph in group.glyphs
        ])) for group in classes
    }
    # @class = [glyph1 glyph2 ....];
    features.statements.extend(groups.values())

    def get_glyph_class(glyph):
        if isinstance(glyph, str):
            assert glyph in groups
            return GlyphClassName(groups[glyph])
        else:
            assert isinstance(glyph, list)
            return GlyphClass([ GlyphName(glyf) for glyf in glyph ])

    def get_value(value):
        return ValueRecord(0, 0, value, 0) if value is not None else None

    for pair in statements:
        left_cls = get_glyph_class(pair.l.cls)
        left_pos = get_value(pair.l.pos)
        right_cls = get_glyph_class(pair.r.cls)
        right_pos = get_value(pair.r.pos)

        assert right_pos is not None
        if left_pos is None:
            pos = PairPosStatement(left_cls, right_pos, right_cls, None)
        else:
            pos = PairPosStatement(left_cls, left_pos, right_cls, right_pos)

        features.statements.append(pos)

    compiled_text: list[str] = _clean_text(features.asFea())
    expected_text: list[str] = _clean_text(expected)

    assert len(compiled_text) == len(expected_text)

    for i, line in enumerate(expected_text):
        assert compiled_text[i] == line
