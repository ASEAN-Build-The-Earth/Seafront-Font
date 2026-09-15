# Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
# with Reserved Font Name "BTE Seafront".
# Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).
#
# This Font Software is licensed under the SIL Open Font License, Version 1.1.
# This license is available with a FAQ at:
# https://openfontlicense.org
"""\
Unicode blocks collection mapping
"""
from seafront.font import unicode_blocks_json as unicode
from typing import TypedDict, ReadOnly, Any
import re
import json

class UnicodeBlock(TypedDict):
    """
    Unicode block data model

    :ivar name: The name of this Unicode block
    :ivar start: The start codepoint (int:04X)
    :ivar end: The end codepoint (int:04X)
    """
    name: ReadOnly[str]
    start: ReadOnly[int]
    end: ReadOnly[int]


def load_unicode_blocks() -> dict[str, UnicodeBlock]:
    """
    Load embedded dict of Unicode blocks' ranges::

        blocks[key] = {
           "name": str(key),
           "start": int(value[0], 16),
           "end": int(value[1], 16),
        }
    :return: dict{name, start, end}
    """
    with unicode().open(encoding="utf-8") as fp:
        data = json.load(fp)

    blocks: dict[str, UnicodeBlock] = {}
    for key, value in data.items():
        blocks[key] = {
            "name": str(key),
            "start": int(value[0], 16),
            "end": int(value[1], 16),
        }
    return blocks


def parse_codepoint(value: Any) -> int:
    """
    Parse a YAML value into a Unicode code point integer.

    :return int: Unicode code point in the range 0x0000..0x10FFFF.
    :raise TypeError: If the value is not a supported type.
    :raise ValueError: If the value is not a valid Unicode code point.
    """
    if isinstance(value, bool):
        raise TypeError("Boolean is not a Unicode code point")
    if isinstance(value, int):
        codepoint = value
    elif isinstance(value, str) and (s := value.strip()):
        if match := re.fullmatch(r"\\u([0-9A-Fa-f]{4})", s):
            codepoint = int(match.group(1), 16) # \uXXXX
        elif match := re.fullmatch(r"U\+([0-9A-Fa-f]{4,6})", s, re.IGNORECASE):
            codepoint = int(match.group(1), 16) # U+XXXX / U+XXXXXX
        elif match := re.fullmatch(r"uni([0-9A-Fa-f]{4,6})", s, re.IGNORECASE):
            codepoint = int(match.group(1), 16) # uniXXXX / uniXXXXXX
        elif match := re.fullmatch(r"0[xX]([0-9A-Fa-f]{1,6})", s):
            codepoint = int(match.group(1), 16) # 0xXXXX / 0xXXXXXX
        elif re.fullmatch(r"[0-9A-Fa-f]{4,6}", s):
            codepoint = int(s, 16) # Plain hexadecimal: XXXX
        else:
            raise ValueError(f"Invalid Unicode code point: {value!r}")
    else:
        raise TypeError(f"Expected int or str for Unicode code point, got {type(value).__name__}")

    if not 0 <= codepoint <= 0x10FFFF:
        raise ValueError(f"Unicode code point out of range: {codepoint:#x} "
                         f"(must be 0x0000..0x10FFFF)")
    # Unicode surrogate code points aren't valid scalar values.
    if 0xD800 <= codepoint <= 0xDFFF:
        raise ValueError(f"Unicode surrogate is not a valid scalar value: {codepoint:#x}")

    return codepoint
