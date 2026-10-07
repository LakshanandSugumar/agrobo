"""Fleet path planning primitives: boustrophedon coverage and target-tour TSP.

Robots drive only in inter-row lanes (y = row boundary), so the TSP metric is a
lane-constrained Manhattan-like distance: switching lanes requires driving to a
headland at x < 0 or x > L.
"""
from __future__ import annotations

import math


def boustrophedon(length_m: float, width_m: float, swath_m: float, start=(0.0, 0.0)):
    xs, ys = [], []
    n = max(1, math.ceil(width_m / swath_m))
    for i in range(n):
        y = min(width_m, (i + 0.5) * swath_m)
        a, b = (-1.0, length_m + 1.0) if i % 2 == 0 else (length_m + 1.0, -1.0)
        xs += [a, b]
        ys += [y, y]
    return xs, ys, path_length(start, xs, ys)


def path_length(start, xs, ys):
    d, (px, py) = 0.0, start
    for x, y in zip(xs, ys):
        d += math.hypot(x - px, y - py)
        px, py = x, y
    return d


class LaneMetric:
    def __init__(self, row_spacing: float, length_m: float):
        self.rs, self.L = row_spacing, length_m

    def lane(self, y):
        return round(y / self.rs)          # lanes sit on row boundaries 0, rs, 2rs, ...

    def __call__(self, a, b):
        la, lb = self.lane(a[1]), self.lane(b[1])
        if la == lb:
            return abs(a[0] - b[0])
        dy = abs(la - lb) * self.rs
        via_left = a[0] + b[0] + 2.0
        via_right = (self.L - a[0]) + (self.L - b[0]) + 2.0
        return dy + min(via_left, via_right)


def tsp_tour(points, start, metric=None, two_opt_iters: int = 2):
    """Nearest-neighbour seed + bounded 2-opt. points: list of (x, y). Returns order, length."""
    metric = metric or (lambda a, b: math.hypot(a[0] - b[0], a[1] - b[1]))
    if not points:
        return [], 0.0
    remaining = set(range(len(points)))
    order, cur = [], start
    # bucket by lane to keep NN O(n * lane_size) for large target sets
    while remaining:
        j = min(remaining, key=lambda k: metric(cur, points[k]))
        order.append(j)
        remaining.remove(j)
        cur = points[j]
    if len(order) <= 400:
        for _ in range(two_opt_iters):
            improved = False
            for i in range(1, len(order) - 2):
                for k in range(i + 1, min(len(order) - 1, i + 60)):
                    a, b = points[order[i - 1]], points[order[i]]
                    c, d = points[order[k]], points[order[k + 1]]
                    if metric(a, c) + metric(b, d) < metric(a, b) + metric(c, d) - 1e-9:
                        order[i:k + 1] = reversed(order[i:k + 1])
                        improved = True
            if not improved:
                break
    length, cur = 0.0, start
    for j in order:
        length += metric(cur, points[j])
        cur = points[j]
    return order, length
