# Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
# with Reserved Font Name "BTE Seafront".
# Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).
#
# This Font Software is licensed under the SIL Open Font License, Version 1.1.
# This license is available with a FAQ at:
# https://openfontlicense.org
r""" file_changes.py

File changes helper
"""
from pathlib import Path
from typing import Literal, TypedDict, Iterator
from importlib.resources.abc import Traversable
from collections.abc import Callable, Collection


class FileChanges[T](TypedDict):
    """
    Record files that is changed after comparing files tree/

    :ivar added: Added files after comparison
    :ivar unsync: Files that exists before the comparison, but not in the changes
    :ivar modified: Modified files after comparison
    """
    added: Collection[T]
    unsync: Collection[T]
    modified: Collection[T]

ChangeTypes = Literal["modified", "unsync", "added"]
"""Dict keys literal of the :class:`FileChanges`"""


def is_synced[T](changes: FileChanges[T]) -> bool:
    """
    :param changes: :class:`FileChanges` to check
    :return: True if all changes is empty
    """
    return not (changes["added"] or changes["unsync"] or changes["modified"])


def get_disk_files(directory: Traversable | Path,
                   root: str | None=None) -> dict[str, bytes]:
    """
    Read files under a filesystem directory, within a root path.

    :param directory: Disk directory to traverse
    :param root: Root path (posix)
    :return: Dict of relative path names inside root, map to its bytes content.
    """
    result: dict[str, bytes] = {}

    if not directory.is_dir():
        return result

    def recursive_iterdir(index: Traversable | Path,
                          parent: str | None=None) -> Iterator[tuple[str, Traversable | Path]]:
        for child in index.iterdir():
            steps: str = child.name if (parent is None) else f"{parent}/{child.name}"

            yield steps, child
            if child.is_dir():
                yield from recursive_iterdir(child, steps)

    for (path, file) in recursive_iterdir(directory):
        if not file.is_file():
            continue

        file_data: bytes = file.read_bytes()

        if isinstance(root, str):
            result[f"{root}/{path}"] = file_data
        else:
            result[path] = file_data

    return result


def compare_files(
    actual: dict[str, bytes],
    expected: dict[str, bytes],
) -> FileChanges[str]:
    """
    Compare two file trees by path and content.

    :param actual: Actual file tree.
    :param expected: Expected file tree.
    :returns: Changes required to make the actual file tree match the expected file tree.
    """
    actual_paths: set[str] = set(actual)
    expected_paths: set[str] = set(expected)

    added: set[str] = expected_paths - actual_paths
    unsync: set[str] = actual_paths - expected_paths
    modified: set[str] = {
        path for path in actual_paths & expected_paths
        if actual[path] != expected[path]
    }

    return {
        "added": added,
        "unsync": unsync,
        "modified": modified
    }


def filter_changes(changes: FileChanges[str] | None,
                   predicate: Callable[[str], bool],
                   *, reverse: bool=False) -> FileChanges[str]:
    """:return: Sort as relative file names for simplicity and omit .pbm files"""
    def collect(change: ChangeTypes) -> list[str]:
        if changes is None:
            return []
        return sorted({
            path for path in changes[change] if predicate(path)
        }, reverse=reverse)

    return {
        "modified": collect("modified"),
        "added": collect("added"),
        "unsync": collect("unsync"),
    }
