# Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
# with Reserved Font Name "BTE Seafront".
# Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).
#
# This Font Software is licensed under the SIL Open Font License, Version 1.1.
# This license is available with a FAQ at:
# https://openfontlicense.org
"""\
Test base asset images integrity against its optimized code counterpart.
"""
import pytest

from collections.abc import Callable
from pathlib import Path

from PIL import Image
from PIL.Image import Image as Sheet

from seafront.font import ASSETS_DIR
from seafront.generate import make_font_cell
from seafront.model.pilfont import seafront_16px_compact, seafront_16px_squared, SeafrontPilFont

BASE_FONT_CELL = "font-cell-64px.png"

BASE_SEAFRONT_UI_COMPACT = "seafront-16px-compact.png"

BASE_SEAFRONT_UI_SQUARED = "seafront-16px-squared.png"


def test_font_cell():
    """
    Test is the embedded font cell image is the same as its base asset counterpart.
    """
    base_file = ASSETS_DIR / BASE_FONT_CELL

    if not base_file.is_file():
        pytest.skip(f"Base file '{base_file.name}' not found to test against.")

    with base_file.open("rb") as io:
        base: Sheet = Image.open(io).convert("RGBA")
        actual: Sheet = make_font_cell() # Our embedded font cell image

        def msg(reason: str):
            return (f"Embedded font cell '{reason}' not match against '{base_file.name}'."
                    f"If the base file is updated, the embedded data should be updated too.")

        assert_image_equal(actual, base, msg)


@pytest.mark.parametrize("font_data, base_data", [
    pytest.param(seafront_16px_compact, BASE_SEAFRONT_UI_COMPACT, id="compact"),
    pytest.param(seafront_16px_squared, BASE_SEAFRONT_UI_SQUARED, id="squared")])
def test_seafront_ui(tmp_path: Path,
                     font_data: Callable[[], SeafrontPilFont],
                     base_data: str):
    """Test embedded UI font if it has the same bitmap image as its base asset counterpart."""
    seafront: SeafrontPilFont = font_data()
    base_file = ASSETS_DIR / base_data

    if not base_file.is_file():
        pytest.skip(f"Base file '{base_file.name}' not found to test against.")

    test_name: str = "font"

    seafront.save(str(tmp_path / f"{test_name}.pil"))

    saved_bitmap = None
    for ext in {".png", ".gif", ".pbm"}:
        saved = tmp_path / f"{test_name}{ext}"
        if saved.exists():
            saved_bitmap = saved

    assert saved_bitmap is not None, f"Saved bitmap file not found... expecting either .png, .gif, .pbm"

    with base_file.open("rb") as io, saved_bitmap.open("rb") as png:
        bitmap: Sheet = Image.open(io)
        actual: Sheet = Image.open(png)

        def msg(reason: str):
            return (f"Seafront UI Bitmap font '{reason}' not match against '{base_file.name}'."
                    f"If the base bitmap is updated, embedded data should be updated too.")

        assert_image_equal(actual, bitmap, msg)


def assert_image_equal(actual: Sheet,
                       expected: Sheet,
                       fn: Callable[[str], str]) -> None:
    assert actual.mode == expected.mode, fn("mode")
    assert actual.size == expected.size, fn("size")
    assert actual.tobytes() == expected.tobytes(), fn("bytes")