# Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
# with Reserved Font Name "BTE Seafront".
# Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).
#
# This Font Software is licensed under the SIL Open Font License, Version 1.1.
# This license is available with a FAQ at:
# https://openfontlicense.org
"""\
Design project aseprite scripts

Note that each subprocess' Virtual path Traversable is convert back to
pathlib to be sure aseprite file won't mistake it
"""
from importlib.resources import as_file
from importlib.resources.abc import Traversable
from pathlib import Path
from sys import stderr

import seafront.font as font
import subprocess

ASEPRITE_EXPORT: str = "aseprite/export-graphics.lua"
"""aseprite export graphics script"""

ASEPRITE_SAVE: str = "aseprite/save-graphics.lua"
"""aseprite save graphics script"""

ASEPRITE_CREATE: str = "aseprite/create-project.lua"
"""aseprite project generation script"""


def save_graphics(aseprite_file: Traversable,
                  verbose: bool=False) -> bool:
    """
    Spin a subprocess to run :code:`/scripts/aseprite/save-graphics.lua`

    :param aseprite_file: The aseprite file to save graphics
    :param verbose: Pass verbose flag to the script
    :raise CalledProcessError If an error occurred inside the executing script
    :raise OSError If aseprite is not available in the system
    :return: Boolean when the script finished running
    """
    try:
        with (as_file(aseprite_file) as file,
              as_file(font.SCRIPTS_DIR / ASEPRITE_SAVE) as script,
              as_file(font.FONT_DIR) as config):
            cli = ["aseprite", "--batch", file,
                   "--script-param", f"config={config}"]

            if verbose:
                cli.append("--script-param")
                cli.append(f"verbose=true")

            cli.append("--script")
            cli.append(script)

            subprocess.run(cli, check=True)
            return True
    except subprocess.CalledProcessError as internal_error:
        print(f"{'\033[93m'}Internal error saving "
              f".aseprite project file:\n{internal_error}{'\033[0m'}", file=stderr)
    except OSError as os_error:
        print(f"{'\033[93m'}Aseprite not found in system. "
              f"Cannot save .aseprite project file:\n{os_error}{'\033[0m'}", file=stderr)
    return False


def export_graphics(aseprite_file: Traversable,
                    start_codepoint: int,
                    verbose: bool=False) -> bool:
    """
    Spin a subprocess to run :code:`/scripts/aseprite/export-graphics.lua`

    :param aseprite_file: The aseprite file to export graphics
    :param verbose: Pass verbose flag to the script
    :param start_codepoint: Unicode start codepoint of the project's annoting this aseprite file
    :param verbose: Pass verbose flag to the script
    :raise CalledProcessError If an error occurred inside the executing script
    :raise OSError If aseprite is not available in the system
    :return: Boolean when the script finished running
    """
    try:
        with (as_file(aseprite_file) as file,
              as_file(font.SCRIPTS_DIR / ASEPRITE_EXPORT) as script,
              as_file(font.FONT_DIR) as config):
            cli = ["aseprite", "--batch", file,
                   "--script-param", f"config={config}",
                   "--script-param", f"codepoint={start_codepoint:04X}"]

            if verbose:
                print("Exporting verbose")
                cli.append("--script-param")
                cli.append(f"verbose=true")

            cli.append("--script")
            cli.append(script)

            subprocess.run(cli, check=True)
            return True
    except subprocess.CalledProcessError as internal_error:
        print(f"{'\033[93m'}Internal error exporting "
              f".aseprite project file:\n{internal_error}{'\033[0m'}", file=stderr)
    except OSError as os_error:
        print(f"{'\033[93m'}Aseprite not found in system. "
              f"Cannot export .aseprite project file:\n{os_error}{'\033[0m'}", file=stderr)
    return False


def create_project(project_dir: Traversable,
                   is_extension: bool,
                   verbose: bool=False) -> bool:
    """
    Spin a subprocess to run :code:`/scripts/aseprite/create-project.lua`

    :param project_dir: The directory path, must be convertible to Path object
    :param is_extension: Is the project an extension project (ext-design.aseprite)
    :param verbose: Pass verbose flag to the script
    :raise CalledProcessError If an error occurred inside the executing script
    :raise OSError If aseprite is not available in the system
    :return: Boolean when the script finished running
    """
    try:
        with (as_file(project_dir) as project,
              as_file(font.SCRIPTS_DIR / ASEPRITE_CREATE) as script,
              as_file(font.FONT_DIR) as config):
            cli: list[str | Path] = [
                "aseprite",
                "--batch",
                "--script-param", f"dir={project}",
                "--script-param", f"config={config}",
                "--script-param", f"ext={is_extension}"
            ]
            if verbose:
                print("Exporting verbose")
                cli.append("--script-param")
                cli.append(f"verbose=true")

            cli.append("--script")
            cli.append(script)

            subprocess.run(cli, check=True)
            return True
    except subprocess.CalledProcessError as internal_error:
        print(f"{'\033[93m'}Internal error generating "
              f".aseprite project file:\n{internal_error}{'\033[0m'}", file=stderr)
    except OSError as os_error:
        print(f"{'\033[93m'}Aseprite not found in system. "
              f"Cannot generate .aseprite project file:\n{os_error}{'\033[0m'}", file=stderr)
    return False
