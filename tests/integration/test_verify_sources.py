# Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
# with Reserved Font Name "BTE Seafront".
# Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).
#
# This Font Software is licensed under the SIL Open Font License, Version 1.1.
# This license is available with a FAQ at:
# https://openfontlicense.org
"""\
Integration test for design projects .pbm bitmap generations.
"""
from pathlib import Path
from typing import Literal

import subprocess
import pytest
import yaml

import seafront.font as font
from scripts.ci.file_changes import compare_files, get_disk_files, FileChanges
from seafront.core.design import saves
from seafront.model.font import FontYML
from seafront.unicode import load_unicode_blocks, UnicodeBlock

MIN_ASEPRITE_API: int = 23


def check_aseprite(script: Path) -> int:
    """
    Check Aseprite app by running a simple script that print :code:`app.apiVersion`

    :param script: Script file location as a temp Path
    :return: Aseprite API version
    """
    script.write_text("print(app.apiVersion)\n", encoding="utf-8")
    try:
        result = subprocess.run(
            ["aseprite", "--batch", "--script", script],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        api = int(result.stdout.strip())
    except ValueError, OSError, subprocess.TimeoutExpired:
        pytest.skip("Aseprite scripting API is unavailable")
    else:
        if result.returncode != 0 or not result.stdout.strip():
            pytest.skip("Aseprite scripting API is unavailable")
        return api


def get_unicode_tests():
    """
    Retrieve snapshot of our projects before either tests touches them.

    * :code:`block`: :class:`UnicodeBlock`
    * :code:`families`: List of family names configured in font.yml
    * :code:`block_files`: Flatten files data inside the block directory (:class:`bytes`)

    :return: tuples as :meth:`pytest.param` list.
    """
    test_blocks: list[tuple[UnicodeBlock, list[str], dict[str, bytes]]] = []

    with (font.project_yml().open(encoding="utf-8") as io,
          font.font_yml().open(encoding="utf-8") as fp):

        config: FontYML = yaml.safe_load(fp)
        projects: dict[Literal["blocks"], list[str]] = yaml.safe_load(io)
        families: list[str] = list(config["typeface"]["family"])
        unicodes: dict[str, UnicodeBlock] = load_unicode_blocks()

        for block_name in projects["blocks"]:
            block = font.project_root(block_name)

            assert block.is_dir(), f"Configured block '{block_name}' not found"
            assert block_name in unicodes, f"Invalid Unicode block name '{block_name}'"
            block_files: dict[str, bytes] = get_disk_files(block)

            test_blocks.append(pytest.param(
                unicodes[block_name],
                families,
                block_files,
                id=block_name)
            )

    assert test_blocks, "No design projects found."
    return test_blocks


def filter_pbm_files(files: dict[str, bytes]) -> dict[str, bytes]:
    return { path: data for path, data in files.items() if path.endswith(".pbm") }


@pytest.mark.design
@pytest.mark.parametrize("block, families, block_files", get_unicode_tests())
def test_verify_source_equality(block,
                                families,
                                block_files,
                                tmp_path: Path,
                                monkeypatch: pytest.MonkeyPatch):
    """
    Test to verify Aseprite & PNG sources integrity, that
    both must generate the same bitmap .pbm files.

    :param tmp_path: pytest temp path
    :param monkeypatch: pytest mocking helper
    """
    # Aseprite is required for this integration test.
    api_version = check_aseprite(tmp_path / "aseprite_check.lua")
    assert api_version >= MIN_ASEPRITE_API, f"Unsupported Aseprite API versions, requires >= {MIN_ASEPRITE_API}"

    test_aseprite_root: Path = tmp_path / "aseprite"
    test_png_root: Path = tmp_path / "png"

    # Recreate the projects in two independent temporary directories.
    for path, data in block_files.items():
        file: Path = Path(path)
        if "glyphs" in file.parts or "profile" in file.parts:
            continue

        for root in (test_aseprite_root, test_png_root):
            destination = root / block["name"] / file
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)

    with monkeypatch.context() as patch:
        # Generate PBMs from Aseprite.
        patch.setattr(font, "PROJECT_DIR", test_aseprite_root)
        saves.aseprite([block], pbm=True, verbose=False)
        aseprite_disk: dict[str, bytes] = get_disk_files(test_aseprite_root)
        aseprite_generated: dict[str, bytes] = filter_pbm_files(aseprite_disk)

        # Generate PBMs from PNG.
        patch.setattr(font, "PROJECT_DIR", test_png_root)
        saves.png_image([block], set(families), pbm=True, verbose=False)
        png_disk: dict[str, bytes] = get_disk_files(test_png_root)
        png_generated: dict[str, bytes] = filter_pbm_files(png_disk)

        # The two source formats must produce identical PBM files.
        # We're expecting NO difference between generated files
        changes: FileChanges[str] = compare_files(png_generated, aseprite_generated)

        assert not changes["added"], (f"Aseprite generated {len(changes["added"])} "
                                      f"PBM files that PNG sheets did not generate.")

        assert not changes["unsync"], (f"PNG sheets generated {len(changes["unsync"])} "
                                       f"PBM files that Aseprite did not generate.")

        assert not changes["modified"], (f"Aseprite and PNG sheets generated different "
                                         f"{len(changes["modified"])} PBM contents.")

    # Final check that the committed files inside repo must be the same as their generated sources.
    repo_disk: dict[str, bytes] = get_disk_files(font.project_root(block["name"]), block["name"])
    repo_files: dict[str, bytes] = filter_pbm_files(repo_disk)
    repo_changes: FileChanges[str] = compare_files(repo_files, aseprite_generated)

    assert not repo_changes["added"], (f"The source generated {len(repo_changes["added"])} "
                                       f"PBM files that are missing from the repository.")

    assert not repo_changes["unsync"], (f"The repository contains {len(repo_changes["unsync"])} "
                                        f"PBM files that are not generated by the source.")

    assert not repo_changes["modified"], (f"Repository has {len(repo_changes["modified"])} "
                                          f"PBM files differ from the PBM files generated by the source.")
