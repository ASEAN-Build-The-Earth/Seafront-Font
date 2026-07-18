#!/usr/bin/env python3
"""\
Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
with Reserved Font Name "BTE Seafront".
Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).

This Font Software is licensed under the SIL Open Font License, Version 1.1.
This license is available with a FAQ at:
https://openfontlicense.org
"""

from collections import defaultdict
from collections.abc import Callable

Point = tuple[int, int]
Edge = tuple[Point, Point]
UniqueEdges = dict[tuple[Point, Point], Edge] # key used only for duplicate detection
Path = list[Edge]

def extract(fn: Callable[[int, int], float | tuple[int, ...]],
            w: int,
            h: int,
            x_starting: int,
            y_baseline: int,
            pixel_size: int) -> tuple[UniqueEdges, tuple[int, int, int, int]] | None:
    """
    Extract the edges and boundary of a given bitmap mask, where 0 is the extracting pixel.

    :param fn: Bitmap function for each pixel inside width and height
    :param w: The width of this boundary
    :param h: The height of this boundary
    :param x_starting: Where the x pixel will start, normalizing as 0
    :param y_baseline: The baseline pixel along y, normalizing as 0
    :param pixel_size: The scale of each pixel

    :return: pair of unique edges and its boundary, None if the bitmap is empty
    """

    edges: UniqueEdges = dict()

    def canonical(a: Point, b: Point) -> Edge:
        return (a, b) if a < b else (b, a)

    def toggle_edge(boundary: UniqueEdges,
                    a: Point,
                    b: Point) -> None:
        key: Edge = canonical(a, b)

        if key in boundary:
            del boundary[key]
        else:
            boundary[key] = (a, b)  # Preserve original direction

    min_x = w
    min_y = h
    max_x = -1
    max_y = -1

    for y in range(h):
        for x in range(w):
            if fn(x, y) == 0:
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)

                left = (x - x_starting) * pixel_size
                right = left + pixel_size
                top = (y_baseline - y) * pixel_size
                bottom = top - pixel_size

                tl = (left, top)
                tr = (right, top)
                br = (right, bottom)
                bl = (left, bottom)

                toggle_edge(edges, tl, tr)
                toggle_edge(edges, tr, br)
                toggle_edge(edges, br, bl)
                toggle_edge(edges, bl, tl)

    if len(edges) == 0:
        return None

    min_x = max(0, min_x)
    min_y = max(0, min_y)

    max_x = min(w - 1, max_x)
    max_y = min(h - 1, max_y)

    bounds = (min_x, min_y, max_x, max_y)

    return edges, bounds

def chain(boundary: UniqueEdges) -> list[Path]:
    """
    Chain edges into continuous loops (polygons)

    :param boundary:
    :return:
    """
    edges: Path = list(boundary.values())
    outgoing: defaultdict[Point, Path] = defaultdict(list)

    for edge in edges:
        outgoing[edge[0]].append(edge)

    visited: set[Edge] = set()
    loops: list[Path] = []

    for edge in edges:
        if edge in visited: continue

        loop: Path = []
        current: Edge = edge

        while True:
            visited.add(current)
            loop.append(current)

            next_point: Point = current[1]
            next_edge: Edge | None = None

            for candidate in outgoing[next_point]:
                if candidate not in visited:
                    next_edge = candidate
                    break

            if next_edge is None:
                break

            current = next_edge

        loops.append(loop)

    return loops


def direction(edge: Edge) -> tuple[bool, bool]:
    """
    Determines edge direction

    :param edge:
    :return: [bool, bool] 
    """
    (x1, y1), (x2, y2) = edge

    return (x2 > x1) - (x2 < x1), (y2 > y1) - (y2 < y1)

def simplify(loop: Path) -> Path:
    """
    Simplify collinear edges

    :param loop: Path to simplify
    :return: Path or points, or an Edge if
    """
    if len(loop) < 2:
        return loop

    result: Path = []

    start: Point = loop[0][0]
    end: Point = loop[0][1]

    current_dir: tuple[bool, bool] = direction(loop[0])

    for edge in loop[1:]:
        d: tuple[bool, bool] = direction(edge)

        if d == current_dir:
            end = edge[1]

        else:
            result.append((start, end))

            start = edge[0]
            end = edge[1]

            current_dir = d

    result.append((start, end))

    return result