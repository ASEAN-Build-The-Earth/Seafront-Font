#!/usr/bin/env python3
# Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
# with Reserved Font Name "BTE Seafront".
# Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).
#
# This Font Software is licensed under the SIL Open Font License, Version 1.1.
# This license is available with a FAQ at:
# https://openfontlicense.org
r""" export_seafront.py

Commandline script to export Seafront fonts.

Usage
-----
using hatch::

    hatch run export-seafront

using python::

    python export_seafront.py
"""
from importlib.resources import as_file
from seafront.font import font_yml, FONT_DIR
from seafront.core.export import export, FontExport, FontProfile
from seafront.model.font import FontYML, TypefaceData, FontMetric, TypefaceStyles, FontInfo, FontData

import argparse
import yaml


def main():
    with font_yml().open(encoding="utf-8") as io:
        config: FontYML = yaml.safe_load(io)

    parser = argparse.ArgumentParser(
        description="Export a TrueType font from this project",
        formatter_class=argparse.RawTextHelpFormatter
    )

    typeface_options: list[TypefaceStyles] = [*config["typeface"]["style"]]
    accent_options: list[FontMetric] = [*config["profile"]["accent"]]
    family_options: list[str] = config["typeface"]["family"]

    parser.add_argument('-v', "--verbose",
        default=False, const=True,
        type=bool, nargs="?",
        help="log verbose outputs",
    )

    parser.add_argument('-i', "--identifier",
        nargs="?",
        type=float,
        help="The font's version number to export, formatted as 3 decimals float ex. 1.000",
    )

    parser.add_argument('-s', "--scale",
        default=accent_options[0],
        choices=accent_options,
        help="The scale preset that affect the font's internal positioning.\n"
             f"Default to '{accent_options[0]}'",
    )

    parser.add_argument('-a', "--accent",
        default=accent_options[0],
        choices=accent_options,
        help="The accent preset of this font which define the ascent\n"
             f"and descend line of this font, Default to '{accent_options[0]}'",
    )

    parser.add_argument(
        "-t", "--typeface",
        default=typeface_options[0],
        choices=typeface_options,
        help="Typeface to export configured in config/font.yml.\n"
             f"Default to '{typeface_options[0]}'",
    )

    parser.add_argument(
        "-c", "--family",
        default=family_options[0],
        choices=family_options,
        help="The family name to export",
    )

    # Positional Arguments
    # export_seafront.py {font_options} {output_filename}

    available_font = {k: v["font-desc-info"] for k, v in config["font"].items()}
    font_desc_text = "\n".join(f"- \033[1m\033[32m{key:<8}\033[0m : {val}" for key, val in available_font.items())
    font_hint_text = "\33[90mThe export profile can be configured under \033[4m/font/font.yml\033[0m"
    font_help_text = "\n".join(["Which font to export? (Required):", font_desc_text, font_hint_text])
    file_help_text = "Output file name *.ttf, default to the psName of exporting font."

    parser.add_argument("font", choices=available_font, help=font_help_text)

    parser.add_argument("output", nargs="?", help=file_help_text)

    args = parser.parse_args()

    def get_argument[T](argument: T,
                        key: str,
                        assertion: TypefaceData | None=None) -> T:
        if assertion is None:
            assertion = config["profile"]
        if argument not in assertion[key]:
            raise ValueError(f"Expected key for '{argument}' in '{key}' not found in font/font.yml")
        return argument

    def assert_profile(key: str,
                       assertion: TypefaceData | dict[TypefaceStyles, str] | None=None):
        if assertion is None:
            assertion = config["profile"]
        if key not in assertion:
            raise ValueError(f"'{key}' export profile not found in font/font.yml")

    face = get_argument(args.typeface, "style", config["typeface"])
    scale = get_argument(args.scale, "scale")
    accent = get_argument(args.accent, "accent")

    assert_profile("info", config["typeface"])
    assert_profile("style", config["typeface"])
    assert_profile("regular", config["typeface"]["style"])
    assert_profile("typography")
    assert_profile("scale")
    assert_profile("accent")

    font_info: FontInfo = config["typeface"]["info"].copy()

    if args.family:
        font_info["family"] = args.family

    if args.identifier:
        font_info["version"] = f"Version {args.identifier:.3f}"

    font: FontExport = {
        "style": config["typeface"]["style"][face],
        "info": font_info,
        "name": args.font,
        "face": face
    }
    profile: FontProfile = {
        "typography": config["profile"]["typography"],
        "scale": config["profile"]["scale"][scale],
        "accent": config["profile"]["accent"][accent],
        "verbose": args.verbose
    }
    data: FontData = config["font"][args.font]

    if args.verbose:
        print("Export Profile: ", font, profile)

    def export_fn(generated_name: str):
        if args.output is None:
            filename = f"{generated_name}.ttf"
        elif str(args.output).endswith(".ttf"):
            filename = args.output
        else:
            filename = f"{args.output}.ttf"

        with as_file(FONT_DIR / "export") as export_path:
            export_path.mkdir(exist_ok=True)
            return export_path / filename

    export(export_fn, font, data, profile)


if __name__ == "__main__":
    main()