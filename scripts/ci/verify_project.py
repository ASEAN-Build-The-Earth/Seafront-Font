#!/usr/bin/env python3
# Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
# with Reserved Font Name "BTE Seafront".
# Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).
#
# This Font Software is licensed under the SIL Open Font License, Version 1.1.
# This license is available with a FAQ at:
# https://openfontlicense.org
r""" verify_project.py

Commandline script for workflow CI/CD verification
"""
import argparse
from importlib.resources.abc import Traversable
from pathlib import Path, PurePosixPath
from typing import Literal, Iterator

import yaml
from git import Repo

from .verification import VerificationReport, Source, FileChanges, is_synced
from seafront.core.design import saves
from seafront.font import font_yml, project_root
from seafront.model.font import FontYML
from seafront.model.glyphs import EXT_PREFIX
from seafront.unicode import load_unicode_blocks, UnicodeBlock


def get_changed_files(
    repo: Repo,
    base: str,
    head: str,
) -> list[str | None]:
    """Return files changed between two commits."""
    base_commit = repo.commit(base)
    head_commit = repo.commit(head)

    return [
        diff.b_path if diff.b_path else diff.a_path
        for diff in base_commit.diff(head_commit)
    ]


def project_from_path(path: str | None) -> str | None:
    """
    Return the Unicode project name from a project path,
    if a path is under /projects directory.
    """
    if path is None:
        return None

    parts = PurePosixPath(path).parts

    if len(parts) < 2 or parts[0] != "projects":
        return None

    return parts[1]


def determine_source(
    block_name: str,
    changed_files: list[str | None],
) -> Source | None:
    """Determine the authoritative source for a project."""

    prefix: str = f"projects/{block_name}/"

    files: list[str | None] = [
        path for path in changed_files
        if isinstance(path, str) and path.startswith(prefix)
    ]

    has_aseprite: bool = (
        f"{prefix}design.aseprite" in files
        or f"{prefix}{EXT_PREFIX}design.aseprite" in files
    )

    has_png: bool = any(
        isinstance(path, str)
        and path.startswith(f"{prefix}design/")
        and path.endswith(".png")
        for path in files
    )

    has_pbm: bool = any(
        isinstance(path, str)
        and path.startswith(f"{prefix}glyphs/")
        and path.endswith(".pbm")
        for path in files
    )

    # Primary source are aseprite files
    if has_aseprite:
        return Source.ASE

    # Otherwise PNG is the secondary source
    if has_png:
        return Source.PNG

    # PBM could be changed without ase/png
    # which we will have to flag it as missing source
    if has_pbm:
        return Source.PBM

    return None


def get_tree_files(repo: Repo, revision: str, root: str) -> dict[str, bytes]:
    """Read files under a path from a Git tree."""

    commit = repo.commit(revision)
    result: dict[str, bytes] = {}

    if commit.tree is None:
        return result

    def iter_tree[T](tree: Iterator[T]):
        """Generic helper to yield proper type hints [T] tree"""
        for item in tree:
            yield item

    for blob in iter_tree(commit.tree.traverse()):
        if isinstance(blob, tuple):
            continue

        if blob.type != "blob" or blob.path is None:
            continue

        if (path := Path(blob.path)) and path.is_relative_to(root):
            result[str(path)] = blob.data_stream.read()

    return result


def get_disk_files(directory: Traversable, root: str) -> dict[str, bytes]:
    """
    Read files under a filesystem directory, within a root path.

    :param directory: Disk directory to traverse
    :param root: Root path (posix)
    :return: Dict of relative path names inside root, map to its bytes content.
    """
    result: dict[str, bytes] = {}

    if not directory.is_dir():
        return result

    def recursive_iterdir(index: Traversable,
                          parent: str | None=None) -> Iterator[tuple[str, Traversable]]:
        for child in index.iterdir():
            steps: str = child.name if (parent is None) else f"{parent}/{child.name}"

            yield steps, child
            if child.is_dir():
                yield from recursive_iterdir(child, steps)

    for (path, file) in recursive_iterdir(directory):
        if not file.is_file():
            continue

        result[f"{root}/{path}"] = file.read_bytes()

    return result


def compare_files(
    actual: dict[str, bytes],
    expected: dict[str, bytes],
) -> FileChanges:
    """
    Compare the PR HEAD tree against the canonical generated tree.

    :param actual: /projects tree from the PR HEAD.
    :param expected: /projects tree after applying generated files
                     from the determined source.
    :returns: file changes data
    """
    actual_paths = set(actual)
    expected_paths = set(expected)

    added = expected_paths - actual_paths
    unsync = actual_paths - expected_paths

    modified = { path for path in actual_paths
                 & expected_paths if actual[path] != expected[path] }

    return {
        "added": added,
        "unsync": unsync,
        "modified": modified
    }


def verify_project(
    repo: Repo,
    head: str,
    block: UnicodeBlock,
    source: Literal[Source.ASE, Source.PNG],
    families: list[str],
    *,
    verbose: bool,
) -> FileChanges:
    """
    Generate project files and compare them with HEAD.

    Files will be modified/added by the source (parameter)

    :return: Modification result as :class:`FileChanges` against HEAD
    """

    project_prefix = f"projects/{block["name"]}"
    original = get_tree_files(repo, head, project_prefix)

    if source is Source.PNG:
        saves.png_image([block], set(families), ase=True, pbm=True, verbose=verbose)
    elif source is Source.ASE:
        saves.aseprite([block], png=True, pbm=True, verbose=verbose)
    else:
        raise ValueError(
            f"Cannot synchronize project {block["name"]!r} "
            f"from source {source.value!r}"
        )

    # Newly saved
    actual = get_disk_files(
        project_root(block["name"]),
        project_prefix,
    )

    return compare_files(original, actual)


def log_changes(source: Source,
                changes: FileChanges,
                *, verbose: bool) -> None:
    print(f"Source: {source.value}")

    if is_synced(changes):
        print("Status: SYNCED")
        return

    print("Status: OUT OF SYNC")

    if changes["added"]:
        print("Added", end="")
        if verbose:
            print(f" ({len(changes["added"])} files):")
            for path in sorted(changes["added"]):
                print(f"  {path}")
        else:
            print(f": {len(changes["added"])} files")

    if changes["unsync"]:
        print("Unsynced", end="")
        if verbose:
            print(f" ({len(changes["unsync"])} files):")
            for path in sorted(changes["unsync"]):
                print(f"  {path}")
        else:
            print(f": {len(changes["unsync"])} files")

    if changes["modified"]:
        print("Changed", end="")
        if verbose:
            print(f" ({len(changes["modified"])} files):")
            for path in sorted(changes["modified"]):
                print(f"  {path}")
        else:
            print(f": {len(changes["modified"])} files")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-j", "--json", action="store_true")
    parser.add_argument("-m", "--html", action="store_true")
    parser.add_argument("-i", "--identifier", type=str, help=argparse.SUPPRESS)
    parser.add_argument("-s", "--sync-token", type=str, help=argparse.SUPPRESS)
    parser.add_argument("--base", type=str, required=True)
    parser.add_argument("--head", type=str, required=True)

    args = parser.parse_args()
    repo = Repo(".")

    if not args.html:
        if (token := "--identifier" if args.identifier else False
        ) or (token := "--sync-token" if args.sync_token else False):
            parser.error(f"{token} requires --html to be specified.")

    changed_files: list[str | None] = get_changed_files(repo, args.base, args.head)

    unicode_blocks = load_unicode_blocks()

    with font_yml().open(encoding="utf-8") as io:
        config: FontYML = yaml.safe_load(io)

    families: list[str] = list(
        config["typeface"]["family"]
    )

    changed_blocks: set[str] = {
        block for path in changed_files
        if (block := project_from_path(path)) is not None
    }

    # Only projects that actually have a known Unicode block are valid.
    unknown_blocks = changed_blocks - unicode_blocks.keys()

    if unknown_blocks:
        for block in sorted(unknown_blocks):
            print( f"ERROR: Unknown Unicode project: {block}")

        return 3

    report = VerificationReport(args.base, args.head)
    all_synced: bool = True


    for i, block_name in enumerate(sorted(changed_blocks)):

        print(f"\33[33m================= \033[1m"
              f"({i + 1}/{len(changed_blocks)}) Verifying '{block_name}'\033[0m")

        block: UnicodeBlock = unicode_blocks[block_name]
        source: Source | None = determine_source(block_name, changed_files)

        if source is None:
            continue

        if source is Source.PBM:
            report.add_project(
                block_name,
                source,
            )

            print(f"\33[33m================= \033[1m"
                  f"WARNING: '{block_name}'\033[0m")
            print("Source: UNKNOWN")
            print("PBM files were changed without any PNG or Aseprite source.")
            print(
                "Modify the PNG design sheets or design.aseprite "
                "instead of modifying generated PBM files directly."
            )

            all_synced = False
            continue

        changes = verify_project(
            repo,
            args.head,
            block,
            source,
            families,
            verbose=args.verbose,
        )

        print(f"\33[33m================= \033[1m"
              f"Generated '{block_name}'\033[0m")

        log_changes(source, changes, verbose=args.verbose)

        report.add_project(block_name, source, changes)

        if not is_synced(changes):
            all_synced = False

    if args.json:
        report.write_json()

    if args.html:
        report.write_html(
            magic=args.identifier if isinstance(args.identifier, str) else None,
            token=args.sync_token if isinstance(args.sync_token, str) else None
        )

    return 0 if all_synced else 1


if __name__ == "__main__":
    raise SystemExit(main())