# Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
# with Reserved Font Name "BTE Seafront".
# Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).
#
# This Font Software is licensed under the SIL Open Font License, Version 1.1.
# This license is available with a FAQ at:
# https://openfontlicense.org
"""\
Seafront display fonts for development (Pillow only)
"""
from io import BytesIO
from typing import TypedDict, cast, NamedTuple
from base64 import b64decode

from PIL import Image
from PIL.Image import Image as Sheet
from PIL.FontFile import FontFile
from PIL.ImageFont import ImageFont


class PilFontData(TypedDict):
    """
    Pre-computed font data compatible to load :class:`SeafrontPilFont`

    :ivar default_adv: Default advance width
                       for codepoints NOT defined in `unicode_adv`
    :ivar unicode_adv: Map sets of Unicode codepoints to its advance width.
    :ivar image_bytes: Raw bytes of the font's bitmap image
    """
    default_adv: int
    unicode_adv: dict[int, set[int]]
    image_bytes: bytes


class SeafrontPilFont(FontFile):
    """
    Seafront 16px Pillow development display font `"Seafront Square"`.

    Limited to characters under 'Basic Latin' Unicode Block::

    94 Printable Characters (U+0021-U+007E) + 1 Space Character (U+0020)

    :ivar name: Name of the font
    :ivar bitmap: f/ :class:`FontFile` compiled bitmap image file
    :ivar metrics: f/ :class:`FontFile` defines each glyphs' boundary metrics
    :ivar ysize: f/ :class:`FontFile` defines the final compiled bitmap's y-size
    :ivar glyph: f/ :class:`FontFile` defines all available glyphs
    :ivar info: f/ :class:`FontFile` defines additional font info (unused)
    :cvar DESCENDER: 4px descender height
    :cvar ASCENDER: 4px font ascender height
    :cvar X_HEIGHT: 8px font x-height typography
    :cvar SPACING: 1px Right spacing for each character
    """
    DESCENDER = 4
    ASCENDER = 4
    X_HEIGHT = 8
    SPACING = 1

    def __init__(self, name: str, data: PilFontData) -> None:
        """
        Load a Seafront bitmap font data as Pillow :class:`FontFile`.

        :param data: Font data to load.
        """
        super().__init__()

        self.bitmap = Image.open(BytesIO(b64decode(data["image_bytes"])))
        self.metrics = [None] * 256
        self.name = name

        # Baseline are constant because our bitmap image only have 1 row
        y_baseline: int = self.X_HEIGHT + self.ASCENDER
        self.ysize = y_baseline + self.DESCENDER

        def get_advance(unicode: int) -> int:
            """Get the advance width of this Unicode glyph"""
            for advance, charset in data["unicode_adv"].items():
                if unicode in charset:
                    return advance
            return data["default_adv"]

        lsb: int = 0
        for codepoint in range(0x20, 0x7F):
            adv = get_advance(codepoint)
            self.glyph[codepoint] = (
                (adv, 0),
                (-self.SPACING, -y_baseline, adv - self.SPACING, self.DESCENDER),
                (lsb, 0, lsb + adv, self.ysize),
                cast(Sheet, cast(object, None)),
            )
            lsb += adv

    def compile(self) -> None:
        """
        Overrides :class:`FontFile`.compile()
        which load :attr:`~.glyph` directly to :attr:`~.metrics` [i]

        :return: None, compiled to :attr:`~.metrics`
        """
        if (self.bitmap is None) or (self.glyph is None):
            raise ValueError("Bitmap and Glyphs must be initialized before compiling")

        for i, glyph in enumerate(self.glyph):
            if not glyph:
                continue
            d, dst, src, _ = glyph
            self.metrics[i] = d, dst, src


class Seafront16pxUI[T](NamedTuple):
    """
    :class:`SeafrontPilFont` wrapper

    :ivar squared: 'Seafront UI Squared' Display font
                   of 16px upm, :code:`8px*8px` 'squared' typography
    :ivar compact: 'Seafront UI Compact' Compact display font
                   of 16px upm, :code:`6px*8px` typography
    """
    squared: T
    compact: T

    @classmethod
    def load_font_data(cls) -> Seafront16pxUI[SeafrontPilFont]:
        """
        Load as :class:`FontFile`
        """
        return cls(
            squared=seafront_16px_squared(),
            compact=seafront_16px_compact()
        )

    @classmethod
    def load_image_font(cls) -> Seafront16pxUI[ImageFont]:
        """
        Load as :class:`ImageFont`
        """
        return cls(
            squared=seafront_16px_squared().to_imagefont(),
            compact=seafront_16px_compact().to_imagefont()
        )


def seafront_16px_squared() -> SeafrontPilFont:
    """
    Display font of 16px upm, 8px*8px 'squared' typography

    :return: Pillow :class:`FontFile` implementations,
             use :code:`to_imagefont()` to load as :class:`ImageFont`.
    """
    return SeafrontPilFont("Seafront UI Squared", {
        "default_adv": 9,
        "unicode_adv": {
            3: { 0x21, 0x27, 0x2E, 0x3A, 0x7C },
            4: { 0x2C, 0x3B },
            5: { 0x28, 0x29, 0x2F, 0x5B, 0x5C, 0x5D, 0x60, 0x7B, 0x7D },
            6: { 0x22, 0x3C, 0x3E, },
            7: { 0x2A, 0x2B, 0x2D, 0x31, 0x3D, 0x3F, 0x5E},
            8: { 0x25, 0x5F }
        },
        "image_bytes": (
            b"iVBORw0KGgoAAAANSUhEUgAAAvIAAAAQAQAAAABc86ZBAAAC7klEQVR4nM2Uz2sbRxzFPzurWhsj"
            b"482Pg41beyml5NAGQYIrk5DdfyCt/4AWZAi4h0J9KMUFWzs2wfGhQaaXHOP8B6KFNJSAV7UbXRLa"
            b"FAoiFLS1IM7BqXaJkVbx7mwPclASnDaQHPpOw/fNvJl5874D/2/kIMcweZ3buve0WOzz4k1sYr6c"
            b"EoAmgYHX0O9CgpMcTk7eqT2YaY5NSJj9q7zTXVIl91rZ06k2w25ccu3GTnssHt8s5uuzO2E3dt1K"
            b"/YvJsSHVPlfUy782wzhO7Y0y7ZHqrrLt8qPN/WRlc6ZS/zK8AQKOnzSFackcGCYmIyxhTX+wVXr3"
            b"xGBGLCExADIcyRjmYEZIAM0CWMOxTgxqAgcHLI5pjpwWZwBygNB6/iRm0ZnMS/hsIJyyWK4uh12Z"
            b"Zc22zNWt7XDqHTO5+DDLgEhsy1ytXpFoCzfL43fvGUm4aFvm6uh2uMdvBW5ubYdd137rInCEMFgY"
            b"9wRPPmzeV1da5g9ZXyPr3ZcL50Wr9tXHy7/gB18nDF/2Qh9OgYbmM38eMlL9/enbsM4nkofMA6DN"
            b"9fxW9wKAB57WVNcRQHT0Z4sngPjJCIym0DLreYCK91y8OrEkOqmWINh20qhA+nkvOer5B40NeI9A"
            b"Co89T8DxUef09NGdC10LmbxvYWxlw/Db70sFH3NVJ/zGsS1N/g6K1Mx8dwl0hDk3B9CVjHAJgHTt"
            b"QD+x4CqmzCyKCxKYaD3+KDorc/mhcqfViUZVmrMbu7WSP7A/pFJ3oz7cHktUza3UW209WUlzdm1l"
            b"tjCjwlsw0ersJ2rErTT824Xkxqa70djNRovqnD3VaD3+EQT5R/Ug9n25B1FAHKFcfO+PeNmvzqNc"
            b"JBGkKgbmAxWQ4t+SqQ+gRwG77RQ8AF+CJysQbfDnXidApb0LaRKAuWdN1CTohzdMH3rUn53zAMj3"
            b"P4ci9PKZ9vSDZ5emEl7SkH0kxsGgdMhhJuRT/QOs/5fcv0ASeS/W/NfQe2X8A1JYPI61ah9CAAAA"
            b"AElFTkSuQmCC"
        )
    })


def seafront_16px_compact() -> SeafrontPilFont:
    """
    Compact display font of 16px upm, 6px*8px typography

    :return: Pillow :class:`FontFile` implementations,
             use :code:`to_imagefont()` to load as :class:`ImageFont`.
    """
    return SeafrontPilFont("Seafront UI Compact", {
        "default_adv": 7,
        "unicode_adv": {
            3: { 0x21, 0x27, 0x2E, 0x3A, 0x69, 0x7C },
            4: { 0x2C, 0x3B, 0x6C},
            5: { 0x28, 0x29, 0x2F, 0x5B, 0x5C, 0x5D, 0x60, 0x7B, 0x7D},
            6: { 0x22, 0x3C, 0x3E, 0x6A }
        },
        "image_bytes": (
            b"iVBORw0KGgoAAAANSUhEUgAAAmIAAAAQAQAAAACdWC6oAAACZklEQVR4nMWTTUgUYRjHfzPMzops"
            b"OnkaRG1WCToYbQi1xaqT90DsXKyXPWl56FCy6GspdBAy6hDbIe1UFwm8RAd9xRBvO4cORR9uYDUH"
            b"sVkdZN3PDn70pRB26H97n+d5fzzvn/8L/1+SiCIjvc/ju8cdqYcF7ntRBSKHwtk8Fn9W37XefPjl"
            b"TAhIh5LFhY10uglTr22K5Ta+fkvPDLU/0vvSHbFcYbPv7UyitHpD1sRy2Y10erZ3JpG+29HxZrtT"
            b"7Beo0DOqGBfaTDCEiqlZxlSiJWtMdQWqDAzAUoQx0hUACAGKpaiBas0yFDTF6h6xj++sJWxU4JUp"
            b"+wQoLyN3DGqP5n2ixUHfdSY7G8+JlBNFzfuuM+bAMlbqieEvOZOd18/7BCnlfdcbcyCEtaxLlc/T"
            b"Z4erPy4naqVK9KT8NL85nuqvOREyW11l4fY4eCiEiAwAa2YD2KUoriKAckUArweAZRrlM1Rg9J5F"
            b"GNCcDu2K0ezEAT2JtutsRVDRClUUFutmo5QcbCCzZ3ylClgjSlmq0DNR393sp7J2mZWJSqcYXEnc"
            b"X5/TXMestA/5SIMy6+qKBYTfDwC4mBWbvZRYFBbruGZfEio2WSkfXCRef6ut6VTLvNBjLGmDPpH4"
            b"fEYnEVnyKjp12YySFD4Nl+NgbrfYMtBDppI5LQibDWFQkdPJspzDBU+QZDXjDT/9UKsHKOQ8PEhm"
            b"wBMvyBUzeQCCGVnYLOJBUeINS3LJ4lVfIiSwm94fRhACzANjG9yeVMQRAUT07arOztOd32k+4B5I"
            b"27IAaPr1c904cP6vdIwgP+2W/DfafvoOtynrcKr4+UEAAAAASUVORK5CYII="
        )
    })
