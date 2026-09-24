#!/usr/bin/env python3
# Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
# with Reserved Font Name "BTE Seafront".
# Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).
#
# This Font Software is licensed under the SIL Open Font License, Version 1.1.
# This license is available with a FAQ at:
# https://openfontlicense.org
r"""generate_projects.py

Commandline script to save Seafront fonts project files.

Usage
-----
using hatch::

    hatch run save-project-with

using python::

    python save_project_with.py
"""
import argparse
from importlib.resources.abc import Traversable
from typing import Literal, NamedTuple

import yaml

from seafront.core.design.saves import png_image, aseprite
from seafront.font import font_yml, project_yml
from seafront.model.font import FontYML
from seafront.unicode import load_unicode_blocks, UnicodeBlock


def load_yaml(file: Traversable):
    with file.open(encoding="utf-8") as fp:
        return yaml.safe_load(fp)


class SaveOption(NamedTuple):
    font: list[UnicodeBlock] | None
    project: list[UnicodeBlock] | None
    unicode: list[UnicodeBlock] | None
    family: list[str]


# 1. Define the handler functions for each subcommand
def with_aseprite(args: SaveOption):

    if args.font is not None:
        aseprite(args.font)

    if args.project is not None:
        aseprite(args.project)

    if args.unicode is not None:
        aseprite(args.unicode)


def with_png_image(args: SaveOption):

    if args.font is not None:
        png_image(args.font, set(args.family))

    if args.project is not None:
        png_image(args.project, set(args.family))

    if args.unicode is not None:
        png_image(args.unicode, set(args.family))


def main():
    config: FontYML = load_yaml(font_yml())
    project: dict[Literal["blocks"], list[str]] = load_yaml(project_yml())
    unicode: dict[str, UnicodeBlock] = {
        k.casefold(): v for k, v in
        load_unicode_blocks().items()
    }
    family_options: list[str] = config["typeface"]["family"]

    # Parent parser, with sub parser as sub commands
    parser = argparse.ArgumentParser(description="Save projects.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument('-v', "--verbose",
        default=False, const=True,
        type=bool, nargs="?",
        help="log verbose outputs",
    )

    available_font = {k: v["font-desc-info"] for k, v in config["font"].items()}
    font_desc_text = "\n".join(f"- \033[1m\033[32m{key:<8}\033[0m : {val}" for key, val in available_font.items())
    font_hint_text = "\33[90mThe export profile can be configured under \033[4m/font/font.yml\033[0m"
    font_help_text = "\n".join(["Save unicode blocks used for this font:", font_desc_text, font_hint_text])
    project_help_text = "Save all configured in project.yml"
    unicode_help_text = "Save only specify unicode block name"

    def validate_unicode(value) -> UnicodeBlock:
        if isinstance(value, str) and (name := value.strip().casefold()):
            if (name in unicode
                or ((name := name.replace("-", " ")) and name in unicode)
                or ((name := name.replace("_", " ")) and name in unicode)
            ):
                return unicode[name]
        raise argparse.ArgumentTypeError(f"invalid choice: '{value}' (not a valid unicode block name)")

    def accept_project(enabled) -> list[UnicodeBlock]:
        return [accept_unicode(name) for name in project["blocks"]] if enabled else []

    def accept_font(font_name) -> list[UnicodeBlock]:
        if font_name not in available_font:
            raise argparse.ArgumentTypeError(f"invalid choice: '{font_name}' (choose from {set(available_font)})")
        font_project = config["font"][font_name]["unicode-blocks"]
        return [accept_unicode(name) for name in font_project]

    def accept_unicode(name: str) -> UnicodeBlock:
        if (block_name := name.strip().casefold()) and block_name in unicode:
            return unicode[block_name]
        raise argparse.ArgumentTypeError(
            f"'{name}' not a valid unicode block name in unicode-blocks.json")

    # Unicode saving options for all parser
    unicode_option = parent_parser.add_mutually_exclusive_group(required=True)
    unicode_option.add_argument('-f', "--font", type=accept_font, help=font_help_text)
    unicode_option.add_argument('-p', "--project",
                                const=accept_project(True),
                                type=accept_project, nargs="?", help=project_help_text)
    unicode_option.add_argument('-u', "--unicode", nargs='+', type=validate_unicode, help=unicode_help_text)

    # aseprite command parser
    parser_aseprite = subparsers.add_parser("aseprite", parents=[parent_parser],
                                            help="Save with aseprite design files",
                                            formatter_class=argparse.RawTextHelpFormatter)
    parser_aseprite.set_defaults(func=with_aseprite)

    # png-images command parser
    parser_png_image = subparsers.add_parser("png-image", parents=[parent_parser],
                                             help="Save with png image files",
                                            formatter_class=argparse.RawTextHelpFormatter)
    parser_png_image.set_defaults(func=with_png_image)
    parser_png_image.add_argument(
        "-f", "--family",
        nargs="+",
        default=[family_options[0]],
        choices=family_options,
        help="The family name to export",
    )

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
