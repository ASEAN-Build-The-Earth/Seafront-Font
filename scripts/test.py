#!/usr/bin/env python3
"""\
Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
with Reserved Font Name "BTE Seafront".
Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).

This Font Software is licensed under the SIL Open Font License, Version 1.1.
This license is available with a FAQ at:
https://openfontlicense.org
"""

import unittest
from extract import extract, chain, simplify, Point, Path

# --------------------------------------------------
# Uncomment for debugging, matplotlib required.
# --------------------------------------------------
# import matplotlib.pyplot as plt
def plot_as_fig(plot, chains):
    """
    Optional matplotlib paths plotting for debugging

    :param plot: import matplotlib.pyplot as plt
    :param chains: Sorted chain from edge tracing algorithm
    :return: fig named test_plot.png
    """
    fig, ax = plot.subplots(figsize=(10, 10))

    cmap = plot.get_cmap("tab20")

    for i, path in enumerate(chains):
        color = cmap(i % 20)

        for j, (a, b) in enumerate(path):
            x1, y1 = a
            x2, y2 = b

            # draw edge
            ax.plot([x1, x2], [y1, y2], color=color, linewidth=2)

            # arrow showing direction
            ax.annotate("",
                xy = (x2, y2),
                xytext = (x1, y1),
                arrowprops=dict(arrowstyle="->", color=color, lw=1, shrinkA=0, nkB=0),
            )

        # label first point
        if path:
            x, y = path[0][0]
            ax.text(x, y, str(i), fontsize=9, color=color,weight="bold")

    ax.set_aspect("equal")
    ax.invert_yaxis()          # match image coordinates
    ax.grid(True)
    plot.savefig('test_plot.png')

def setup():
    """
    Set up a test for the '%' character

    :return: expected simplified paths and the boundary of this test case
    """
    test: list[list[int]] = [
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1],
        [1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1],
        [1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 1],
        [1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 1],
        [1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    ]
    expected: list[list[Point]] = [
        [(11, 21), (15, 21), (15, 17), (13, 17), (13, 13), (11, 13), (11, 9), (9, 9), (9, 5), (7, 5),
         (7, 1), (3, 1), (3, 5), (5, 5), (5, 9), (7, 9), (7, 13), (9, 13), (9, 17), (11, 17), (11, 21)],
        [(2, 20), (5, 20), (5, 18), (7, 18), (7, 15), (5, 15), (5, 13), (2, 13), (2, 15), (0, 15), (0, 18), (2, 18), (2, 20)],
        [(13, 9), (16, 9), (16, 7), (18, 7), (18, 4), (16, 4), (16, 2), (13, 2), (13, 4), (11, 4), (11, 7), (13, 7), (13, 9)]
    ]
    w = len(test[0])
    h = len(test)
    fn = lambda x, y: test[y][x]
    return expected, extract(fn, w, h, 1, h,1)

class TestEdgeTracing(unittest.TestCase):

    def test(self):
        expected, (edges, bounds) = setup()
        paths = chain(edges)
        # --------------------------------------------------
        # Uncomment for debugging, output to test_plot.png. or do plt.show()
        # plot_as_fig(plt, paths)
        # --------------------------------------------------

        self.assertEqual(3, len(paths))
        print("Edges: ", edges.values())

        simplified: list[list[Point]] = []
        for path in paths:
            result: Path = simplify(path)
            points: list[Point] = [result[0][0]]

            for edge in result:
                points.append(edge[1])

            simplified.append(points)

        for path in simplified:
            print("Simplified: ", path)

        self.assertListEqual(expected, simplified)

if __name__ == '__main__':
    unittest.main()
