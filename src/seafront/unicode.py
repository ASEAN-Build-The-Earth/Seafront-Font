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
import json


def load_unicode_blocks():
    """
    Load embedded dict of Unicode blocks' ranges

    :return: dict{name, start, end}
    """
    with unicode().open(encoding="utf-8") as fp:
        data = json.load(fp)

    blocks = {}

    for key, value in data.items():
        blocks[key] = {
            "name": key,
            "start": int(value[0], 16),
            "end": int(value[1], 16),
        }

    return blocks