# Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
# with Reserved Font Name "BTE Seafront".
# Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).
#
# This Font Software is licensed under the SIL Open Font License, Version 1.1.
# This license is available with a FAQ at:
# https://openfontlicense.org
"""\
Anchoring data model
"""

def parse_glyph_anchors(anchors_yml: dict):
    """
    Parse Unicode block's profile/anchors.yml

    :param anchors_yml: anchors.yml file
    :return: Glyph positioning dictionary
    :raises TypeError: If the configuration is invalid.
    """

    mark_class = { "above", "below" }
    result = {}

    def zero():
        return { "x": 0, "y": 0 }

    def parse_position(pos):
        # Parse (Optional) position
        if isinstance(pos, dict):
            x: int = int( pos.get("x", 0) )
            y: int = int( pos.get("y", 0) )
        elif isinstance(pos, list):
            x: int = int( pos[0] ) if len(pos) > 0 else 0
            y: int = int( pos[1] ) if len(pos) > 1 else 0
        else:
            return zero()

        # Pixel coordinates to font units
        return { "x": x, "y": y }

    for glyph_name, value in anchors_yml.items():
        # Resolve shorthand anchor type
        # glyph_name: ABOVE
        if isinstance(value, str):
            anchor = { "type": value }
            metric = zero()
        elif isinstance(value, dict):
            # Resolve shorthand
            # glyph_name.anchor: ABOVE
            # glyph_name.anchor.type: ABOVE

            anchor = value.get("anchor", { "type": None })
            metric = value.get("pos", zero())

            if isinstance(anchor, str):
                anchor = { "type": anchor }
            elif not isinstance(anchor, dict):
                raise TypeError(f"{glyph_name}: anchor must be a string or mapping")
            if not isinstance(metric, dict):
                raise TypeError(f"{glyph_name}: metric position must be a mapping of x, y")
        else:
            raise TypeError(f"{glyph_name}: expected anchor definition or shorthand")

        # Parse anchor class
        anchor_type = anchor.get("type")
        group_tuple = None

        if anchor_type is not None:
            selected: str = anchor_type.lower()
            # If anchor is of base class
            if selected == "base":
                group_tuple = ("base", "base")
            else: # If anchor is of mark class
                for classes in mark_class:
                    if classes == selected:
                        group_tuple = (classes, "mark")
        if group_tuple is None:
            raise TypeError(f"{glyph_name}: anchor must specify its type")

        def create[T](base: set[T], out: str):
            name = anchor.get(out)
            if isinstance(name, dict):
                mapping = { k: name.get(k) for k in base }
                return { k: parse_position(v) for k, v in mapping.items() }
            return { k: zero() for k in base }

        base_yml = { "above", "below" }
        mark_yml = { "base", "mkmk"}
        final_class, group = group_tuple
        base_anchor = create(base_yml, group)
        mark_anchor = create(mark_yml, group)

        result[glyph_name] = {
            "anchor": {
                "type": final_class,
                "mark": mark_anchor,
                "base": base_anchor
            },
            "pos": parse_position(metric)
        }

    return result